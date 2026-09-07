from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SteamAccount, OwnedGame, Game

async def get_steam_account(session: AsyncSession, steam_id: int) -> SteamAccount | None:
    return await session.get(SteamAccount, steam_id)

async def upsert_steam_account(
    session: AsyncSession, steam_id: int, persona_name: str, avatar_url: str | None,
    profile_url: str, account_created: datetime | None, visibility: str,
) -> SteamAccount:
    stmt = insert(SteamAccount).values(
        steam_id=steam_id,
        persona_name=persona_name,
        avatar_url=avatar_url,
        profile_url=profile_url,
        account_created=account_created,
        visibility=visibility,
        last_fetched_at=func.now(),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[SteamAccount.steam_id],
        set_={
            "persona_name": stmt.excluded.persona_name,
            "avatar_url": stmt.excluded.avatar_url,
            "profile_url": stmt.excluded.profile_url,
            "visibility": stmt.excluded.visibility,
            "last_fetched_at": func.now(),
        },
    ).returning(SteamAccount)
    result = await session.execute(stmt)
    await session.commit()
    return result.scalar_one()


async def get_library_last_fetch(session: AsyncSession, steam_id: int) -> datetime | None:
    result = await session.execute(
        select(func.max(OwnedGame.last_fetched_at)).where(OwnedGame.steam_id == steam_id)
    )
    return result.scalar_one_or_none()


async def upsert_games(session: AsyncSession, games: list[dict]) -> None:
    if not games:
        return
    stmt = insert(Game).values(games)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Game.app_id],
        set_={"name": stmt.excluded.name, "icon_url": stmt.excluded.icon_url},
    )
    await session.execute(stmt)


async def upsert_owned_games(session: AsyncSession, rows: list[dict]) -> None:
    if not rows:
        return
    stmt = insert(OwnedGame).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[OwnedGame.steam_id, OwnedGame.app_id],
        set_={
            "playtime_minutes": stmt.excluded.playtime_minutes,
            "playtime_2weeks_minutes": stmt.excluded.playtime_2weeks_minutes,
            "last_played": stmt.excluded.last_played,
            "achievements_unlocked": stmt.excluded.achievements_unlocked,
            "achievements_total": stmt.excluded.achievements_total,
            "last_fetched_at": stmt.excluded.last_fetched_at,
        },
    )
    await session.execute(stmt)

async def get_library(session: AsyncSession, steam_id: int) -> list:
    result = await session.execute(
        select(OwnedGame, Game)
        .join(Game, OwnedGame.app_id == Game.app_id)
        .where(OwnedGame.steam_id == steam_id)
    )
    return result.all()