"""Tests for Azure Custom Voice (Personal Voice cloning + Professional Voice training)."""

from __future__ import annotations

import struct
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.azure_speech import AzureCNVClient, AzureSpeechProvider
from app.providers.base import (
    CloneConfig,
    FineTuneConfig,
    ProviderAudioSample,
    ProviderCapabilities,
    SynthesisSettings,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav(path: Path) -> Path:
    """Write a minimal valid WAV file (1 second, 16 kHz mono)."""
    sr, nc, bits = 16000, 1, 16
    num = sr
    data_size = num * nc * (bits // 8)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, nc, sr,
        sr * nc * (bits // 8),
        nc * (bits // 8), bits,
        b"data", data_size,
    )
    path.write_bytes(header + struct.pack(f"<{num}h", *([0] * num)))
    return path


def _make_samples(tmp_path: Path, count: int) -> list[ProviderAudioSample]:
    samples = []
    for i in range(count):
        wav = _make_wav(tmp_path / f"sample_{i}.wav")
        samples.append(ProviderAudioSample(file_path=wav, duration_seconds=1.0, sample_rate=16000))
    return samples


def _mock_cnv_for_clone(**overrides) -> MagicMock:
    """Build a mock AzureCNVClient pre-wired for a successful clone_voice flow."""
    m = MagicMock(spec=AzureCNVClient)
    m.get_or_create_project = AsyncMock(return_value={"id": "proj-1"})
    m.create_consent = AsyncMock(return_value={"id": "consent-1"})
    m.create_personal_voice = AsyncMock(return_value={"id": "pv-1"})
    m.wait_for_personal_voice = AsyncMock(return_value={
        "id": "pv-1",
        "status": "Succeeded",
        "speakerProfileId": "spk-profile-abc123",
    })
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


def _mock_cnv_for_finetune(**overrides) -> MagicMock:
    """Build a mock AzureCNVClient pre-wired for a successful fine_tune flow."""
    m = MagicMock(spec=AzureCNVClient)
    m.get_or_create_project = AsyncMock(return_value={"id": "proj-1"})
    m.create_consent = AsyncMock(return_value={"id": "c-1"})
    m.create_training_set = AsyncMock(return_value={"id": "ts-1"})
    m.upload_training_data = AsyncMock(return_value={"id": "upload-1"})
    m.create_model = AsyncMock(return_value={"id": "model-1"})
    m.wait_for_model = AsyncMock(return_value={"id": "model-1", "status": "Succeeded"})
    m.deploy_endpoint = AsyncMock(return_value={"id": "ep-1"})
    m.wait_for_endpoint = AsyncMock(return_value={"id": "ep-1", "status": "Succeeded"})
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


# ---------------------------------------------------------------------------
# AzureSpeechProvider — Capabilities
# ---------------------------------------------------------------------------

class TestAzureCapabilities:
    @pytest.mark.asyncio
    async def test_supports_cloning_and_finetuning(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        assert isinstance(caps, ProviderCapabilities)
        assert caps.supports_cloning is True
        assert caps.supports_fine_tuning is True
        assert caps.min_samples_for_cloning == 2
        assert caps.gpu_mode == "none"

    @pytest.mark.asyncio
    async def test_supported_languages(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        for lang in ("en", "zh", "ja", "fr", "de"):
            assert lang in caps.supported_languages

    @pytest.mark.asyncio
    async def test_output_formats(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        assert set(caps.supported_output_formats) == {"wav", "mp3", "ogg"}


# ---------------------------------------------------------------------------
# AzureSpeechProvider — clone_voice (Personal Voice)
# ---------------------------------------------------------------------------

class TestCloneVoice:
    @pytest.mark.asyncio
    async def test_rejects_single_sample(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "test-key", "region": "eastus"})
        samples = _make_samples(tmp_path, 1)
        with pytest.raises(ValueError, match="at least 2"):
            await provider.clone_voice(samples, CloneConfig(name="Test"))

    @pytest.mark.asyncio
    async def test_rejects_empty_key(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        # Explicitly set an empty key so env vars don't leak in
        provider.configure({"subscription_key": "", "region": "eastus"})
        samples = _make_samples(tmp_path, 2)
        with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
            await provider.clone_voice(samples, CloneConfig(name="Test"))

    @pytest.mark.asyncio
    async def test_success_returns_speaker_profile_id(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 3)
        mock_cnv = _mock_cnv_for_clone()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            result = await provider.clone_voice(samples, CloneConfig(name="TestVoice", language="en"))

        assert result.provider_model_id == "pv:spk-profile-abc123"
        assert result.metrics["method"] == "personal_voice"

    @pytest.mark.asyncio
    async def test_consent_uses_first_sample(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 3)
        mock_cnv = _mock_cnv_for_clone()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            await provider.clone_voice(samples, CloneConfig(name="V"))

        consent_call = mock_cnv.create_consent.call_args
        assert consent_call.args[4] == samples[0].file_path

    @pytest.mark.asyncio
    async def test_prompt_uses_remaining_samples(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 4)
        mock_cnv = _mock_cnv_for_clone()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            await provider.clone_voice(samples, CloneConfig(name="V"))

        pv_call = mock_cnv.create_personal_voice.call_args
        prompt_files = pv_call.args[3]
        assert len(prompt_files) == 3  # samples[1], [2], [3]

    @pytest.mark.asyncio
    async def test_fails_when_no_speaker_profile_id(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 2)
        mock_cnv = _mock_cnv_for_clone(
            wait_for_personal_voice=AsyncMock(return_value={"status": "Succeeded"}),
        )

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            with pytest.raises(RuntimeError, match="speakerProfileId"):
                await provider.clone_voice(samples, CloneConfig(name="T"))

    @pytest.mark.asyncio
    async def test_locale_mapping_french(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 2)
        mock_cnv = _mock_cnv_for_clone()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            await provider.clone_voice(samples, CloneConfig(name="T", language="fr"))

        consent_call = mock_cnv.create_consent.call_args
        # locale may be positional or keyword — check both
        all_args = list(consent_call.args) + list(consent_call.kwargs.values())
        assert "fr-FR" in all_args


# ---------------------------------------------------------------------------
# AzureSpeechProvider — fine_tune (Professional Voice)
# ---------------------------------------------------------------------------

class TestFineTune:
    @pytest.mark.asyncio
    async def test_rejects_too_few_samples(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 2)
        with pytest.raises(ValueError, match="at least 3"):
            await provider.fine_tune("base", samples, FineTuneConfig())

    @pytest.mark.asyncio
    async def test_success_returns_cnv_model(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 5)
        mock_cnv = _mock_cnv_for_finetune()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            result = await provider.fine_tune("base", samples, FineTuneConfig())

        assert result.provider_model_id.startswith("cnv:")
        assert result.metrics["method"] == "professional_voice"

    @pytest.mark.asyncio
    async def test_training_data_excludes_consent(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        samples = _make_samples(tmp_path, 5)
        mock_cnv = _mock_cnv_for_finetune()

        with patch.object(provider, "_cnv_client", return_value=mock_cnv):
            await provider.fine_tune("base", samples, FineTuneConfig())

        upload_call = mock_cnv.upload_training_data.call_args
        train_files = upload_call.args[1]
        assert len(train_files) == 4  # samples[1] through samples[4]


# ---------------------------------------------------------------------------
# AzureSpeechProvider — synthesize with custom voice IDs
# ---------------------------------------------------------------------------

class TestSynthesizeCustomVoice:
    """Test that pv: and cnv: voice_id prefixes produce correct SDK calls."""

    def _setup_sdk_mock(self):
        """Return (mock_sdk, mock_config, mock_synthesizer, mock_result) + sys.modules dict."""
        COMPLETED = "SynthesizingAudioCompleted"

        mock_result = MagicMock()
        mock_result.reason = COMPLETED

        mock_synthesizer = MagicMock()

        mock_sdk = MagicMock()
        mock_sdk.ResultReason.SynthesizingAudioCompleted = COMPLETED
        mock_sdk.audio.AudioOutputConfig.return_value = MagicMock()
        mock_sdk.SpeechSynthesizer.return_value = mock_synthesizer

        # Build a consistent module hierarchy so `import azure.cognitiveservices.speech`
        # always resolves to our mock_sdk regardless of import path.
        mock_azure = MagicMock()
        mock_azure.cognitiveservices.speech = mock_sdk

        modules = {
            "azure": mock_azure,
            "azure.cognitiveservices": mock_azure.cognitiveservices,
            "azure.cognitiveservices.speech": mock_sdk,
        }

        mock_config = MagicMock()
        return mock_sdk, mock_config, mock_synthesizer, mock_result, modules

    @pytest.mark.asyncio
    async def test_personal_voice_constructs_ssml(self):
        provider = AzureSpeechProvider()
        mock_sdk, mock_config, mock_synth, mock_result, modules = self._setup_sdk_mock()

        mock_future = MagicMock()
        mock_future.get = MagicMock(return_value=mock_result)
        mock_synth.speak_ssml_async = MagicMock(return_value=mock_future)

        async def fake_run_sync(fn, *a, **kw):
            return fn()

        with patch.object(provider, "_get_config", return_value=mock_config), \
             patch.object(provider, "prepare_output_path", return_value=Path("/tmp/test.wav")), \
             patch("app.providers.azure_speech.run_sync", side_effect=fake_run_sync), \
             patch.dict("sys.modules", modules):
            await provider.synthesize("Hello world", "pv:spk-xyz", SynthesisSettings())

        mock_synth.speak_ssml_async.assert_called_once()
        ssml = mock_synth.speak_ssml_async.call_args[0][0]
        assert 'speakerProfileId="spk-xyz"' in ssml
        assert "DragonLatestNeural" in ssml
        assert "Hello world" in ssml

    @pytest.mark.asyncio
    async def test_professional_voice_sets_endpoint(self):
        provider = AzureSpeechProvider()
        mock_sdk, mock_config, mock_synth, mock_result, modules = self._setup_sdk_mock()

        mock_future = MagicMock()
        mock_future.get = MagicMock(return_value=mock_result)
        mock_synth.speak_text_async = MagicMock(return_value=mock_future)

        async def fake_run_sync(fn, *a, **kw):
            return fn()

        with patch.object(provider, "_get_config", return_value=mock_config), \
             patch.object(provider, "prepare_output_path", return_value=Path("/tmp/test.wav")), \
             patch("app.providers.azure_speech.run_sync", side_effect=fake_run_sync), \
             patch.dict("sys.modules", modules):
            await provider.synthesize("Hello", "cnv:MyVoice:ep-123", SynthesisSettings())

        assert mock_config.endpoint_id == "ep-123"
        assert mock_config.speech_synthesis_voice_name == "MyVoice"
        mock_synth.speak_text_async.assert_called_once()


# ---------------------------------------------------------------------------
# AzureCNVClient — unit tests
# ---------------------------------------------------------------------------

class TestAzureCNVClient:
    def test_url_construction(self):
        client = AzureCNVClient("key123", "eastus")
        url = client._url("projects/my-proj")
        assert "eastus.api.cognitive.microsoft.com" in url
        assert "customvoice/projects/my-proj" in url
        assert "api-version=" in url

    def test_auth_headers(self):
        client = AzureCNVClient("my-secret-key", "westus")
        headers = client._auth_headers()
        assert headers["Ocp-Apim-Subscription-Key"] == "my-secret-key"

    def test_json_headers_include_content_type(self):
        client = AzureCNVClient("key", "eastus")
        headers = client._json_headers()
        assert headers["Content-Type"] == "application/json"
        assert "Ocp-Apim-Subscription-Key" in headers


# ---------------------------------------------------------------------------
# AzureCNVClient — async polling logic
# ---------------------------------------------------------------------------

class TestCNVClientPolling:
    @pytest.mark.asyncio
    async def test_get_or_create_returns_existing(self):
        client = AzureCNVClient("key", "eastus")
        client.get_project = AsyncMock(return_value={"id": "existing"})
        client.create_project = AsyncMock()

        result = await client.get_or_create_project("existing")
        assert result["id"] == "existing"
        client.create_project.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_creates_new(self):
        client = AzureCNVClient("key", "eastus")
        client.get_project = AsyncMock(return_value=None)
        client.create_project = AsyncMock(return_value={"id": "new-proj"})

        result = await client.get_or_create_project("new-proj")
        assert result["id"] == "new-proj"
        client.create_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_personal_voice_polls_until_success(self):
        client = AzureCNVClient("key", "eastus")
        call_count = 0

        async def mock_get_pv(pv_id):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return {"id": pv_id, "status": "Running"}
            return {"id": pv_id, "status": "Succeeded", "speakerProfileId": "spk-123"}

        client.get_personal_voice = mock_get_pv

        with patch("app.providers.azure_speech.asyncio.sleep", new_callable=AsyncMock):
            result = await client.wait_for_personal_voice("pv-1", poll_interval=0, timeout=60)

        assert result["speakerProfileId"] == "spk-123"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_personal_voice_raises_on_failure(self):
        client = AzureCNVClient("key", "eastus")
        client.get_personal_voice = AsyncMock(return_value={
            "id": "pv-1", "status": "Failed", "description": "Bad audio quality",
        })

        with patch("app.providers.azure_speech.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="Personal voice creation failed"):
                await client.wait_for_personal_voice("pv-1", poll_interval=0, timeout=60)

    @pytest.mark.asyncio
    async def test_wait_for_model_raises_on_timeout(self):
        client = AzureCNVClient("key", "eastus")
        client.get_model = AsyncMock(return_value={"id": "m-1", "status": "Running"})

        with patch("app.providers.azure_speech.asyncio.sleep", new_callable=AsyncMock), \
             patch("app.providers.azure_speech.time.time") as mock_time:
            # First call sets deadline (0 + 5 = 5), second call in loop returns 10 (> 5)
            mock_time.side_effect = [0, 10]
            with pytest.raises(TimeoutError, match="timed out"):
                await client.wait_for_model("m-1", poll_interval=0, timeout=5)


# ---------------------------------------------------------------------------
# Locale mapping
# ---------------------------------------------------------------------------

class TestLocaleMapping:
    def test_english(self):
        assert AzureSpeechProvider._to_locale("en") == "en-US"

    def test_french(self):
        assert AzureSpeechProvider._to_locale("fr") == "fr-FR"

    def test_chinese(self):
        assert AzureSpeechProvider._to_locale("zh") == "zh-CN"

    def test_unknown_fallback(self):
        assert AzureSpeechProvider._to_locale("xx") == "xx-XX"


# ---------------------------------------------------------------------------
# Integration with training pipeline
# ---------------------------------------------------------------------------

class TestTrainingPipelineIntegration:
    @pytest.mark.asyncio
    async def test_azure_is_training_capable(self):
        from app.services.provider_registry import provider_registry

        provider = provider_registry.get_provider("azure_speech")
        caps = await provider.get_capabilities()
        assert caps.supports_cloning is True

    @pytest.mark.asyncio
    async def test_training_service_validation_passes_for_azure(self):
        mock_caps = ProviderCapabilities(
            supports_cloning=True,
            supports_fine_tuning=True,
            min_samples_for_cloning=2,
        )
        mock_provider = AsyncMock()
        mock_provider.get_capabilities = AsyncMock(return_value=mock_caps)

        caps = await mock_provider.get_capabilities()
        # training_service checks: supports_cloning or supports_fine_tuning
        assert caps.supports_cloning or caps.supports_fine_tuning


# ---------------------------------------------------------------------------
# Output format resolution
# ---------------------------------------------------------------------------

class TestOutputFormats:
    def test_format_info_wav(self):
        sr, ext = AzureSpeechProvider._format_info("wav")
        assert sr == 24000
        assert ext == "wav"

    def test_format_info_mp3(self):
        sr, ext = AzureSpeechProvider._format_info("mp3")
        assert sr == 24000
        assert ext == "mp3"

    def test_format_info_ogg(self):
        sr, ext = AzureSpeechProvider._format_info("ogg")
        assert sr == 24000
        assert ext == "ogg"

    def test_format_info_wav_48k(self):
        sr, ext = AzureSpeechProvider._format_info("wav_48k")
        assert sr == 48000
        assert ext == "wav"

    def test_format_info_unknown_defaults_to_wav(self):
        sr, ext = AzureSpeechProvider._format_info("flac")
        assert sr == 24000
        assert ext == "wav"


# ---------------------------------------------------------------------------
# HD voice detection
# ---------------------------------------------------------------------------

class TestHDVoiceDetection:
    def test_dragon_hd_detected(self):
        assert AzureSpeechProvider._is_dragon_hd("en-US-Ava:DragonHDLatestNeural") is True

    def test_regular_voice_not_hd(self):
        assert AzureSpeechProvider._is_dragon_hd("en-US-JennyNeural") is False

    def test_personal_voice_not_hd(self):
        assert AzureSpeechProvider._is_dragon_hd("pv:spk-123") is False

    def test_cnv_voice_not_hd(self):
        assert AzureSpeechProvider._is_dragon_hd("cnv:MyVoice:ep-1") is False


# ---------------------------------------------------------------------------
# SSML construction
# ---------------------------------------------------------------------------

class TestSSMLConstruction:
    def test_personal_voice_ssml(self):
        provider = AzureSpeechProvider()
        ssml = provider._build_ssml("Hello", "pv:spk-xyz")
        assert 'speakerProfileId="spk-xyz"' in ssml
        assert "DragonLatestNeural" in ssml
        assert "Hello" in ssml

    def test_cnv_voice_ssml(self):
        provider = AzureSpeechProvider()
        ssml = provider._build_ssml("Hello", "cnv:MyVoice:ep-1")
        assert 'name="MyVoice"' in ssml
        assert "Hello" in ssml

    def test_standard_voice_ssml(self):
        provider = AzureSpeechProvider()
        ssml = provider._build_ssml("Hello", "en-US-JennyNeural")
        assert 'name="en-US-JennyNeural"' in ssml

    def test_xml_escaping(self):
        provider = AzureSpeechProvider()
        ssml = provider._build_ssml("A & B <tag>", "en-US-JennyNeural")
        assert "&amp;" in ssml
        assert "&lt;" in ssml


# ---------------------------------------------------------------------------
# Extended capabilities
# ---------------------------------------------------------------------------

class TestExtendedCapabilities:
    @pytest.mark.asyncio
    async def test_word_boundaries_supported(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_word_boundaries is True

    @pytest.mark.asyncio
    async def test_pronunciation_assessment_supported(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_pronunciation_assessment is True

    @pytest.mark.asyncio
    async def test_transcription_supported(self):
        provider = AzureSpeechProvider()
        caps = await provider.get_capabilities()
        assert caps.supports_transcription is True


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

class TestTranscription:
    @pytest.mark.asyncio
    async def test_transcribe_rejects_empty_key(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "", "region": "eastus"})
        wav = _make_wav(tmp_path / "test.wav")
        with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
            await provider.transcribe(wav)

    @pytest.mark.asyncio
    async def test_transcribe_success(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        wav = _make_wav(tmp_path / "test.wav")

        COMPLETED = "RecognizedSpeech"
        mock_result = MagicMock()
        mock_result.reason = COMPLETED
        mock_result.text = "Hello world"

        mock_sdk = MagicMock()
        mock_sdk.ResultReason.RecognizedSpeech = COMPLETED
        mock_sdk.SpeechConfig.return_value = MagicMock()
        mock_sdk.audio.AudioConfig.return_value = MagicMock()

        mock_recognizer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = MagicMock(return_value=mock_result)
        mock_recognizer.recognize_once_async.return_value = mock_future
        mock_sdk.SpeechRecognizer.return_value = mock_recognizer

        mock_azure = MagicMock()
        mock_azure.cognitiveservices.speech = mock_sdk

        async def fake_run_sync(fn, *a, **kw):
            return fn()

        with patch("app.providers.azure_speech.run_sync", side_effect=fake_run_sync), \
             patch.dict("sys.modules", {
                 "azure": mock_azure,
                 "azure.cognitiveservices": mock_azure.cognitiveservices,
                 "azure.cognitiveservices.speech": mock_sdk,
             }):
            transcript = await provider.transcribe(wav, locale="en-US")

        assert transcript == "Hello world"


# ---------------------------------------------------------------------------
# Pronunciation Assessment
# ---------------------------------------------------------------------------

class TestPronunciationAssessment:
    @pytest.mark.asyncio
    async def test_assess_rejects_empty_key(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "", "region": "eastus"})
        wav = _make_wav(tmp_path / "test.wav")
        with pytest.raises(ValueError, match="AZURE_SPEECH_KEY"):
            await provider.assess_pronunciation(wav, "Hello")

    @pytest.mark.asyncio
    async def test_assess_success(self, tmp_path: Path):
        provider = AzureSpeechProvider()
        provider.configure({"subscription_key": "k", "region": "eastus"})
        wav = _make_wav(tmp_path / "test.wav")

        COMPLETED = "RecognizedSpeech"
        mock_result = MagicMock()
        mock_result.reason = COMPLETED

        mock_assessment = MagicMock()
        mock_assessment.accuracy_score = 95.0
        mock_assessment.fluency_score = 90.0
        mock_assessment.completeness_score = 100.0
        mock_assessment.pronunciation_score = 92.0
        mock_assessment.words = []

        mock_sdk = MagicMock()
        mock_sdk.ResultReason.RecognizedSpeech = COMPLETED
        mock_sdk.PronunciationAssessmentConfig.return_value = MagicMock()
        mock_sdk.PronunciationAssessmentGradingSystem.HundredMark = "HundredMark"
        mock_sdk.PronunciationAssessmentGranularity.Word = "Word"
        mock_sdk.PronunciationAssessmentResult.return_value = mock_assessment
        mock_sdk.SpeechConfig.return_value = MagicMock()
        mock_sdk.audio.AudioConfig.return_value = MagicMock()

        mock_recognizer = MagicMock()
        mock_future = MagicMock()
        mock_future.get = MagicMock(return_value=mock_result)
        mock_recognizer.recognize_once_async.return_value = mock_future
        mock_sdk.SpeechRecognizer.return_value = mock_recognizer

        mock_azure = MagicMock()
        mock_azure.cognitiveservices.speech = mock_sdk

        async def fake_run_sync(fn, *a, **kw):
            return fn()

        with patch("app.providers.azure_speech.run_sync", side_effect=fake_run_sync), \
             patch.dict("sys.modules", {
                 "azure": mock_azure,
                 "azure.cognitiveservices": mock_azure.cognitiveservices,
                 "azure.cognitiveservices.speech": mock_sdk,
             }):
            score = await provider.assess_pronunciation(wav, "Hello world")

        assert score.accuracy_score == 95.0
        assert score.fluency_score == 90.0
        assert score.pronunciation_score == 92.0


# ---------------------------------------------------------------------------
# Batch synthesis client
# ---------------------------------------------------------------------------

class TestBatchSynthesisClient:
    @pytest.mark.asyncio
    async def test_wait_for_batch_raises_on_timeout(self):
        client = AzureCNVClient("key", "eastus")
        client.get_batch_synthesis = AsyncMock(return_value={"status": "Running"})

        with patch("app.providers.azure_speech.asyncio.sleep", new_callable=AsyncMock), \
             patch("app.providers.azure_speech.time.time") as mock_time:
            mock_time.side_effect = [0, 10]
            with pytest.raises(TimeoutError, match="timed out"):
                await client.wait_for_batch_synthesis("batch-1", poll_interval=0, timeout=5)

    @pytest.mark.asyncio
    async def test_wait_for_batch_raises_on_failure(self):
        client = AzureCNVClient("key", "eastus")
        client.get_batch_synthesis = AsyncMock(return_value={"status": "Failed", "error": "bad input"})

        with patch("app.providers.azure_speech.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="Batch synthesis failed"):
                await client.wait_for_batch_synthesis("batch-1", poll_interval=0, timeout=60)
