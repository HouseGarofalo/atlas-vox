"""Remote TTS provider — bridges Atlas Vox to a GPU TTS service via HTTP."""

from __future__ import annotations

import time
import uuid

import httpx
import structlog

from app.core.config import settings
from app.providers.base import (
    AudioResult,
    AudioSample,
    CloneConfig,
    FineTuneConfig,
    ProviderCapabilities,
    ProviderHealth,
    SynthesisSettings,
    TTSProvider,
    VoiceInfo,
    VoiceModel,
)

logger = structlog.get_logger(__name__)


class RemoteProvider(TTSProvider):
    """Bridges Atlas Vox to a remote GPU TTS service via HTTP.

    All TTS operations are delegated to the GPU service at the configured URL.
    The provider handles connection failures, timeouts, and HTTP errors gracefully
    so that Atlas Vox continues operating even when the GPU service is offline.
    """

    def __init__(
        self,
        name: str,
        display_name: str,
        gpu_service_url: str,
        timeout: int = 120,
    ) -> None:
        self._name = name
        self._display_name = display_name
        self._base_url = gpu_service_url.rstrip("/")
        self._timeout = timeout
        self._capabilities_cache: ProviderCapabilities | None = None

        # Set up auth headers
        headers = {}
        if settings.gpu_service_api_key:
            headers["Authorization"] = f"Bearer {settings.gpu_service_api_key}"

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout, connect=10.0),
            headers=headers,
        )

    async def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        await self._client.aclose()

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        """Synthesize text via the remote GPU service."""
        url = f"{self._base_url}/providers/{self._name}/synthesize"
        output_file = self.prepare_output_path(prefix=self._name, ext="wav")

        logger.info(
            "remote_synthesize_started",
            provider=self._name,
            voice_id=voice_id,
            text_length=len(text),
        )
        start = time.perf_counter()
        try:
            resp = await self._client.post(
                url,
                json={
                    "text": text,
                    "voice_id": voice_id,
                    "speed": settings_.speed,
                },
            )
            resp.raise_for_status()
        except Exception as exc:
            elapsed = time.perf_counter() - start
            logger.error(
                "remote_synthesize_failed",
                provider=self._name,
                voice_id=voice_id,
                latency_ms=int(elapsed * 1000),
                error=str(exc),
            )
            raise

        output_file.write_bytes(resp.content)
        elapsed = time.perf_counter() - start

        # Try to determine duration from WAV header (PCM 16-bit)
        duration: float | None = None
        try:
            import wave

            with wave.open(str(output_file), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    duration = frames / rate
        except Exception:
            pass

        logger.info(
            "remote_synthesize_completed",
            provider=self._name,
            voice_id=voice_id,
            duration_seconds=duration,
            latency_ms=int(elapsed * 1000),
        )
        return AudioResult(
            audio_path=output_file,
            duration_seconds=duration,
            sample_rate=22050,
            format="wav",
        )

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        """Clone a voice via the remote GPU service."""
        url = f"{self._base_url}/providers/{self._name}/clone"

        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for sample in samples:
            file_bytes = sample.file_path.read_bytes()
            files.append(
                ("files", (sample.file_path.name, file_bytes, "audio/wav"))
            )

        data: dict[str, str] = {}
        if config.name:
            data["voice_name"] = config.name
        if config.language:
            data["language"] = config.language

        resp = await self._client.post(url, files=files, data=data)
        resp.raise_for_status()

        result = resp.json()
        logger.info(
            "remote_clone_complete",
            provider=self._name,
            voice_id=result.get("voice_id"),
        )
        return VoiceModel(
            model_id=result.get("voice_id", f"{self._name}_clone_{uuid.uuid4().hex[:8]}"),
            model_path=None,
            provider_model_id=result.get("voice_id"),
            metrics=result.get("metrics"),
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        """Fine-tune via the remote GPU service (if supported)."""
        url = f"{self._base_url}/providers/{self._name}/fine-tune"

        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for sample in samples:
            file_bytes = sample.file_path.read_bytes()
            files.append(
                ("files", (sample.file_path.name, file_bytes, "audio/wav"))
            )

        data: dict[str, str] = {
            "model_id": model_id,
            "epochs": str(config.epochs),
            "learning_rate": str(config.learning_rate),
            "batch_size": str(config.batch_size),
        }

        resp = await self._client.post(url, files=files, data=data)
        resp.raise_for_status()

        result = resp.json()
        logger.info("remote_fine_tune_complete", provider=self._name)
        return VoiceModel(
            model_id=result.get("model_id", model_id),
            model_path=None,
            provider_model_id=result.get("model_id"),
            metrics=result.get("metrics"),
        )

    async def list_voices(self) -> list[VoiceInfo]:
        """List voices from the remote GPU service."""
        url = f"{self._base_url}/providers/{self._name}/voices"
        try:
            resp = await self._client.get(url)
            resp.raise_for_status()

            voices_data = resp.json()
            voices: list[VoiceInfo] = []
            for v in voices_data if isinstance(voices_data, list) else voices_data.get("voices", []):
                voices.append(
                    VoiceInfo(
                        voice_id=v.get("voice_id", v.get("id", "")),
                        name=v.get("name", v.get("voice_id", "unknown")),
                        language=v.get("language", "en"),
                        gender=v.get("gender"),
                        description=v.get("description"),
                        preview_url=v.get("preview_url"),
                    )
                )
            logger.info("remote_voices_listed", provider=self._name, count=len(voices))
            return voices
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            logger.warning("remote_list_voices_failed", provider=self._name, error=str(exc))
            return []
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "remote_list_voices_http_error",
                provider=self._name,
                status=exc.response.status_code,
            )
            return []

    async def get_capabilities(self) -> ProviderCapabilities:
        """Get capabilities from the remote GPU service (cached after first call)."""
        if self._capabilities_cache is not None:
            return self._capabilities_cache

        url = f"{self._base_url}/providers"
        try:
            resp = await self._client.get(url, timeout=10.0)
            resp.raise_for_status()

            data = resp.json()
            providers_list = data.get("providers", [])
            for p in providers_list:
                if p.get("name") == self._name:
                    caps = p.get("capabilities", {})
                    self._capabilities_cache = ProviderCapabilities(
                        supports_cloning=caps.get("supports_cloning", False),
                        supports_fine_tuning=caps.get("supports_fine_tuning", False),
                        supports_streaming=caps.get("supports_streaming", False),
                        supports_ssml=caps.get("supports_ssml", False),
                        supports_zero_shot=caps.get("supports_zero_shot", False),
                        supports_batch=caps.get("supports_batch", False),
                        requires_gpu=caps.get("requires_gpu", True),
                        gpu_mode=caps.get("gpu_mode", "docker_gpu"),
                        min_samples_for_cloning=caps.get("min_samples_for_cloning", 0),
                        max_text_length=caps.get("max_text_length", 5000),
                        supported_languages=caps.get("supported_languages", ["en"]),
                        supported_output_formats=caps.get("supported_output_formats", ["wav"]),
                    )
                    return self._capabilities_cache
        except Exception as exc:
            logger.warning(
                "remote_capabilities_fetch_failed",
                provider=self._name,
                error=str(exc),
            )

        # Return sensible defaults if the GPU service is unreachable
        self._capabilities_cache = ProviderCapabilities(
            supports_cloning=True,
            requires_gpu=True,
            gpu_mode="docker_gpu",
        )
        return self._capabilities_cache

    async def health_check(self) -> ProviderHealth:
        """Check health of this provider on the remote GPU service."""
        url = f"{self._base_url}/providers/{self._name}/health"
        start = time.perf_counter()
        try:
            resp = await self._client.post(url, timeout=15.0)
            latency = int((time.perf_counter() - start) * 1000)

            if resp.status_code == 200:
                data = resp.json()
                health = ProviderHealth(
                    name=self._name,
                    healthy=data.get("healthy", True),
                    latency_ms=latency,
                    error=data.get("error"),
                )
                logger.info("remote_health_check", provider=self._name, healthy=health.healthy, latency_ms=latency)
                return health
            else:
                logger.info("remote_health_check", provider=self._name, healthy=False, latency_ms=latency, status_code=resp.status_code)
                return ProviderHealth(
                    name=self._name,
                    healthy=False,
                    latency_ms=latency,
                    error=f"HTTP {resp.status_code}",
                )
        except httpx.ConnectError:
            logger.warning("remote_health_check", provider=self._name, healthy=False, error="gpu_service_not_reachable")
            return ProviderHealth(
                name=self._name,
                healthy=False,
                error="GPU service not reachable",
            )
        except httpx.TimeoutException:
            logger.warning("remote_health_check", provider=self._name, healthy=False, error="timeout")
            return ProviderHealth(
                name=self._name,
                healthy=False,
                error="GPU service timeout",
            )
        except Exception as exc:
            return ProviderHealth(
                name=self._name,
                healthy=False,
                error=str(exc),
            )
