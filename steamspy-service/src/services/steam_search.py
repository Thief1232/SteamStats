from src.services.http import get_json

# Steam's own store search — not SteamSPY. Used only to resolve a free-text
# game name to an app_id, since SteamSPY itself has no search-by-name endpoint.
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch/"


async def search_games(term: str) -> list[dict]:
    data = await get_json(STEAM_SEARCH_URL, {"term": term, "l": "english", "cc": "us"})
    return [{"app_id": item["id"], "name": item["name"]} for item in data.get("items", [])]
