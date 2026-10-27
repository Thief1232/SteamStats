from datetime import datetime, timedelta, timezone

import pytest

from src.services.cache import TTL, is_stale
from src.services.profile import is_steamid64


@pytest.mark.parametrize(
    ("lookup", "expected"),
    [
        ("76561197960287930", True),
        ("7656119796028793", False),  # 16 digits
        ("765611979602879300", False),  # 18 digits
        ("gabelogannewell", False),
        ("7656119796028793a", False),
        ("", False),
    ],
)
def test_is_steamid64(lookup, expected):
    assert is_steamid64(lookup) is expected


def test_fresh_entry_is_not_stale():
    assert not is_stale(datetime.now(timezone.utc) - TTL + timedelta(minutes=1))


def test_old_entry_is_stale():
    assert is_stale(datetime.now(timezone.utc) - TTL - timedelta(minutes=1))
