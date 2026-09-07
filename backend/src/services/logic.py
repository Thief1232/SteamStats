import httpx
import asyncio
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from src.db import queries

STEAM_API_KEY = os.environ["STEAM_API_KEY"]
TTL = timedelta(hours=1)
ACHIEVEMENTS_CONCURRENCY = 10


async def _fetch_achievements_limited(sem: asyncio.Semaphore, steam_id: int, app_id: int):
    async with sem:
        return app_id, await fetch_achievements(steam_id, app_id)

async def resolve_vanity(vanity: str) -> str | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
            params={"key": STEAM_API_KEY, "vanityurl": vanity},
        )
    resp.raise_for_status()
    data = resp.json()["response"]
    if data.get("success") != 1:
        return None
    return data["steamid"]


async def fetch_player_summary(steam_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
 "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
            params={"key": STEAM_API_KEY, "steamids": steam_id},
        )
    resp.raise_for_status()
    players = resp.json()["response"]["players"]
    return players[0] if players else None


def is_steamid64(lookup: str) -> bool:
    return lookup.isdigit() and len(lookup) == 17


def _is_stale(last_fetched_at: datetime) -> bool:
    return datetime.now(timezone.utc) - last_fetched_at > TTL

async def is_library_stale(session: AsyncSession, steam_id: int) -> bool:
    last_fetched = await queries.get_library_last_fetch(session, steam_id)
    return last_fetched is None or _is_stale(last_fetched)

async def get_or_refresh_profile(session: AsyncSession, lookup: str):
    steam_id = lookup if is_steamid64(lookup) else await resolve_vanity(lookup)
    if steam_id is None:
        return None

    account = await queries.get_steam_account(session, int(steam_id))

    if account is None or _is_stale(account.last_fetched_at):
        player = await fetch_player_summary(steam_id)
        if player is not None:
            account_created = (
                datetime.fromtimestamp(player["timecreated"], tz=timezone.utc)
                if player.get("timecreated") else None
            )
            account = await queries.upsert_steam_account(
                session, int(steam_id), player["personaname"], player.get("avatarfull"),
                player["profileurl"], account_created,
                "public" if player.get("communityvisibilitystate") == 3 else "private",
            )
        elif account is None:
            return None

    return account


async def fetch_owned_games(steam_id: int) -> list[dict] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": STEAM_API_KEY,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
                "format": "json",
            },
        )
    resp.raise_for_status()
    return resp.json()["response"].get("games")

async def fetch_achievements(steam_id: int, app_id: int) -> tuple[int, int] | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/",
            params={"key": STEAM_API_KEY, "steamid": steam_id, "appid": app_id},
        )
    if resp.status_code != 200:
        return None 
    data = resp.json()["playerstats"]
    if not data.get("success") or not data.get("achievements"):
        return None
    achievements = data["achievements"]
    return sum(1 for a in achievements if a["achieved"] == 1), len(achievements)



async def get_or_refresh_library(session: AsyncSession, steam_id: int) -> bool:
    """Обновляет owned_games в БД, если кэш протух. False — если библиотека закрыта."""
    if not await is_library_stale(session, steam_id):
        return True

    games = await fetch_owned_games(steam_id)
    if games is None:
        return False 

    await queries.upsert_games(session, [
        {
            "app_id": g["appid"],
            "name": g["name"],
            "icon_url": (
                f"https://media.steampowered.com/steamcommunity/public/images/apps/{g['appid']}/{g['img_icon_url']}.jpg"
                if g.get("img_icon_url") else None
            ),
        }
        for g in games
    ])
    sem = asyncio.Semaphore(ACHIEVEMENTS_CONCURRENCY)
    results = await asyncio.gather(*(
        _fetch_achievements_limited(sem, steam_id, g["appid"])
        for g in games if g.get("has_community_visible_stats")
    ))
    achievements_by_app = dict(results)

    owned_rows = []
    for g in games:
        achievements = achievements_by_app.get(g["appid"])
        owned_rows.append({
            "steam_id": steam_id,
            "app_id": g["appid"],
            "playtime_minutes": g.get("playtime_forever", 0),
            "playtime_2weeks_minutes": g.get("playtime_2weeks", 0),
            "last_played": datetime.fromtimestamp(g["rtime_last_played"], tz=timezone.utc)
                if g.get("rtime_last_played") else None,
            "achievements_unlocked": achievements[0] if achievements else None,
            "achievements_total": achievements[1] if achievements else None,
            "last_fetched_at": datetime.now(timezone.utc),
        })
    await queries.upsert_owned_games(session, owned_rows)
    await session.commit()
    return True