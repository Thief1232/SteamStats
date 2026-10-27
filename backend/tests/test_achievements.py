import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import routers
from src.db.connection import get_session
from src.services import library
from src.services.cache import TTL

STEAM_ID = 76561197960287930


def run(coro):
    return asyncio.run(coro)


class FakeSession:
    def __init__(self):
        self.commits = 0

    async def commit(self):
        self.commits += 1


class FakeDb:
    """Stands in for src.db.queries: only what refresh_achievements touches."""

    def __init__(self, app_ids, last_fetch=None):
        self.app_ids = app_ids
        self.last_fetch = last_fetch
        self.updates: list[list[dict]] = []

    async def get_achievements_last_fetch(self, session, steam_id):
        return self.last_fetch

    async def get_owned_app_ids(self, session, steam_id):
        return self.app_ids

    async def update_achievements(self, session, steam_id, rows):
        self.updates.append(rows)


@pytest.fixture
def db(monkeypatch):
    fake = FakeDb(app_ids=[10, 20, 30])
    monkeypatch.setattr(library.queries, "get_achievements_last_fetch", fake.get_achievements_last_fetch)
    monkeypatch.setattr(library.queries, "get_owned_app_ids", fake.get_owned_app_ids)
    monkeypatch.setattr(library.queries, "update_achievements", fake.update_achievements)
    return fake


@pytest.fixture(autouse=True)
def clean_progress():
    library._achievements_progress.clear()
    yield
    library._achievements_progress.clear()


def patch_steam(monkeypatch, results):
    """results: app_id -> (unlocked, total) | None | Exception. Returns the call log."""
    calls: list[int] = []

    async def fake_fetch(steam_id, app_id):
        calls.append(app_id)
        result = results[app_id]
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(library, "fetch_achievements", fake_fetch)
    return calls


# --- TTL -----------------------------------------------------------------------


def test_fresh_data_does_not_hit_steam(db, monkeypatch):
    db.last_fetch = datetime.now(timezone.utc) - TTL + timedelta(minutes=1)
    calls = patch_steam(monkeypatch, {})
    session = FakeSession()

    run(library.refresh_achievements(session, STEAM_ID))

    assert calls == []
    assert db.updates == []
    assert session.commits == 0
    assert STEAM_ID not in library._achievements_progress


def test_stale_data_is_refetched(db, monkeypatch):
    db.last_fetch = datetime.now(timezone.utc) - TTL - timedelta(minutes=1)
    calls = patch_steam(monkeypatch, {10: (1, 2), 20: (0, 5), 30: (4, 4)})
    session = FakeSession()

    run(library.refresh_achievements(session, STEAM_ID))

    assert sorted(calls) == [10, 20, 30]
    assert session.commits == 1


def test_never_fetched_is_refetched(db, monkeypatch):
    db.last_fetch = None
    calls = patch_steam(monkeypatch, {10: (1, 2), 20: (0, 5), 30: (4, 4)})

    run(library.refresh_achievements(FakeSession(), STEAM_ID))

    assert sorted(calls) == [10, 20, 30]


# --- results -------------------------------------------------------------------


def test_rows_are_written_and_failed_games_skipped(db, monkeypatch):
    # None = game without achievements or a transient Steam error. Writing it would
    # overwrite previously stored counts, so such games must be left alone.
    patch_steam(monkeypatch, {10: (1, 2), 20: None, 30: (4, 4)})

    run(library.refresh_achievements(FakeSession(), STEAM_ID))

    (rows,) = db.updates
    assert sorted(rows, key=lambda r: r["app_id"]) == [
        {"app_id": 10, "achievements_unlocked": 1, "achievements_total": 2},
        {"app_id": 30, "achievements_unlocked": 4, "achievements_total": 4},
    ]


def test_progress_is_reported_and_cleared(db, monkeypatch):
    seen: list[tuple[int, int] | None] = []

    async def fake_fetch(steam_id, app_id):
        seen.append(library.get_achievements_progress(steam_id))
        return (1, 1)

    monkeypatch.setattr(library, "fetch_achievements", fake_fetch)

    run(library.refresh_achievements(FakeSession(), STEAM_ID))

    assert all(p is not None and p[1] == 3 for p in seen)
    assert library.get_achievements_progress(STEAM_ID) is None


# --- one refresh per steam_id ----------------------------------------------------


def test_second_concurrent_refresh_is_rejected(db, monkeypatch):
    release = asyncio.Event()
    calls: list[int] = []

    async def slow_fetch(steam_id, app_id):
        calls.append(app_id)
        await release.wait()
        return (1, 1)

    monkeypatch.setattr(library, "fetch_achievements", slow_fetch)

    async def scenario():
        first = asyncio.create_task(library.refresh_achievements(FakeSession(), STEAM_ID))
        await asyncio.sleep(0)  # let it take the slot and start fetching
        await asyncio.sleep(0)

        with pytest.raises(library.AchievementsRefreshInProgress):
            await library.refresh_achievements(FakeSession(), STEAM_ID)

        # The rejected call must not clear the first one's progress.
        assert library.get_achievements_progress(STEAM_ID) is not None

        release.set()
        await first

    # The timeout turns a missing guard into a failure instead of a hang.
    run(asyncio.wait_for(scenario(), timeout=5))

    assert sorted(calls) == [10, 20, 30]  # Steam was queried once per game, not twice
    assert library.get_achievements_progress(STEAM_ID) is None


def test_different_users_do_not_block_each_other(db, monkeypatch):
    patch_steam(monkeypatch, {10: (1, 1), 20: (1, 1), 30: (1, 1)})

    async def scenario():
        await asyncio.gather(
            library.refresh_achievements(FakeSession(), STEAM_ID),
            library.refresh_achievements(FakeSession(), STEAM_ID + 1),
        )

    run(scenario())

    assert len(db.updates) == 2


def test_slot_is_released_after_steam_error(db, monkeypatch):
    patch_steam(monkeypatch, {10: (1, 1), 20: RuntimeError("boom"), 30: (1, 1)})

    with pytest.raises(RuntimeError):
        run(library.refresh_achievements(FakeSession(), STEAM_ID))

    assert library.get_achievements_progress(STEAM_ID) is None
    assert db.updates == []  # a half-finished run writes nothing

    # ...and the next attempt is allowed.
    patch_steam(monkeypatch, {10: (1, 1), 20: (1, 1), 30: (1, 1)})
    run(library.refresh_achievements(FakeSession(), STEAM_ID))
    assert len(db.updates) == 1


def test_pending_requests_are_cancelled_after_error(db, monkeypatch):
    cancelled: list[int] = []

    async def fetch(steam_id, app_id):
        if app_id == 10:
            raise RuntimeError("boom")
        try:
            await asyncio.Event().wait()  # never finishes on its own
        except asyncio.CancelledError:
            cancelled.append(app_id)
            raise

    monkeypatch.setattr(library, "fetch_achievements", fetch)

    async def scenario():
        with pytest.raises(RuntimeError):
            await library.refresh_achievements(FakeSession(), STEAM_ID)
        await asyncio.sleep(0)  # let the cancellations be delivered
        # Checked inside the loop: asyncio.run() would cancel leftovers on exit and
        # mask a missing cancel().
        assert sorted(cancelled) == [20, 30]

    run(scenario())


def test_slot_is_released_when_fresh_check_returns_early(db, monkeypatch):
    db.last_fetch = datetime.now(timezone.utc)
    patch_steam(monkeypatch, {})

    run(library.refresh_achievements(FakeSession(), STEAM_ID))
    run(library.refresh_achievements(FakeSession(), STEAM_ID))  # would raise if the slot leaked


# --- HTTP layer ------------------------------------------------------------------


class FakeAccount:
    visibility = "public"


@pytest.fixture
def client(monkeypatch):
    app = FastAPI()
    app.include_router(routers.router)

    async def fake_session():
        yield FakeSession()

    app.dependency_overrides[get_session] = fake_session

    async def fake_account(session, steam_id):
        return FakeAccount() if steam_id == STEAM_ID else None

    async def fake_library(session, steam_id):
        return []

    monkeypatch.setattr(routers.queries, "get_steam_account", fake_account)
    monkeypatch.setattr(routers.queries, "get_library", fake_library)
    return TestClient(app)


URL = f"/api/users/{STEAM_ID}/library/achievements"


def test_post_returns_409_when_refresh_in_progress(client, monkeypatch):
    async def busy(session, steam_id):
        raise library.AchievementsRefreshInProgress

    monkeypatch.setattr(routers, "refresh_achievements", busy)

    assert client.post(URL).status_code == 409


def test_post_returns_library_on_success(client, monkeypatch):
    async def ok(session, steam_id):
        return None

    monkeypatch.setattr(routers, "refresh_achievements", ok)

    resp = client.post(URL)

    assert resp.status_code == 200
    assert resp.json()["total_games"] == 0


def test_post_unknown_user_is_404(client):
    assert client.post(f"/api/users/{STEAM_ID + 1}/library/achievements").status_code == 404


def test_post_private_profile_is_403(client, monkeypatch):
    async def private(session, steam_id):
        account = FakeAccount()
        account.visibility = "private"
        return account

    monkeypatch.setattr(routers.queries, "get_steam_account", private)

    assert client.post(URL).status_code == 403


def test_progress_endpoint_defaults_to_zero(client):
    resp = client.get(f"{URL}/progress")

    assert resp.json() == {"done": 0, "total": 0}


def test_progress_endpoint_reports_running_refresh(client):
    library._achievements_progress[STEAM_ID] = (3, 10)

    assert client.get(f"{URL}/progress").json() == {"done": 3, "total": 10}
