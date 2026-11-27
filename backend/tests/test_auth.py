import asyncio

import pytest

from src.services import auth
from src.services.steam_client import (
    OPENID_NS,
    STEAM_OPENID_URL,
    validate_openid_response,
)

RETURN_TO = "http://localhost:8000/auth/steam/callback"
CLAIMED = "https://steamcommunity.com/openid/id/76561197960287930"


def valid_params() -> dict:
    return {
        "openid.ns": OPENID_NS,
        "openid.mode": "id_res",
        "openid.op_endpoint": STEAM_OPENID_URL,
        "openid.claimed_id": CLAIMED,
        "openid.identity": CLAIMED,
        "openid.return_to": RETURN_TO,
        "openid.response_nonce": "2026-10-27T12:00:00Zabc",
        "openid.assoc_handle": "1234567890",
        "openid.signed": "signed,op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle",
        "openid.sig": "c2ln",
    }


def test_valid_response_is_accepted():
    assert validate_openid_response(valid_params(), RETURN_TO)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("openid.return_to", "https://evil.example.com/auth/steam/callback"),
        ("openid.return_to", RETURN_TO + "?x=1"),
        ("openid.mode", "cancel"),
        ("openid.mode", "check_authentication"),
        ("openid.ns", "http://specs.openid.net/auth/1.1"),
        ("openid.op_endpoint", "https://evil.example.com/openid/login"),
        ("openid.identity", "https://steamcommunity.com/openid/id/76561197960287931"),
    ],
)
def test_response_with_a_wrong_field_is_rejected(key, value):
    params = valid_params()
    params[key] = value

    assert not validate_openid_response(params, RETURN_TO)


@pytest.mark.parametrize(
    "missing", ["return_to", "claimed_id", "identity", "op_endpoint", "response_nonce"]
)
def test_response_that_does_not_sign_a_required_field_is_rejected(missing):
    params = valid_params()
    signed = params["openid.signed"].split(",")
    params["openid.signed"] = ",".join(f for f in signed if f != missing)

    assert not validate_openid_response(params, RETURN_TO)


@pytest.mark.parametrize("missing", ["openid.return_to", "openid.signed", "openid.mode"])
def test_response_with_a_missing_field_is_rejected(missing):
    params = valid_params()
    del params[missing]

    assert not validate_openid_response(params, RETURN_TO)


def test_handle_callback_does_not_call_steam_for_a_foreign_return_to(monkeypatch):
    async def must_not_be_called(params):
        raise AssertionError("Steam must not be asked to verify a foreign assertion")

    monkeypatch.setattr(auth, "verify_openid", must_not_be_called)
    params = valid_params()
    params["openid.return_to"] = "https://evil.example.com/auth/steam/callback"

    assert asyncio.run(auth.handle_callback(None, params, RETURN_TO)) is None


def test_handle_callback_rejects_when_steam_says_invalid(monkeypatch):
    async def invalid(params):
        return False

    monkeypatch.setattr(auth, "verify_openid", invalid)

    assert asyncio.run(auth.handle_callback(None, valid_params(), RETURN_TO)) is None


# --- sessions and first sign-in ----------------------------------------------------


def test_session_key_is_a_sha256_hex_of_the_token():
    from src.db.queries import session_key

    key = session_key("token-from-cookie")

    assert len(key) == 64 and key != "token-from-cookie"
    assert key == session_key("token-from-cookie")  # lookups find what create stored
    assert key != session_key("another-token")


class _Account:
    def __init__(self, user_id):
        self.user_id = user_id
        self.persona_name = "Gabe"


class _Session:
    async def commit(self):
        pass


def _signed_in_callback(monkeypatch, locked_account):
    """Run handle_callback past Steam's checks; returns the queries that were called."""
    calls: list[str] = []

    async def valid(params):
        return True

    async def profile(session, lookup):
        return _Account(user_id=None)  # what the cache said before taking the lock

    async def lock(session, steam_id):
        calls.append("lock")
        return locked_account

    async def create_user(session, name):
        calls.append("create_user")

        class U:
            id = 99

        return U()

    async def record(*args, **kwargs):
        calls.append("write")

    monkeypatch.setattr(auth, "verify_openid", valid)
    monkeypatch.setattr(auth, "get_or_refresh_profile", profile)
    monkeypatch.setattr(auth.queries, "lock_steam_account", lock)
    monkeypatch.setattr(auth.queries, "create_user", create_user)
    monkeypatch.setattr(auth.queries, "link_steam_account", record)
    monkeypatch.setattr(auth.queries, "create_session", record)
    result = asyncio.run(auth.handle_callback(_Session(), valid_params(), RETURN_TO))
    return calls, result


def test_first_sign_in_creates_a_user_under_the_lock(monkeypatch):
    calls, result = _signed_in_callback(monkeypatch, _Account(user_id=None))

    assert calls[:2] == ["lock", "create_user"]
    assert result[1] == 76561197960287930


def test_sign_in_racing_another_one_reuses_the_user_it_created(monkeypatch):
    # The cached account said "no user", but after the lock another callback has
    # already linked one: no second user may be created.
    calls, _ = _signed_in_callback(monkeypatch, _Account(user_id=7))

    assert "create_user" not in calls
