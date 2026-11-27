import os

import httpx
import pytest

# steam_client reads the key at import time, so it has to be set before any
# test module imports it.
os.environ.setdefault("STEAM_API_KEY", "test-key")

from src.services import steam_client  # noqa: E402

_RealAsyncClient = httpx.AsyncClient


@pytest.fixture(autouse=True)
def fresh_quota(monkeypatch):
    """A fresh, unthrottled quota per test, so tests neither wait nor share counts."""
    monkeypatch.setattr(steam_client, "quota", steam_client._Quota(daily_budget=1000, per_second=1e9))


@pytest.fixture
def mock_http(monkeypatch):
    """Route every Steam request to a handler instead of the network.

    Usage: requests = mock_http(lambda request: httpx.Response(200, json=...))
    Returns the list of requests that were made.
    """

    def install(handler):
        requests: list[httpx.Request] = []

        def recording_handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return handler(request)

        transport = httpx.MockTransport(recording_handler)
        monkeypatch.setattr(steam_client, "_http", _RealAsyncClient(transport=transport))
        return requests

    return install
