"""Tests for the cost estimator (VQ-39)."""

from __future__ import annotations

import pytest

from app.services.cost_estimator import (
    PROVIDER_COST_PER_1K_CHARS,
    estimate_cost_usd,
    get_rate,
)


class TestEstimateCost:
    def test_elevenlabs_one_thousand_chars(self):
        # $0.30 / 1k — 1_000 chars should return exactly $0.30.
        cost = estimate_cost_usd("elevenlabs", 1000)
        assert cost == pytest.approx(0.30, rel=1e-6)

    def test_azure_one_million_chars(self):
        # Azure Neural TTS: $0.016/1k → $16 for 1M chars.
        cost = estimate_cost_usd("azure_speech", 1_000_000)
        assert cost == pytest.approx(16.0, rel=1e-3)

    def test_local_provider_is_zero(self):
        for p in ("kokoro", "piper", "coqui_xtts", "styletts2", "dia"):
            assert estimate_cost_usd(p, 10_000) == 0.0

    def test_unknown_provider_is_zero(self):
        assert estimate_cost_usd("no-such-provider", 5000) == 0.0

    def test_zero_chars_is_zero(self):
        assert estimate_cost_usd("elevenlabs", 0) == 0.0

    def test_negative_chars_is_clamped_to_zero(self):
        assert estimate_cost_usd("elevenlabs", -500) == 0.0

    def test_fractional_chars_rounded_to_six_decimals(self):
        # 500 elevenlabs chars → 0.5 * 0.30 = 0.15
        cost = estimate_cost_usd("elevenlabs", 500)
        assert cost == pytest.approx(0.15)


class TestGetRate:
    def test_known_rate(self):
        assert get_rate("elevenlabs") == 0.30

    def test_unknown_rate_defaults_zero(self):
        assert get_rate("does-not-exist") == 0.0

    def test_rate_table_contains_all_known_providers(self):
        # Ensures nobody accidentally removes a provider from the rate table.
        for provider in (
            "elevenlabs", "azure_speech", "kokoro", "piper",
            "coqui_xtts", "styletts2", "cosyvoice", "dia", "dia2",
        ):
            assert provider in PROVIDER_COST_PER_1K_CHARS
