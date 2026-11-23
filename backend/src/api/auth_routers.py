import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.schemas.schemas import Me
from src.db.connection import get_session
from src.services.auth import SESSION_TTL, handle_callback
from src.services.steam_client import steam_login_url

router = APIRouter()

SESSION_COOKIE = "session_id"


def _app_url() -> str:
    return os.environ["APP_URL"].rstrip("/")


def _callback_url() -> str:
    return f"{_app_url()}/auth/steam/callback"


@router.get("/auth/steam/login")
async def steam_login():
    url = steam_login_url(_callback_url(), _app_url())
    return RedirectResponse(url)


@router.get("/auth/steam/callback")
async def steam_callback(request: Request, session: AsyncSession = Depends(get_session)):
    result = await handle_callback(session, dict(request.query_params), _callback_url())
    if result is None:
        raise HTTPException(400)
    session_id, steam_id = result

    # Relative: the frontend is on the same origin as this callback.
    response = RedirectResponse(f"/u/{steam_id}")
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        # The app itself sees plain HTTP behind the proxy, so go by the public URL.
        secure=_app_url().startswith("https://"),
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
    )
    return response


@router.get("/api/me", response_model=Me)
async def get_me(
    session_id: str | None = Cookie(None, alias=SESSION_COOKIE),
    session: AsyncSession = Depends(get_session),
):
    if session_id is None:
        raise HTTPException(401)
    user = await queries.get_session_user(session, session_id)
    if user is None:
        raise HTTPException(401)
    account = await queries.get_steam_account_by_user(session, user.id)
    if account is None:
        raise HTTPException(401)
    return Me.from_rows(user, account)


@router.post("/api/auth/logout", status_code=204)
async def logout(
    session_id: str | None = Cookie(None, alias=SESSION_COOKIE),
    session: AsyncSession = Depends(get_session),
):
    if session_id is not None:
        await queries.delete_session(session, session_id)
        await session.commit()
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE)
    return response