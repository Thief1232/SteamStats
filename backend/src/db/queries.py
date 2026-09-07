from datetime import datetime
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import SteamAccount

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