import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from src.services import steam_search, steamspy_client
from src.services.cache import TTL, is_stale
from src.services.stats import parse_owners


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0 .. 20,000", (0, 20_000)),
        ("1,000,000 .. 2,000,000", (1_000_000, 2_000_000)),
        ("50,000,000 .. 100,000,000", (50_000_000, 100_000_000)),
    ],
)
def test_parse_owners(raw, expected):
    assert parse_owners(raw) == expected


def test_cache_ttl():
    now = datetime.now(timezone.utc)
    assert not is_stale(now - TTL + timedelta(minutes=1))
    assert is_stale(now - TTL - timedelta(minutes=1))


def test_fetch_all_stats_returns_data(mock_http):
    payload = {"appid": 730, "name": "Counter-Strike 2", "owners": "0 .. 20,000"}
    requests = mock_http(lambda r: httpx.Response(200, json=payload))

    assert run(steamspy_client.fetch_all_stats(730)) == payload
    assert requests[0].url.params["request"] == "appdetails"
    assert requests[0].url.params["appid"] == "730"


def test_fetch_all_stats_unknown_app_returns_none(mock_http):
    # SteamSPY answers unknown app ids with an object whose name is empty.
    mock_http(lambda r: httpx.Response(200, json={"appid": 999999999, "name": ""}))

    assert run(steamspy_client.fetch_all_stats(999999999)) is None


def test_fetch_top_games_returns_list(mock_http):
    payload = {
        "730": {"appid": 730, "name": "Counter-Strike 2"},
        "570": {"appid": 570, "name": "Dota 2"},
    }
    mock_http(lambda r: httpx.Response(200, json=payload))

    games = run(steamspy_client.fetch_top_games())

    assert [g["appid"] for g in games] == [730, 570]


def test_fetch_top_games_raises_on_http_error(mock_http):
    mock_http(lambda r: httpx.Response(503))

    with pytest.raises(httpx.HTTPStatusError):
        run(steamspy_client.fetch_top_games())


def test_search_games_maps_store_results(mock_http):
    requests = mock_http(
        lambda r: httpx.Response(
            200,
            json={"total": 1, "items": [{"id": 730, "name": "Counter-Strike 2", "type": "app"}]},
        )
    )

    assert run(steam_search.search_games("counter")) == [
        {"app_id": 730, "name": "Counter-Strike 2"}
    ]
    assert requests[0].url.params["term"] == "counter"


def test_search_games_no_items(mock_http):
    mock_http(lambda r: httpx.Response(200, json={"total": 0}))

    assert run(steam_search.search_games("zzzz")) == []
