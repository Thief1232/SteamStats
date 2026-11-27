import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.profile import get_or_refresh_profile
from src.services.steam_client import (
    extract_steam_id,
    validate_openid_response,
    verify_openid,
)

log = logging.getLogger(__name__)

SESSION_TTL = timedelta(days=30)


async def handle_callback(
    session: AsyncSession, params: dict, return_to: str
) -> tuple[str, int] | None:
    if not validate_openid_response(params, return_to):
        # Most often a wrong APP_URL: Steam sends the user back to a return_to
        # that does not match ours.
        log.warning(
            "Steam sign-in rejected: return_to %r, expected %r",
            params.get("openid.return_to"), return_to,
        )
        return None

    if not await verify_openid(params):
        log.warning("Steam sign-in rejected: Steam did not confirm the signature")
        return None

    steam_id = extract_steam_id(params.get("openid.claimed_id", ""))
    if steam_id is None:
        return None

    account = await get_or_refresh_profile(session, str(steam_id))
    if account is None:
        return None

    # Two callbacks of the same new user (double click, two tabs) must not both create
    # a user: lock the row and decide on what it says now.
    account = await queries.lock_steam_account(session, steam_id)
    if account.user_id is None:
        user = await queries.create_user(session, account.persona_name)
        await queries.link_steam_account(session, steam_id, user.id)
        user_id = user.id
    else:
        user_id = account.user_id

    session_id = secrets.token_urlsafe(32)  # goes to the cookie; the DB keeps its hash
    await queries.create_session(
        session, session_id, user_id, datetime.now(timezone.utc) + SESSION_TTL
    )
    await session.commit()
    log.info("user %s signed in as steam_id %s", user_id, steam_id)
    return session_id, steam_id