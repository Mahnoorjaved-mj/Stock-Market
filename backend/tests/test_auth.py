"""Unit tests for password hashing + validation."""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def test_password_validation_rules():
    from routes.auth import _validate_password
    assert _validate_password("short1!") is not None  # too short
    assert _validate_password("abcdefghij") is not None  # no digit
    assert _validate_password("abcd1234ef") is not None  # missing symbol, <14 chars
    assert _validate_password("abcd1234ef$") is None    # ok: 11 chars + symbol
    assert _validate_password("a" * 14 + "1") is None   # ok: 15 chars, has digit, length>=14 waives symbol


def test_bcrypt_roundtrip():
    from routes.auth import _hash_password, _check_password
    pw = "Correct-Horse-9-Battery"
    h = _hash_password(pw)
    assert _check_password(pw, h) is True
    assert _check_password("wrong-password", h) is False
    assert _check_password(pw, "not-a-real-hash") is False


def test_password_too_short_message():
    from routes.auth import _validate_password
    msg = _validate_password("a1!")
    assert msg is not None
    assert "10" in msg
