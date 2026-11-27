import hashlib
from datetime import datetime  # noqa: I001

from sqlalchemy import Integer, bindparam, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Game, OwnedGame, Session, SteamAccount, User


async def get_steam_account(
    session: AsyncSession, steam_id: int
) -> SteamAccount | None:
    return await session.get(SteamAccount, steam_id)


async def upsert_steam_account(
    session: AsyncSession,
    steam_id: int,
    persona_name: str,
    avatar_url: str | None,
    profile_url: str,
    account_created: datetime | None,
    visibility: str,
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
    # The caller may already hold this account in the session (it checked the cache
    # first); without populate_existing that stale object would be returned as is.
    result = await session.execute(stmt, execution_options={"populate_existing": True})
    await session.commit()
    return result.scalar_one()


async def get_library_last_fetch(
    session: AsyncSession, steam_id: int
) -> datetime | None:
    result = await session.execute(
        select(func.max(OwnedGame.last_fetched_at)).where(
            OwnedGame.steam_id == steam_id
        )
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

async def get_app_ids_needing_achievements(
    session: AsyncSession, steam_id: int
) -> list[int]:
    """Games whose achievements may have changed since we last asked Steam.

    Achievements only move while a game is played, so a game is asked about once,
    and again only after it was played since then. Never-launched games are skipped:
    nothing can be unlocked there, and they are often a large share of a library.
    """
    result = await session.execute(
        select(OwnedGame.app_id).where(
            OwnedGame.steam_id == steam_id,
            OwnedGame.playtime_minutes > 0,
            or_(
                OwnedGame.achievements_fetched_at.is_(None),
                OwnedGame.last_played > OwnedGame.achievements_fetched_at,
            ),
        )
    )
    return list(result.scalars().all())


async def update_achievements(session: AsyncSession, steam_id: int, rows: list[dict]) -> None:
    """Store fetched counts and mark the games as checked.

    A row with None counts means Steam had nothing to report (no achievements, or
    hidden game details): the game is marked as checked so it is not asked about again
    until it is played, and counts stored earlier are kept.
    """
    if not rows:
        return
    stmt = (
        update(OwnedGame.__table__)
        .where(OwnedGame.steam_id == steam_id, OwnedGame.app_id == bindparam("b_app_id"))
        .values(
            achievements_unlocked=func.coalesce(
                bindparam("b_unlocked", type_=Integer), OwnedGame.achievements_unlocked
            ),
            achievements_total=func.coalesce(
                bindparam("b_total", type_=Integer), OwnedGame.achievements_total
            ),
            achievements_fetched_at=func.now(),
        )
    )
    await session.execute(
        stmt,
        [
            {
                "b_app_id": r["app_id"],
                "b_unlocked": r["achievements_unlocked"],
                "b_total": r["achievements_total"],
            }
            for r in rows
        ],
    )


async def create_user(session: AsyncSession, username: str) -> User:
    user = User(username=username, created_at=func.now())
    session.add(user)
    await session.flush()
    return user


async def link_steam_account(session: AsyncSession, steam_id: int, user_id: int) -> None:
    await session.execute(
        update(SteamAccount)
        .where(SteamAccount.steam_id == steam_id)
        .values(user_id=user_id, linked_at=func.now())
    )


def session_key(token: str) -> str:
    """Sessions are stored under the SHA-256 of the cookie token, so the database (and
    its backups) hold nothing that can be used as a cookie. The token is random and
    long, so a plain hash is enough; no salt or slow KDF is needed."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_session(
    session: AsyncSession, token: str, user_id: int, expires_at: datetime
) -> None:
    # Housekeeping: expired sessions are useless, drop them while we are here.
    await session.execute(delete(Session).where(Session.expires_at <= func.now()))
    session.add(
        Session(
            id=session_key(token), user_id=user_id, created_at=func.now(), expires_at=expires_at
        )
    )


async def get_session_user(session: AsyncSession, token: str) -> User | None:
    result = await session.execute(
        select(User)
        .join(Session, Session.user_id == User.id)
        .where(Session.id == session_key(token), Session.expires_at > func.now())
    )
    return result.scalar_one_or_none()


async def delete_session(session: AsyncSession, token: str) -> None:
    await session.execute(delete(Session).where(Session.id == session_key(token)))


async def lock_steam_account(session: AsyncSession, steam_id: int) -> SteamAccount:
    """Re-read the account with a row lock held until commit, so two sign-ins of the
    same new user cannot both decide it has no user yet."""
    result = await session.execute(
        select(SteamAccount).where(SteamAccount.steam_id == steam_id).with_for_update(),
        execution_options={"populate_existing": True},
    )
    return result.scalar_one()


async def get_steam_account_by_user(session: AsyncSession, user_id: int) -> SteamAccount | None:
    result = await session.execute(
        select(SteamAccount).where(SteamAccount.user_id == user_id)
    )
    return result.scalar_one_or_none()