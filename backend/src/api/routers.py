from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.services.logic import get_or_refresh_profile
from src.schemas.schemas import UserProfile

router = APIRouter()

@router.get("/api/users/{lookup}", response_model=UserProfile)
async def get_user(lookup: str, session: AsyncSession = Depends(get_session)):
    account = await get_or_refresh_profile(session, lookup)
    if account is None:
        raise HTTPException(404)
    return UserProfile.from_row(account)