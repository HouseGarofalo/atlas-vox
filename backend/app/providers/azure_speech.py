"""Azure AI Speech provider — cloud TTS with SSML, Personal Voice cloning, and Professional Voice training.

Supports both API key and Microsoft Entra ID (formerly Azure AD) token-based
authentication.  When ``auth_mode`` is ``"auto"`` (the default), the provider
uses Entra ID tokens if no subscription key is configured, and API keys
otherwise.  Set ``auth_mode`` to ``"entra_token"`` to force token-based auth
even when a key is present.

For Entra ID auth:
- Install ``azure-identity``: ``pip install azure-identity``
- Set ``resource_id`` to the full ARM Resource ID of your Cognitive Services
  account (found in Azure Portal → Properties → Resource ID).
- The caller must have ``Cognitive Services User`` or
  ``Cognitive Services Speech Contributor`` RBAC role on the resource.
- ``DefaultAzureCredential`` is used, which chains through env-var service
  principal, managed identity, Azure CLI, and more.
"""

from __future__ import annotations

import asyncio
import copy
import io
import json
import threading
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

# Module-level cache for hardcoded Azure voice data loaded from JSON.
_azure_voices_cache: list[VoiceInfo] | None = None

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

# Scope for all Azure Cognitive Services Entra ID tokens
_COGNITIVE_SERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


# ---------------------------------------------------------------------------
# Azure Entra ID Token Manager
# ---------------------------------------------------------------------------

class AzureTokenManager:
    """Thread-safe token manager for Azure Entra ID authentication.

    Acquires tokens via ``azure.identity.DefaultAzureCredential`` and caches
    them until 5 minutes before expiry.  Provides both raw bearer tokens
    (for REST API calls) and composite tokens in the ``aad#<resource_id>#<jwt>``
    format required by the Speech SDK's ``SpeechSynthesizer``.
    """

    def __init__(self, resource_id: str = "", config: dict | None = None) -> None:
        self.resource_id = resource_id
        self._config = config or {}
        self._token: str | None = None
        self._expires_on: float = 0
        self._lock = threading.Lock()
        self._credential = None
        # Refresh 5 minutes before expiry
        self._refresh_margin = 300

    def _get_credential(self):
        """Lazy-load the credential to avoid importing azure.identity at module level."""
        if self._credential is None:
            try:
                from azure.identity import DefaultAzureCredential
            except ImportError:
                raise ImportError(
                    "azure-identity is required for Entra ID authentication. "
                    "Install with: pip install azure-identity"
                )

            # Build credential from config if SP fields present
            tenant_id = self._config.get("tenant_id", "")
            client_id = self._config.get("client_id", "")
            client_secret = self._config.get("client_secret", "")

            if tenant_id and client_id and client_secret:
                from azure.identity import ClientSecretCredential
                self._credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret,
                )
                logger.info("azure_token_manager_using_service_principal")
            else:
                self._credential = DefaultAzureCredential()
                logger.info("azure_token_manager_using_default_credential")
        return self._credential

    def get_token(self) -> str:
        """Get a valid access token string, refreshing if expired or near-expiry.

        Priority: Redis-cached token (from device code / SP login) → direct credential.
        """
        # First, try the shared auth manager (Redis cache + device code tokens)
        try:
            from app.providers.azure_auth import get_azure_auth_manager
            cached = get_azure_auth_manager().get_cached_token(self._config)
            if cached:
                return cached
        except Exception as exc:
            logger.debug("azure_auth_manager_unavailable", error=str(exc))
        with self._lock:
            now = time.time()
            if self._token is None or now >= (self._expires_on - self._refresh_margin):
                credential = self._get_credential()
                try:
                    result = credential.get_token(_COGNITIVE_SERVICES_SCOPE)
                except Exception as exc:
                    error_msg = str(exc)
                    # Provide actionable error messages for auth failures
                    if "unauthorized" in error_msg.lower() or "401" in error_msg:
                        raise RuntimeError(
                            "Azure authentication failed (401 Unauthorized). "
                            "Your credentials may have expired. Please re-login "
                            "via the Azure Login section in the provider settings."
                        ) from exc
                    if "forbidden" in error_msg.lower() or "403" in error_msg:
                        raise RuntimeError(
                            "Azure authorization failed (403 Forbidden). "
                            "Your account may lack the 'Cognitive Services User' "
                            "or 'Cognitive Services Speech Contributor' RBAC role "
                            "on the Azure Speech resource."
                        ) from exc
                    raise
                self._token = result.token
                self._expires_on = result.expires_on
                logger.debug(
                    "azure_entra_token_acquired",
                    expires_in=int(self._expires_on - now),
                )
            return self._token

    def get_composite_token(self) -> str:
        """Get composite token for SpeechSynthesizer ``auth_token`` parameter.

        Format: ``aad#<resource_id>#<jwt_token>``
        """
        if not self.resource_id:
            raise ValueError(
                "resource_id is required for Entra ID Speech SDK auth. "
                "Set AZURE_SPEECH_RESOURCE_ID to the full ARM Resource ID "
                "(e.g., /subscriptions/.../Microsoft.CognitiveServices/accounts/...)"
            )
        raw = self.get_token()
        return f"aad#{self.resource_id}#{raw}"

    def get_bearer_header(self) -> dict[str, str]:
        """Get ``Authorization: Bearer`` header dict for REST API calls."""
        return {"Authorization": f"Bearer {self.get_token()}"}

    def close(self) -> None:
        """Release credential resources."""
        if self._credential is not None and hasattr(self._credential, "close"):
            try:
                self._credential.close()
            except Exception:
                pass
            self._credential = None


# ---------------------------------------------------------------------------
# Custom Neural Voice REST client
# ---------------------------------------------------------------------------

class AzureCNVClient:
    """REST API client for Azure Custom Voice (Personal + Professional).

    Supports both API key (``Ocp-Apim-Subscription-Key`` header) and
    Entra ID token (``Authorization: Bearer`` header) authentication.
    """

    def __init__(
        self,
        region: str,
        subscription_key: str | None = None,
        token_manager: AzureTokenManager | None = None,
    ) -> None:
        self.subscription_key = subscription_key
        self.token_manager = token_manager
        self.region = region
        self.base_url = f"https://{region}.api.cognitive.microsoft.com/customvoice"

        if not subscription_key and not token_manager:
            raise ValueError(
                "AzureCNVClient requires either a subscription_key or token_manager"
            )

    def _auth_headers(self) -> dict[str, str]:
        """Return authentication headers — bearer token or API key."""
        if self.token_manager:
            return self.token_manager.get_bearer_header()
        return {"Ocp-Apim-Subscription-Key": self.subscription_key}

    def _json_headers(self) -> dict[str, str]:
        return {**self._auth_headers(), "Content-Type": "application/json"}

    @staticmethod
    def _raise_for_auth(resp) -> None:
        """Raise with actionable message for 401/403 from Azure APIs."""
        if resp.status_code == 401:
            raise RuntimeError(
                "Azure API returned 401 Unauthorized. Your authentication "
                "token may have expired. Please re-login via the Azure Login "
                "section in the provider settings."
            )
        if resp.status_code == 403:
            raise PermissionError(
                "Azure API returned 403 Forbidden. Your account may lack "
                "the required RBAC role ('Cognitive Services User' or "
                "'Cognitive Services Speech Contributor') on the Speech resource."
            )

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
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def get_consent(self, consent_id: str) -> dict:
        """Get consent status."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"consents/{consent_id}"),
                headers=self._auth_headers(),
            )
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def wait_for_consent(self, consent_id: str,
                                poll_interval: int = 3,
                                timeout: int = 120) -> dict:
        """Poll consent until Succeeded/Failed. Consent creation is async."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            consent = await self.get_consent(consent_id)
            status = consent.get("status", "")
            logger.info("azure_consent_poll", id=consent_id, status=status)
            if status == "Succeeded":
                return consent
            if status == "Failed":
                props = consent.get("properties", {})
                error_msg = props.get("error", {}).get("message", str(consent))
                if "AudioAndScriptNotMatch" in error_msg or "AudioAndScriptNotMatch" in str(consent):
                    raise ValueError(
                        "Azure consent validation failed: the audio does not match the "
                        "required consent statement. The first audio sample must be a "
                        "recording of the speaker reading the consent statement verbatim. "
                        "See: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/"
                        "personal-voice-consent"
                    )
                raise RuntimeError(f"Consent creation failed: {error_msg}")
            await asyncio.sleep(poll_interval)
        raise TimeoutError(f"Consent creation timed out after {timeout}s")

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

            if resp.status_code == 403:
                raise PermissionError(
                    "Azure Personal Voice access denied (403 Forbidden). "
                    "Your resource may not have Personal Voice enabled. "
                    "Apply for access at https://aka.ms/customneural"
                )
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def get_personal_voice(self, personal_voice_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"personalvoices/{personal_voice_id}"),
                headers=self._auth_headers(),
            )
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def get_model(self, model_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"models/{model_id}"),
                headers=self._auth_headers(),
            )
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def get_endpoint(self, endpoint_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                self._url(f"endpoints/{endpoint_id}"),
                headers=self._auth_headers(),
            )
            self._raise_for_auth(resp)
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
            self._raise_for_auth(resp)
            resp.raise_for_status()
            return resp.json()

    async def get_batch_synthesis(self, batch_id: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://{self.region}.customvoice.api.speech.microsoft.com"
                f"/api/batchsyntheses/{batch_id}?api-version={CNV_API_VERSION}",
                headers=self._auth_headers(),
            )
            self._raise_for_auth(resp)
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


# ---------------------------------------------------------------------------
# Main Provider
# ---------------------------------------------------------------------------

class AzureSpeechProvider(TTSProvider):
    """Azure AI Speech — cloud TTS with SSML, Personal Voice cloning, and Professional Voice training.

    Supports dual authentication:
    - **API key**: traditional ``Ocp-Apim-Subscription-Key`` header
    - **Entra ID token**: ``Authorization: Bearer`` header + composite
      ``aad#<resource_id>#<token>`` for the Speech SDK

    Auth mode is controlled by the ``auth_mode`` config value:
    - ``"api_key"``: always use subscription key
    - ``"entra_token"``: always use Entra ID (requires ``resource_id``)
    - ``"auto"`` (default): use Entra ID if no key configured, else use key
    """

    def __init__(self) -> None:
        self._speech_config = None
        self._token_manager: AzureTokenManager | None = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._speech_config = None
        # Reset token manager on reconfigure
        if self._token_manager:
            self._token_manager.close()
            self._token_manager = None

    # ---- Auth helpers ----

    def _get_auth_mode(self) -> str:
        """Return effective auth mode: 'api_key', 'entra_token', or 'auto'."""
        return self.get_config_value("auth_mode", settings.azure_speech_auth_mode) or "auto"

    def _get_key_and_region(self) -> tuple[str | None, str]:
        """Return (subscription_key_or_None, region)."""
        key = self.get_config_value("subscription_key", settings.azure_speech_key) or None
        region = self.get_config_value("region", settings.azure_speech_region) or "eastus"
        return key, region

    def _get_resource_id(self) -> str:
        return self.get_config_value("resource_id", settings.azure_speech_resource_id) or ""

    def _get_endpoint(self) -> str:
        return self.get_config_value("endpoint", settings.azure_speech_endpoint) or ""

    def _use_token_auth(self) -> bool:
        """Determine whether to use Entra ID token auth."""
        mode = self._get_auth_mode()
        if mode == "api_key":
            return False
        if mode == "entra_token":
            return True
        # auto — use token if no key available
        key, _ = self._get_key_and_region()
        return not key

    def _get_token_manager(self) -> AzureTokenManager:
        """Get or create the shared token manager.

        Passes the full runtime config (including service-principal fields)
        so the token manager can try SP auth and the shared
        ``AzureAuthManager`` Redis cache.
        """
        if self._token_manager is None:
            resource_id = self._get_resource_id()
            # Build config dict with SP fields for the token manager
            sp_config = {
                "tenant_id": self.get_config_value("tenant_id", ""),
                "client_id": self.get_config_value("client_id", ""),
                "client_secret": self.get_config_value("client_secret", ""),
            }
            self._token_manager = AzureTokenManager(
                resource_id=resource_id, config=sp_config,
            )
        return self._token_manager

    # ---- Speech SDK config ----

    def _get_config(self):
        """Create or return cached SpeechConfig with appropriate auth."""
        if self._speech_config is None:
            try:
                import azure.cognitiveservices.speech as speechsdk
            except ImportError:
                raise ImportError("pip install azure-cognitiveservices-speech")

            key, region = self._get_key_and_region()

            if self._use_token_auth():
                # Entra ID: use composite token for SpeechSynthesizer
                tm = self._get_token_manager()
                composite_token = tm.get_composite_token()
                self._speech_config = speechsdk.SpeechConfig(
                    auth_token=composite_token,
                    region=region,
                )
                logger.info("azure_speech_config_created", region=region, auth="entra_token")
            else:
                # API key auth
                if not key:
                    raise ValueError(
                        "Azure Speech not configured: set subscription_key or "
                        "switch auth_mode to 'entra_token' with a resource_id"
                    )
                self._speech_config = speechsdk.SpeechConfig(
                    subscription=key,
                    region=region,
                )
                logger.info("azure_speech_config_created", region=region, auth="api_key")

            # Default to 24kHz WAV — callers override per-request via _apply_output_format
            self._speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff24Khz16BitMonoPcm
            )
        return self._speech_config

    def _get_fresh_config(self):
        """Get a deep copy of config, refreshing Entra token if needed.

        For Entra ID auth, the token embedded in the SpeechConfig may expire.
        This method refreshes it on each synthesis call.
        """
        import azure.cognitiveservices.speech as speechsdk

        config = copy.deepcopy(self._get_config())

        if self._use_token_auth() and self._token_manager:
            # Refresh the composite token on the copy
            config.authorization_token = self._token_manager.get_composite_token()

        return config

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
        """Create a CNV REST client with the appropriate auth."""
        key, region = self._get_key_and_region()

        if self._use_token_auth():
            tm = self._get_token_manager()
            return AzureCNVClient(region=region, token_manager=tm)
        else:
            if not key:
                raise ValueError(
                    "Azure Speech not configured for Custom Voice: "
                    "set subscription_key or switch to entra_token auth"
                )
            return AzureCNVClient(region=region, subscription_key=key)

    def _get_recognition_config(self):
        """Create a SpeechConfig optimized for speech recognition (STT).

        For Entra ID, uses ``token_credential`` parameter which handles
        automatic token refresh internally.  Falls back to composite token
        if ``token_credential`` is unavailable.
        """
        import azure.cognitiveservices.speech as speechsdk

        key, region = self._get_key_and_region()

        if self._use_token_auth():
            endpoint = self._get_endpoint()
            resource_id = self._get_resource_id()

            # Try native token_credential (preferred for recognition)
            try:
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()

                if endpoint:
                    config = speechsdk.SpeechConfig(
                        token_credential=credential,
                        endpoint=endpoint,
                    )
                else:
                    # Fallback to composite token + region
                    tm = self._get_token_manager()
                    composite = tm.get_composite_token()
                    config = speechsdk.SpeechConfig(
                        auth_token=composite,
                        region=region,
                    )
            except ImportError:
                # azure.identity not installed — use composite token
                tm = self._get_token_manager()
                composite = tm.get_composite_token()
                config = speechsdk.SpeechConfig(
                    auth_token=composite,
                    region=region,
                )

            logger.info("azure_recognition_config_created", region=region, auth="entra_token")
            return config
        else:
            if not key:
                raise ValueError(
                    "Azure Speech not configured for STT: "
                    "set subscription_key or switch to entra_token auth"
                )
            config = speechsdk.SpeechConfig(subscription=key, region=region)
            logger.info("azure_recognition_config_created", region=region, auth="api_key")
            return config

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

        config = self._get_fresh_config()
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

        config = self._get_fresh_config()
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

        config = self._get_fresh_config()
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

        speech_config = self._get_recognition_config()
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

        speech_config = self._get_recognition_config()
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

        # 2. Consent (first sample) — wait for async validation
        await cnv.create_consent(consent_id, project_id, talent, company,
                                  samples[0].file_path, locale=locale)
        await cnv.wait_for_consent(consent_id)

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

        # 2. Consent — wait for async validation
        await cnv.create_consent(consent_id, project_id, "Voice Talent", company,
                                  samples[0].file_path, locale=locale)
        await cnv.wait_for_consent(consent_id)

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

        Tries the SDK first (requires subscription key or Entra token).
        Falls back to an extensive hardcoded catalog of English neural
        voices so the voice library is useful even without credentials.
        """
        # Try live SDK call first
        try:
            config = self._get_config()
            if config:
                import azure.cognitiveservices.speech as speechsdk

                # Refresh token if using Entra ID
                if self._use_token_auth() and self._token_manager:
                    config.authorization_token = self._token_manager.get_composite_token()

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
        """Comprehensive catalog of Azure English neural voices (130+).

        Voice data is loaded from ``data/azure_voices.json`` and cached at
        module level so the file is only read once per process.
        """
        global _azure_voices_cache  # noqa: PLW0603
        if _azure_voices_cache is not None:
            return _azure_voices_cache

        voices_path = Path(__file__).parent / "data" / "azure_voices.json"
        with open(voices_path, encoding="utf-8") as fh:
            entries: list[dict] = json.load(fh)

        _azure_voices_cache = [
            VoiceInfo(
                voice_id=entry["voice_id"],
                name=entry["name"],
                language=entry["language"],
                gender=entry["gender"],
                description="Azure Neural Voice",
            )
            for entry in entries
        ]
        return _azure_voices_cache

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
            auth_mode = self._get_auth_mode()
            key, _ = self._get_key_and_region()
            use_token = self._use_token_auth()

            if not key and not use_token:
                # No auth configured at all
                try:
                    import azure.cognitiveservices.speech as _sdk  # noqa: F401
                except ImportError:
                    pass
                latency = int((time.perf_counter() - start) * 1000)
                return ProviderHealth(
                    name="azure_speech", healthy=True, latency_ms=latency,
                    error="SDK ready — configure credentials in Providers settings",
                )

            if use_token:
                # Validate Entra ID token acquisition
                tm = self._get_token_manager()
                tm.get_token()  # Will raise if credential chain fails
                latency = int((time.perf_counter() - start) * 1000)

                # Check token expiry from Redis/auth manager
                token_warning = None
                try:
                    from app.providers.azure_auth import get_azure_auth_manager
                    auth_mgr = get_azure_auth_manager()
                    status = auth_mgr.get_status()
                    if status.authenticated and status.expires_in_seconds is not None:
                        if status.expires_in_seconds < 300:
                            token_warning = (
                                f"Token expires in {status.expires_in_seconds // 60}m "
                                f"{status.expires_in_seconds % 60}s — consider re-authenticating"
                            )
                except Exception:
                    pass

                logger.info("azure_health_check", healthy=True, latency_ms=latency, auth="entra_token")
                return ProviderHealth(
                    name="azure_speech", healthy=True, latency_ms=latency,
                    error=token_warning,
                )
            else:
                # Validate API key by creating config
                self._get_config()
                latency = int((time.perf_counter() - start) * 1000)
                logger.info("azure_health_check", healthy=True, latency_ms=latency, auth="api_key")
                return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency)

        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            logger.info("azure_health_check", healthy=False, latency_ms=latency, error=str(e))
            return ProviderHealth(name="azure_speech", healthy=False, latency_ms=latency, error=str(e))
