import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.profile import get_or_refresh_profile
from src.services.steam_client import extract_steam_id, verify_openid

SESSION_TTL = timedelta(days=30)


async def handle_callback(session: AsyncSession, params: dict) -> str | None:
    if not await verify_openid(params):
        return None

    steam_id = extract_steam_id(params.get("openid.claimed_id", ""))
    if steam_id is None:
        return None

    account = await get_or_refresh_profile(session, str(steam_id))
    if account is None:
        return None

    if account.user_id is None:
        user = await queries.create_user(session, account.persona_name)
        await queries.link_steam_account(session, steam_id, user.id)
        user_id = user.id
    else:
        user_id = account.user_id

    session_id = secrets.token_urlsafe(32)
    await queries.create_session(
        session, session_id, user_id, datetime.now(timezone.utc) + SESSION_TTL
    )
    await session.commit()
    return session_id, steam_id