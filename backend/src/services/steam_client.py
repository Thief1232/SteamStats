import os

import httpx

STEAM_API_KEY = os.environ["STEAM_API_KEY"]


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
