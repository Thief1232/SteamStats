import httpx
import pytest

from src.services import http, stats, steamspy_client

_RealAsyncClient = httpx.AsyncClient


def _refuse_network(request: httpx.Request) -> httpx.Response:
    raise RuntimeError(
        f"test tried to reach the network: {request.method} {request.url.host}{request.url.path}"
        " (use the mock_http fixture or patch the fetch function)"
    )


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests never talk to Steam: a request nobody mocked fails loudly instead of
    going out from the developer's IP (Steam blocks IPs that send bursts)."""
    monkeypatch.setattr(http, "_http", _RealAsyncClient(transport=httpx.MockTransport(_refuse_network)))


@pytest.fixture(autouse=True)
def no_pacing_no_cache(monkeypatch):
    """Tests neither wait for SteamSPY's 1 req/s pacing nor share the top-games cache."""
    monkeypatch.setattr(steamspy_client, "MIN_INTERVAL", 0.0)
    monkeypatch.setattr(steamspy_client, "_next_slot", 0.0)
    monkeypatch.setattr(stats, "_top_games", None)


@pytest.fixture
def mock_http(monkeypatch):
    """Route every outgoing request to a handler instead of the network.

    Usage: requests = mock_http(lambda request: httpx.Response(200, json=...))
    Returns the list of requests that were made.
    """

    def install(handler):
        requests: list[httpx.Request] = []

        def recording_handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return handler(request)

        transport = httpx.MockTransport(recording_handler)
        monkeypatch.setattr(http, "_http", _RealAsyncClient(transport=transport))
        return requests

    return install
