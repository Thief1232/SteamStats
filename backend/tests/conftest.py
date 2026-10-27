import os

import httpx
import pytest

# steam_client reads the key at import time, so it has to be set before any
# test module imports it.
os.environ.setdefault("STEAM_API_KEY", "test-key")

_RealAsyncClient = httpx.AsyncClient


@pytest.fixture
def mock_http(monkeypatch):
    """Route every httpx.AsyncClient request to a handler instead of the network.

    Usage: requests = mock_http(lambda request: httpx.Response(200, json=...))
    Returns the list of requests that were made.
    """

    def install(handler):
        requests: list[httpx.Request] = []

        def recording_handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return handler(request)

        transport = httpx.MockTransport(recording_handler)

        def client_factory(*args, **kwargs):
            kwargs["transport"] = transport
            return _RealAsyncClient(*args, **kwargs)

        monkeypatch.setattr(httpx, "AsyncClient", client_factory)
        return requests

    return install
