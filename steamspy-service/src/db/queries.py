from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import GameStats


async def get_game_stats(session: AsyncSession, app_id: int) -> GameStats | None:
    return await session.get(GameStats, app_id)


async def upsert_game_stats(session: AsyncSession, row: dict) -> None:
    stmt = insert(GameStats).values(row)
    stmt = stmt.on_conflict_do_update(
        index_elements=[GameStats.app_id],
        set_={
            "name": stmt.excluded.name,
            "owners_min": stmt.excluded.owners_min,
            "owners_max": stmt.excluded.owners_max,
            "average_playtime_forever": stmt.excluded.average_playtime_forever,
            "median_playtime_forever": stmt.excluded.median_playtime_forever,
            "ccu": stmt.excluded.ccu,
            "positive": stmt.excluded.positive,
            "negative": stmt.excluded.negative,
            "last_fetched_at": stmt.excluded.last_fetched_at,
        },
    )
    await session.execute(stmt)
    await session.commit()