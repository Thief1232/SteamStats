from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.connection import get_session
from src.schemas.schemas import GameSearchResult, GameStatsResponse
from src.services.stats import get_or_refresh_stats, parse_owners
from src.services.steam_search import search_games
from src.services.steamspy_client import fetch_top_games

router = APIRouter()


@router.get("/api/games/search", response_model=list[GameSearchResult])
async def search_games_route(q: str):
    if not q.strip():
        return []
    return await search_games(q)


@router.get("/api/games/top", response_model=list[GameStatsResponse])
async def get_top_games():
    games = await fetch_top_games()
    result = []
    for g in games:
        owners_min, owners_max = parse_owners(g["owners"])
        result.append(
            GameStatsResponse(
                app_id=g["appid"],
                name=g["name"],
                owners_min=owners_min,
                owners_max=owners_max,
                average_playtime_forever=g.get("average_forever"),
                median_playtime_forever=g.get("median_forever"),
                ccu=g.get("ccu"),
                positive=g.get("positive"),
                negative=g.get("negative"),
            )
        )
    return result


@router.get("/api/games/{app_id}", response_model=GameStatsResponse)
async def get_game_stats(app_id: int, session: AsyncSession = Depends(get_session)):
    stats = await get_or_refresh_stats(session, app_id)
    if stats is None:
        raise HTTPException(404)
    return GameStatsResponse.from_row(stats)