import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.cache import is_stale
from src.services.steam_client import (
    SteamApiError,
    SteamRateLimited,
    fetch_achievements,
    fetch_owned_games,
)

log = logging.getLogger(__name__)

ACHIEVEMENTS_CONCURRENCY = 10

# Marks a game whose achievements request failed transiently: it is left unchecked
# so the next refresh asks again.
_FAILED = object()

# steam_id -> (done, total) for an in-flight refresh_achievements() call.
# In-memory only: fine for a single-process app, purely used for progress polling.
_achievements_progress: dict[int, tuple[int, int]] = {}


class AchievementsRefreshInProgress(Exception):
    pass


def get_achievements_progress(steam_id: int) -> tuple[int, int] | None:
    return _achievements_progress.get(steam_id)


async def _fetch_achievements_limited(
    sem: asyncio.Semaphore, steam_id: int, app_id: int
):
    async with sem:
        try:
            return app_id, await fetch_achievements(steam_id, app_id)
        except SteamRateLimited:
            raise  # stops the whole refresh
        except SteamApiError as e:
            log.warning("achievements of app %s for %s: %s", app_id, steam_id, e)
            return app_id, _FAILED


async def is_library_stale(session: AsyncSession, steam_id: int) -> bool:
    last_fetched = await queries.get_library_last_fetch(session, steam_id)
    return last_fetched is None or is_stale(last_fetched)


async def get_or_refresh_library(session: AsyncSession, steam_id: int) -> bool:
    """Refresh owned_games in the DB if the cache is stale. False if the library is private."""
    if not await is_library_stale(session, steam_id):
        return True

    try:
        games = await fetch_owned_games(steam_id)
    except SteamApiError as e:
        if await queries.get_library_last_fetch(session, steam_id) is None:
            raise
        log.warning("serving cached library of %s: %s", steam_id, e)
        return True
    if games is None:
        return False

    await queries.upsert_games(
        session,
        [
            {
                "app_id": g["appid"],
                "name": g["name"],
                "icon_url": (
                    f"https://media.steampowered.com/steamcommunity/public/images/apps/{g['appid']}/{g['img_icon_url']}.jpg"
                    if g.get("img_icon_url")
                    else None
                ),
            }
            for g in games
        ],
    )

    owned_rows = []
    for g in games:
        owned_rows.append(
            {
                "steam_id": steam_id,
                "app_id": g["appid"],
                "playtime_minutes": g.get("playtime_forever", 0),
                "playtime_2weeks_minutes": g.get("playtime_2weeks", 0),
                "last_played": datetime.fromtimestamp(
                    g["rtime_last_played"], tz=timezone.utc
                )
                if g.get("rtime_last_played")
                else None,
                "last_fetched_at": datetime.now(timezone.utc),
            }
        )
    await queries.upsert_owned_games(session, owned_rows)
    await session.commit()
    log.info("library of %s refreshed: %d games", steam_id, len(games))
    return True


async def refresh_achievements(session: AsyncSession, steam_id: int) -> None:
    """Ask Steam for achievements of the games that may have changed since last time
    (see queries.get_app_ids_needing_achievements) and store them.

    A game that fails transiently is skipped and asked again next time. If Steam
    rate-limits us, the remaining requests are dropped, what was fetched is saved,
    and SteamRateLimited is raised.

    Raises AchievementsRefreshInProgress if a refresh for this steam_id is already running.
    """
    # Checking and taking the slot has no await in between, so there is no race.
    if steam_id in _achievements_progress:
        raise AchievementsRefreshInProgress
    _achievements_progress[steam_id] = (0, 0)

    tasks: list[asyncio.Task] = []
    try:
        app_ids = await queries.get_app_ids_needing_achievements(session, steam_id)
        if not app_ids:
            return
        total = len(app_ids)
        _achievements_progress[steam_id] = (0, total)

        sem = asyncio.Semaphore(ACHIEVEMENTS_CONCURRENCY)
        tasks = [
            asyncio.create_task(_fetch_achievements_limited(sem, steam_id, app_id))
            for app_id in app_ids
        ]

        rows = []
        done = 0
        failed = 0
        rate_limited = False
        for task in asyncio.as_completed(tasks):
            try:
                app_id, ach = await task
            except SteamRateLimited:
                rate_limited = True
                break
            done += 1
            _achievements_progress[steam_id] = (done, total)
            if ach is _FAILED:
                failed += 1
                continue
            rows.append(
                {
                    "app_id": app_id,
                    "achievements_unlocked": ach[0] if ach else None,
                    "achievements_total": ach[1] if ach else None,
                }
            )

        await queries.update_achievements(session, steam_id, rows)
        await session.commit()
        log.info(
            "achievements of %s: %d of %d games checked, %d failed%s",
            steam_id, len(rows), total, failed,
            ", stopped by Steam rate limit" if rate_limited else "",
        )
        if rate_limited:
            raise SteamRateLimited(f"achievements refresh for {steam_id} stopped early")
    finally:
        for task in tasks:
            task.cancel()
        _achievements_progress.pop(steam_id, None)
