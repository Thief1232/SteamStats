from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api import auth_routers
from src.db.connection import get_session

STEAM_ID = 76561197960287930


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("APP_URL", "https://steam.example.com")
    app = FastAPI()
    app.include_router(auth_routers.router)

    async def fake_session():
        yield None

    async def signed_in(session, params, return_to):
        return "session-token", STEAM_ID

    app.dependency_overrides[get_session] = fake_session
    monkeypatch.setattr(auth_routers, "handle_callback", signed_in)
    return TestClient(app, base_url="https://steam.example.com", follow_redirects=False)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/u/76561197960287930", "/u/76561197960287930"),
        ("/games/730", "/games/730"),
        ("//evil.example.com", None),
        ("/\\evil.example.com", None),
        ("https://evil.example.com", None),
        ("u/1", None),
        ("", None),
        (None, None),
    ],
)
def test_safe_next_keeps_only_paths_on_this_site(value, expected):
    assert auth_routers.safe_next(value) == expected


def test_login_redirects_to_steam_and_remembers_next(client):
    resp = client.get("/auth/steam/login", params={"next": "/u/42"})

    assert resp.status_code == 307
    query = parse_qs(urlparse(resp.headers["location"]).query)
    assert query["openid.return_to"] == ["https://steam.example.com/auth/steam/callback"]
    assert resp.cookies.get(auth_routers.NEXT_COOKIE) == "%2Fu%2F42"


def test_login_ignores_unsafe_next(client):
    resp = client.get("/auth/steam/login", params={"next": "//evil.example.com"})

    assert auth_routers.NEXT_COOKIE not in resp.cookies


def test_callback_returns_to_remembered_page(client):
    client.cookies.set(auth_routers.NEXT_COOKIE, "%2Fu%2F42")

    resp = client.get("/auth/steam/callback")

    assert resp.headers["location"] == "/u/42"
    assert resp.cookies.get("session_id") == "session-token"


def test_callback_ignores_a_tampered_next_cookie(client):
    client.cookies.set(auth_routers.NEXT_COOKIE, "%2F%2Fevil.example.com")

    resp = client.get("/auth/steam/callback")

    assert resp.headers["location"] == f"/u/{STEAM_ID}"


def test_callback_without_next_goes_to_own_profile(client):
    resp = client.get("/auth/steam/callback")

    assert resp.headers["location"] == f"/u/{STEAM_ID}"
