"""Tests for app.core.security — hashing, JWT creation and decoding."""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_api_key,
    verify_api_key,
)


# ---------------------------------------------------------------------------
# API key hashing
# ---------------------------------------------------------------------------


def test_hash_api_key_returns_string():
    """hash_api_key returns a non-empty string."""
    result = hash_api_key("my-secret-key")
    assert isinstance(result, str)
    assert len(result) > 0


def test_hash_api_key_different_inputs_different_hashes():
    """Different keys produce different hashes (collision resistance)."""
    h1 = hash_api_key("key-alpha")
    h2 = hash_api_key("key-beta")
    assert h1 != h2


def test_hash_api_key_same_input_different_hashes():
    """Argon2 includes a random salt so the same key hashes differently each time."""
    h1 = hash_api_key("same-key")
    h2 = hash_api_key("same-key")
    # With Argon2 the two hashes should differ (different salts)
    assert h1 != h2


# ---------------------------------------------------------------------------
# API key verification
# ---------------------------------------------------------------------------


def test_verify_api_key_correct():
    """verify_api_key returns True when the plain key matches the stored hash."""
    key = "correct-horse-battery-staple"
    hashed = hash_api_key(key)
    assert verify_api_key(key, hashed) is True


def test_verify_api_key_incorrect():
    """verify_api_key returns False for the wrong plain-text key."""
    key = "correct-key"
    wrong = "wrong-key"
    hashed = hash_api_key(key)
    assert verify_api_key(wrong, hashed) is False


def test_verify_api_key_garbage_hash():
    """verify_api_key returns False when the stored hash is garbage."""
    assert verify_api_key("some-key", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# JWT creation
# ---------------------------------------------------------------------------


def test_create_access_token_returns_string():
    """create_access_token returns a non-empty JWT string."""
    token = create_access_token({"sub": "user-123"})
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_access_token_has_three_parts():
    """A well-formed JWT consists of exactly three dot-separated segments."""
    token = create_access_token({"sub": "user-123"})
    parts = token.split(".")
    assert len(parts) == 3


def test_create_access_token_custom_expiry():
    """create_access_token accepts a custom expiry delta without raising."""
    token = create_access_token({"sub": "user-abc"}, expires_delta=timedelta(hours=2))
    assert isinstance(token, str)
    assert len(token.split(".")) == 3


# ---------------------------------------------------------------------------
# JWT decoding
# ---------------------------------------------------------------------------


def test_decode_access_token_valid():
    """decode_access_token returns the original claims for a freshly minted token."""
    payload = {"sub": "user-xyz", "role": "admin"}
    token = create_access_token(payload)
    claims = decode_access_token(token)
    assert claims is not None
    assert claims["sub"] == "user-xyz"
    assert claims["role"] == "admin"
    assert "exp" in claims


def test_decode_access_token_expired():
    """decode_access_token returns None for a token that expired immediately."""
    token = create_access_token({"sub": "user-expired"}, expires_delta=timedelta(seconds=-1))
    result = decode_access_token(token)
    assert result is None


def test_decode_access_token_invalid_garbage():
    """decode_access_token returns None for a random garbage string."""
    result = decode_access_token("this.is.garbage")
    assert result is None


def test_decode_access_token_invalid_empty():
    """decode_access_token returns None for an empty string."""
    result = decode_access_token("")
    assert result is None


def test_decode_access_token_wrong_segments():
    """decode_access_token returns None for a string that isn't a JWT."""
    result = decode_access_token("not-a-jwt-at-all")
    assert result is None
