import asyncio
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from src.services import steam_client


def run(coro):
    return asyncio.run(coro)


# --- pure helpers -------------------------------------------------------------


def test_extract_steam_id_from_valid_claimed_id():
    claimed = "https://steamcommunity.com/openid/id/76561197960287930"
    assert steam_client.extract_steam_id(claimed) == 76561197960287930


@pytest.mark.parametrize(
    "claimed",
    [
        "",
        "https://steamcommunity.com/openid/id/",
        "https://steamcommunity.com/openid/id/abc",
        "http://steamcommunity.com/openid/id/76561197960287930",
        "https://evil.example.com/openid/id/76561197960287930",
        "https://steamcommunity.com/openid/id/76561197960287930/extra",
    ],
)
def test_extract_steam_id_rejects_anything_else(claimed):
    assert steam_client.extract_steam_id(claimed) is None


def test_steam_login_url_contains_openid_params():
    url = steam_client.steam_login_url(
        "http://localhost:8000/auth/steam/callback", "http://localhost:8000"
    )
    parsed = urlparse(url)
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}

    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == steam_client.STEAM_OPENID_URL
    assert params["openid.mode"] == "checkid_setup"
    assert params["openid.return_to"] == "http://localhost:8000/auth/steam/callback"
    assert params["openid.realm"] == "http://localhost:8000"


# --- Steam Web API calls (network mocked) ---------------------------------------


def test_resolve_vanity_success(mock_http):
    requests = mock_http(
        lambda r: httpx.Response(
            200, json={"response": {"success": 1, "steamid": "76561197960287930"}}
        )
    )

    assert run(steam_client.resolve_vanity("gabelogannewell")) == "76561197960287930"
    assert requests[0].url.params["vanityurl"] == "gabelogannewell"
    assert requests[0].url.params["key"] == steam_client.STEAM_API_KEY


def test_resolve_vanity_not_found(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"response": {"success": 42}}))

    assert run(steam_client.resolve_vanity("nobody")) is None


def test_resolve_vanity_raises_on_http_error(mock_http):
    mock_http(lambda r: httpx.Response(500))

    with pytest.raises(steam_client.SteamApiError):
        run(steam_client.resolve_vanity("whatever"))


def test_network_error_becomes_steam_api_error(mock_http):
    def fail(request):
        raise httpx.ConnectError("no route", request=request)

    mock_http(fail)

    with pytest.raises(steam_client.SteamApiError):
        run(steam_client.fetch_player_summary("1"))


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(429),
        # What Steam's CDN sends when it blocks the IP: a 403 HTML page, not JSON.
        httpx.Response(403, text="<HTML><TITLE>Access Denied</TITLE></HTML>",
                       headers={"content-type": "text/html"}),
    ],
)
def test_throttling_is_reported_and_pauses_further_calls(mock_http, response):
    requests = mock_http(lambda r: response)

    with pytest.raises(steam_client.SteamRateLimited):
        run(steam_client.fetch_owned_games(1))
    # During the cooldown nothing more is sent to Steam.
    with pytest.raises(steam_client.SteamRateLimited):
        run(steam_client.fetch_player_summary("1"))

    assert len(requests) == 1


def test_daily_budget_stops_calls_before_they_are_made(mock_http, monkeypatch):
    requests = mock_http(lambda r: httpx.Response(200, json={"response": {"players": []}}))
    monkeypatch.setattr(steam_client, "quota", steam_client._Quota(daily_budget=2, per_second=1e9))

    run(steam_client.fetch_player_summary("1"))
    run(steam_client.fetch_player_summary("1"))
    with pytest.raises(steam_client.SteamRateLimited):
        run(steam_client.fetch_player_summary("1"))

    assert len(requests) == 2


def test_quota_spaces_out_calls():
    quota = steam_client._Quota(daily_budget=100, per_second=20)

    async def three_calls():
        start = asyncio.get_running_loop().time()
        await asyncio.gather(quota.acquire(), quota.acquire(), quota.acquire())
        return asyncio.get_running_loop().time() - start

    # Slots at 0, 50 and 100 ms: the last call waits about 0.1 s.
    assert 0.08 <= run(three_calls()) < 0.5


def test_fetch_player_summary(mock_http):
    player = {"steamid": "1", "personaname": "Gabe"}
    mock_http(lambda r: httpx.Response(200, json={"response": {"players": [player]}}))

    assert run(steam_client.fetch_player_summary("1")) == player


def test_fetch_player_summary_unknown_player(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"response": {"players": []}}))

    assert run(steam_client.fetch_player_summary("1")) is None


def test_fetch_owned_games_private_library_returns_none(mock_http):
    # Steam answers 200 with an empty "response" when the library is private.
    mock_http(lambda r: httpx.Response(200, json={"response": {}}))

    assert run(steam_client.fetch_owned_games(1)) is None


def test_fetch_owned_games_empty_public_library_returns_empty_list(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"response": {"game_count": 0}}))

    assert run(steam_client.fetch_owned_games(1)) == []


def test_fetch_owned_games_returns_games(mock_http):
    games = [{"appid": 440, "name": "Team Fortress 2"}]
    mock_http(
        lambda r: httpx.Response(200, json={"response": {"game_count": 1, "games": games}})
    )

    assert run(steam_client.fetch_owned_games(1)) == games


def test_fetch_achievements_counts_unlocked(mock_http):
    mock_http(
        lambda r: httpx.Response(
            200,
            json={
                "playerstats": {
                    "success": True,
                    "achievements": [
                        {"apiname": "a", "achieved": 1},
                        {"apiname": "b", "achieved": 0},
                        {"apiname": "c", "achieved": 1},
                    ],
                }
            },
        )
    )

    assert run(steam_client.fetch_achievements(1, 440)) == (2, 3)


def test_fetch_achievements_game_without_achievements(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"playerstats": {"success": True}}))

    assert run(steam_client.fetch_achievements(1, 440)) is None


@pytest.mark.parametrize("status", [400, 403])
def test_fetch_achievements_definite_no_answer_returns_none(mock_http, status):
    # 400: the game has no stats; 403: the owner hides game details. Both come as JSON.
    mock_http(lambda r: httpx.Response(status, json={"playerstats": {"success": False}}))

    assert run(steam_client.fetch_achievements(1, 440)) is None


def test_fetch_achievements_unexpected_400_is_not_taken_as_no_achievements(mock_http):
    mock_http(lambda r: httpx.Response(400, json={"error": "bad request"}))

    with pytest.raises(steam_client.SteamApiError):
        run(steam_client.fetch_achievements(1, 440))


def test_fetch_achievements_server_error_raises(mock_http):
    mock_http(lambda r: httpx.Response(502))

    with pytest.raises(steam_client.SteamApiError):
        run(steam_client.fetch_achievements(1, 440))


@pytest.mark.parametrize(("body", "expected"), [("ns:...\nis_valid:true\n", True),
                                                ("ns:...\nis_valid:false\n", False)])
def test_verify_openid(mock_http, body, expected):
    requests = mock_http(lambda r: httpx.Response(200, text=body))

    params = {"openid.mode": "id_res", "openid.claimed_id": "x"}
    assert run(steam_client.verify_openid(params)) is expected
    # The verification request must switch the mode, but not mutate the input.
    assert b"openid.mode=check_authentication" in requests[0].content
    assert params["openid.mode"] == "id_res"
