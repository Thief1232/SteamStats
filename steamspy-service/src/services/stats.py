import logging
import time
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.cache import is_stale
from src.services.http import UpstreamError
from src.services.steamspy_client import fetch_all_stats, fetch_top_games

log = logging.getLogger(__name__)

# SteamSPY recomputes the top once a day; an hour keeps it fresh enough.
TOP_GAMES_TTL_SECONDS = 3600
_top_games: tuple[float, list[dict]] | None = None  # (monotonic time fetched, games)


def parse_owners(raw: str) -> tuple[int, int]:
    low, high = raw.split(" .. ")
    return int(low.replace(",", "")), int(high.replace(",", ""))


async def get_or_refresh_stats(session: AsyncSession, app_id: int):
    existing = await queries.get_game_stats(session, app_id)
    if existing is not None and not is_stale(existing.last_fetched_at):
        return existing

    try:
        data = await fetch_all_stats(app_id)
    except UpstreamError as e:
        if existing is None:
            raise
        log.warning("serving cached stats of app %s: %s", app_id, e)
        return existing
    if data is None:
        log.info("SteamSPY has no data for app %s", app_id)
        return existing

    owners_min, owners_max = parse_owners(data["owners"])
    await queries.upsert_game_stats(
        session,
        {
            "app_id": app_id,
            "name": data["name"],
            "owners_min": owners_min,
            "owners_max": owners_max,
            "average_playtime_forever": data.get("average_forever"),
            "median_playtime_forever": data.get("median_forever"),
            "ccu": data.get("ccu"),
            "positive": data.get("positive"),
            "negative": data.get("negative"),
            "last_fetched_at": datetime.now(timezone.utc),
        },
    )
    return await queries.get_game_stats(session, app_id)


async def get_top_games() -> list[dict]:
    """SteamSPY's top 100, cached in memory; a stale copy is served if SteamSPY fails."""
    global _top_games
    if _top_games is not None and time.monotonic() - _top_games[0] < TOP_GAMES_TTL_SECONDS:
        return _top_games[1]
    try:
        games = await fetch_top_games()
    except UpstreamError as e:
        if _top_games is None:
            raise
        log.warning("serving cached top games: %s", e)
        return _top_games[1]
    _top_games = (time.monotonic(), games)
    log.info("top games refreshed from SteamSPY: %d games", len(games))
    return games
