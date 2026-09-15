import httpx


STEAMSPY_URL = "https://steamspy.com/api.php"


async def fetch_all_stats(app_id: int) -> dict | None:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            STEAMSPY_URL, 
            params={"request": "appdetails", "appid": app_id},
        )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("name"):
        return None
    return data


async def fetch_top_games() -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            STEAMSPY_URL,
            params={"request": "top100in2weeks"},
        )
    resp.raise_for_status()
    data = resp.json()
    return list(data.values())