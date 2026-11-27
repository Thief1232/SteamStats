import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import current_user
from src.db import queries
from src.db.connection import get_session
from src.db.models import User
from src.schemas.schemas import AchievementsProgress, Library, UserProfile
from src.services.library import (
    get_achievements_progress,
    AchievementsRefreshInProgress,
    get_or_refresh_library,
    refresh_achievements,
)
from src.services.profile import get_or_refresh_profile

log = logging.getLogger(__name__)

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


# Costs up to one Steam API call per game, so only signed-in users may start it
# (any of them, for any public profile). Reading stored achievements needs no sign-in.
@router.post("/api/users/{steam_id}/library/achievements", response_model=Library)
async def refresh_library_achievements(
    steam_id: int,
    user: User = Depends(current_user),
    session: AsyncSession = Depends(get_session),
):
    account = await queries.get_steam_account(session, steam_id)
    if account is None:
        raise HTTPException(404)
    if account.visibility == "private":
        raise HTTPException(403)
    log.info("achievements refresh of %s requested by user %s", steam_id, user.id)
    try:
        await refresh_achievements(session, steam_id)
    except AchievementsRefreshInProgress:
        raise HTTPException(409, "Achievements refresh already in progress") from None
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
