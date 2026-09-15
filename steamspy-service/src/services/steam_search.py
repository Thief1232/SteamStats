import httpx

# Steam's own store search — not SteamSPY. Used only to resolve a free-text
# game name to an app_id, since SteamSPY itself has no search-by-name endpoint.
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"


async def search_games(term: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            STEAM_SEARCH_URL,
            params={"term": term, "l": "english", "cc": "us"},
        )
    resp.raise_for_status()
    data = resp.json()
    return [{"app_id": item["id"], "name": item["name"]} for item in data.get("items", [])]
