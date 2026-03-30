import { useState, useMemo } from "react";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import {
  CheckCircle2,
  Circle,
  ExternalLink,
  Search,
  BookOpen,
  Layers,
  Settings,
  Plug,
  ShieldCheck,
  Rocket,
  AlertTriangle,
  Terminal,
  Server,
  Database,
  Cpu,
  Globe,
  Workflow,
  Box,
} from "lucide-react";
import ProviderLogo from "../components/providers/ProviderLogo";
import { createLogger } from "../utils/logger";

const logger = createLogger("DocsPage");

/* ================================================================
   Types
   ================================================================ */

interface ProviderGuide {
  name: string;
  displayName: string;
  type: "cloud" | "local-cpu" | "local-gpu";
  description: string;
  website: string;
  voiceCount: string;
  qualityNotes: string;
  steps: SetupStep[];
  envVars: EnvVar[];
  checklist: string[];
  tips: string[];
  commonIssues: CommonIssue[];
  cliExample: string;
  apiExample: string;
}

interface SetupStep {
  title: string;
  description: string;
  code?: string;
}

interface EnvVar {
  name: string;
  required: boolean;
  defaultValue: string;
  description: string;
}

interface CommonIssue {
  problem: string;
  solution: string;
}

/* ================================================================
   Tab definitions
   ================================================================ */

const TABS = [
  "Provider Guides",
  "Architecture",
  "Configuration",
  "MCP Integration",
  "Self-Healing",
  "Deployment",
] as const;
type Tab = (typeof TABS)[number];

const TAB_ICONS: Record<Tab, typeof BookOpen> = {
  "Provider Guides": BookOpen,
  Architecture: Layers,
  Configuration: Settings,
  "MCP Integration": Plug,
  "Self-Healing": ShieldCheck,
  Deployment: Rocket,
};

/* ================================================================
   Provider Guides data (enhanced)
   ================================================================ */

const PROVIDER_GUIDES: ProviderGuide[] = [
  {
    name: "kokoro",
    displayName: "Kokoro",
    type: "local-cpu",
    description:
      "Lightweight, fast TTS with 54 built-in voices. CPU-only, no GPU required. Default provider in Atlas Vox.",
    website: "https://github.com/hexgrad/kokoro",
    voiceCount: "54 built-in voices",
    qualityNotes:
      "Good quality for an 82M parameter model. Best for English. Fastest CPU provider with sub-100ms latency on modern hardware.",
    steps: [
      {
        title: "No Setup Required",
        description:
          "Kokoro works out of the box with no configuration. It is the default provider and is automatically enabled when the backend starts.",
      },
      {
        title: "Verify Installation",
        description:
          "Confirm the kokoro Python package is installed in your environment. Docker handles this automatically.",
        code: "pip show kokoro   # Should show version 0.x.x",
      },
      {
        title: "Check Provider Health",
        description:
          'Go to the Providers page and check that Kokoro shows a green "healthy" badge. You can also verify via CLI.',
        code: "atlas-vox providers list\natlas-vox providers health kokoro",
      },
      {
        title: "Browse Available Voices",
        description:
          "Kokoro includes 54 built-in voices organized by accent and gender. Prefixes: af_ (American female), am_ (American male), bf_ (British female), bm_ (British male).",
        code: "atlas-vox synthesize --provider kokoro --voice af_heart --text \"Hello world\"",
      },
      {
        title: "Test Synthesis",
        description:
          "Run a quick synthesis to verify audio output quality. Try different voices to find your preferred one.",
      },
    ],
    envVars: [
      {
        name: "KOKORO_ENABLED",
        required: false,
        defaultValue: "true",
        description: "Enable or disable Kokoro provider",
      },
    ],
    checklist: [
      "Backend is running",
      "kokoro Python package installed",
      "Kokoro health check passes",
      "Can list Kokoro voices in Voice Library",
      "Can synthesize speech with a Kokoro voice",
    ],
    tips: [
      "Kokoro is the fastest CPU provider -- ideal for testing and prototyping",
      "Keep text under 500 characters per request for best quality",
      "82M parameter model uses minimal RAM (~200 MB)",
      "Use af_heart for a warm, natural-sounding female voice",
      "Supports speed adjustment from 0.5x to 2.0x",
    ],
    commonIssues: [
      {
        problem: "Health check shows unhealthy",
        solution:
          'Ensure the kokoro package is installed: pip install kokoro. Check logs for import errors.',
      },
      {
        problem: "No voices appear in Voice Library",
        solution:
          'Verify the provider is enabled (KOKORO_ENABLED=true). Try restarting the backend.',
      },
      {
        problem: "Audio sounds robotic or choppy",
        solution:
          'Keep text under 500 characters. Try a different voice (af_heart is recommended). Ensure sample rate is 24000.',
      },
    ],
    cliExample: 'atlas-vox synthesize --text "Hello from Kokoro" --provider kokoro --voice af_heart',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from Kokoro", "provider_name": "kokoro", "voice_id": "af_heart"}'`,
  },
  {
    name: "piper",
    displayName: "Piper",
    type: "local-cpu",
    description:
      "Fast, local TTS optimized for Raspberry Pi and Home Assistant. ONNX-based with many pre-trained voices across 30+ languages.",
    website: "https://github.com/rhasspy/piper",
    voiceCount: "100+ downloadable voice models across 30+ languages",
    qualityNotes:
      "Medium quality VITS models. Very fast inference, even on Raspberry Pi. Best for home automation and IoT. Low memory footprint.",
    steps: [
      {
        title: "Default Model Downloaded Automatically",
        description:
          "The Docker build downloads en_US-lessac-medium.onnx automatically. For local dev, you may need to download it manually.",
        code: "mkdir -p storage/models/piper\ncd storage/models/piper\n# Download from https://huggingface.co/rhasspy/piper-voices",
      },
      {
        title: "Install espeak-ng",
        description:
          "Piper requires espeak-ng for phoneme generation. This is installed automatically in Docker.",
        code: "# Ubuntu/Debian\nsudo apt install espeak-ng\n\n# macOS\nbrew install espeak-ng",
      },
      {
        title: "Add More Voices (Optional)",
        description:
          "Download additional ONNX models from the Piper Voices repository and place them in the model directory.",
        code: "# Each voice needs two files:\n# <name>.onnx       -- the model weights\n# <name>.onnx.json  -- the config file\n\n# Example: download German voice\nwget https://huggingface.co/rhasspy/piper-voices/.../de_DE-thorsten-medium.onnx\nwget https://huggingface.co/rhasspy/piper-voices/.../de_DE-thorsten-medium.onnx.json",
      },
      {
        title: "Configure Model Path",
        description:
          "Set the PIPER_MODEL_PATH if you use a non-default location for model files.",
        code: "PIPER_MODEL_PATH=./storage/models/piper",
      },
      {
        title: "Verify Setup",
        description:
          "Run a health check on the Providers page. Piper should show healthy if at least one model file is present.",
      },
    ],
    envVars: [
      {
        name: "PIPER_ENABLED",
        required: false,
        defaultValue: "true",
        description: "Enable or disable Piper",
      },
      {
        name: "PIPER_MODEL_PATH",
        required: false,
        defaultValue: "./storage/models/piper",
        description: "Path to ONNX model files",
      },
    ],
    checklist: [
      "ONNX model files present in model directory",
      "espeak-ng installed on the system",
      "Piper health check passes",
      "At least one voice appears in the Voice Library",
      "Can synthesize and play audio",
    ],
    tips: [
      "Use medium quality models for the best speed/quality balance",
      "Piper supports 30+ languages -- download models for each language you need",
      "Very low memory footprint, works on Raspberry Pi 4",
      "Home Assistant compatible voice format",
      "Fastest inference of all local providers",
    ],
    commonIssues: [
      {
        problem: "espeak-ng not found error",
        solution:
          'Install espeak-ng: sudo apt install espeak-ng (Linux) or brew install espeak-ng (macOS).',
      },
      {
        problem: "No model files found",
        solution:
          'Download at least one .onnx + .onnx.json pair from https://huggingface.co/rhasspy/piper-voices and place in the PIPER_MODEL_PATH directory.',
      },
      {
        problem: "Model loading error",
        solution:
          'Ensure both the .onnx and .onnx.json files are present. They must have the same base filename.',
      },
    ],
    cliExample: 'atlas-vox synthesize --text "Hello from Piper" --provider piper',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from Piper", "provider_name": "piper"}'`,
  },
  {
    name: "elevenlabs",
    displayName: "ElevenLabs",
    type: "cloud",
    description:
      "Industry-leading cloud TTS with the most natural-sounding voices. Supports instant voice cloning and 29 languages.",
    website: "https://elevenlabs.io",
    voiceCount: "Thousands of voices, plus custom voice cloning",
    qualityNotes:
      "Best-in-class quality. The most natural-sounding provider available. Supports voice cloning from 1-5 minutes of audio. Multilingual v2 model supports 29 languages.",
    steps: [
      {
        title: "Create an ElevenLabs Account",
        description:
          "Sign up at elevenlabs.io. A free tier with 10,000 characters/month is available. No credit card required.",
      },
      {
        title: "Get Your API Key",
        description:
          "Go to Profile Settings > API Keys and copy your key. Keep this key secure -- it provides full access to your account.",
      },
      {
        title: "Configure in Atlas Vox",
        description:
          "Set the API key via environment variable or the Providers settings page in the Web UI.",
        code: "# Via environment variable\nELEVENLABS_API_KEY=sk_xxxxxxxxxxxxxxxx\n\n# Or via Web UI:\n# Providers > ElevenLabs > Settings > API Key",
      },
      {
        title: "Run Health Check",
        description:
          "Click the Health Check button on the Providers page. If the API key is valid, the status should change to healthy.",
      },
      {
        title: "Test Synthesis",
        description:
          "Click Test to run a quick synthesis and verify audio output. Try the Rachel voice for a high-quality demo.",
      },
    ],
    envVars: [
      {
        name: "ELEVENLABS_API_KEY",
        required: true,
        defaultValue: "",
        description: "Your ElevenLabs API key (starts with sk_)",
      },
      {
        name: "ELEVENLABS_MODEL_ID",
        required: false,
        defaultValue: "eleven_multilingual_v2",
        description: "TTS model ID",
      },
    ],
    checklist: [
      "ElevenLabs account created",
      "API key configured in provider settings",
      "Health check passes (status: healthy)",
      "Test synthesis produces audio",
      "Voices appear in Voice Library",
    ],
    tips: [
      "Free tier: 10,000 characters/month, 3 custom voices",
      "eleven_multilingual_v2 supports all 29 languages",
      "Use eleven_monolingual_v1 for faster English-only synthesis",
      "Voice cloning works best with 1-5 minutes of clean audio",
      "Rachel and Adam are the most popular default voices",
    ],
    commonIssues: [
      {
        problem: "401 Unauthorized error",
        solution:
          'Verify your API key is correct. Go to elevenlabs.io > Profile Settings > API Keys and copy a fresh key.',
      },
      {
        problem: "429 Rate limit exceeded",
        solution:
          'Free tier has rate limits. Wait 60 seconds and try again, or upgrade your plan.',
      },
      {
        problem: "No voices returned",
        solution:
          'Check that ELEVENLABS_API_KEY is set correctly. The provider needs a valid key to fetch the voice list.',
      },
    ],
    cliExample:
      'atlas-vox synthesize --text "Hello from ElevenLabs" --provider elevenlabs --voice Rachel',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from ElevenLabs", "provider_name": "elevenlabs", "voice_id": "Rachel"}'`,
  },
  {
    name: "azure_speech",
    displayName: "Azure Speech",
    type: "cloud",
    description:
      "Microsoft Azure Cognitive Services TTS with 400+ neural voices, full SSML support, and enterprise reliability.",
    website: "https://azure.microsoft.com/en-us/products/ai-services/text-to-speech",
    voiceCount: "400+ neural voices across 140+ languages",
    qualityNotes:
      "Enterprise-grade quality. Only provider with full SSML support for fine-grained prosody control. Very low latency. Best for multilingual and enterprise deployments.",
    steps: [
      {
        title: "Create an Azure Account",
        description:
          "Sign up at azure.microsoft.com. A free tier with 500K characters/month is available for neural voices.",
      },
      {
        title: "Create a Speech Resource",
        description:
          "In the Azure Portal, search for 'Speech' and create a new Speech resource. Note the region you select (e.g., eastus).",
      },
      {
        title: "Get Your Key and Region",
        description:
          "Go to your Speech resource > Keys and Endpoint. Copy Key 1 and the Region.",
        code: "AZURE_SPEECH_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\nAZURE_SPEECH_REGION=eastus",
      },
      {
        title: "Configure in Atlas Vox",
        description:
          "Go to Providers > Azure Speech > Settings. Enter the subscription key and region. Click Save.",
      },
      {
        title: "Test with SSML",
        description:
          "Azure is the only provider that supports SSML. Try the SSML editor in the Synthesis Lab for prosody control.",
        code: '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">\n  <voice name="en-US-JennyNeural">\n    <prosody rate="medium" pitch="+2st">Hello from Azure Speech!</prosody>\n  </voice>\n</speak>',
      },
    ],
    envVars: [
      {
        name: "AZURE_SPEECH_KEY",
        required: true,
        defaultValue: "",
        description: "Azure subscription key",
      },
      {
        name: "AZURE_SPEECH_REGION",
        required: true,
        defaultValue: "eastus",
        description: "Azure region (e.g., eastus, westus2, westeurope)",
      },
    ],
    checklist: [
      "Azure account and Speech resource created",
      "Subscription key and region configured",
      "Health check passes",
      "Can list Azure voices in Voice Library",
      "SSML synthesis works with Azure profiles",
    ],
    tips: [
      "Free tier: 500K characters/month for neural voices",
      "400+ neural voices across 140+ languages and variants",
      "Only provider with full SSML support for prosody, emphasis, and pronunciation",
      "Use en-US-JennyNeural for natural conversational English",
      "eastus region typically has lowest latency for US users",
    ],
    commonIssues: [
      {
        problem: "401 Access Denied",
        solution:
          'Verify your subscription key is correct. Copy Key 1 from the Azure Portal > Speech resource > Keys.',
      },
      {
        problem: "Wrong region error",
        solution:
          'Ensure AZURE_SPEECH_REGION matches the region where your Speech resource was created (e.g., eastus, not East US).',
      },
      {
        problem: "SSML parsing errors",
        solution:
          'Validate your SSML against the W3C schema. Common issue: missing xmlns attribute or incorrect voice name.',
      },
    ],
    cliExample:
      'atlas-vox synthesize --text "Hello from Azure" --provider azure_speech --voice en-US-JennyNeural',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from Azure", "provider_name": "azure_speech", "voice_id": "en-US-JennyNeural"}'`,
  },
  {
    name: "coqui_xtts",
    displayName: "Coqui XTTS v2",
    type: "local-gpu",
    description:
      "State-of-the-art voice cloning from just 6 seconds of audio. Supports 17 languages with zero-shot synthesis.",
    website: "https://github.com/coqui-ai/TTS",
    voiceCount: "Unlimited via voice cloning (any reference audio)",
    qualityNotes:
      "Excellent cloning quality from short audio. 6 seconds minimum, 15-30 seconds recommended for best results. ~1.5B parameters. GPU strongly recommended.",
    steps: [
      {
        title: "Enable GPU Mode (Recommended)",
        description:
          "For usable speed, GPU mode is strongly recommended. CPU mode is 10-50x slower.",
        code: "COQUI_XTTS_GPU_MODE=docker_gpu\n# Or use: make docker-gpu-up",
      },
      {
        title: "Install NVIDIA Container Toolkit (Docker GPU)",
        description:
          "If using Docker GPU mode, install the NVIDIA Container Toolkit for GPU passthrough.",
        code: "# Ubuntu/Debian\nsudo apt install nvidia-container-toolkit\nsudo systemctl restart docker",
      },
      {
        title: "Model Downloads Automatically",
        description:
          "The XTTS v2 model (~1.8 GB) downloads on first use. Ensure internet access and sufficient disk space.",
      },
      {
        title: "Prepare Reference Audio",
        description:
          "For voice cloning, upload a clean audio sample (15-30 seconds of clear speech, no background noise) via the Training Studio.",
      },
      {
        title: "Run Health Check",
        description:
          "Go to Providers > Coqui XTTS > Health Check. First check will be slow while the model loads into memory.",
      },
    ],
    envVars: [
      {
        name: "COQUI_XTTS_GPU_MODE",
        required: false,
        defaultValue: "host_cpu",
        description: "GPU mode: host_cpu, docker_gpu, or auto",
      },
    ],
    checklist: [
      "TTS Python package installed",
      "GPU mode configured (if using GPU)",
      "NVIDIA Container Toolkit installed (for Docker GPU)",
      "Model downloaded successfully (~1.8 GB)",
      "Health check passes",
    ],
    tips: [
      "Voice cloning from 6 seconds, but 15-30 seconds gives much better results",
      "GPU mode is 10-50x faster than CPU",
      "Supports 17 languages: English, Spanish, French, German, Italian, Portuguese, Polish, Turkish, Russian, Dutch, Czech, Arabic, Chinese, Japanese, Korean, Hungarian, Hindi",
      "Clean audio without background noise is critical for good cloning",
      "Minimum 4 GB VRAM required for GPU mode",
    ],
    commonIssues: [
      {
        problem: "CUDA out of memory",
        solution:
          'Coqui XTTS needs at least 4 GB VRAM. Close other GPU applications. Use shorter text segments.',
      },
      {
        problem: "Model download fails",
        solution:
          'Check internet access from the container. The model is ~1.8 GB. Try increasing Docker timeout.',
      },
      {
        problem: "Very slow synthesis on CPU",
        solution:
          'CPU mode is impractical for production. Switch to docker_gpu mode or use Kokoro/Piper instead.',
      },
    ],
    cliExample:
      'atlas-vox synthesize --text "Hello from XTTS" --provider coqui_xtts --profile my-clone',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from XTTS", "provider_name": "coqui_xtts", "profile_id": "abc-123"}'`,
  },
  {
    name: "styletts2",
    displayName: "StyleTTS2",
    type: "local-gpu",
    description:
      "Style diffusion and adversarial training for human-level speech quality. Zero-shot voice transfer with the highest MOS scores.",
    website: "https://github.com/yl4579/StyleTTS2",
    voiceCount: "Style transfer from reference audio (unlimited)",
    qualityNotes:
      "Achieves the highest MOS (Mean Opinion Score) of any open-source TTS. English-only. ~200M parameters. Style transfer allows combining voice identity with speaking style.",
    steps: [
      {
        title: "Enable GPU Mode",
        description:
          "StyleTTS2 is impractical on CPU. Use GPU mode for any real-time synthesis.",
        code: "STYLETTS2_GPU_MODE=docker_gpu",
      },
      {
        title: "Install System Dependencies",
        description:
          "espeak-ng and NLTK punkt data are required. Both are installed automatically in Docker.",
        code: "sudo apt install espeak-ng\npython -c \"import nltk; nltk.download('punkt')\"",
      },
      {
        title: "Configure GPU Container",
        description:
          "Use the GPU Docker Compose configuration for automatic setup.",
        code: "make docker-gpu-up",
      },
      {
        title: "Run Health Check",
        description:
          "First health check may be slow as the model loads. Subsequent checks are faster. Check the Providers page.",
      },
      {
        title: "Test Style Transfer",
        description:
          "Upload reference audio and synthesize with style transfer to combine the identity of one voice with the style of another.",
      },
    ],
    envVars: [
      {
        name: "STYLETTS2_GPU_MODE",
        required: false,
        defaultValue: "host_cpu",
        description: "GPU mode: host_cpu, docker_gpu, or auto",
      },
    ],
    checklist: [
      "styletts2 Python package installed",
      "espeak-ng installed",
      "NLTK punkt data downloaded",
      "GPU mode configured",
      "Health check passes",
    ],
    tips: [
      "English-only, but achieves the highest quality MOS scores of any open-source model",
      "Style transfer lets you apply one voice's style to another voice's identity",
      "CPU mode is very slow -- GPU is strongly recommended",
      "~200M parameters, needs ~2 GB VRAM",
    ],
    commonIssues: [
      {
        problem: "espeak-ng not found",
        solution: 'Install with: sudo apt install espeak-ng (Linux) or brew install espeak-ng (macOS).',
      },
      {
        problem: "NLTK punkt error",
        solution:
          "Run: python -c \"import nltk; nltk.download('punkt')\" before starting the backend.",
      },
      {
        problem: "Extremely slow synthesis",
        solution:
          'You are likely running on CPU. Switch to STYLETTS2_GPU_MODE=docker_gpu.',
      },
    ],
    cliExample: 'atlas-vox synthesize --text "Hello from StyleTTS2" --provider styletts2',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from StyleTTS2", "provider_name": "styletts2"}'`,
  },
  {
    name: "cosyvoice",
    displayName: "CosyVoice",
    type: "local-gpu",
    description:
      "Alibaba's multilingual TTS with natural prosody. Supports 9 languages with ~150ms streaming latency on GPU.",
    website: "https://github.com/FunAudioLLM/CosyVoice",
    voiceCount: "Built-in voices + voice cloning",
    qualityNotes:
      "Excellent multilingual quality. Handles code-switching between languages naturally. ~300M parameters. ~150ms first-chunk latency in streaming mode on GPU.",
    steps: [
      {
        title: "Enable GPU Mode",
        description: "GPU mode is recommended for acceptable performance.",
        code: "COSYVOICE_GPU_MODE=docker_gpu",
      },
      {
        title: "Docker Installation",
        description:
          "CosyVoice is installed from its GitHub repository during Docker build. No manual installation needed.",
        code: "make docker-gpu-up",
      },
      {
        title: "Verify Model Download",
        description:
          "The CosyVoice model downloads on first use. Monitor Docker logs for download progress.",
        code: "docker compose -f docker/docker-compose.yml logs -f worker",
      },
      {
        title: "Run Health Check",
        description:
          "Verify the provider is operational via the Providers page.",
      },
      {
        title: "Test Multilingual Synthesis",
        description:
          "Try synthesizing in different languages. CosyVoice excels at Chinese, Japanese, Korean, and natural code-switching.",
      },
    ],
    envVars: [
      {
        name: "COSYVOICE_GPU_MODE",
        required: false,
        defaultValue: "host_cpu",
        description: "GPU mode: host_cpu, docker_gpu, or auto",
      },
    ],
    checklist: [
      "CosyVoice package installed",
      "GPU mode configured",
      "Model downloaded",
      "Health check passes",
      "Multilingual synthesis works",
    ],
    tips: [
      "Excellent for Chinese and Asian language TTS",
      "~150ms first-chunk latency in streaming mode on GPU",
      "Handles code-switching between languages naturally",
      "300M parameters, needs ~3 GB VRAM",
    ],
    commonIssues: [
      {
        problem: "Import error for CosyVoice",
        solution:
          'CosyVoice must be installed from GitHub. Use Docker for automatic installation.',
      },
      {
        problem: "Slow first synthesis",
        solution:
          'First synthesis triggers model download (~2 GB). Subsequent calls are fast.',
      },
    ],
    cliExample: 'atlas-vox synthesize --text "Hello from CosyVoice" --provider cosyvoice',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello from CosyVoice", "provider_name": "cosyvoice"}'`,
  },
  {
    name: "dia",
    displayName: "Dia",
    type: "local-gpu",
    description:
      "Nari Labs dialogue TTS with 1.6B parameters. Generates natural multi-speaker conversations with non-verbal sounds.",
    website: "https://github.com/nari-labs/dia",
    voiceCount: "2 built-in dialogue speakers ([S1] and [S2])",
    qualityNotes:
      "Excellent for dialogue and podcast generation. Supports non-verbal sounds like (laughs), (sighs), (clears throat). 1.6B parameters, needs 6 GB+ VRAM.",
    steps: [
      {
        title: "Enable GPU Mode",
        description:
          "Dia's 1.6B model requires GPU. Minimum 6 GB VRAM. CPU mode is impractical.",
        code: "DIA_GPU_MODE=docker_gpu",
      },
      {
        title: "Launch with GPU Compose",
        description:
          "Use the GPU Docker Compose configuration.",
        code: "make docker-gpu-up",
      },
      {
        title: "Format Dialogue Text",
        description:
          "Use [S1] and [S2] tags for speakers. Non-verbal sounds go in parentheses.",
        code: '[S1] Hello, how are you today?\n[S2] Great, thanks! (laughs) And you?\n[S1] Doing well. (clears throat) Let me tell you something.',
      },
      {
        title: "Wait for Model Download",
        description:
          "Model downloads on first use (~3 GB). Health check will be slow initially.",
      },
      {
        title: "Test Dialogue Synthesis",
        description:
          "Run a test with dialogue-formatted text. The output will contain two distinct speakers.",
      },
    ],
    envVars: [
      {
        name: "DIA_GPU_MODE",
        required: false,
        defaultValue: "host_cpu",
        description: "GPU mode: host_cpu, docker_gpu, or auto",
      },
    ],
    checklist: [
      "GPU with 6 GB+ VRAM available",
      "GPU mode configured",
      "Model downloaded successfully (~3 GB)",
      "Health check passes",
      "Dialogue synthesis produces two distinct speakers",
    ],
    tips: [
      "Use [S1] and [S2] tags for different speakers",
      "Supports non-verbal sounds: (laughs), (sighs), (clears throat), (gasps)",
      "Great for podcast and conversation generation",
      "CPU mode is impractical for this model size",
      "Best results with natural, conversational text",
    ],
    commonIssues: [
      {
        problem: "CUDA out of memory",
        solution: 'Dia needs 6 GB+ VRAM. Close other GPU applications. Reduce dialogue length.',
      },
      {
        problem: "Only one speaker in output",
        solution:
          'Ensure you are using [S1] and [S2] tags at the start of each line. The tags are case-sensitive.',
      },
      {
        problem: "Non-verbal sounds not working",
        solution:
          'Use parentheses with no spaces before: (laughs), not ( laughs ). Only supported sounds work.',
      },
    ],
    cliExample:
      'atlas-vox synthesize --text "[S1] Hello! [S2] Hi there! (laughs)" --provider dia',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "[S1] Hello! [S2] Hi there!", "provider_name": "dia"}'`,
  },
  {
    name: "dia2",
    displayName: "Dia2",
    type: "local-gpu",
    description:
      "Next-gen dialogue model with 2B parameters and streaming support. Real-time conversation generation with improved quality.",
    website: "https://github.com/nari-labs/dia",
    voiceCount: "2 built-in dialogue speakers ([S1] and [S2])",
    qualityNotes:
      "Higher quality than Dia with streaming support. 2B parameters produce more natural speech. Needs 8 GB+ VRAM.",
    steps: [
      {
        title: "Enable GPU Mode",
        description:
          "Dia2's 2B model requires GPU. Minimum 8 GB VRAM.",
        code: "DIA2_GPU_MODE=docker_gpu",
      },
      {
        title: "Launch with GPU Compose",
        description:
          "Use the GPU Docker Compose configuration.",
        code: "make docker-gpu-up",
      },
      {
        title: "Wait for Model Download",
        description:
          "The 2B parameter model is approximately 4 GB. Ensure sufficient disk space and internet access.",
      },
      {
        title: "Test Streaming Output",
        description:
          "Dia2's primary advantage over Dia is streaming. Test with the Synthesis Lab to hear audio as it generates.",
      },
      {
        title: "Verify Health",
        description:
          "First health check will be slow while the model loads. Subsequent checks are faster.",
      },
    ],
    envVars: [
      {
        name: "DIA2_GPU_MODE",
        required: false,
        defaultValue: "host_cpu",
        description: "GPU mode: host_cpu, docker_gpu, or auto",
      },
    ],
    checklist: [
      "GPU with 8 GB+ VRAM available",
      "GPU mode configured",
      "Model downloaded (~4 GB)",
      "Health check passes",
      "Streaming synthesis works",
    ],
    tips: [
      "Primary advantage over Dia: streaming support for real-time output",
      "2B parameters produce higher quality than Dia's 1.6B",
      "CPU mode is not practical for this model",
      "Uses same [S1]/[S2] dialogue format as Dia",
    ],
    commonIssues: [
      {
        problem: "CUDA out of memory",
        solution: 'Dia2 needs 8 GB+ VRAM. This is the most VRAM-hungry provider. Close all other GPU apps.',
      },
      {
        problem: "Model download timeout",
        solution:
          'The 4 GB model download can take a while. Ensure stable internet. Check Docker logs for progress.',
      },
      {
        problem: "Streaming not working",
        solution:
          'Verify WebSocket connection is established. Check browser console for connection errors.',
      },
    ],
    cliExample:
      'atlas-vox synthesize --text "[S1] Hello! [S2] Hi!" --provider dia2',
    apiExample: `curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "[S1] Hello! [S2] Hi!", "provider_name": "dia2"}'`,
  },
];

/* ================================================================
   Configuration data
   ================================================================ */

interface ConfigVar {
  name: string;
  type: string;
  defaultValue: string;
  description: string;
  group: string;
}

const CONFIG_VARS: ConfigVar[] = [
  // Application
  { name: "APP_NAME", type: "str", defaultValue: "Atlas Vox", description: "Application display name", group: "Application" },
  { name: "APP_VERSION", type: "str", defaultValue: "0.1.0", description: "Application version string", group: "Application" },
  { name: "DEBUG", type: "bool", defaultValue: "false", description: "Enable debug mode with verbose logging", group: "Application" },
  { name: "LOG_LEVEL", type: "str", defaultValue: "INFO", description: "Logging level: DEBUG, INFO, WARNING, ERROR", group: "Application" },
  { name: "AUTH_DISABLED", type: "bool", defaultValue: "true", description: "Disable authentication (single-user mode)", group: "Application" },
  // Server
  { name: "BACKEND_HOST", type: "str", defaultValue: "0.0.0.0", description: "Backend bind address", group: "Server" },
  { name: "BACKEND_PORT", type: "int", defaultValue: "8100", description: "Backend HTTP port", group: "Server" },
  { name: "FRONTEND_PORT", type: "int", defaultValue: "3100", description: "Frontend dev server port (Vite)", group: "Server" },
  { name: "CORS_ORIGINS", type: "str", defaultValue: "*", description: "Comma-separated allowed CORS origins", group: "Server" },
  { name: "RATE_LIMIT_SYNTHESIS", type: "int", defaultValue: "10", description: "Synthesis requests per minute", group: "Server" },
  { name: "RATE_LIMIT_TRAINING", type: "int", defaultValue: "5", description: "Training requests per minute", group: "Server" },
  // Database
  { name: "DATABASE_URL", type: "str", defaultValue: "sqlite+aiosqlite:///atlas_vox.db", description: "SQLAlchemy async database URL", group: "Database" },
  { name: "DATABASE_ECHO", type: "bool", defaultValue: "false", description: "Echo SQL statements (debug)", group: "Database" },
  // Auth
  { name: "JWT_SECRET", type: "str", defaultValue: "(auto-generated)", description: "JWT signing secret (32+ characters)", group: "Auth" },
  { name: "JWT_ALGORITHM", type: "str", defaultValue: "HS256", description: "JWT signing algorithm", group: "Auth" },
  { name: "JWT_EXPIRATION_MINUTES", type: "int", defaultValue: "60", description: "JWT token expiration in minutes", group: "Auth" },
  // Redis
  { name: "REDIS_URL", type: "str", defaultValue: "redis://localhost:6379/1", description: "Redis connection URL (uses db 1)", group: "Redis" },
  { name: "CELERY_BROKER_URL", type: "str", defaultValue: "redis://localhost:6379/1", description: "Celery broker URL", group: "Redis" },
  { name: "CELERY_RESULT_BACKEND", type: "str", defaultValue: "redis://localhost:6379/1", description: "Celery result backend URL", group: "Redis" },
  // Storage
  { name: "STORAGE_DIR", type: "str", defaultValue: "./storage", description: "Root directory for file storage", group: "Storage" },
  { name: "AUDIO_OUTPUT_DIR", type: "str", defaultValue: "./storage/audio", description: "Synthesized audio output directory", group: "Storage" },
  { name: "SAMPLES_DIR", type: "str", defaultValue: "./storage/samples", description: "Training sample upload directory", group: "Storage" },
  { name: "MODELS_DIR", type: "str", defaultValue: "./storage/models", description: "Model weights directory", group: "Storage" },
  // Providers
  { name: "KOKORO_ENABLED", type: "bool", defaultValue: "true", description: "Enable Kokoro TTS provider", group: "Providers" },
  { name: "PIPER_ENABLED", type: "bool", defaultValue: "true", description: "Enable Piper TTS provider", group: "Providers" },
  { name: "PIPER_MODEL_PATH", type: "str", defaultValue: "./storage/models/piper", description: "Path to Piper ONNX model files", group: "Providers" },
  { name: "ELEVENLABS_API_KEY", type: "str", defaultValue: "", description: "ElevenLabs API key", group: "Providers" },
  { name: "ELEVENLABS_MODEL_ID", type: "str", defaultValue: "eleven_multilingual_v2", description: "ElevenLabs TTS model ID", group: "Providers" },
  { name: "AZURE_SPEECH_KEY", type: "str", defaultValue: "", description: "Azure Speech subscription key", group: "Providers" },
  { name: "AZURE_SPEECH_REGION", type: "str", defaultValue: "eastus", description: "Azure Speech service region", group: "Providers" },
  { name: "COQUI_XTTS_GPU_MODE", type: "str", defaultValue: "host_cpu", description: "Coqui XTTS GPU mode: host_cpu, docker_gpu, auto", group: "Providers" },
  { name: "STYLETTS2_GPU_MODE", type: "str", defaultValue: "host_cpu", description: "StyleTTS2 GPU mode", group: "Providers" },
  { name: "COSYVOICE_GPU_MODE", type: "str", defaultValue: "host_cpu", description: "CosyVoice GPU mode", group: "Providers" },
  { name: "DIA_GPU_MODE", type: "str", defaultValue: "host_cpu", description: "Dia GPU mode", group: "Providers" },
  { name: "DIA2_GPU_MODE", type: "str", defaultValue: "host_cpu", description: "Dia2 GPU mode", group: "Providers" },
];

const CONFIG_GROUPS = ["Application", "Server", "Database", "Auth", "Redis", "Storage", "Providers"];

/* ================================================================
   MCP data
   ================================================================ */

interface MCPTool {
  name: string;
  description: string;
  requiredInputs: string;
  example: string;
}

const MCP_TOOLS: MCPTool[] = [
  {
    name: "atlas_vox_synthesize",
    description: "Synthesize text to speech using a voice profile",
    requiredInputs: "text (str), profile_id (str), speed? (number)",
    example: '{"text": "Hello world", "profile_id": "abc-123", "speed": 1.0}',
  },
  {
    name: "atlas_vox_speak",
    description: "Speak text using any available voice. No profile needed.",
    requiredInputs: "text (str), voice? (str), provider? (str), speed? (number)",
    example: '{"text": "Hello world", "voice": "af_heart", "provider": "kokoro"}',
  },
  {
    name: "atlas_vox_list_voices",
    description: "List all voice profiles in Atlas Vox",
    requiredInputs: "(none)",
    example: "{}",
  },
  {
    name: "atlas_vox_list_available_voices",
    description: "List all available voices from all TTS providers (not profiles)",
    requiredInputs: "provider? (str)",
    example: '{"provider": "kokoro"}',
  },
  {
    name: "atlas_vox_train_voice",
    description: "Start training a voice model from uploaded samples",
    requiredInputs: "profile_id (str), provider_name? (str)",
    example: '{"profile_id": "abc-123"}',
  },
  {
    name: "atlas_vox_get_training_status",
    description: "Get the status of a training job",
    requiredInputs: "job_id (str)",
    example: '{"job_id": "job-456"}',
  },
  {
    name: "atlas_vox_manage_profile",
    description: "Create, update, or delete a voice profile",
    requiredInputs: 'action (create|update|delete), profile_id? (str), name? (str)',
    example: '{"action": "create", "name": "My Voice", "provider_name": "kokoro"}',
  },
  {
    name: "atlas_vox_compare_voices",
    description: "Compare the same text across multiple voice profiles",
    requiredInputs: "text (str), profile_ids (str[])",
    example: '{"text": "Test phrase", "profile_ids": ["id1", "id2"]}',
  },
  {
    name: "atlas_vox_provider_status",
    description: "Get status and health of TTS providers",
    requiredInputs: "provider_name? (str)",
    example: '{"provider_name": "kokoro"}',
  },
];

/* ================================================================
   Self-Healing data
   ================================================================ */

interface DetectionRule {
  rule: string;
  threshold: string;
  severity: string;
  action: string;
}

const DETECTION_RULES: DetectionRule[] = [
  { rule: "Redis connection failure", threshold: "3 consecutive failures", severity: "critical", action: "Restart Redis, switch to in-memory fallback" },
  { rule: "Provider health check failure", threshold: "5 consecutive failures", severity: "warning", action: "Mark provider unhealthy, remove from rotation" },
  { rule: "High error rate", threshold: ">10% error rate over 5 min", severity: "warning", action: "Log alert, throttle requests" },
  { rule: "Celery worker unresponsive", threshold: "30 second heartbeat miss", severity: "critical", action: "Restart worker process" },
  { rule: "Disk space low", threshold: "<500 MB free in storage/", severity: "warning", action: "Purge old audio files, alert user" },
  { rule: "Database connection pool exhausted", threshold: "0 available connections", severity: "critical", action: "Close idle connections, increase pool size" },
  { rule: "Memory usage high", threshold: ">90% system memory", severity: "warning", action: "Trigger garbage collection, unload idle models" },
  { rule: "GPU VRAM exhausted", threshold: "CUDA OOM error", severity: "critical", action: "Unload least-used model, retry operation" },
];

/* ================================================================
   Deployment data
   ================================================================ */

interface PortAssignment {
  service: string;
  port: string;
  protocol: string;
  description: string;
}

const PORT_ASSIGNMENTS: PortAssignment[] = [
  { service: "Backend (FastAPI)", port: "8100", protocol: "HTTP", description: "REST API and WebSocket" },
  { service: "Frontend (Vite/Nginx)", port: "3100", protocol: "HTTP", description: "Web UI" },
  { service: "Redis", port: "6379", protocol: "TCP", description: "Cache, Celery broker (db 1)" },
  { service: "MCP Server", port: "8100", protocol: "SSE", description: "Shares backend port, /mcp/sse endpoint" },
  { service: "Swagger UI", port: "8100", protocol: "HTTP", description: "/docs endpoint" },
  { service: "ReDoc", port: "8100", protocol: "HTTP", description: "/redoc endpoint" },
];

/* ================================================================
   Reusable sub-components
   ================================================================ */

function CodeBlock({ children, className, title }: { children: string; className?: string; title?: string }) {
  return (
    <div className={className}>
      {title && (
        <div className="rounded-t bg-gray-800 px-3 py-1.5 text-[10px] font-medium text-gray-400">
          {title}
        </div>
      )}
      <pre
        className={`${title ? "rounded-b" : "rounded"} bg-gray-900 p-3 text-xs text-green-400 font-mono overflow-x-auto whitespace-pre-wrap`}
      >
        {children}
      </pre>
    </div>
  );
}

function StepCircle({ n }: { n: number }) {
  return (
    <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700 dark:bg-primary-900 dark:text-primary-300">
      {n}
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return <h3 className="mb-3 text-lg font-semibold">{children}</h3>;
}

/* ================================================================
   Tab: Provider Guides
   ================================================================ */

export function ProviderGuidesTab() {
  const [selectedProvider, setSelectedProvider] = useState(PROVIDER_GUIDES[0].name);
  const guide = PROVIDER_GUIDES.find((g) => g.name === selectedProvider) ?? PROVIDER_GUIDES[0];

  const providerOptions = PROVIDER_GUIDES.map((g) => ({
    value: g.name,
    label: g.displayName,
  }));

  return (
    <div className="space-y-4">
      {/* Provider selector */}
      <Card>
        <div className="max-w-xs">
          <Select
            label="Select Provider"
            value={selectedProvider}
            onChange={(e) => {
              logger.info("provider_selected", { provider: e.target.value });
              setSelectedProvider(e.target.value);
            }}
            options={providerOptions}
          />
        </div>
      </Card>

      {/* Provider header */}
      <Card>
        <div className="flex items-start gap-4">
          <ProviderLogo name={guide.name} size={40} />
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-bold">{guide.displayName}</h2>
              <Badge
                status={
                  guide.type === "cloud"
                    ? "cloud"
                    : guide.type === "local-cpu"
                    ? "ready"
                    : "gpu"
                }
              />
            </div>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{guide.description}</p>
            <div className="mt-2 flex flex-wrap gap-4 text-xs text-[var(--color-text-secondary)]">
              <span>Voices: {guide.voiceCount}</span>
            </div>
            <a
              href={guide.website}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-2 inline-flex items-center gap-1 text-sm text-primary-500 hover:underline"
            >
              {guide.website} <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </Card>

      {/* Quality notes */}
      <Card>
        <SectionHeading>Quality & Performance</SectionHeading>
        <p className="text-sm text-[var(--color-text-secondary)]">{guide.qualityNotes}</p>
      </Card>

      {/* Setup steps */}
      <CollapsiblePanel title="Setup Steps" defaultOpen icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          {guide.steps.map((step, i) => (
            <div key={i} className="flex gap-4">
              <StepCircle n={i + 1} />
              <div className="flex-1 min-w-0">
                <h4 className="font-medium">{step.title}</h4>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{step.description}</p>
                {step.code && <CodeBlock className="mt-2">{step.code}</CodeBlock>}
              </div>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Environment variables */}
      <CollapsiblePanel title="Environment Variables" defaultOpen={false} icon={<Settings className="h-4 w-4 text-primary-500" />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 font-medium">Variable</th>
                <th className="pb-2 font-medium">Required</th>
                <th className="pb-2 font-medium">Default</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {guide.envVars.map((v) => (
                <tr key={v.name} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">
                      {v.name}
                    </code>
                  </td>
                  <td className="py-2">
                    {v.required ? (
                      <span className="text-red-500 font-medium">Yes</span>
                    ) : (
                      <span className="text-[var(--color-text-secondary)]">No</span>
                    )}
                  </td>
                  <td className="py-2 text-[var(--color-text-secondary)]">
                    {v.defaultValue || <span className="italic">empty</span>}
                  </td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{v.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      {/* Common Issues */}
      <CollapsiblePanel title="Common Issues" defaultOpen={false} icon={<AlertTriangle className="h-4 w-4 text-yellow-500" />}>
        <div className="space-y-3">
          {guide.commonIssues.map((issue, i) => (
            <div key={i} className="rounded-lg border border-[var(--color-border)] p-3">
              <p className="text-sm font-medium text-red-600 dark:text-red-400">{issue.problem}</p>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{issue.solution}</p>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Code Examples */}
      <CollapsiblePanel title="Code Examples" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          <div>
            <p className="mb-2 text-sm font-medium">CLI Usage</p>
            <CodeBlock>{guide.cliExample}</CodeBlock>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">API Usage (curl)</p>
            <CodeBlock>{guide.apiExample}</CodeBlock>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Checklist */}
      <CollapsiblePanel title="Configuration Checklist" defaultOpen={false} icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}>
        <div className="space-y-2">
          {guide.checklist.map((item, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <Circle className="h-4 w-4 shrink-0 text-[var(--color-text-secondary)]" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Tips */}
      <CollapsiblePanel title="Tips & Best Practices" defaultOpen={false} icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}>
        <ul className="space-y-2">
          {guide.tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--color-text-secondary)]">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Tab: Architecture
   ================================================================ */

export function ArchitectureTab() {
  return (
    <div className="space-y-4">
      <Card>
        <SectionHeading>System Overview</SectionHeading>
        <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
          Atlas Vox is a modular voice platform with 4 access interfaces, 9 TTS providers,
          and a complete training pipeline backed by Celery workers.
        </p>
        <CodeBlock>{`
  +---------------------------+     +---------------------------+
  |        Frontend           |     |          CLI              |
  |   React 18 + TypeScript   |     |    Typer + Rich           |
  |   Tailwind + Zustand      |     |    atlas-vox <command>    |
  +------------+--------------+     +------------+--------------+
               |                                 |
               |  HTTP / WebSocket               |  HTTP
               v                                 v
  +----------------------------------------------------------+
  |                   Backend (FastAPI)                       |
  |  +-----------+  +-----------+  +----------+  +---------+ |
  |  | REST API  |  | WebSocket |  | MCP/SSE  |  | OpenAI  | |
  |  | /api/v1/* |  | /ws       |  | /mcp/sse |  | Compat  | |
  |  +-----------+  +-----------+  +----------+  +---------+ |
  |                                                          |
  |  +----------------------------------------------------+  |
  |  |              Service Layer                         |  |
  |  |  synthesis_service  |  training_service            |  |
  |  |  profile_service    |  comparison_service          |  |
  |  |  audio_processor    |  webhook_dispatcher          |  |
  |  +----------------------------------------------------+  |
  |                                                          |
  |  +----------------------------------------------------+  |
  |  |           Provider Abstraction Layer                |  |
  |  |  TTSProvider ABC -> get_capabilities() -> UI adapts |  |
  |  |  9 providers: kokoro, piper, elevenlabs, azure,     |  |
  |  |  coqui_xtts, styletts2, cosyvoice, dia, dia2       |  |
  |  +----------------------------------------------------+  |
  +---------------------------+------------------------------+
                              |
                +-------------+-------------+
                |                           |
  +-------------v---------+   +-------------v---------+
  |   SQLite / PostgreSQL |   |     Redis (db 1)      |
  |   10 tables           |   |   Celery broker        |
  |   async via aiosqlite |   |   Cache + pub/sub      |
  +-----------------------+   +-----------------------+
                                        |
                              +---------v---------+
                              |   Celery Worker    |
                              |   Training jobs    |
                              |   Preprocessing    |
                              +-------------------+`.trim()}</CodeBlock>
      </Card>

      <CollapsiblePanel title="Component Descriptions" defaultOpen icon={<Layers className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          {[
            {
              icon: <Server className="h-5 w-5 text-blue-500" />,
              name: "Backend (FastAPI)",
              description:
                "Python 3.11+ async web framework. Handles REST API, WebSocket connections, MCP server, and OpenAI-compatible endpoints. Uses Pydantic v2 for validation and structlog for structured logging.",
            },
            {
              icon: <Globe className="h-5 w-5 text-green-500" />,
              name: "Frontend (React)",
              description:
                "React 18 with TypeScript, Vite bundler, Tailwind CSS for styling, Zustand for state management. Features wavesurfer.js for audio visualization and Monaco Editor for SSML editing.",
            },
            {
              icon: <Terminal className="h-5 w-5 text-yellow-500" />,
              name: "CLI (Typer)",
              description:
                "Command-line interface built with Typer and Rich. Provides synthesize, train, compare, and provider management commands. Entry point: atlas-vox.",
            },
            {
              icon: <Plug className="h-5 w-5 text-purple-500" />,
              name: "MCP Server (JSONRPC 2.0)",
              description:
                "Model Context Protocol server with SSE transport. Exposes 9 tools and 2 resources for AI assistant integration. Connects via /mcp/sse endpoint.",
            },
            {
              icon: <Workflow className="h-5 w-5 text-red-500" />,
              name: "Celery Worker (Redis)",
              description:
                "Background task processor for training jobs, audio preprocessing, and model fine-tuning. Uses Redis as broker and result backend. Never blocks the FastAPI event loop.",
            },
          ].map((comp) => (
            <div key={comp.name} className="flex gap-3">
              <div className="mt-0.5 shrink-0">{comp.icon}</div>
              <div>
                <h4 className="font-medium">{comp.name}</h4>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{comp.description}</p>
              </div>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel title="Data Flow" defaultOpen={false} icon={<Workflow className="h-4 w-4 text-primary-500" />}>
        <CodeBlock>{`
Request Flow (Synthesis):
  Client Request
    -> FastAPI Router (/api/v1/synthesize)
      -> Dependency Injection (get_db, get_current_user)
        -> SynthesisService.synthesize()
          -> ProviderRegistry.get_provider(name)
            -> TTSProvider.synthesize(text, voice, params)
              -> Audio bytes returned
          -> Save to storage/audio/
          -> Record in synthesis_history table
        -> Return {audio_url, latency_ms, provider, voice}

Request Flow (Training):
  Client Request
    -> FastAPI Router (/api/v1/training)
      -> TrainingService.start_training()
        -> Create training_job record (status: queued)
        -> Dispatch Celery task
          -> Celery Worker picks up job
            -> Preprocessing (noise reduction, normalization)
            -> Provider-specific fine-tuning
            -> Save model weights
            -> Update job status (completed/failed)
          -> WebSocket notification to client`.trim()}</CodeBlock>
      </CollapsiblePanel>

      <CollapsiblePanel title="Database Schema" defaultOpen={false} icon={<Database className="h-4 w-4 text-primary-500" />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-4 font-medium">Table</th>
                <th className="pb-2 pr-4 font-medium">Key Columns</th>
                <th className="pb-2 font-medium">Purpose</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {[
                { table: "voice_profiles", cols: "id, name, provider_name, voice_id, language, status", purpose: "Voice identities bound to providers" },
                { table: "training_jobs", cols: "id, profile_id, provider_name, status, progress, error", purpose: "Training job tracking" },
                { table: "model_versions", cols: "id, profile_id, version, model_path, metrics", purpose: "Trained model versions" },
                { table: "audio_samples", cols: "id, profile_id, file_path, duration, format, preprocessed", purpose: "Training audio samples" },
                { table: "synthesis_history", cols: "id, profile_id, text, audio_url, latency_ms, provider", purpose: "Synthesis request log" },
                { table: "api_keys", cols: "id, key_hash, name, scopes, expires_at, revoked", purpose: "API key management" },
                { table: "presets", cols: "id, name, speed, pitch, volume, provider_name", purpose: "Persona presets" },
                { table: "provider_configs", cols: "id, provider_name, config_json, enabled", purpose: "Per-provider settings" },
                { table: "webhook_subscriptions", cols: "id, url, events, secret, active", purpose: "Webhook delivery config" },
                { table: "healing_incidents", cols: "id, severity, category, title, action_taken, outcome", purpose: "Self-healing event log" },
              ].map((row) => (
                <tr key={row.table} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-4">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">
                      {row.table}
                    </code>
                  </td>
                  <td className="py-2 pr-4 text-[var(--color-text-secondary)]">{row.cols}</td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{row.purpose}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      <CollapsiblePanel title="Provider Abstraction Pattern" defaultOpen={false} icon={<Box className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          All TTS providers implement the <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">TTSProvider</code> abstract
          base class. Each provider declares its capabilities via <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">get_capabilities()</code>,
          and the frontend dynamically adapts the UI based on what each provider supports.
        </p>
        <CodeBlock>{`
# backend/app/providers/base.py

class TTSProvider(ABC):
    """Abstract base class for all TTS providers."""

    @abstractmethod
    async def synthesize(self, text: str, voice_id: str, **params) -> bytes:
        """Synthesize text to audio bytes."""

    @abstractmethod
    async def get_voices(self) -> list[Voice]:
        """List available voices."""

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check provider health."""

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities:
        """Declare provider capabilities."""
        # Returns: { ssml, streaming, voice_cloning, languages, ... }

# The ProviderRegistry discovers and manages all providers:
#   registry.get_provider("kokoro")  -> KokoroProvider instance
#   registry.get_all_healthy()       -> list of healthy providers
#   registry.get_capabilities("dia") -> { dialogue: true, ... }`.trim()}</CodeBlock>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Tab: Configuration
   ================================================================ */

export function ConfigurationTab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedGroup, setSelectedGroup] = useState("All");

  const filtered = useMemo(() => {
    return CONFIG_VARS.filter((v) => {
      const matchesGroup = selectedGroup === "All" || v.group === selectedGroup;
      if (!searchTerm.trim()) return matchesGroup;
      const lower = searchTerm.toLowerCase();
      return (
        matchesGroup &&
        (v.name.toLowerCase().includes(lower) ||
          v.description.toLowerCase().includes(lower) ||
          v.group.toLowerCase().includes(lower))
      );
    });
  }, [searchTerm, selectedGroup]);

  const groupOptions = [{ value: "All", label: "All Groups" }, ...CONFIG_GROUPS.map((g) => ({ value: g, label: g }))];

  return (
    <div className="space-y-4">
      {/* Search and filter */}
      <Card>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-secondary)]" />
            <input
              type="text"
              placeholder="Search environment variables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>
          <div className="w-full sm:w-48">
            <Select
              label=""
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              options={groupOptions}
            />
          </div>
        </div>
      </Card>

      {/* Variable table */}
      <Card>
        <SectionHeading>
          Environment Variables
          <span className="ml-2 text-sm font-normal text-[var(--color-text-secondary)]">
            ({filtered.length} of {CONFIG_VARS.length})
          </span>
        </SectionHeading>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-3 font-medium">Variable</th>
                <th className="pb-2 pr-3 font-medium hidden sm:table-cell">Type</th>
                <th className="pb-2 pr-3 font-medium">Default</th>
                <th className="pb-2 pr-3 font-medium hidden md:table-cell">Group</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr key={v.name} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-3">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800 break-all">
                      {v.name}
                    </code>
                  </td>
                  <td className="py-2 pr-3 text-[var(--color-text-secondary)] hidden sm:table-cell">
                    <Badge status={v.type === "bool" ? "pending" : v.type === "int" ? "training" : "ready"} className="text-[10px]" />
                  </td>
                  <td className="py-2 pr-3 text-[var(--color-text-secondary)] text-xs font-mono">
                    {v.defaultValue || <span className="italic text-red-400">required</span>}
                  </td>
                  <td className="py-2 pr-3 hidden md:table-cell">
                    <Badge status={v.group === "Providers" ? "cloud" : v.group === "Auth" ? "archived" : "pending"} className="text-[10px]" />
                  </td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{v.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Configuration profiles */}
      <CollapsiblePanel title="Configuration Profiles" defaultOpen={false} icon={<Settings className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          {[
            {
              name: "Development",
              badge: "ready",
              description: "Local development with hot reload. No GPU, no auth, SQLite database.",
              config: `DEBUG=true
LOG_LEVEL=DEBUG
AUTH_DISABLED=true
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db
REDIS_URL=redis://localhost:6379/1
KOKORO_ENABLED=true
PIPER_ENABLED=true`,
            },
            {
              name: "Homelab",
              badge: "training",
              description: "Self-hosted deployment with GPU support. Optional auth. Docker Compose recommended.",
              config: `DEBUG=false
LOG_LEVEL=INFO
AUTH_DISABLED=true
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db
REDIS_URL=redis://redis:6379/1
COQUI_XTTS_GPU_MODE=docker_gpu
DIA_GPU_MODE=docker_gpu
ELEVENLABS_API_KEY=sk_your_key_here`,
            },
            {
              name: "Production",
              badge: "cloud",
              description: "Full production deployment with PostgreSQL, auth enabled, and all providers configured.",
              config: `DEBUG=false
LOG_LEVEL=WARNING
AUTH_DISABLED=false
JWT_SECRET=your-32-char-secret-here-change-me
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/atlas_vox
REDIS_URL=redis://redis:6379/1
CORS_ORIGINS=https://your-domain.com
ELEVENLABS_API_KEY=sk_your_key
AZURE_SPEECH_KEY=your_azure_key
AZURE_SPEECH_REGION=eastus`,
            },
          ].map((profile) => (
            <div key={profile.name}>
              <div className="mb-2 flex items-center gap-2">
                <h4 className="font-medium">{profile.name}</h4>
                <Badge status={profile.badge} />
              </div>
              <p className="mb-2 text-sm text-[var(--color-text-secondary)]">{profile.description}</p>
              <CodeBlock>{profile.config}</CodeBlock>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Example .env */}
      <CollapsiblePanel title="Example .env File" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <CodeBlock>{`# Atlas Vox Environment Configuration
# Copy to .env and customize for your deployment

# --- Application ---
APP_NAME=Atlas Vox
DEBUG=false
LOG_LEVEL=INFO
AUTH_DISABLED=true

# --- Server ---
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8100
CORS_ORIGINS=http://localhost:3100,http://localhost:3000

# --- Database ---
DATABASE_URL=sqlite+aiosqlite:///atlas_vox.db

# --- Redis ---
REDIS_URL=redis://localhost:6379/1
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# --- Storage ---
STORAGE_DIR=./storage
AUDIO_OUTPUT_DIR=./storage/audio
SAMPLES_DIR=./storage/samples
MODELS_DIR=./storage/models

# --- Cloud Providers (optional) ---
# ELEVENLABS_API_KEY=sk_your_key_here
# AZURE_SPEECH_KEY=your_key_here
# AZURE_SPEECH_REGION=eastus

# --- GPU Providers (optional) ---
# COQUI_XTTS_GPU_MODE=docker_gpu
# STYLETTS2_GPU_MODE=docker_gpu
# COSYVOICE_GPU_MODE=docker_gpu
# DIA_GPU_MODE=docker_gpu
# DIA2_GPU_MODE=docker_gpu`}</CodeBlock>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Tab: MCP Integration
   ================================================================ */

export function MCPIntegrationTab() {
  return (
    <div className="space-y-4">
      <Card>
        <SectionHeading>What is MCP?</SectionHeading>
        <p className="text-sm text-[var(--color-text-secondary)]">
          The <strong>Model Context Protocol (MCP)</strong> is an open standard that allows AI assistants like
          Claude to interact with external tools and data sources. Atlas Vox implements an MCP server that
          exposes voice synthesis, training, and management capabilities as tools that any MCP-compatible
          AI assistant can invoke. This means you can ask Claude to "speak this text with my voice" or
          "start training a new voice model" and it will use Atlas Vox behind the scenes.
        </p>
      </Card>

      {/* Tools */}
      <CollapsiblePanel title="MCP Tools (9)" defaultOpen icon={<Plug className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          {MCP_TOOLS.map((tool) => (
            <div key={tool.name} className="rounded-lg border border-[var(--color-border)] p-3">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-bold dark:bg-gray-800">
                  {tool.name}
                </code>
                <Badge status="ready" className="text-[10px]" />
              </div>
              <p className="text-sm text-[var(--color-text-secondary)] mb-2">{tool.description}</p>
              <div className="text-xs text-[var(--color-text-secondary)] mb-2">
                <strong>Inputs:</strong> {tool.requiredInputs}
              </div>
              <CodeBlock>{tool.example}</CodeBlock>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Resources */}
      <CollapsiblePanel title="MCP Resources (2)" defaultOpen icon={<Database className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-3">
          {[
            {
              uri: "atlas-vox://profiles",
              name: "Voice Profiles",
              mime: "application/json",
              description: "List of all voice profiles in Atlas Vox with their status, provider, and configuration.",
            },
            {
              uri: "atlas-vox://providers",
              name: "TTS Providers",
              mime: "application/json",
              description: "Available TTS providers and their health status, capabilities, and configuration.",
            },
          ].map((res) => (
            <div key={res.uri} className="rounded-lg border border-[var(--color-border)] p-3">
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <code className="rounded bg-gray-100 px-2 py-0.5 text-xs font-bold dark:bg-gray-800">
                  {res.uri}
                </code>
                <Badge status="cloud" className="text-[10px]" />
              </div>
              <p className="text-sm font-medium">{res.name}</p>
              <p className="text-sm text-[var(--color-text-secondary)]">{res.description}</p>
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">MIME: {res.mime}</p>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Connection example */}
      <CollapsiblePanel title="Claude Desktop Configuration" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Add this to your Claude Desktop <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">claude_desktop_config.json</code> to
          connect Claude to your Atlas Vox instance:
        </p>
        <CodeBlock>{`{
  "mcpServers": {
    "atlas-vox": {
      "transport": "sse",
      "url": "http://localhost:8100/mcp/sse",
      "headers": {
        "Authorization": "Bearer avx_your_api_key_here"
      }
    }
  }
}`}</CodeBlock>
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>Note:</strong> When <code className="text-xs">AUTH_DISABLED=true</code> (default),
            the Authorization header is optional. In production, create an API key with
            appropriate scopes on the API Keys page.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Claude Code CLI */}
      <CollapsiblePanel title="Claude Code (CLI) Configuration" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Add Atlas Vox as an MCP server in your Claude Code <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">settings.json</code> or
          project-level <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">.claude/settings.json</code>:
        </p>
        <CodeBlock title="~/.claude/settings.json">{`{
  "mcpServers": {
    "atlas-vox": {
      "type": "sse",
      "url": "http://localhost:8100/mcp/sse",
      "headers": {
        "Authorization": "Bearer avx_your_api_key_here"
      }
    }
  }
}`}</CodeBlock>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          Once configured, you can use Atlas Vox tools directly in Claude Code:
        </p>
        <CodeBlock title="Example usage in Claude Code">{`> Use atlas_vox_list_voices to show available voices
> Synthesize "Hello world" with the kokoro provider using atlas_vox_speak
> Check provider health with atlas_vox_provider_status`}</CodeBlock>
      </CollapsiblePanel>

      {/* Custom Agents (Python) */}
      <CollapsiblePanel title="Custom Python Agent Integration" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Connect any Python agent to Atlas Vox using the <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">mcp</code> SDK:
        </p>
        <CodeBlock title="pip install">{`pip install mcp httpx-sse`}</CodeBlock>
        <CodeBlock title="Python MCP Client">{`import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def main():
    # Connect to Atlas Vox MCP server
    async with sse_client(
        url="http://localhost:8100/mcp/sse",
        headers={"Authorization": "Bearer avx_your_api_key_here"}
    ) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize the connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # List available voices
            result = await session.call_tool(
                "atlas_vox_list_voices", arguments={}
            )
            print(f"Voices: {result.content}")

            # Synthesize speech
            result = await session.call_tool(
                "atlas_vox_speak",
                arguments={
                    "text": "Hello from my custom agent!",
                    "voice": "af_heart",
                    "provider": "kokoro"
                }
            )
            print(f"Audio: {result.content}")

            # Check provider health
            result = await session.call_tool(
                "atlas_vox_provider_status", arguments={}
            )
            print(f"Providers: {result.content}")

asyncio.run(main())`}</CodeBlock>
      </CollapsiblePanel>

      {/* Claude Agent SDK */}
      <CollapsiblePanel title="Claude Agent SDK (Anthropic)" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Use Atlas Vox as a tool server in agents built with the Anthropic Agent SDK:
        </p>
        <CodeBlock title="Python — claude_agent_sdk">{`from anthropic import Anthropic
from claude_agent_sdk import Agent, MCPServerConfig

# Configure Atlas Vox as an MCP server
atlas_vox = MCPServerConfig(
    name="atlas-vox",
    transport="sse",
    url="http://localhost:8100/mcp/sse",
    headers={"Authorization": "Bearer avx_your_api_key_here"}
)

# Create an agent with Atlas Vox tools
agent = Agent(
    model="claude-sonnet-4-6",
    mcp_servers=[atlas_vox],
    system_prompt="""You are a voice assistant. You can:
    - List available voices with atlas_vox_list_voices
    - Synthesize speech with atlas_vox_speak
    - Train new voice models with atlas_vox_train_voice
    - Compare voices with atlas_vox_compare_voices
    - Check provider status with atlas_vox_provider_status"""
)

# Run the agent
result = agent.run("Synthesize 'Welcome to Atlas Vox' using the best available voice")`}</CodeBlock>
      </CollapsiblePanel>

      {/* LangChain / LangGraph */}
      <CollapsiblePanel title="LangChain / LangGraph Integration" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Use the OpenAI-compatible API endpoint for LangChain agents. No MCP configuration needed — Atlas Vox
          exposes <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">POST /v1/audio/speech</code> which
          works with any OpenAI SDK client:
        </p>
        <CodeBlock title="Python — LangChain">{`from openai import OpenAI

# Point the OpenAI client at Atlas Vox
client = OpenAI(
    base_url="http://localhost:8100/v1",
    api_key="not-needed"  # AUTH_DISABLED=true
)

# Synthesize speech (OpenAI-compatible)
response = client.audio.speech.create(
    model="tts-1",       # Maps to Kokoro
    voice="alloy",       # Maps to af_alloy
    input="Hello from LangChain!",
    speed=1.0
)

# Save the audio
response.stream_to_file("output.mp3")`}</CodeBlock>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          <strong>Model mapping:</strong> <code className="text-xs">tts-1</code> → Kokoro,{" "}
          <code className="text-xs">tts-1-hd</code> → ElevenLabs.{" "}
          <strong>Voice mapping:</strong> alloy, echo, fable, onyx, nova, shimmer map to Kokoro voices.
        </p>
      </CollapsiblePanel>

      {/* Direct REST API */}
      <CollapsiblePanel title="Direct REST API (curl / httpx / fetch)" defaultOpen={false} icon={<Terminal className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          For custom integrations without MCP, use the REST API directly:
        </p>
        <CodeBlock title="curl — Synthesize speech">{`# Synthesize text (requires a voice profile ID)
curl -X POST http://localhost:8100/api/v1/synthesize \\
  -H "Content-Type: application/json" \\
  -d '{"text": "Hello world", "profile_id": "YOUR_PROFILE_ID"}' \\
  | jq .

# OpenAI-compatible endpoint (no profile needed)
curl -X POST http://localhost:8100/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{"model": "tts-1", "voice": "alloy", "input": "Hello world"}' \\
  --output hello.mp3

# List all providers
curl http://localhost:8100/api/v1/providers | jq .

# Health check
curl http://localhost:8100/api/v1/health | jq .`}</CodeBlock>
        <CodeBlock title="Python — httpx">{`import httpx

client = httpx.Client(base_url="http://localhost:8100")

# List voices
voices = client.get("/api/v1/voices").json()
print(f"{voices['count']} voices available")

# Synthesize
result = client.post("/api/v1/synthesize", json={
    "text": "Hello from Python!",
    "profile_id": "your-profile-id",
    "speed": 1.0,
    "output_format": "wav"
}).json()
print(f"Audio: {result['audio_url']}")`}</CodeBlock>
        <CodeBlock title="JavaScript — fetch">{`// List providers
const providers = await fetch('http://localhost:8100/api/v1/providers')
  .then(r => r.json());
console.log(providers.providers.map(p => p.display_name));

// OpenAI-compatible synthesis
const audio = await fetch('http://localhost:8100/v1/audio/speech', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'tts-1',
    voice: 'alloy',
    input: 'Hello from JavaScript!'
  })
});
const blob = await audio.blob();
// Play or save the audio blob`}</CodeBlock>
      </CollapsiblePanel>

      {/* n8n / Make / Zapier */}
      <CollapsiblePanel title="n8n / Make / Zapier (Webhook)" defaultOpen={false} icon={<Workflow className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Use Atlas Vox webhooks to trigger automations when training completes or fails:
        </p>
        <CodeBlock title="Create a webhook subscription">{`# Subscribe to training events
curl -X POST http://localhost:8100/api/v1/webhooks \\
  -H "Content-Type: application/json" \\
  -d '{
    "url": "https://your-n8n-instance.com/webhook/atlas-vox",
    "events": "training.completed,training.failed",
    "secret": "your-hmac-secret"
  }'`}</CodeBlock>
        <p className="mt-3 text-sm text-[var(--color-text-secondary)]">
          Atlas Vox sends HMAC-SHA256 signed payloads to your webhook URL. Verify with the{" "}
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">X-Atlas-Vox-Signature</code> header.
        </p>
        <p className="mt-2 text-sm text-[var(--color-text-secondary)]">
          For <strong>n8n</strong>: Use an HTTP Webhook trigger node. For <strong>Make</strong>: Use a Custom Webhook module.
          For <strong>Zapier</strong>: Use Webhooks by Zapier as the trigger. The payload includes job ID, profile ID,
          provider, status, and error details.
        </p>
      </CollapsiblePanel>

      {/* SSE Transport */}
      <CollapsiblePanel title="SSE Transport Details" defaultOpen={false} icon={<Workflow className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Atlas Vox uses <strong>Server-Sent Events (SSE)</strong> as the MCP transport mechanism.
          SSE provides a persistent, one-way connection from server to client, with client-to-server
          communication via HTTP POST to a messages endpoint.
        </p>
        <CodeBlock>{`Transport Flow:
  1. Client connects to GET /mcp/sse
  2. Server sends SSE event with messages endpoint URL
  3. Client sends JSONRPC 2.0 requests via POST to /mcp/message
  4. Server streams responses back via SSE

Endpoints:
  GET  /mcp/sse          — SSE connection (persistent)
  POST /mcp/message      — JSONRPC 2.0 requests

Protocol:     JSONRPC 2.0
Auth:         Bearer token in Authorization header
              Optional when AUTH_DISABLED=true (default)
Scopes:       read, write, synthesize, train, admin
Keepalive:    Ping every 30 seconds`}</CodeBlock>
      </CollapsiblePanel>

      {/* API Key Scopes for MCP */}
      <CollapsiblePanel title="API Key Scopes for MCP" defaultOpen={false} icon={<ShieldCheck className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Each MCP tool requires specific scopes. Create an API key on the API Keys page with the appropriate scopes for your use case:
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 font-medium">Tool</th>
                <th className="pb-2 font-medium">Required Scope</th>
                <th className="pb-2 font-medium">Use Case</th>
              </tr>
            </thead>
            <tbody>
              {[
                { tool: "atlas_vox_list_voices", scope: "read", use: "Browse available voices" },
                { tool: "atlas_vox_provider_status", scope: "read", use: "Check provider health" },
                { tool: "atlas_vox_get_training_status", scope: "read", use: "Monitor training jobs" },
                { tool: "atlas_vox_list_available_voices", scope: "read", use: "Browse provider voices" },
                { tool: "atlas_vox_synthesize", scope: "synthesize", use: "Generate speech from profile" },
                { tool: "atlas_vox_speak", scope: "synthesize", use: "Quick synthesis (no profile)" },
                { tool: "atlas_vox_compare_voices", scope: "synthesize", use: "Side-by-side comparison" },
                { tool: "atlas_vox_manage_profile", scope: "write", use: "Create/update/delete profiles" },
                { tool: "atlas_vox_train_voice", scope: "train", use: "Start training jobs" },
              ].map((row) => (
                <tr key={row.tool} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2"><code className="text-xs">{row.tool}</code></td>
                  <td className="py-2"><Badge status={row.scope === "read" ? "ready" : row.scope === "synthesize" ? "training" : row.scope === "write" ? "pending" : "error"} className="text-[10px]" /></td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{row.use}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <CodeBlock title="Create a scoped API key">{`# Read-only key (list voices, check health)
curl -X POST http://localhost:8100/api/v1/api-keys \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-agent-readonly", "scopes": ["read"]}'

# Synthesis key (read + synthesize)
curl -X POST http://localhost:8100/api/v1/api-keys \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-agent-synth", "scopes": ["read", "synthesize"]}'

# Full access key
curl -X POST http://localhost:8100/api/v1/api-keys \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-agent-admin", "scopes": ["admin"]}'`}</CodeBlock>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Tab: Self-Healing
   ================================================================ */

export function SelfHealingTab() {
  return (
    <div className="space-y-4">
      <Card>
        <SectionHeading>Self-Healing Architecture</SectionHeading>
        <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
          Atlas Vox includes a self-healing system that automatically detects and remediates common
          infrastructure issues. It monitors provider health, Redis connectivity, error rates, and
          resource usage, taking corrective action without manual intervention.
        </p>
        <CodeBlock>{`
  +------------------+     +-------------------+     +------------------+
  |   Health Monitor |---->| Detection Engine  |---->| Remediation      |
  |                  |     |                   |     | Engine           |
  |  - Provider pings|     | - Rule matching   |     |                  |
  |  - Redis check   |     | - Threshold eval  |     | - Restart svc    |
  |  - Error rates   |     | - Severity assign |     | - Fallback mode  |
  |  - Resource usage|     |                   |     | - Purge cache    |
  +------------------+     +-------------------+     | - Alert user     |
                                    |                +--------+---------+
                                    v                         |
                           +-------------------+              v
                           | Incident Log      |     +------------------+
                           | (healing_incidents)|     | MCP Bridge       |
                           | - Severity         |     | (AI-assisted     |
                           | - Action taken     |     |  remediation)    |
                           | - Outcome          |     +------------------+
                           +-------------------+`.trim()}</CodeBlock>
      </Card>

      {/* Detection rules */}
      <CollapsiblePanel title="Detection Rules" defaultOpen icon={<AlertTriangle className="h-4 w-4 text-yellow-500" />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-3 font-medium">Rule</th>
                <th className="pb-2 pr-3 font-medium">Threshold</th>
                <th className="pb-2 pr-3 font-medium">Severity</th>
                <th className="pb-2 font-medium">Action</th>
              </tr>
            </thead>
            <tbody>
              {DETECTION_RULES.map((rule, i) => (
                <tr key={i} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-3 font-medium">{rule.rule}</td>
                  <td className="py-2 pr-3 text-[var(--color-text-secondary)] text-xs">{rule.threshold}</td>
                  <td className="py-2 pr-3">
                    <Badge
                      status={rule.severity === "critical" ? "error" : "archived"}
                      className="text-[10px]"
                    />
                  </td>
                  <td className="py-2 text-[var(--color-text-secondary)] text-xs">{rule.action}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      {/* Remediation hierarchy */}
      <CollapsiblePanel title="Remediation Action Hierarchy" defaultOpen={false} icon={<ShieldCheck className="h-4 w-4 text-green-500" />}>
        <div className="space-y-3">
          {[
            { level: 1, name: "Automatic Recovery", description: "Restart services, reconnect, retry operations. No human intervention needed.", badge: "ready" },
            { level: 2, name: "Graceful Degradation", description: "Switch to fallback mode (in-memory cache, alternative provider, reduced features).", badge: "training" },
            { level: 3, name: "Resource Cleanup", description: "Purge old files, close idle connections, trigger garbage collection, unload unused models.", badge: "pending" },
            { level: 4, name: "Alert & Escalate", description: "Log incident, send webhook notification, mark as requiring human attention.", badge: "archived" },
            { level: 5, name: "MCP-Assisted Fix", description: "If MCP bridge is enabled, allow AI assistant to analyze the incident and suggest or apply a fix.", badge: "cloud" },
          ].map((action) => (
            <div key={action.level} className="flex gap-3">
              <StepCircle n={action.level} />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h4 className="font-medium">{action.name}</h4>
                  <Badge status={action.badge} className="text-[10px]" />
                </div>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{action.description}</p>
              </div>
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* MCP Bridge */}
      <CollapsiblePanel title="MCP Bridge" defaultOpen={false} icon={<Plug className="h-4 w-4 text-purple-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          The MCP bridge allows an AI assistant (e.g., Claude) to participate in incident remediation.
          When enabled, the self-healing system can expose incident details to the MCP server, allowing
          the AI to analyze root causes and suggest or apply fixes.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-3 font-medium">Setting</th>
                <th className="pb-2 pr-3 font-medium">Default</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                { setting: "MCP bridge enabled", def: "true", desc: "Allow AI-assisted remediation" },
                { setting: "Max fixes per hour", def: "10", desc: "Rate limit on automated fixes" },
                { setting: "Auto-apply fixes", def: "false", desc: "Apply fixes without confirmation (dangerous)" },
              ].map((s, i) => (
                <tr key={i} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-3 font-medium">{s.setting}</td>
                  <td className="py-2 pr-3 text-[var(--color-text-secondary)]">{s.def}</td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{s.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      {/* Testing */}
      <CollapsiblePanel title="How to Test Self-Healing" defaultOpen={false} icon={<Cpu className="h-4 w-4 text-primary-500" />}>
        <div className="space-y-4">
          <div>
            <p className="mb-2 text-sm font-medium">1. Simulate Redis failure</p>
            <CodeBlock>{`# Stop Redis
docker compose -f docker/docker-compose.yml stop redis

# Watch the Healing page for a critical incident
# The system should detect the failure within 30 seconds
# and switch to in-memory fallback mode

# Restart Redis
docker compose -f docker/docker-compose.yml start redis

# The system should auto-reconnect and log a "resolved" incident`}</CodeBlock>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">2. Check incident log</p>
            <CodeBlock>{`# Via API
curl http://localhost:8100/api/v1/healing/incidents

# Via Web UI
# Navigate to the Self-Healing page and expand "Incident History"

# Each incident shows:
# - Severity (critical, warning, info)
# - Category (redis, provider, resource, etc.)
# - Action taken and outcome (resolved, failed, escalated)`}</CodeBlock>
          </div>
          <div>
            <p className="mb-2 text-sm font-medium">3. Trigger provider failure</p>
            <CodeBlock>{`# Set an invalid API key for ElevenLabs
# The provider health check should fail
# After 5 consecutive failures, the system will:
# 1. Mark the provider as unhealthy
# 2. Remove it from the synthesis rotation
# 3. Log a warning-level incident`}</CodeBlock>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Incident log format */}
      <CollapsiblePanel title="Incident Log Format" defaultOpen={false} icon={<Database className="h-4 w-4 text-primary-500" />}>
        <CodeBlock>{`{
  "id": "inc_a1b2c3d4",
  "severity": "critical",
  "category": "redis",
  "title": "Redis connection failure",
  "description": "Connection refused after 3 consecutive attempts",
  "action_taken": "restart_service",
  "action_detail": "Attempted Redis reconnection with exponential backoff",
  "outcome": "resolved",
  "created_at": "2025-03-29T14:32:00Z",
  "resolved_at": "2025-03-29T14:32:45Z",
  "duration_seconds": 45
}`}</CodeBlock>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Tab: Deployment
   ================================================================ */

export function DeploymentTab() {
  return (
    <div className="space-y-4">
      {/* Quickstart */}
      <Card>
        <SectionHeading>Docker Compose Quickstart</SectionHeading>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          Get Atlas Vox running in 3 commands:
        </p>
        <div className="space-y-3">
          {[
            { n: 1, label: "Clone the repository", cmd: "git clone https://github.com/HouseGarofalo/atlas-vox.git && cd atlas-vox" },
            { n: 2, label: "Configure environment (optional)", cmd: "cp docker/.env.example docker/.env  # Edit as needed" },
            { n: 3, label: "Start all services", cmd: "make docker-up  # or: docker compose -f docker/docker-compose.yml up -d" },
          ].map((step) => (
            <div key={step.n} className="flex gap-3">
              <StepCircle n={step.n} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">{step.label}</p>
                <CodeBlock className="mt-1">{step.cmd}</CodeBlock>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Docker Compose services */}
      <CollapsiblePanel title="Docker Compose Services" defaultOpen icon={<Box className="h-4 w-4 text-primary-500" />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-3 font-medium">Service</th>
                <th className="pb-2 pr-3 font-medium">Image / Build</th>
                <th className="pb-2 pr-3 font-medium">Port</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {[
                { service: "backend", image: "Build from Dockerfile", port: "8100", desc: "FastAPI server, REST API, WebSocket, MCP" },
                { service: "frontend", image: "Build from Dockerfile", port: "3100", desc: "React app served by Nginx" },
                { service: "redis", image: "redis:7-alpine", port: "6379", desc: "Cache, Celery broker, pub/sub (db 1)" },
                { service: "worker", image: "Same as backend", port: "--", desc: "Celery worker for training/preprocessing" },
              ].map((svc) => (
                <tr key={svc.service} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-3">
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">{svc.service}</code>
                  </td>
                  <td className="py-2 pr-3 text-[var(--color-text-secondary)] text-xs">{svc.image}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{svc.port}</td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{svc.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      {/* GPU Deployment */}
      <CollapsiblePanel title="GPU Deployment" defaultOpen={false} icon={<Cpu className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          For GPU-accelerated providers (Coqui XTTS, StyleTTS2, CosyVoice, Dia, Dia2), use the GPU
          Docker Compose configuration:
        </p>
        <CodeBlock>{`# Start with GPU support
make docker-gpu-up

# Or manually:
docker compose -f docker/docker-compose.yml -f docker/compose.gpu.yml up -d

# Prerequisites:
# - NVIDIA GPU with CUDA support
# - NVIDIA Container Toolkit installed
# - Docker configured for GPU passthrough

# Verify GPU access inside container:
docker compose -f docker/docker-compose.yml exec worker nvidia-smi`}</CodeBlock>
        <div className="mt-3 rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20">
          <p className="text-sm text-yellow-800 dark:text-yellow-300">
            <strong>VRAM Requirements:</strong> Coqui XTTS (4 GB), StyleTTS2 (2 GB), CosyVoice (3 GB),
            Dia (6 GB), Dia2 (8 GB). Running multiple GPU providers simultaneously requires sufficient VRAM.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Port assignments */}
      <CollapsiblePanel title="Port Assignments" defaultOpen={false} icon={<Server className="h-4 w-4 text-primary-500" />}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 pr-3 font-medium">Service</th>
                <th className="pb-2 pr-3 font-medium">Port</th>
                <th className="pb-2 pr-3 font-medium">Protocol</th>
                <th className="pb-2 font-medium">Description</th>
              </tr>
            </thead>
            <tbody>
              {PORT_ASSIGNMENTS.map((p, i) => (
                <tr key={i} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 pr-3 font-medium">{p.service}</td>
                  <td className="py-2 pr-3 font-mono text-xs">{p.port}</td>
                  <td className="py-2 pr-3">
                    <Badge status={p.protocol === "HTTP" ? "ready" : p.protocol === "SSE" ? "cloud" : "pending"} className="text-[10px]" />
                  </td>
                  <td className="py-2 text-[var(--color-text-secondary)]">{p.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-3 rounded-lg border border-blue-200 bg-blue-50 p-3 dark:border-blue-800 dark:bg-blue-900/20">
          <p className="text-sm text-blue-800 dark:text-blue-300">
            <strong>Coexistence with ATLAS:</strong> Atlas Vox uses port 8100 (ATLAS uses 8000),
            Redis db 1 (ATLAS uses db 0), and a separate SQLite file. Both can run simultaneously.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Docker environment variables */}
      <CollapsiblePanel title="Docker Environment Variables" defaultOpen={false} icon={<Settings className="h-4 w-4 text-primary-500" />}>
        <p className="mb-3 text-sm text-[var(--color-text-secondary)]">
          These variables are specific to the Docker deployment and are set in <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">docker/.env</code>:
        </p>
        <CodeBlock>{`# Docker-specific settings
COMPOSE_PROJECT_NAME=atlas-vox
BACKEND_PORT=8100
FRONTEND_PORT=3100
REDIS_PORT=6379

# Resource limits
BACKEND_MEMORY_LIMIT=2g
WORKER_MEMORY_LIMIT=4g
WORKER_CPU_LIMIT=4

# GPU settings (compose.gpu.yml)
NVIDIA_VISIBLE_DEVICES=all
NVIDIA_DRIVER_CAPABILITIES=compute,utility

# All other Atlas Vox env vars can be set here too
# They will be passed to the backend and worker containers`}</CodeBlock>
      </CollapsiblePanel>

      {/* Health checks */}
      <CollapsiblePanel title="Health Check Verification" defaultOpen={false} icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}>
        <div className="space-y-3">
          <p className="text-sm text-[var(--color-text-secondary)]">
            After deployment, verify all services are running:
          </p>
          <CodeBlock>{`# Check all containers are running
docker compose -f docker/docker-compose.yml ps

# Backend health check
curl http://localhost:8100/api/v1/health
# Expected: {"status":"healthy","checks":{"database":"ok","redis":"ok","storage":"ok"}}

# Frontend check
curl -s -o /dev/null -w "%{http_code}" http://localhost:3100
# Expected: 200

# Redis check
docker compose -f docker/docker-compose.yml exec redis redis-cli -n 1 ping
# Expected: PONG

# Provider health (all providers)
curl http://localhost:8100/api/v1/providers
# Each provider should have status: "healthy" or "unhealthy" with reason

# Celery worker check
docker compose -f docker/docker-compose.yml exec worker celery -A app.tasks.celery_app inspect ping
# Expected: pong response`}</CodeBlock>
        </div>
      </CollapsiblePanel>

      {/* Production checklist */}
      <CollapsiblePanel title="Production Checklist" defaultOpen={false} icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}>
        <div className="space-y-2">
          {[
            "Set AUTH_DISABLED=false and configure JWT_SECRET (32+ characters)",
            "Use PostgreSQL instead of SQLite for production workloads",
            "Set CORS_ORIGINS to specific allowed domains (not *)",
            "Configure HTTPS via reverse proxy (Nginx, Traefik, or Caddy)",
            "Set LOG_LEVEL=WARNING to reduce log volume",
            "Configure backup strategy for storage/ directory and database",
            "Set up monitoring and alerting (Prometheus, Grafana, or similar)",
            "Review and set rate limits (RATE_LIMIT_SYNTHESIS, RATE_LIMIT_TRAINING)",
            "Configure webhook subscriptions for critical events",
            "Test self-healing system and verify incident notifications",
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-3 text-sm">
              <Circle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--color-text-secondary)]" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   Main Page
   ================================================================ */

export default function DocsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Provider Guides");

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Documentation</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Technical guides, architecture reference, and deployment instructions for Atlas Vox
        </p>
      </div>

      {/* Tab bar (same style as HelpPage) */}
      <div className="flex gap-1 overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-sidebar)] p-1">
        {TABS.map((tab) => {
          const Icon = TAB_ICONS[tab];
          return (
            <button
              key={tab}
              onClick={() => {
                logger.info("tab_change", { tab });
                setActiveTab(tab);
              }}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab
                  ? "bg-primary-500 text-white"
                  : "text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">{tab}</span>
              <span className="sm:hidden">{tab.split(" ")[0]}</span>
            </button>
          );
        })}
      </div>

      {/* Tab content */}
      {activeTab === "Provider Guides" && <ProviderGuidesTab />}
      {activeTab === "Architecture" && <ArchitectureTab />}
      {activeTab === "Configuration" && <ConfigurationTab />}
      {activeTab === "MCP Integration" && <MCPIntegrationTab />}
      {activeTab === "Self-Healing" && <SelfHealingTab />}
      {activeTab === "Deployment" && <DeploymentTab />}
    </div>
  );
}
