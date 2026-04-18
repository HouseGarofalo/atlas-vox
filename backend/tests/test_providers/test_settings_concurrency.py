"""P0-02 regression: per-request voice_settings must not race under concurrent calls.

These tests exercise :meth:`TTSProvider.resolve_setting` — the race-free path
for per-request voice tunables — and the ElevenLabs provider's
``_build_voice_settings`` which consumes it.
"""

from __future__ import annotations

import asyncio

import pytest

from app.providers.base import SynthesisSettings, TTSProvider


class _DummyProvider(TTSProvider):
    """Minimal concrete provider for exercising the base helpers."""

    async def synthesize(self, text, voice_id, settings):  # pragma: no cover
        raise NotImplementedError

    async def clone_voice(self, samples, config):  # pragma: no cover
        raise NotImplementedError

    async def fine_tune(self, model_id, samples, config):  # pragma: no cover
        raise NotImplementedError

    async def list_voices(self):  # pragma: no cover
        return []

    async def get_capabilities(self):  # pragma: no cover
        from app.providers.base import ProviderCapabilities
        return ProviderCapabilities()

    async def health_check(self):  # pragma: no cover
        from app.providers.base import ProviderHealth
        return ProviderHealth(name="dummy", healthy=True)


class TestResolveSetting:
    def test_per_request_overrides_runtime(self):
        p = _DummyProvider()
        p.configure({"stability": 0.5})
        req = SynthesisSettings(voice_settings={"stability": 0.95})
        assert p.resolve_setting("stability", req, 0.1) == 0.95

    def test_runtime_used_when_no_per_request(self):
        p = _DummyProvider()
        p.configure({"stability": 0.5})
        req = SynthesisSettings()
        assert p.resolve_setting("stability", req, 0.1) == 0.5

    def test_default_when_missing_everywhere(self):
        p = _DummyProvider()
        req = SynthesisSettings()
        assert p.resolve_setting("stability", req, 0.1) == 0.1

    def test_none_settings_is_safe(self):
        p = _DummyProvider()
        p.configure({"stability": 0.7})
        assert p.resolve_setting("stability", None, 0.1) == 0.7

    def test_none_value_in_voice_settings_falls_through(self):
        p = _DummyProvider()
        p.configure({"stability": 0.7})
        req = SynthesisSettings(voice_settings={"stability": None})
        # None in voice_settings should fall back to runtime, not win.
        assert p.resolve_setting("stability", req, 0.1) == 0.7


@pytest.mark.asyncio
async def test_concurrent_resolve_setting_is_race_free():
    """20 concurrent calls with distinct voice_settings must each see their own value."""
    p = _DummyProvider()
    p.configure({"stability": 0.5})

    async def one(i: int) -> float:
        req = SynthesisSettings(voice_settings={"stability": 0.01 * i})
        # Yield to let the scheduler interleave.
        await asyncio.sleep(0)
        val = p.resolve_setting("stability", req, -1.0)
        await asyncio.sleep(0)
        # Read again — should STILL be the per-request value, not a neighbour's.
        return p.resolve_setting("stability", req, -1.0)

    results = await asyncio.gather(*(one(i) for i in range(20)))
    expected = [0.01 * i for i in range(20)]
    assert results == pytest.approx(expected, rel=1e-9)


@pytest.mark.asyncio
async def test_elevenlabs_build_voice_settings_uses_per_request():
    """ElevenLabs _build_voice_settings must prefer per-request overrides."""
    try:
        from elevenlabs import VoiceSettings  # noqa: F401
    except ImportError:
        pytest.skip("elevenlabs SDK not installed")

    from app.providers.elevenlabs import ElevenLabsProvider

    p = ElevenLabsProvider()
    p.configure({"stability": 0.1, "similarity_boost": 0.1})

    req_a = SynthesisSettings(voice_settings={"stability": 0.9, "similarity_boost": 0.8})
    req_b = SynthesisSettings(voice_settings={"stability": 0.2, "similarity_boost": 0.3})

    a = p._build_voice_settings(req_a)
    b = p._build_voice_settings(req_b)

    assert float(a.stability) == pytest.approx(0.9)
    assert float(a.similarity_boost) == pytest.approx(0.8)
    assert float(b.stability) == pytest.approx(0.2)
    assert float(b.similarity_boost) == pytest.approx(0.3)

    # Shared runtime_config remains untouched after both calls.
    assert p._runtime_config["stability"] == 0.1
    assert p._runtime_config["similarity_boost"] == 0.1


@pytest.mark.asyncio
async def test_elevenlabs_build_voice_settings_falls_back_to_runtime():
    try:
        from elevenlabs import VoiceSettings  # noqa: F401
    except ImportError:
        pytest.skip("elevenlabs SDK not installed")

    from app.providers.elevenlabs import ElevenLabsProvider

    p = ElevenLabsProvider()
    p.configure({"stability": 0.42, "similarity_boost": 0.37})
    req = SynthesisSettings()  # no voice_settings

    vs = p._build_voice_settings(req)
    assert float(vs.stability) == pytest.approx(0.42)
    assert float(vs.similarity_boost) == pytest.approx(0.37)
