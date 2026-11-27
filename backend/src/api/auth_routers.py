import os
import re
from urllib.parse import quote, unquote

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import SESSION_COOKIE, current_user
from src.db import queries
from src.db.connection import get_session
from src.db.models import User
from src.schemas.schemas import Me
from src.services.auth import SESSION_TTL, handle_callback
from src.services.steam_client import steam_login_url

router = APIRouter()

# Where to send the user after Steam sign-in, kept for the round trip through Steam.
NEXT_COOKIE = "login_next"
NEXT_TTL_SECONDS = 600
# Only paths on this site: "/u/123", not "//evil.com" or "https://evil.com".
SAFE_NEXT_RE = re.compile(r"^/(?![/\\])[\x21-\x7e]*$")


def _app_url() -> str:
    return os.environ["APP_URL"].rstrip("/")


def _callback_url() -> str:
    return f"{_app_url()}/auth/steam/callback"


def _secure() -> bool:
    # The app itself sees plain HTTP behind the proxy, so go by the public URL.
    return _app_url().startswith("https://")


def safe_next(value: str | None) -> str | None:
    return value if value and SAFE_NEXT_RE.match(value) else None


@router.get("/auth/steam/login")
async def steam_login(next_: str | None = Query(None, alias="next")):
    response = RedirectResponse(steam_login_url(_callback_url(), _app_url()))
    if (target := safe_next(next_)) is not None:
        # Lax: still sent when Steam redirects the browser back to the callback.
        # Percent-encoded: a raw "/" would make the cookie value a quoted string.
        response.set_cookie(
            NEXT_COOKIE, quote(target, safe=""), max_age=NEXT_TTL_SECONDS,
            httponly=True, secure=_secure(), samesite="lax",
        )
    return response


@router.get("/auth/steam/callback")
async def steam_callback(
    request: Request,
    login_next: str | None = Cookie(None, alias=NEXT_COOKIE),
    session: AsyncSession = Depends(get_session),
):
    result = await handle_callback(session, dict(request.query_params), _callback_url())
    if result is None:
        raise HTTPException(400)
    session_id, steam_id = result

    # Relative: the frontend is on the same origin as this callback.
    next_ = safe_next(unquote(login_next)) if login_next else None
    response = RedirectResponse(next_ or f"/u/{steam_id}")
    response.delete_cookie(NEXT_COOKIE)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        secure=_secure(),
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
    )
    return response


@router.get("/api/me", response_model=Me)
async def get_me(
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
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
