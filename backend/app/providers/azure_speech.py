"""Azure AI Speech provider — cloud TTS with SSML support and Custom Neural Voice."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

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
    run_sync,
)

logger = structlog.get_logger(__name__)


class AzureSpeechProvider(TTSProvider):
    """Azure AI Speech — cloud TTS with SSML and Custom Neural Voice."""

    def __init__(self) -> None:
        self._speech_config = None

    def configure(self, config: dict) -> None:
        super().configure(config)
        self._speech_config = None

    def _get_config(self):
        if self._speech_config is None:
            subscription_key = self.get_config_value('subscription_key', settings.azure_speech_key)
            region = self.get_config_value('region', settings.azure_speech_region)
            if not subscription_key:
                raise ValueError("AZURE_SPEECH_KEY not configured")
            try:
                import azure.cognitiveservices.speech as speechsdk

                self._speech_config = speechsdk.SpeechConfig(
                    subscription=subscription_key,
                    region=region,
                )
                self._speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )
                logger.info("azure_speech_config_created", region=region)
            except ImportError:
                raise ImportError("pip install azure-cognitiveservices-speech")
        return self._speech_config

    async def synthesize(
        self, text: str, voice_id: str, settings_: SynthesisSettings
    ) -> AudioResult:
        import azure.cognitiveservices.speech as speechsdk

        config = self._get_config()
        output_dir = Path(settings.storage_path) / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"azure_{uuid.uuid4().hex[:12]}.wav"

        audio_config = speechsdk.audio.AudioOutputConfig(filename=str(output_file))
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=config, audio_config=audio_config
        )

        start = time.perf_counter()

        if settings_.ssml:
            result = await run_sync(synthesizer.speak_ssml_async(text).get)
        else:
            config.speech_synthesis_voice_name = voice_id or "en-US-JennyNeural"
            result = await run_sync(synthesizer.speak_text_async(text).get)

        elapsed = time.perf_counter() - start

        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            logger.info("azure_synthesis_complete", latency_ms=int(elapsed * 1000))
            return AudioResult(
                audio_path=output_file,
                sample_rate=16000,
                format="wav",
            )
        else:
            error = result.cancellation_details.error_details if result.cancellation_details else "Unknown error"
            raise RuntimeError(f"Azure synthesis failed: {error}")

    async def clone_voice(
        self, samples: list[AudioSample], config: CloneConfig
    ) -> VoiceModel:
        raise NotImplementedError(
            "Azure Custom Neural Voice requires portal setup. "
            "Create your CNV project at speech.microsoft.com"
        )

    async def fine_tune(
        self, model_id: str, samples: list[AudioSample], config: FineTuneConfig
    ) -> VoiceModel:
        raise NotImplementedError("Azure CNV fine-tuning is managed via Azure portal")

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
                    # Only return English voices to keep the library focused
                    if locale.startswith("en"):
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
                    return voices
        except Exception as exc:
            logger.debug("azure_sdk_list_voices_failed", error=str(exc))

        # Fallback: hardcoded English neural voices
        return self._hardcoded_english_voices()

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
        # Azure Custom Neural Voice (CNV) requires setup through the Azure Speech
        # Studio portal (https://speech.microsoft.com) and cannot be initiated
        # programmatically via the Speech SDK.  supports_cloning is therefore
        # always False here; the clone_voice() method raises NotImplementedError
        # with instructions for the portal workflow.
        return ProviderCapabilities(
            supports_cloning=False,
            supports_fine_tuning=False,
            supports_streaming=True,
            supports_ssml=True,
            supports_zero_shot=False,
            supports_batch=True,
            requires_gpu=False,
            gpu_mode="none",
            min_samples_for_cloning=0,
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
                return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency,
                                      error="SDK ready — configure subscription key in Providers settings")
            self._get_config()
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="azure_speech", healthy=True, latency_ms=latency)
        except Exception as e:
            latency = int((time.perf_counter() - start) * 1000)
            return ProviderHealth(name="azure_speech", healthy=False, latency_ms=latency, error=str(e))
