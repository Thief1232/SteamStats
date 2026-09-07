import httpx
import os
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from src.db import queries

STEAM_API_KEY = os.environ["STEAM_API_KEY"]
TTL = timedelta(hours=1)


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