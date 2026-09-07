from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.db.connection import get_session
from src.schemas.schemas import Library, UserProfile
from src.services.library import get_or_refresh_library
from src.services.profile import get_or_refresh_profile

router = APIRouter()


@router.get("/api/users/{lookup}", response_model=UserProfile)
async def get_user(lookup: str, session: AsyncSession = Depends(get_session)):
    account = await get_or_refresh_profile(session, lookup)
    if account is None:
        raise HTTPException(404)
    return UserProfile.from_row(account)


@router.get("/api/users/{steam_id}/library", response_model=Library)
async def get_library(steam_id: int, session: AsyncSession = Depends(get_session)):
    account = await queries.get_steam_account(session, steam_id)
    if account is None:
        raise HTTPException(404)
    if account.visibility == "private":
        raise HTTPException(403)

    ok = await get_or_refresh_library(session, steam_id)
    if not ok:
        raise HTTPException(403)

    rows = await queries.get_library(session, steam_id)
    return Library.from_rows(rows)
