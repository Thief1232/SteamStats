from fastapi import APIRouter, HTTPException

from src.services.logic import resolve_vanity

router = APIRouter()

def is_steamid64(lookup: str) -> bool:
    return lookup.isdigit() and len(lookup) == 17

@router.get("/api/users/{lookup}")
async def get_user(lookup: str):
    steam_id = lookup if is_steamid64(lookup) else await resolve_vanity(lookup)
    if steam_id is None:
        raise HTTPException(404)
    return {"steam_id": steam_id}