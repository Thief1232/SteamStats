import asyncio
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.cache import is_stale
from src.services.steam_client import fetch_achievements, fetch_owned_games

ACHIEVEMENTS_CONCURRENCY = 10


async def _fetch_achievements_limited(
    sem: asyncio.Semaphore, steam_id: int, app_id: int
):
    async with sem:
        return app_id, await fetch_achievements(steam_id, app_id)


async def is_library_stale(session: AsyncSession, steam_id: int) -> bool:
    last_fetched = await queries.get_library_last_fetch(session, steam_id)
    return last_fetched is None or is_stale(last_fetched)


async def get_or_refresh_library(session: AsyncSession, steam_id: int) -> bool:
    """Обновляет owned_games в БД, если кэш протух. False — если библиотека закрыта."""
    if not await is_library_stale(session, steam_id):
        return True

    games = await fetch_owned_games(steam_id)
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

    sem = asyncio.Semaphore(ACHIEVEMENTS_CONCURRENCY)
    results = await asyncio.gather(
        *(
            _fetch_achievements_limited(sem, steam_id, g["appid"])
            for g in games
            if g.get("has_community_visible_stats")
        )
    )
    achievements_by_app = dict(results)

    owned_rows = []
    for g in games:
        achievements = achievements_by_app.get(g["appid"])
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
                "achievements_unlocked": achievements[0] if achievements else None,
                "achievements_total": achievements[1] if achievements else None,
                "last_fetched_at": datetime.now(timezone.utc),
            }
        )
    await queries.upsert_owned_games(session, owned_rows)
    await session.commit()
    return True
