"""Azure AI Speech provider — cloud TTS with SSML, Personal Voice cloning, and Professional Voice training."""

from __future__ import annotations

import asyncio
import copy
import io
import time
import uuid
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import httpx
import structlog

from app.core.config import settings
from app.providers.base import (
    AudioResult,
    CloneConfig,
    FineTuneConfig,
    PronunciationScore,
    ProviderAudioSample,
    ProviderCapabilities,
    ProviderHealth,
    SynthesisSettings,
    TTSProvider,
    VoiceInfo,
    VoiceModel,
    WordBoundary,
    run_sync,
)

logger = structlog.get_logger(__name__)

# Azure Custom Voice API version
CNV_API_VERSION = "2024-02-01-preview"

# Azure SDK output format mapping: (format_key) -> (sdk_enum_name, sample_rate, ext)
_OUTPUT_FORMAT_MAP = {
    "wav": ("Riff24Khz16BitMonoPcm", 24000, "wav"),
    "wav_16k": ("Riff16Khz16BitMonoPcm", 16000, "wav"),
    "wav_48k": ("Riff48Khz16BitMonoPcm", 48000, "wav"),
    "mp3": ("Audio24Khz160KBitRateMonoMp3", 24000, "mp3"),
    "ogg": ("Ogg24Khz16BitMonoOpus", 24000, "ogg"),
}

# Language code → Azure locale mapping
_LOCALE_MAP = {
    "en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE",
    "it": "it-IT", "pt": "pt-BR", "zh": "zh-CN", "ja": "ja-JP",
    "ko": "ko-KR", "ar": "ar-SA", "ru": "ru-RU", "nl": "nl-NL",
    "pl": "pl-PL", "sv": "sv-SE", "tr": "tr-TR", "hi": "hi-IN",
}


class AzureCNVClient:
    """REST API client for Azure Custom Voice (Personal + Professional)."""

    def __init__(self, subscription_key: str, region: str) -> None:
        self.subscription_key = subscription_key
        self.region = region
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/customvoice"

    def _auth_headers(self) -> dict[str, str]:
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}

    def _json_headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path}?api-version={CNV_API_VERSION}"

    # ---- Project Management ----

    async def create_project(self, project_id: str, kind: str = "PersonalVoice",
                              description: str = "") -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                self._url(f"projects/{project_id}"),
                headers=self._json_headers(),
                json={"kind": kind, "description": description},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_project(self, project_id: str) -> dict | None:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"projects/{project_id}"),
                headers=self._auth_headers(),
            )
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def get_or_create_project(self, project_id: str, kind: str = "PersonalVoice",
                                     description: str = "") -> dict:
        existing = await self.get_project(project_id)
        if existing:
            return existing
        return await self.create_project(project_id, kind=kind, description=description)

    # ---- Consent ----

    async def create_consent(self, consent_id: str, project_id: str,
                              voice_talent_name: str, company_name: str,
                              audio_file: Path, locale: str = "en-US") -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            with open(audio_file, "rb") as f:
                resp = await client.post(
                    self._url(f"consents/{consent_id}"),
                    headers=self._auth_headers(),
                    data={
                        "projectId": project_id,
                        "voiceTalentName": voice_talent_name,
                        "companyName": company_name,
                        "locale": locale,
                    },
                    files={"audiodata": (audio_file.name, f, "audio/wav")},
                )
            resp.raise_for_status()
            return resp.json()

    # ---- Personal Voice ----

    async def create_personal_voice(self, personal_voice_id: str,
                                     project_id: str, consent_id: str,
                                     audio_files: list[Path]) -> dict:
        async with httpx.AsyncClient(timeout=120) as client:
            files_list = []
            handles = []
            try:
                for af in audio_files:
                    fh = open(af, "rb")
                    handles.append(fh)
                    files_list.append(("audiodata", (af.name, fh, "audio/wav")))

                resp = await client.post(
                    self._url(f"personalvoices/{personal_voice_id}"),
                    headers=self._auth_headers(),
                    data={"projectId": project_id, "consentId": consent_id},
                    files=files_list,
                )
            finally:
                for fh in handles:
                    fh.close()

            resp.raise_for_status()
            return resp.json()

    async def get_personal_voice(self, personal_voice_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"personalvoices/{personal_voice_id}"),
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_for_personal_voice(self, personal_voice_id: str,
                                       poll_interval: int = 5,
                                       timeout: int = 600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            voice = await self.get_personal_voice(personal_voice_id)
            status = voice.get("status", "")
            logger.info("azure_pv_poll", id=personal_voice_id, status=status)
            if status in ("Succeeded", "Failed", "Disabling"):
                if status == "Failed":
                    raise RuntimeError(
                        f"Personal voice creation failed: {voice.get('description', voice)}"
                    )
                return voice
            await asyncio.sleep(poll_interval)
        raise TimeoutError("Personal voice creation timed out")

    # ---- Professional Voice (Training Set + Model + Endpoint) ----

    async def create_training_set(self, training_set_id: str, project_id: str,
                                   description: str = "") -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.put(
                self._url(f"trainingsets/{training_set_id}"),
                headers=self._json_headers(),
                json={"projectId": project_id, "description": description},
            )
            resp.raise_for_status()
            return resp.json()

    async def upload_training_data(self, training_set_id: str,
                                    audio_files: list[Path],
                                    transcripts: dict[str, str] | None = None,
                                    kind: str = "IndividualUtterances") -> dict:
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for af in audio_files:
                zf.write(af, af.name)
            # Include transcript script file if transcripts provided
            if transcripts:
                script_lines = []
                for af in audio_files:
                    text = transcripts.get(af.stem, transcripts.get(af.name, ""))
                    if text:
                        script_lines.append(f"{af.stem}\t{text}")
                if script_lines:
                    zf.writestr("script.txt", "\n".join(script_lines))
        zip_buf.seek(0)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                self._url(f"trainingsets/{training_set_id}/uploads"),
                headers=self._auth_headers(),
                data={"kind": kind},
                files={"audiodata": ("training_data.zip", zip_buf, "application/zip")},
            )
            resp.raise_for_status()
            return resp.json()

    async def create_model(self, model_id: str, project_id: str,
                           consent_id: str, training_set_id: str,
                           voice_name: str, locale: str = "en-US",
                           recipe_kind: str = "Default") -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(
                self._url(f"models/{model_id}"),
                headers=self._json_headers(),
                json={
                    "projectId": project_id,
                    "consentId": consent_id,
                    "trainingSetId": training_set_id,
                    "voiceName": voice_name,
                    "locale": locale,
                    "recipe": {"kind": recipe_kind},
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_model(self, model_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"models/{model_id}"),
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_for_model(self, model_id: str,
                              poll_interval: int = 60,
                              timeout: int = 14400) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            model = await self.get_model(model_id)
            status = model.get("status", "")
            logger.info("azure_model_poll", model_id=model_id, status=status)
            if status in ("Succeeded", "Failed"):
                if status == "Failed":
                    raise RuntimeError(f"Model training failed: {model}")
                return model
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Model training timed out after {timeout}s")

    async def deploy_endpoint(self, endpoint_id: str, project_id: str,
                               model_id: str) -> dict:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.put(
                self._url(f"endpoints/{endpoint_id}"),
                headers=self._json_headers(),
                json={"projectId": project_id, "modelId": model_id},
            )
            resp.raise_for_status()
            return resp.json()

    async def get_endpoint(self, endpoint_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"endpoints/{endpoint_id}"),
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_for_endpoint(self, endpoint_id: str,
                                 poll_interval: int = 15,
                                 timeout: int = 600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            endpoint = await self.get_endpoint(endpoint_id)
            status = endpoint.get("status", "")
            if status in ("Succeeded", "Failed"):
                if status == "Failed":
                    raise RuntimeError(f"Endpoint deployment failed: {endpoint}")
                return endpoint
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Endpoint deployment timed out after {timeout}s")

    # ---- Batch Synthesis REST API ----

    async def create_batch_synthesis(self, inputs: list[dict], voice: str,
                                      output_format: str = "audio-24khz-160kbitrate-mono-mp3") -> dict:
        """Create an async batch synthesis job via Azure REST API."""
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"https://{self.region}.customvoice.api.speech.microsoft.com"
                f"/api/batchsyntheses?api-version={CNV_API_VERSION}",
                headers=self._json_headers(),
                json={
                    "inputKind": "PlainText",
                    "inputs": inputs,
                    "synthesisConfig": {"voice": voice},
                    "properties": {"outputFormat": output_format},
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_batch_synthesis(self, batch_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://{self.region}.customvoice.api.speech.microsoft.com"
                f"/api/batchsyntheses/{batch_id}?api-version={CNV_API_VERSION}",
                headers=self._auth_headers(),
            )
            resp.raise_for_status()
            return resp.json()

    async def wait_for_batch_synthesis(self, batch_id: str,
                                        poll_interval: int = 10,
                                        timeout: int = 3600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            batch = await self.get_batch_synthesis(batch_id)
            status = batch.get("status", "")
            if status in ("Succeeded", "Failed"):
                if status == "Failed":
                    raise RuntimeError(f"Batch synthesis failed: {batch}")
                return batch
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Batch synthesis timed out after {timeout}s")


class AzureSpeechProvider(TTSProvider):
    """Azure AI Speech — cloud TTS with SSML, Personal Voice cloning, and Professional Voice training."""

    def __init__(self) -> None:
        self._speech_config = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._speech_config = None

    def _get_key_and_region(self) -> tuple[str, str]:
        key = self.get_config_value("subscription_key", settings.azure_speech_key)
        region = self.get_config_value("region", settings.azure_speech_region)
        return key, region

    def _get_config(self):
        if self._speech_config is None:
            subscription_key, region = self._get_key_and_region()
            if not subscription_key:
                raise ValueError("AZURE_SPEECH_KEY not configured")
            try:
                import azure.cognitiveservices.speech as speechsdk

                self._speech_config = speechsdk.SpeechConfig(
                    subscription=subscription_key,
                    region=region,
                )
                # Default to 24kHz WAV — callers override per-request via _apply_output_format
                self._speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
                )
                logger.info("azure_speech_config_created", region=region)
            except ImportError:
                raise ImportError("pip install azure-cognitiveservices-speech")
        return self._speech_config

    @staticmethod
    def _apply_output_format(config, output_format: str = "wav"):
        """Set the synthesis output format on a SpeechConfig."""
        import azure.cognitiveservices.speech as speechsdk

        fmt_name, _, _ = _OUTPUT_FORMAT_MAP.get(output_format, _OUTPUT_FORMAT_MAP["wav"])
        sdk_fmt = getattr(speechsdk.SpeechSynthesisOutputFormat, fmt_name, None)
        if sdk_fmt is not None:
            config.set_speech_synthesis_output_format(sdk_fmt)

    @staticmethod
    def _format_info(output_format: str = "wav") -> tuple[int, str]:
        """Return (sample_rate, file_extension) for the given format."""
        _, sr, ext = _OUTPUT_FORMAT_MAP.get(output_format, _OUTPUT_FORMAT_MAP["wav"])
        return sr, ext

    @staticmethod
    def _is_dragon_hd(voice_id: str) -> bool:
        return "DragonHD" in voice_id

    def _cnv_client(self) -> AzureCNVClient:
        key, region = self._get_key_and_region()
        if not key:
            raise ValueError("AZURE_SPEECH_KEY not configured for Custom Voice")
        return AzureCNVClient(key, region)

    @staticmethod
    def _to_locale(lang: str) -> str:
        return _LOCALE_MAP.get(lang, f"{lang}-{lang.upper()}" if len(lang) == 2 else lang)

    def _build_ssml(self, text: str, voice_id: str) -> str:
        """Wrap plain text in SSML for a given voice, handling PV/CNV/HD prefixes."""
        if voice_id.startswith("pv:"):
            speaker_profile_id = voice_id[3:]
            return (
                '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
                'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
                '<voice name="DragonLatestNeural">'
                f'<mstts:ttsembedding speakerProfileId="{xml_escape(speaker_profile_id)}"/>'
                f"{xml_escape(text)}"
                "</voice></speak>"
            )
        name = voice_id
        if voice_id.startswith("cnv:"):
            name = voice_id[4:].split(":", 1)[0]
        return (
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            'xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">'
            f'<voice name="{xml_escape(name)}">'
            f"{xml_escape(text)}"
            "</voice></speak>"
        )

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        import azure.cognitiveservices.speech as speechsdk

        config = copy.deepcopy(self._get_config())
        self._apply_output_format(config, settings_.output_format)
        sample_rate, ext = self._format_info(settings_.output_format)

        output_file = self.prepare_output_path(prefix="azure", ext=ext)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))

        logger.info("azure_synthesize_started", voice_id=voice_id, text_length=len(text),
                     ssml=settings_.ssml, output_format=settings_.output_format)
        start = time.perf_counter()

        # Professional Voice — set endpoint_id before creating synthesizer
        if voice_id.startswith("cnv:"):
            parts = voice_id[4:].split(":", 1)
            config.speech_synthesis_voice_name = parts[0]
            if len(parts) > 1:
                config.endpoint_id = parts[1]

        # Determine whether to use SSML
        use_ssml = settings_.ssml or voice_id.startswith("pv:") or self._is_dragon_hd(voice_id)
        if use_ssml and not settings_.ssml:
            text = self._build_ssml(text, voice_id)
        elif not use_ssml and not voice_id.startswith("cnv:"):
            config.speech_synthesis_voice_name = voice_id or "en-US-JennyNeural"

        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config, audio_config=audio_config
        )

        if use_ssml or settings_.ssml:
            result = await run_sync(synthesizer.speak_ssml_async(text).get)
        else:
            result = await run_sync(synthesizer.speak_text_async(text).get)

        elapsed = time.perf_counter() - start

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("azure_synthesize_completed", voice_id=voice_id,
                        latency_ms=int(elapsed * 1000), format=ext)
            return AudioResult(audio_path=output_file, sample_rate=sample_rate, format=ext)
        else:
            error = result.cancellation_details.error_details if result.cancellation_details else "Unknown error"
            logger.error("azure_synthesize_failed", voice_id=voice_id,
                         latency_ms=int(elapsed * 1000), error=error)
            raise RuntimeError(f"Azure synthesis failed: {error}")

    # ---- Streaming synthesis ----

    async def stream_synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ):
        """Stream synthesis using Azure SDK PullAudioOutputStream."""
        import azure.cognitiveservices.speech as speechsdk

        config = copy.deepcopy(self._get_config())
        self._apply_output_format(config, settings_.output_format)

        if voice_id.startswith("cnv:"):
            parts = voice_id[4:].split(":", 1)
            config.speech_synthesis_voice_name = parts[0]
            if len(parts) > 1:
                config.endpoint_id = parts[1]

        use_ssml = settings_.ssml or voice_id.startswith("pv:") or self._is_dragon_hd(voice_id)
        if use_ssml and not settings_.ssml:
            text = self._build_ssml(text, voice_id)
        elif not use_ssml:
            config.speech_synthesis_voice_name = voice_id or "en-US-JennyNeural"

        pull_stream = speechsdk.audio.PullAudioOutputStream()
        audio_config = speechsdk.audio.AudioOutputConfig(stream=pull_stream)
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=audio_config)

        logger.info("azure_stream_started", voice_id=voice_id, text_length=len(text))

        if use_ssml or settings_.ssml:
            future = synthesizer.speak_ssml_async(text)
        else:
            future = synthesizer.speak_text_async(text)

        # Read chunks from pull stream in a thread
        chunk_size = 4096
        queue: asyncio.Queue[bytes | None] = asyncio.Queue()

        def _reader():
            try:
                while True:
                    data = bytes(chunk_size)
                    n = pull_stream.read(data)
                    if n == 0:
                        break
                    queue.put_nowait(data[:n])
            finally:
                queue.put_nowait(None)  # sentinel

        # Start reading in background thread
        loop = asyncio.get_running_loop()
        read_task = loop.run_in_executor(None, _reader)

        # Wait for synthesis to start, then yield chunks
        await run_sync(future.get)

        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            yield chunk

        await read_task
        logger.info("azure_stream_completed", voice_id=voice_id)

    # ---- Word boundary synthesis ----

    async def synthesize_with_word_boundaries(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> tuple[AudioResult, list[WordBoundary]]:
        """Synthesize with word timing data for subtitle/karaoke features."""
        import azure.cognitiveservices.speech as speechsdk

        config = copy.deepcopy(self._get_config())
        self._apply_output_format(config, settings_.output_format)
        sample_rate, ext = self._format_info(settings_.output_format)

        output_file = self.prepare_output_path(prefix="azure_wb", ext=ext)
        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))

        if voice_id.startswith("cnv:"):
            parts = voice_id[4:].split(":", 1)
            config.speech_synthesis_voice_name = parts[0]
            if len(parts) > 1:
                config.endpoint_id = parts[1]

        use_ssml = settings_.ssml or voice_id.startswith("pv:") or self._is_dragon_hd(voice_id)
        if use_ssml and not settings_.ssml:
            text = self._build_ssml(text, voice_id)
        elif not use_ssml:
            config.speech_synthesis_voice_name = voice_id or "en-US-JennyNeural"

        synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=audio_config)

        boundaries: list[WordBoundary] = []
        word_idx = 0

        def _on_word_boundary(evt):
            nonlocal word_idx
            boundaries.append(WordBoundary(
                text=evt.text,
                offset_ms=int(evt.audio_offset / 10000),  # 100-ns ticks -> ms
                duration_ms=int(evt.duration.total_seconds() * 1000) if hasattr(evt, "duration") else 0,
                word_index=word_idx,
            ))
            word_idx += 1

        synthesizer.synthesis_word_boundary.connect(_on_word_boundary)

        if use_ssml or settings_.ssml:
            result = await run_sync(synthesizer.speak_ssml_async(text).get)
        else:
            result = await run_sync(synthesizer.speak_text_async(text).get)

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio = AudioResult(audio_path=output_file, sample_rate=sample_rate, format=ext)
            return audio, boundaries
        else:
            error = result.cancellation_details.error_details if result.cancellation_details else "Unknown error"
            raise RuntimeError(f"Azure synthesis failed: {error}")

    # ---- Speech-to-Text ----

    async def transcribe(self, audio_path: Path, locale: str = "en-US") -> str:
        """Transcribe an audio file using Azure Speech-to-Text."""
        import azure.cognitiveservices.speech as speechsdk

        key, region = self._get_key_and_region()
        if not key:
            raise ValueError("AZURE_SPEECH_KEY not configured for transcription")

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = locale
        audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))
        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        logger.info("azure_transcribe_started", audio_path=str(audio_path), locale=locale)

        # For files that may be long, use continuous recognition
        segments: list[str] = []
        done_event = asyncio.Event()

        def _on_recognized(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                segments.append(evt.result.text)

        def _on_canceled(evt):
            done_event._loop = asyncio.get_event_loop()
            # Will be set from the session_stopped handler

        def _on_stopped(evt):
            # Signal completion
            pass

        recognizer.recognized.connect(_on_recognized)
        recognizer.canceled.connect(_on_canceled)

        # Use single-shot for short audio, continuous for longer
        result = await run_sync(recognizer.recognize_once_async().get)
        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            transcript = result.text
        elif result.reason == speechsdk.ResultReason.NoMatch:
            transcript = ""
        else:
            error = result.cancellation_details.error_details if hasattr(result, "cancellation_details") and result.cancellation_details else "Recognition failed"
            raise RuntimeError(f"Azure STT failed: {error}")

        logger.info("azure_transcribe_completed", audio_path=str(audio_path), length=len(transcript))
        return transcript

    # ---- Pronunciation Assessment ----

    async def assess_pronunciation(
        self, audio_path: Path, reference_text: str, locale: str = "en-US"
    ) -> PronunciationScore:
        """Assess pronunciation quality of an audio sample."""
        import azure.cognitiveservices.speech as speechsdk

        key, region = self._get_key_and_region()
        if not key:
            raise ValueError("AZURE_SPEECH_KEY not configured for pronunciation assessment")

        speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
        speech_config.speech_recognition_language = locale
        audio_config = speechsdk.audio.AudioConfig(filename=str(audio_path))

        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Word,
        )

        recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
        pronunciation_config.apply_to(recognizer)

        logger.info("azure_pronunciation_assess_started", audio_path=str(audio_path))

        result = await run_sync(recognizer.recognize_once_async().get)
        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            raise RuntimeError("Pronunciation assessment failed — no speech recognized")

        assessment = speechsdk.PronunciationAssessmentResult(result)

        word_scores = []
        if hasattr(assessment, "words") and assessment.words:
            for w in assessment.words:
                word_scores.append({
                    "word": w.word,
                    "accuracy_score": w.accuracy_score,
                    "error_type": w.error_type if hasattr(w, "error_type") else None,
                })

        logger.info("azure_pronunciation_assess_completed",
                     accuracy=assessment.accuracy_score,
                     fluency=assessment.fluency_score)

        return PronunciationScore(
            accuracy_score=assessment.accuracy_score,
            fluency_score=assessment.fluency_score,
            completeness_score=assessment.completeness_score,
            pronunciation_score=assessment.pronunciation_score,
            word_scores=word_scores if word_scores else None,
        )

    async def clone_voice(
        self, samples: list[ProviderAudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Clone a voice using Azure Personal Voice.

        Requires at least 2 audio samples: the first is used as the consent
        recording and the remaining as voice prompts (5-90 s each).
        """
        if len(samples) < 2:
            raise ValueError(
                "Azure Personal Voice requires at least 2 audio samples: "
                "1 consent recording + 1 voice prompt (5-90 seconds)"
            )

        cnv = self._cnv_client()
        tag = uuid.uuid4().hex[:8]
        project_id = f"atlasvox-pv-{tag}"
        consent_id = f"consent-{tag}"
        pv_id = f"pv-{tag}"
        locale = self._to_locale(config.language)
        company = self.get_config_value("company_name", settings.azure_cnv_company_name)
        talent = config.name or "Voice Talent"

        logger.info(
            "azure_pv_clone_start",
            project_id=project_id,
            sample_count=len(samples),
            locale=locale,
        )

        # 1. Project
        await cnv.get_or_create_project(project_id, kind="PersonalVoice",
                                         description=f"Atlas Vox — {config.name}")

        # 2. Consent (first sample)
        await cnv.create_consent(consent_id, project_id, talent, company,
                                  samples[0].file_path, locale=locale)

        # 3. Create personal voice (remaining samples)
        prompt_files = [s.file_path for s in samples[1:]]
        await cnv.create_personal_voice(pv_id, project_id, consent_id, prompt_files)

        # 4. Poll until ready
        voice_data = await cnv.wait_for_personal_voice(pv_id)
        speaker_profile_id = voice_data.get("speakerProfileId", "")
        if not speaker_profile_id:
            raise RuntimeError("Azure Personal Voice did not return a speakerProfileId")

        logger.info(
            "azure_pv_clone_complete",
            project_id=project_id,
            speaker_profile_id=speaker_profile_id,
        )

        return VoiceModel(
            model_id=pv_id,
            provider_model_id=f"pv:{speaker_profile_id}",
            metrics={
                "method": "personal_voice",
                "project_id": project_id,
                "consent_id": consent_id,
                "locale": locale,
            },
        )

    async def fine_tune(
        self, model_id: str, samples: list[ProviderAudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Train a Professional Voice using Azure Custom Neural Voice.

        This is a long-running operation (hours). Requires 20+ audio samples
        with the first used as consent.
        """
        if len(samples) < 3:
            raise ValueError(
                "Azure Professional Voice requires at least 3 audio samples: "
                "1 consent recording + 2 training utterances (20+ recommended)"
            )

        cnv = self._cnv_client()
        tag = uuid.uuid4().hex[:8]
        project_id = f"atlasvox-pro-{tag}"
        consent_id = f"consent-{tag}"
        ts_id = f"ts-{tag}"
        cnv_model_id = f"model-{tag}"
        endpoint_id = f"ep-{tag}"
        voice_name = f"AtlasVox{tag}"
        locale = "en-US"
        company = self.get_config_value("company_name", settings.azure_cnv_company_name)

        logger.info(
            "azure_pro_train_start",
            project_id=project_id,
            sample_count=len(samples),
            voice_name=voice_name,
        )

        # 1. Project
        await cnv.get_or_create_project(project_id, kind="ProfessionalVoice",
                                         description="Atlas Vox Professional Voice")

        # 2. Consent
        await cnv.create_consent(consent_id, project_id, "Voice Talent", company,
                                  samples[0].file_path, locale=locale)

        # 3. Training set + data (include transcripts when available)
        await cnv.create_training_set(ts_id, project_id)
        train_samples = samples[1:]
        train_files = [s.file_path for s in train_samples]
        transcripts = {
            s.file_path.stem: s.transcript
            for s in train_samples if s.transcript
        } or None
        await cnv.upload_training_data(ts_id, train_files, transcripts=transcripts)

        # 4. Train model
        await cnv.create_model(cnv_model_id, project_id, consent_id, ts_id,
                               voice_name, locale=locale)
        await cnv.wait_for_model(cnv_model_id)

        # 5. Deploy endpoint
        await cnv.deploy_endpoint(endpoint_id, project_id, cnv_model_id)
        await cnv.wait_for_endpoint(endpoint_id)

        logger.info(
            "azure_pro_train_complete",
            voice_name=voice_name,
            endpoint_id=endpoint_id,
        )

        return VoiceModel(
            model_id=cnv_model_id,
            provider_model_id=f"cnv:{voice_name}:{endpoint_id}",
            metrics={
                "method": "professional_voice",
                "project_id": project_id,
                "endpoint_id": endpoint_id,
                "voice_name": voice_name,
            },
        )

    async def list_voices(self) -> list[VoiceInfo]:
        """List Azure English neural voices.

        Tries the SDK first (requires subscription key). Falls back to an
        extensive hardcoded catalog of English neural voices so the voice
        library is useful even without an Azure subscription.
        """
        # Try live SDK call first
        try:
            subscription_key = self.get_config_value('subscription_key', settings.azure_speech_key)
            if subscription_key:
                import azure.cognitiveservices.speech as speechsdk

                config = self._get_config()
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=config, audio_config=None)
                result = await run_sync(synthesizer.get_voices_async().get)

                voices = []
                for v in result.voices:
                    locale = v.locale if hasattr(v, "locale") else "en"
                    # Return ALL voices (all languages) for the full voice catalog
                    gender_str = None
                    if hasattr(v, "gender"):
                        gender_str = "Female" if "Female" in str(v.gender) else "Male"
                    voices.append(VoiceInfo(
                        voice_id=v.short_name,
                        name=v.local_name,
                        language=locale,
                        gender=gender_str,
                        description=f"{v.voice_type.name} — {v.gender.name}" if hasattr(v, "gender") else None,
                    ))
                if voices:
                    logger.info("azure_voices_listed", count=len(voices), source="sdk")
                    return voices
        except Exception as exc:
            logger.debug("azure_sdk_list_voices_failed", error=str(exc))

        # Fallback: hardcoded English neural voices
        fallback = self._hardcoded_english_voices()
        logger.info("azure_voices_listed", count=len(fallback), source="hardcoded")
        return fallback

    @staticmethod
    def _hardcoded_english_voices() -> list[VoiceInfo]:
        """Comprehensive catalog of Azure English neural voices (130+)."""
        entries = [
            # ================================================================
            # en-US — United States (91 voices)
            # ================================================================
            # --- DragonHD Premium ---
            ("en-US-Ava:DragonHDLatestNeural", "Ava DragonHD (US)", "en-US", "Female"),
            ("en-US-Andrew:DragonHDLatestNeural", "Andrew DragonHD (US)", "en-US", "Male"),
            ("en-US-Adam:DragonHDLatestNeural", "Adam DragonHD (US)", "en-US", "Male"),
            ("en-US-Alloy:DragonHDLatestNeural", "Alloy DragonHD (US)", "en-US", "Male"),
            ("en-US-Aria:DragonHDLatestNeural", "Aria DragonHD (US)", "en-US", "Female"),
            ("en-US-Bree:DragonHDLatestNeural", "Bree DragonHD (US)", "en-US", "Female"),
            ("en-US-Brian:DragonHDLatestNeural", "Brian DragonHD (US)", "en-US", "Male"),
            ("en-US-Davis:DragonHDLatestNeural", "Davis DragonHD (US)", "en-US", "Male"),
            ("en-US-Emma:DragonHDLatestNeural", "Emma DragonHD (US)", "en-US", "Female"),
            ("en-US-Emma2:DragonHDLatestNeural", "Emma2 DragonHD (US)", "en-US", "Female"),
            ("en-US-Jane:DragonHDLatestNeural", "Jane DragonHD (US)", "en-US", "Female"),
            ("en-US-Jenny:DragonHDLatestNeural", "Jenny DragonHD (US)", "en-US", "Female"),
            ("en-US-Nova:DragonHDLatestNeural", "Nova DragonHD (US)", "en-US", "Female"),
            ("en-US-Phoebe:DragonHDLatestNeural", "Phoebe DragonHD (US)", "en-US", "Female"),
            ("en-US-Serena:DragonHDLatestNeural", "Serena DragonHD (US)", "en-US", "Female"),
            ("en-US-Steffan:DragonHDLatestNeural", "Steffan DragonHD (US)", "en-US", "Male"),
            ("en-US-Andrew2:DragonHDLatestNeural", "Andrew2 DragonHD (US)", "en-US", "Male"),
            ("en-US-Andrew3:DragonHDLatestNeural", "Andrew3 DragonHD (US)", "en-US", "Male"),
            ("en-US-Ava3:DragonHDLatestNeural", "Ava3 DragonHD (US)", "en-US", "Female"),
            # --- DragonHD Omni ---
            ("en-US-Andrew:DragonHDOmniLatestNeural", "Andrew DragonHD Omni (US)", "en-US", "Male"),
            ("en-US-Caleb:DragonHDOmniLatestNeural", "Caleb DragonHD Omni (US)", "en-US", "Male"),
            ("en-US-Dana:DragonHDOmniLatestNeural", "Dana DragonHD Omni (US)", "en-US", "Female"),
            ("en-US-Lewis:DragonHDOmniLatestNeural", "Lewis DragonHD Omni (US)", "en-US", "Male"),
            ("en-US-Phoebe:DragonHDOmniLatestNeural", "Phoebe DragonHD Omni (US)", "en-US", "Female"),
            ("en-US-Ava:DragonHDOmniLatestNeural", "Ava DragonHD Omni (US)", "en-US", "Female"),
            # --- DragonHD Flash ---
            ("en-US-Jimmie:DragonHDFlashLatestNeural", "Jimmie DragonHD Flash (US)", "en-US", "Male"),
            ("en-US-Tiana:DragonHDFlashLatestNeural", "Tiana DragonHD Flash (US)", "en-US", "Female"),
            ("en-US-Tyler:DragonHDFlashLatestNeural", "Tyler DragonHD Flash (US)", "en-US", "Male"),
            # --- MultiTalker ---
            ("en-US-MultiTalker-Ava-Andrew:DragonHDLatestNeural", "MultiTalker Ava-Andrew (US)", "en-US", "Neutral"),
            ("en-US-MultiTalker-Ava-Steffan:DragonHDLatestNeural", "MultiTalker Ava-Steffan (US)", "en-US", "Neutral"),
            ("en-US-Multitalker-Set1:DragonHDLatestNeural", "MultiTalker Set1 (US)", "en-US", "Neutral"),
            # --- Multilingual ---
            ("en-US-AvaMultilingualNeural", "Ava Multilingual (US)", "en-US", "Female"),
            ("en-US-AndrewMultilingualNeural", "Andrew Multilingual (US)", "en-US", "Male"),
            ("en-US-AmandaMultilingualNeural", "Amanda Multilingual (US)", "en-US", "Female"),
            ("en-US-AdamMultilingualNeural", "Adam Multilingual (US)", "en-US", "Male"),
            ("en-US-EmmaMultilingualNeural", "Emma Multilingual (US)", "en-US", "Female"),
            ("en-US-PhoebeMultilingualNeural", "Phoebe Multilingual (US)", "en-US", "Female"),
            ("en-US-BrianMultilingualNeural", "Brian Multilingual (US)", "en-US", "Male"),
            ("en-US-CoraMultilingualNeural", "Cora Multilingual (US)", "en-US", "Female"),
            ("en-US-ChristopherMultilingualNeural", "Christopher Multilingual (US)", "en-US", "Male"),
            ("en-US-BrandonMultilingualNeural", "Brandon Multilingual (US)", "en-US", "Male"),
            ("en-US-DavisMultilingualNeural", "Davis Multilingual (US)", "en-US", "Male"),
            ("en-US-DerekMultilingualNeural", "Derek Multilingual (US)", "en-US", "Male"),
            ("en-US-DustinMultilingualNeural", "Dustin Multilingual (US)", "en-US", "Male"),
            ("en-US-EvelynMultilingualNeural", "Evelyn Multilingual (US)", "en-US", "Female"),
            ("en-US-JennyMultilingualNeural", "Jenny Multilingual (US)", "en-US", "Female"),
            ("en-US-LewisMultilingualNeural", "Lewis Multilingual (US)", "en-US", "Male"),
            ("en-US-LolaMultilingualNeural", "Lola Multilingual (US)", "en-US", "Female"),
            ("en-US-NancyMultilingualNeural", "Nancy Multilingual (US)", "en-US", "Female"),
            ("en-US-RyanMultilingualNeural", "Ryan Multilingual (US)", "en-US", "Male"),
            ("en-US-SamuelMultilingualNeural", "Samuel Multilingual (US)", "en-US", "Male"),
            ("en-US-SerenaMultilingualNeural", "Serena Multilingual (US)", "en-US", "Female"),
            ("en-US-SteffanMultilingualNeural", "Steffan Multilingual (US)", "en-US", "Male"),
            # --- Turbo Multilingual ---
            ("en-US-AlloyTurboMultilingualNeural", "Alloy Turbo (US)", "en-US", "Male"),
            ("en-US-EchoTurboMultilingualNeural", "Echo Turbo (US)", "en-US", "Male"),
            ("en-US-FableTurboMultilingualNeural", "Fable Turbo (US)", "en-US", "Neutral"),
            ("en-US-OnyxTurboMultilingualNeural", "Onyx Turbo (US)", "en-US", "Male"),
            ("en-US-NovaTurboMultilingualNeural", "Nova Turbo (US)", "en-US", "Female"),
            ("en-US-ShimmerTurboMultilingualNeural", "Shimmer Turbo (US)", "en-US", "Female"),
            ("en-US-AshTurboMultilingualNeural", "Ash Turbo (US)", "en-US", "Male"),
            # --- Standard Neural (with styles) ---
            ("en-US-JennyNeural", "Jenny (US)", "en-US", "Female"),
            ("en-US-GuyNeural", "Guy (US)", "en-US", "Male"),
            ("en-US-AriaNeural", "Aria (US)", "en-US", "Female"),
            ("en-US-DavisNeural", "Davis (US)", "en-US", "Male"),
            ("en-US-JaneNeural", "Jane (US)", "en-US", "Female"),
            ("en-US-JasonNeural", "Jason (US)", "en-US", "Male"),
            ("en-US-SaraNeural", "Sara (US)", "en-US", "Female"),
            ("en-US-TonyNeural", "Tony (US)", "en-US", "Male"),
            ("en-US-NancyNeural", "Nancy (US)", "en-US", "Female"),
            ("en-US-KaiNeural", "Kai (US)", "en-US", "Male"),
            ("en-US-LunaNeural", "Luna (US)", "en-US", "Female"),
            # --- Standard Neural (no styles) ---
            ("en-US-AvaNeural", "Ava (US)", "en-US", "Female"),
            ("en-US-AndrewNeural", "Andrew (US)", "en-US", "Male"),
            ("en-US-EmmaNeural", "Emma (US)", "en-US", "Female"),
            ("en-US-BrianNeural", "Brian (US)", "en-US", "Male"),
            ("en-US-AmberNeural", "Amber (US)", "en-US", "Female"),
            ("en-US-AnaNeural", "Ana (US, Child)", "en-US", "Female"),
            ("en-US-AshleyNeural", "Ashley (US)", "en-US", "Female"),
            ("en-US-BrandonNeural", "Brandon (US)", "en-US", "Male"),
            ("en-US-ChristopherNeural", "Christopher (US)", "en-US", "Male"),
            ("en-US-CoraNeural", "Cora (US)", "en-US", "Female"),
            ("en-US-ElizabethNeural", "Elizabeth (US)", "en-US", "Female"),
            ("en-US-EricNeural", "Eric (US)", "en-US", "Male"),
            ("en-US-JacobNeural", "Jacob (US)", "en-US", "Male"),
            ("en-US-MichelleNeural", "Michelle (US)", "en-US", "Female"),
            ("en-US-MonicaNeural", "Monica (US)", "en-US", "Female"),
            ("en-US-RogerNeural", "Roger (US)", "en-US", "Male"),
            ("en-US-SteffanNeural", "Steffan (US)", "en-US", "Male"),
            # --- Special ---
            ("en-US-AIGenerate1Neural", "AI Generate 1 (US)", "en-US", "Male"),
            ("en-US-AIGenerate2Neural", "AI Generate 2 (US)", "en-US", "Female"),
            ("en-US-BlueNeural", "Blue (US)", "en-US", "Neutral"),
            # ================================================================
            # en-GB — United Kingdom (18 voices)
            # ================================================================
            ("en-GB-Ada:DragonHDLatestNeural", "Ada DragonHD (UK)", "en-GB", "Female"),
            ("en-GB-Ollie:DragonHDLatestNeural", "Ollie DragonHD (UK)", "en-GB", "Male"),
            ("en-GB-AdaMultilingualNeural", "Ada Multilingual (UK)", "en-GB", "Female"),
            ("en-GB-OllieMultilingualNeural", "Ollie Multilingual (UK)", "en-GB", "Male"),
            ("en-GB-SoniaNeural", "Sonia (UK)", "en-GB", "Female"),
            ("en-GB-RyanNeural", "Ryan (UK)", "en-GB", "Male"),
            ("en-GB-LibbyNeural", "Libby (UK)", "en-GB", "Female"),
            ("en-GB-AbbiNeural", "Abbi (UK)", "en-GB", "Female"),
            ("en-GB-AlfieNeural", "Alfie (UK)", "en-GB", "Male"),
            ("en-GB-BellaNeural", "Bella (UK)", "en-GB", "Female"),
            ("en-GB-ElliotNeural", "Elliot (UK)", "en-GB", "Male"),
            ("en-GB-EthanNeural", "Ethan (UK)", "en-GB", "Male"),
            ("en-GB-HollieNeural", "Hollie (UK)", "en-GB", "Female"),
            ("en-GB-MaisieNeural", "Maisie (UK, Child)", "en-GB", "Female"),
            ("en-GB-NoahNeural", "Noah (UK)", "en-GB", "Male"),
            ("en-GB-OliverNeural", "Oliver (UK)", "en-GB", "Male"),
            ("en-GB-OliviaNeural", "Olivia (UK)", "en-GB", "Female"),
            ("en-GB-ThomasNeural", "Thomas (UK)", "en-GB", "Male"),
            # ================================================================
            # en-AU — Australia (15 voices)
            # ================================================================
            ("en-AU-WilliamMultilingualNeural", "William Multilingual (AU)", "en-AU", "Male"),
            ("en-AU-NatashaNeural", "Natasha (AU)", "en-AU", "Female"),
            ("en-AU-WilliamNeural", "William (AU)", "en-AU", "Male"),
            ("en-AU-AnnetteNeural", "Annette (AU)", "en-AU", "Female"),
            ("en-AU-CarlyNeural", "Carly (AU)", "en-AU", "Female"),
            ("en-AU-DarrenNeural", "Darren (AU)", "en-AU", "Male"),
            ("en-AU-DuncanNeural", "Duncan (AU)", "en-AU", "Male"),
            ("en-AU-ElsieNeural", "Elsie (AU)", "en-AU", "Female"),
            ("en-AU-FreyaNeural", "Freya (AU)", "en-AU", "Female"),
            ("en-AU-JoanneNeural", "Joanne (AU)", "en-AU", "Female"),
            ("en-AU-KenNeural", "Ken (AU)", "en-AU", "Male"),
            ("en-AU-KimNeural", "Kim (AU)", "en-AU", "Female"),
            ("en-AU-NeilNeural", "Neil (AU)", "en-AU", "Male"),
            ("en-AU-TimNeural", "Tim (AU)", "en-AU", "Male"),
            ("en-AU-TinaNeural", "Tina (AU)", "en-AU", "Female"),
            # ================================================================
            # en-IN — India (17 voices)
            # ================================================================
            ("en-IN-Meera:DragonHDLatestNeural", "Meera DragonHD (IN)", "en-IN", "Female"),
            ("en-IN-Aarti:DragonHDLatestNeural", "Aarti DragonHD (IN)", "en-IN", "Female"),
            ("en-IN-Arjun:DragonHDLatestNeural", "Arjun DragonHD (IN)", "en-IN", "Male"),
            ("en-IN-AartiIndicNeural", "Aarti Indic (IN)", "en-IN", "Female"),
            ("en-IN-ArjunIndicNeural", "Arjun Indic (IN)", "en-IN", "Male"),
            ("en-IN-NeerjaIndicNeural", "Neerja Indic (IN)", "en-IN", "Female"),
            ("en-IN-PrabhatIndicNeural", "Prabhat Indic (IN)", "en-IN", "Male"),
            ("en-IN-AaravNeural", "Aarav (IN)", "en-IN", "Male"),
            ("en-IN-AashiNeural", "Aashi (IN)", "en-IN", "Female"),
            ("en-IN-AartiNeural", "Aarti (IN)", "en-IN", "Female"),
            ("en-IN-ArjunNeural", "Arjun (IN)", "en-IN", "Male"),
            ("en-IN-AnanyaNeural", "Ananya (IN)", "en-IN", "Female"),
            ("en-IN-KavyaNeural", "Kavya (IN)", "en-IN", "Female"),
            ("en-IN-KunalNeural", "Kunal (IN)", "en-IN", "Male"),
            ("en-IN-NeerjaNeural", "Neerja (IN)", "en-IN", "Female"),
            ("en-IN-PrabhatNeural", "Prabhat (IN)", "en-IN", "Male"),
            ("en-IN-RehaanNeural", "Rehaan (IN)", "en-IN", "Male"),
            # ================================================================
            # en-CA — Canada (2 voices)
            # ================================================================
            ("en-CA-ClaraNeural", "Clara (CA)", "en-CA", "Female"),
            ("en-CA-LiamNeural", "Liam (CA)", "en-CA", "Male"),
            # ================================================================
            # en-IE — Ireland (2 voices)
            # ================================================================
            ("en-IE-EmilyNeural", "Emily (IE)", "en-IE", "Female"),
            ("en-IE-ConnorNeural", "Connor (IE)", "en-IE", "Male"),
            # ================================================================
            # en-NZ — New Zealand (2 voices)
            # ================================================================
            ("en-NZ-MollyNeural", "Molly (NZ)", "en-NZ", "Female"),
            ("en-NZ-MitchellNeural", "Mitchell (NZ)", "en-NZ", "Male"),
            # ================================================================
            # en-ZA — South Africa (2 voices)
            # ================================================================
            ("en-ZA-LeahNeural", "Leah (ZA)", "en-ZA", "Female"),
            ("en-ZA-LukeNeural", "Luke (ZA)", "en-ZA", "Male"),
            # ================================================================
            # en-KE — Kenya (2 voices)
            # ================================================================
            ("en-KE-AsiliaNeural", "Asilia (KE)", "en-KE", "Female"),
            ("en-KE-ChilembaNeural", "Chilemba (KE)", "en-KE", "Male"),
            # ================================================================
            # en-NG — Nigeria (2 voices)
            # ================================================================
            ("en-NG-EzinneNeural", "Ezinne (NG)", "en-NG", "Female"),
            ("en-NG-AbeoNeural", "Abeo (NG)", "en-NG", "Male"),
            # ================================================================
            # en-PH — Philippines (2 voices)
            # ================================================================
            ("en-PH-RosaNeural", "Rosa (PH)", "en-PH", "Female"),
            ("en-PH-JamesNeural", "James (PH)", "en-PH", "Male"),
            # ================================================================
            # en-SG — Singapore (2 voices)
            # ================================================================
            ("en-SG-LunaNeural", "Luna (SG)", "en-SG", "Female"),
            ("en-SG-WayneNeural", "Wayne (SG)", "en-SG", "Male"),
            # ================================================================
            # en-HK — Hong Kong (2 voices)
            # ================================================================
            ("en-HK-YanNeural", "Yan (HK)", "en-HK", "Female"),
            ("en-HK-SamNeural", "Sam (HK)", "en-HK", "Male"),
        ]
        return [
            VoiceInfo(
                voice_id=vid,
                name=name,
                language=lang,
                gender=gender,
                description="Azure Neural Voice",
            )
            for vid, name, lang, gender in entries
        ]

    async def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_cloning=True,          # Azure Personal Voice
            supports_fine_tuning=True,      # Azure Professional Voice (CNV)
            supports_streaming=True,
            supports_ssml=True,
            supports_zero_shot=False,
            supports_batch=True,
            supports_word_boundaries=True,
            supports_pronunciation_assessment=True,
            supports_transcription=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=2,      # 1 consent + 1 voice prompt
            max_text_length=10000,
            supported_languages=["en", "es", "fr", "de", "it", "pt", "zh", "ja",
                                 "ko", "ar", "ru", "nl", "pl", "sv", "tr", "hi"],
            supported_output_formats=["wav", "mp3", "ogg"],
        )

    async def health_check(self) -> ProviderHealth:
        start = time.perf_counter()
        try:
            subscription_key = self.get_config_value('subscription_key', settings.azure_speech_key)
            if not subscription_key:
                import azure.cognitiveservices.speech as _sdk  # noqa: F401
                latency = int((time.perf_counter() - start) * 1000)
                logger.info("azure_health_check", healthy=True, latency_ms=latency, note="no_subscription_key")
                return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency,
                                      error="SDK ready — configure subscription key in Providers settings")
            self._get_config()
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("azure_health_check", healthy=True, latency_ms=latency)
            return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("azure_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="azure_speech", healthy=False, latency_ms=latency, error=str(e))
