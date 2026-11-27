import httpx

# One client for the whole process: reuses connections to SteamSPY and the Steam
# store instead of opening a new one per request.
_http: httpx.AsyncClient | None = None


class UpstreamError(Exception):
    """SteamSPY or the Steam store gave no usable answer. Retry later."""


def client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=10)
    return _http


async def close_client() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None


async def get_json(url: str, params: dict):
    try:
        resp = await client().get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except (httpx.HTTPError, ValueError) as e:  # ValueError: body is not JSON
        raise UpstreamError(f"{url}: {e!r}") from e
