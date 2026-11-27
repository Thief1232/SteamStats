import asyncio
import logging
import os
import re
import time
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

STEAM_API_KEY = os.environ["STEAM_API_KEY"]

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d+)$")
OPENID_NS = "http://specs.openid.net/auth/2.0"
# Fields the OpenID 2.0 spec requires the provider to sign in a positive assertion.
REQUIRED_SIGNED_FIELDS = frozenset(
    {"op_endpoint", "claimed_id", "identity", "return_to", "response_nonce", "assoc_handle"}
)

# Steam allows about 100k Web API calls a day per key. Stay below it with a margin,
# and space calls out: in a burst Steam's CDN starts refusing the whole IP (403 HTML
# pages, even for keyless methods), not just answering 429. 100 calls at 10/s were
# enough to trigger that, so the pace is kept well below.
DAILY_BUDGET = 90_000
CALLS_PER_SECOND = 3
# After Steam throttles us, stop calling for a while instead of making the block longer.
THROTTLE_COOLDOWN_SECONDS = 300


class SteamApiError(Exception):
    """Steam gave no usable answer (network error, 5xx, unexpected status). Retry later."""


class SteamRateLimited(SteamApiError):
    """Steam throttles us (429 or a CDN 403 page), or our own daily budget is spent:
    stop calling for now."""


class _Quota:
    """Paces Web API calls and counts them against the daily budget.

    The count lives in memory, so it restarts with the process; it guards against
    runaway loops, not against an exact daily total.
    """

    def __init__(self, daily_budget: int, per_second: float):
        self.daily_budget = daily_budget
        self._interval = 1 / per_second
        self._next_slot = 0.0
        self._day = datetime.now(timezone.utc).date()
        self.used_today = 0
        self._paused_until = 0.0

    def pause(self, seconds: float) -> None:
        self._paused_until = max(self._paused_until, time.monotonic() + seconds)

    async def acquire(self) -> None:
        if time.monotonic() < self._paused_until:
            raise SteamRateLimited("Steam throttled us recently, cooling down")
        today = datetime.now(timezone.utc).date()
        if today != self._day:
            log.info(
                "Steam API calls on %s: %d of %d budget",
                self._day, self.used_today, self.daily_budget,
            )
            self._day, self.used_today = today, 0
        if self.used_today >= self.daily_budget:
            raise SteamRateLimited("daily Steam API budget is spent")
        self.used_today += 1
        if self.used_today == self.daily_budget:
            log.warning("daily Steam API budget (%d calls) is spent", self.daily_budget)

        # No await between reading and moving the slot, so concurrent callers
        # each get their own slot without a lock.
        now = time.monotonic()
        slot = max(now, self._next_slot)
        self._next_slot = slot + self._interval
        if slot > now:
            await asyncio.sleep(slot - now)


quota = _Quota(DAILY_BUDGET, CALLS_PER_SECOND)

# One client for the whole process: reuses connections (and TLS sessions) to Steam
# instead of opening a new one per call.
_http: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=10)
    return _http


async def close_client() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None


async def _call_web_api(url: str, params: dict) -> httpx.Response:
    """GET a Steam Web API method within the quota. Statuses below 500 are returned for
    the caller to interpret, except throttling (SteamRateLimited); 5xx and network
    errors raise SteamApiError."""
    await quota.acquire()
    try:
        resp = await _client().get(url, params={"key": STEAM_API_KEY, **params})
    except httpx.HTTPError as e:
        raise SteamApiError(f"{url}: {e!r}") from e
    # Real API errors are JSON; an HTML 403 is the CDN refusing this IP.
    throttled = resp.status_code == 429 or (
        resp.status_code == 403 and "json" not in resp.headers.get("content-type", "")
    )
    if throttled:
        log.warning(
            "Steam throttles us (HTTP %s on %s), pausing for %ss",
            resp.status_code, url, THROTTLE_COOLDOWN_SECONDS,
        )
        quota.pause(THROTTLE_COOLDOWN_SECONDS)
        raise SteamRateLimited(url)
    if resp.status_code >= 500:
        raise SteamApiError(f"{url}: HTTP {resp.status_code}")
    return resp


def _expect_ok(resp: httpx.Response) -> dict:
    if resp.status_code != 200:
        raise SteamApiError(f"{resp.request.url.path}: HTTP {resp.status_code}")
    return resp.json()


async def resolve_vanity(vanity: str) -> str | None:
    resp = await _call_web_api(
        "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
        {"vanityurl": vanity},
    )
    data = _expect_ok(resp)["response"]
    if data.get("success") != 1:
        return None
    return data["steamid"]


async def fetch_player_summary(steam_id: str) -> dict | None:
    resp = await _call_web_api(
        "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
        {"steamids": steam_id},
    )
    players = _expect_ok(resp)["response"]["players"]
    return players[0] if players else None


async def fetch_owned_games(steam_id: int) -> list[dict] | None:
    resp = await _call_web_api(
        "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
        {
            "steamid": steam_id,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        },
    )
    data = _expect_ok(resp)["response"]
    # A private library comes back as an empty "response"; a public one with no
    # games still carries game_count (0).
    if "games" not in data:
        return [] if "game_count" in data else None
    return data["games"]


async def fetch_achievements(steam_id: int, app_id: int) -> tuple[int, int] | None:
    """(unlocked, total), or None when Steam has a definite "nothing here": the game
    has no achievements (400 "Requested app has no stats") or the owner hides their
    game details (403). Transient failures raise SteamApiError instead."""
    resp = await _call_web_api(
        "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/",
        {"steamid": steam_id, "appid": app_id},
    )
    if resp.status_code in (400, 403):
        # Only Steam's own JSON answer is definite; anything else is retried later.
        try:
            if "playerstats" in resp.json():
                return None
        except ValueError:
            pass
        raise SteamApiError(f"GetPlayerAchievements: HTTP {resp.status_code}")
    data = _expect_ok(resp)["playerstats"]
    if not data.get("success") or not data.get("achievements"):
        return None
    achievements = data["achievements"]
    return sum(1 for a in achievements if a["achieved"] == 1), len(achievements)


def steam_login_url(return_to: str, realm: str) -> str:
    params = {
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


def validate_openid_response(params: dict, return_to: str) -> bool:
    """Check that a callback is a Steam assertion meant for this app.

    Steam's check_authentication only verifies the signature of whatever fields were
    signed; it does not know which return_to we expect, so that is checked here.
    """
    if params.get("openid.ns") != OPENID_NS:
        return False
    if params.get("openid.mode") != "id_res":
        return False
    if params.get("openid.op_endpoint") != STEAM_OPENID_URL:
        return False
    if params.get("openid.return_to") != return_to:
        return False
    if params.get("openid.claimed_id") != params.get("openid.identity"):
        return False
    # An unsigned claimed_id/return_to could be swapped without breaking the signature.
    signed = set(params.get("openid.signed", "").split(","))
    return REQUIRED_SIGNED_FIELDS <= signed


async def verify_openid(params: dict) -> bool:
    verify_params = dict(params)
    verify_params["openid.mode"] = "check_authentication"
    # Not a Web API method (no key, no quota), but the same shared client.
    try:
        resp = await _client().post(STEAM_OPENID_URL, data=verify_params)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        raise SteamApiError(f"OpenID check_authentication: {e!r}") from e
    return "is_valid:true" in resp.text


def extract_steam_id(claimed_id: str) -> int | None:
    match = CLAIMED_ID_RE.match(claimed_id)
    return int(match.group(1)) if match else None
