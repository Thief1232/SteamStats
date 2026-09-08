from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.db.connection import get_session
from src.schemas.schemas import AchievementsProgress, Library, UserProfile
from src.services.library import (
    get_achievements_progress,
    get_or_refresh_library,
    refresh_achievements,
)
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


@router.post("/api/users/{steam_id}/library/achievements", response_model=Library)
async def refresh_library_achievements(
    steam_id: int, session: AsyncSession = Depends(get_session)
):
    account = await queries.get_steam_account(session, steam_id)
    if account is None:
        raise HTTPException(404)
    if account.visibility == "private":
        raise HTTPException(403)
    await refresh_achievements(session, steam_id)
    rows = await queries.get_library(session, steam_id)
    return Library.from_rows(rows)


@router.get(
    "/api/users/{steam_id}/library/achievements/progress",
    response_model=AchievementsProgress,
)
async def get_library_achievements_progress(steam_id: int):
    progress = get_achievements_progress(steam_id)
    done, total = progress if progress is not None else (0, 0)
    return AchievementsProgress(done=done, total=total)
