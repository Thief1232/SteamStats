import os
import re
from urllib.parse import urlencode

import httpx

STEAM_API_KEY = os.environ["STEAM_API_KEY"]

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d+)$")
OPENID_NS = "http://specs.openid.net/auth/2.0"
# Fields the OpenID 2.0 spec requires the provider to sign in a positive assertion.
REQUIRED_SIGNED_FIELDS = frozenset(
    {"op_endpoint", "claimed_id", "identity", "return_to", "response_nonce", "assoc_handle"}
)


async def resolve_vanity(vanity: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
            params={"key": STEAM_API_KEY, "vanityurl": vanity},
        )
    resp.raise_for_status()
    data = resp.json()["response"]
    if data.get("success") != 1:
        return None
    return data["steamid"]


async def fetch_player_summary(steam_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": STEAM_API_KEY, "steamids": steam_id},
        )
    resp.raise_for_status()
    players = resp.json()["response"]["players"]
    return players[0] if players else None


async def fetch_owned_games(steam_id: int) -> list[dict] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": STEAM_API_KEY,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
                "format": "json",
            },
        )
    resp.raise_for_status()
    data = resp.json()["response"]
    # A private library comes back as an empty "response"; a public one with no
    # games still carries game_count (0).
    if "games" not in data:
        return [] if "game_count" in data else None
    return data["games"]


async def fetch_achievements(steam_id: int, app_id: int) -> tuple[int, int] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/",
            params={"key": STEAM_API_KEY, "steamid": steam_id, "appid": app_id},
        )
    if resp.status_code != 200:
        return None
    data = resp.json()["playerstats"]
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
    async with httpx.AsyncClient() as client:
        resp = await client.post(STEAM_OPENID_URL, data=verify_params)
    resp.raise_for_status()
    return "is_valid:true" in resp.text

def extract_steam_id(claimed_id: str) -> int | None:
    match = CLAIMED_ID_RE.match(claimed_id)
    return int(match.group(1)) if match else None