from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.db import queries
from src.services.cache import is_stale
from src.services.steam_client import fetch_player_summary, resolve_vanity


def is_steamid64(lookup: str) -> bool:
    return lookup.isdigit() and len(lookup) == 17


async def get_or_refresh_profile(session: AsyncSession, lookup: str):
    steam_id = lookup if is_steamid64(lookup) else await resolve_vanity(lookup)
    if steam_id is None:
        return None

    account = await queries.get_steam_account(session, int(steam_id))

    if account is None or is_stale(account.last_fetched_at):
        player = await fetch_player_summary(steam_id)
        if player is not None:
            account_created = (
                datetime.fromtimestamp(player["timecreated"], tz=timezone.utc)
                if player.get("timecreated")
                else None
            )
            account = await queries.upsert_steam_account(
                session,
                int(steam_id),
                player["personaname"],
                player.get("avatarfull"),
                player["profileurl"],
                account_created,
                "public" if player.get("communityvisibilitystate") == 3 else "private",
            )
        elif account is None:
            return None

    return account
