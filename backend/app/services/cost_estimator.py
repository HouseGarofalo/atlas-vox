"""Cost estimator — USD cost per synthesis request by provider/character count.

Single source of truth for "how expensive was that request?" Used by
``synthesis_service`` to stamp ``synthesis_history.estimated_cost_usd`` and by
``/usage/cost`` aggregation. Numbers are *estimates* based on publicly quoted
list prices and must not be treated as billing-grade.
"""

from __future__ import annotations

# USD per 1_000 characters. Values reflect list pricing for the cheapest
# relevant tier and are conservative (tend to over-estimate). Keep this dict
# in sync with ``app.api.v1.endpoints.usage.DEFAULT_COST_PER_1K`` — the
# usage endpoint reads from this module directly to avoid drift.
PROVIDER_COST_PER_1K_CHARS: dict[str, float] = {
    # Cloud APIs
    "elevenlabs": 0.30,  # Creator tier ~ $0.30/1k chars (quality tier)
    "azure_speech": 0.016,  # Neural TTS — $16 / 1M chars
    # Local/self-hosted — zero marginal cost per character
    "kokoro": 0.0,
    "piper": 0.0,
    "coqui_xtts": 0.0,
    "styletts2": 0.0,
    "cosyvoice": 0.0,
    "dia": 0.0,
    "dia2": 0.0,
}


def estimate_cost_usd(provider_name: str, char_count: int) -> float:
    """Return the estimated USD cost for synthesizing ``char_count`` chars.

    Unknown providers default to 0.0 (local / no-cost assumption). Negative
    char counts are clamped to zero so callers cannot accidentally credit
    themselves.
    """
    if char_count <= 0:
        return 0.0
    rate = PROVIDER_COST_PER_1K_CHARS.get(provider_name, 0.0)
    return round((char_count / 1000.0) * rate, 6)


def get_rate(provider_name: str) -> float:
    """Return the per-1k-char rate for a provider, or 0.0 if unknown."""
    return PROVIDER_COST_PER_1K_CHARS.get(provider_name, 0.0)
