from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.cache import is_stale
from src.services.steamspy_client import fetch_all_stats


def parse_owners(raw: str) -> tuple[int, int]:
    low, high = raw.split(" .. ")
    return int(low.replace(",", "")), int(high.replace(",", ""))


async def get_or_refresh_stats(session: AsyncSession, app_id: int):
    existing = await queries.get_game_stats(session, app_id)
    if existing is not None and not is_stale(existing.last_fetched_at):
        return existing

    data = await fetch_all_stats(app_id)
    if data is None:
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