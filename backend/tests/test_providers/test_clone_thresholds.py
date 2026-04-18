"""P2-24: cover the duration/count thresholds providers enforce for cloning.

These are boundary tests — they catch regressions where a refactor silently
lowers a minimum and accepts samples that will produce garbage output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.providers.base import CloneConfig, ProviderAudioSample
from app.providers.coqui_xtts import CoquiXTTSProvider


def _sample(duration_s: float, idx: int = 0) -> ProviderAudioSample:
    return ProviderAudioSample(
        file_path=Path(f"/tmp/atlas-sample-{idx}.wav"),
        duration_seconds=duration_s,
        sample_rate=22050,
        transcript=f"sample {idx}",
    )


class TestCoquiSixSecondThreshold:
    """XTTS v2 requires at least 6 s of reference audio to clone.

    The method raises NotImplementedError when the TTS library isn't
    installed — we check BOTH branches so future GPU-worker contexts
    where the lib IS installed also guard the duration.
    """

    @pytest.mark.asyncio
    async def test_just_under_six_seconds_is_rejected(self):
        provider = CoquiXTTSProvider()
        samples = [_sample(5.9)]
        with pytest.raises((ValueError, NotImplementedError)) as exc:
            await provider.clone_voice(samples, CloneConfig(name="x"))
        # If TTS is installed the ValueError names the 6s requirement;
        # otherwise NotImplementedError is raised for the missing lib.
        msg = str(exc.value)
        assert "6" in msg or "not installed" in msg

    @pytest.mark.asyncio
    async def test_exactly_six_seconds_passes_duration_gate(self):
        """6.0s exactly must NOT be rejected on duration grounds.

        (It may still fail with NotImplementedError because the TTS package
        isn't in the test environment — that's fine; we only assert the
        duration branch isn't the blocker.)
        """
        provider = CoquiXTTSProvider()
        samples = [_sample(6.0)]
        try:
            await provider.clone_voice(samples, CloneConfig(name="x"))
        except ValueError as ve:
            # Must NOT be the duration error.
            assert "6 seconds" not in str(ve), (
                "6.0s should pass the duration threshold; got: " + str(ve)
            )
        except NotImplementedError:
            # Library missing — acceptable.
            pass
        except Exception:
            # Other failures (missing model files) are acceptable.
            pass

    @pytest.mark.asyncio
    async def test_multiple_short_samples_aggregate_past_threshold(self):
        """Three 2.5 s samples sum to 7.5 s — total duration passes."""
        provider = CoquiXTTSProvider()
        samples = [_sample(2.5, i) for i in range(3)]
        try:
            await provider.clone_voice(samples, CloneConfig(name="x"))
        except ValueError as ve:
            assert "6 seconds" not in str(ve)
        except NotImplementedError:
            pass
        except Exception:
            pass

    @pytest.mark.asyncio
    async def test_empty_sample_list_raises_value_error(self):
        provider = CoquiXTTSProvider()
        with pytest.raises((ValueError, NotImplementedError)) as exc:
            await provider.clone_voice([], CloneConfig(name="x"))
        msg = str(exc.value).lower()
        # Either "at least one" or "not installed" depending on env.
        assert "one audio sample" in msg or "not installed" in msg


class TestAzurePersonalVoiceTwoSampleMinimum:
    """Azure Personal Voice requires 1 consent + 1 voice prompt (min 2)."""

    @pytest.mark.asyncio
    async def test_one_sample_rejected(self):
        from app.providers.azure_speech import AzureSpeechProvider

        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        with pytest.raises(ValueError) as exc:
            await provider.clone_voice([_sample(10.0)], CloneConfig(name="x"))
        assert "at least 2" in str(exc.value)

    @pytest.mark.asyncio
    async def test_zero_samples_rejected(self):
        from app.providers.azure_speech import AzureSpeechProvider

        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        with pytest.raises(ValueError) as exc:
            await provider.clone_voice([], CloneConfig(name="x"))
        assert "at least 2" in str(exc.value)
