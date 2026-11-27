from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.db.connection import get_session
from src.db.models import User

SESSION_COOKIE = "session_id"


async def current_user(
    session_id: str | None = Cookie(None, alias=SESSION_COOKIE),
    session: AsyncSession = Depends(get_session),
) -> User:
    """The signed-in user, or 401. For endpoints that cost Steam API quota."""
    if session_id is None:
        raise HTTPException(401)
    user = await queries.get_session_user(session, session_id)
    if user is None:
        raise HTTPException(401)
    return user
