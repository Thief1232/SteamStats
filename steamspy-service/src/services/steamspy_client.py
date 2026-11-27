import asyncio
import time

from src.services.http import get_json

STEAMSPY_URL = "https://steamspy.com/api.php"

# SteamSPY asks for at most one request per second (see its API page).
MIN_INTERVAL = 1.0
_next_slot = 0.0


async def _wait_for_slot() -> None:
    # No await between reading and moving the slot, so concurrent callers each
    # get their own slot without a lock.
    global _next_slot
    now = time.monotonic()
    slot = max(now, _next_slot)
    _next_slot = slot + MIN_INTERVAL
    if slot > now:
        await asyncio.sleep(slot - now)


async def _get(params: dict):
    await _wait_for_slot()
    return await get_json(STEAMSPY_URL, params)


async def fetch_all_stats(app_id: int) -> dict | None:
    data = await _get({"request": "appdetails", "appid": app_id})
    if not data.get("name"):
        return None
    return data


async def fetch_top_games() -> list[dict]:
    data = await _get({"request": "top100in2weeks"})
    return list(data.values())
