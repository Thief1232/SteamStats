import asyncio

from datetime import datetime, timezone

import pytest

from src.schemas.schemas import Library
from src.services import library
from src.services.steam_client import SteamApiError


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


def test_empty_public_library_is_not_reported_as_private(monkeypatch):
    async def no_cache(session, steam_id):
        return None

    async def empty(steam_id):
        return []

    async def only_empty(session, rows):
        assert rows == []  # queries skips the write itself when given nothing

    monkeypatch.setattr(library.queries, "get_library_last_fetch", no_cache)
    monkeypatch.setattr(library, "fetch_owned_games", empty)
    monkeypatch.setattr(library.queries, "upsert_games", only_empty)
    monkeypatch.setattr(library.queries, "upsert_owned_games", only_empty)

    assert asyncio.run(library.get_or_refresh_library(FakeSession(), 1)) is True


def test_private_library_is_reported_as_private(monkeypatch):
    async def no_cache(session, steam_id):
        return None

    async def private(steam_id):
        return None

    monkeypatch.setattr(library.queries, "get_library_last_fetch", no_cache)
    monkeypatch.setattr(library, "fetch_owned_games", private)

    assert asyncio.run(library.get_or_refresh_library(FakeSession(), 1)) is False


def _steam_down(steam_id):
    raise SteamApiError("502")


def test_steam_failure_falls_back_to_cached_library(monkeypatch):
    async def cached_long_ago(session, steam_id):
        return datetime(2020, 1, 1, tzinfo=timezone.utc)

    async def down(steam_id):
        _steam_down(steam_id)

    monkeypatch.setattr(library.queries, "get_library_last_fetch", cached_long_ago)
    monkeypatch.setattr(library, "fetch_owned_games", down)

    assert asyncio.run(library.get_or_refresh_library(FakeSession(), 1)) is True


def test_steam_failure_without_cache_propagates(monkeypatch):
    async def no_cache(session, steam_id):
        return None

    async def down(steam_id):
        _steam_down(steam_id)

    monkeypatch.setattr(library.queries, "get_library_last_fetch", no_cache)
    monkeypatch.setattr(library, "fetch_owned_games", down)

    with pytest.raises(SteamApiError):
        asyncio.run(library.get_or_refresh_library(FakeSession(), 1))


def test_library_response_for_no_games():
    lib = Library.from_rows([])

    assert (lib.total_games, lib.played_count, lib.never_played_count) == (0, 0, 0)
    assert lib.games == [] and lib.recent == []
