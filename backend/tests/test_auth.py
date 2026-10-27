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
