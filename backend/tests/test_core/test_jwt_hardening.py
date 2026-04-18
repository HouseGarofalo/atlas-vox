"""P1-11 regression: JWT decode must reject expired, tampered, and claim-missing tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt as pyjwt
import pytest

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)


class TestAccessTokenHardening:
    def test_valid_access_token_round_trips(self):
        token = create_access_token({"sub": "user-1"})
        claims = decode_access_token(token)
        assert claims is not None
        assert claims["sub"] == "user-1"

    def test_expired_access_token_rejected(self):
        token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(seconds=-60))
        assert decode_access_token(token) is None

    def test_tampered_access_token_rejected(self):
        token = create_access_token({"sub": "user-1"})
        # Flip last char to break the signature.
        tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
        assert decode_access_token(tampered) is None

    def test_access_token_without_exp_rejected(self):
        # Mint a token manually with no `exp` — should be rejected by
        # the explicit ``require=["exp", ...]`` option.
        now = datetime.now(UTC)
        payload = {"sub": "user-1", "iat": now, "iss": "atlas-vox", "type": "access"}
        token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        assert decode_access_token(token) is None

    def test_access_token_with_wrong_issuer_rejected(self):
        now = datetime.now(UTC)
        payload = {
            "sub": "user-1",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "iss": "not-atlas-vox",
            "type": "access",
        }
        token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        assert decode_access_token(token) is None

    def test_refresh_token_passed_to_access_decoder_rejected(self):
        refresh = create_refresh_token({"sub": "user-1"})
        # type=refresh → access decoder must reject.
        assert decode_access_token(refresh) is None


class TestRefreshTokenHardening:
    def test_valid_refresh_token_round_trips(self):
        token = create_refresh_token({"sub": "user-1"})
        claims = decode_refresh_token(token)
        assert claims is not None
        assert claims["sub"] == "user-1"
        assert claims["type"] == "refresh"
        assert "jti" in claims

    def test_expired_refresh_token_rejected(self):
        token = create_refresh_token({"sub": "user-1"}, expires_delta=timedelta(seconds=-1))
        assert decode_refresh_token(token) is None

    def test_refresh_token_without_jti_rejected(self):
        # Tokens missing jti can't be individually revoked — must be rejected.
        now = datetime.now(UTC)
        payload = {
            "sub": "user-1",
            "iat": now,
            "exp": now + timedelta(days=1),
            "iss": "atlas-vox",
            "type": "refresh",
        }
        token = pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        assert decode_refresh_token(token) is None

    def test_access_token_passed_to_refresh_decoder_rejected(self):
        access = create_access_token({"sub": "user-1"})
        assert decode_refresh_token(access) is None
