import httpx
import os

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

