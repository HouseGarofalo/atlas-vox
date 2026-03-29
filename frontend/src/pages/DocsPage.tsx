import { useEffect, useState } from "react";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import { Badge } from "../components/ui/Badge";
import { CheckCircle2, Circle, ExternalLink } from "lucide-react";
import ProviderLogo from "../components/providers/ProviderLogo";
import { createLogger } from "../utils/logger";

const logger = createLogger("DocsPage");

/* ---------- types ---------- */

interface ProviderGuide {
  name: string;
  displayName: string;
  type: "cloud" | "local-cpu" | "local-gpu";
  description: string;
  website: string;
  steps: SetupStep[];
  envVars: EnvVar[];
  checklist: string[];
  tips: string[];
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

/* ---------- data ---------- */

const PROVIDER_GUIDES: ProviderGuide[] = [
  {
    name: "kokoro",
    displayName: "Kokoro",
    type: "local-cpu",
    description:
      "Lightweight, fast TTS with 54 built-in voices. CPU-only, no GPU required. Default provider in Atlas Vox.",
    website: "https://github.com/hexgrad/kokoro",
    steps: [
      {
        title: "No Setup Required",
        description:
          "Kokoro works out of the box with no configuration. It is the default provider and is automatically enabled.",
      },
      {
        title: "Verify Health",
        description:
          'Go to the Providers page and check that Kokoro shows a green "healthy" badge. If not, check that the kokoro Python package is installed.',
      },
      {
        title: "Browse Voices",
        description:
          "Kokoro includes 54 built-in voices. Prefixes: af_ (American female), am_ (American male), bf_ (British female), bm_ (British male).",
      },
    ],
    envVars: [
      { name: "KOKORO_ENABLED", required: false, defaultValue: "true", description: "Enable or disable Kokoro" },
    ],
    checklist: [
      "Backend is running",
      "Kokoro health check passes",
      "Can list Kokoro voices in Voice Library",
      "Can synthesize speech with a Kokoro profile",
    ],
    tips: [
      "Kokoro is the fastest CPU provider -- ideal for testing and prototyping",
      "Keep text under 500 characters per request for best quality",
      "82M parameter model uses minimal RAM",
    ],
  },
  {
    name: "piper",
    displayName: "Piper",
    type: "local-cpu",
    description:
      "Fast, local TTS optimized for Raspberry Pi and Home Assistant. ONNX-based with many pre-trained voices across 30+ languages.",
    website: "https://github.com/rhasspy/piper",
    steps: [
      {
        title: "Default Model Downloaded Automatically",
        description:
          "The Docker build downloads en_US-lessac-medium.onnx automatically. For local dev, you may need to download it manually.",
        code: "mkdir -p storage/models/piper\ncd storage/models/piper\n# Download from https://huggingface.co/rhasspy/piper-voices",
      },
      {
        title: "Add More Voices (Optional)",
        description:
          "Download additional ONNX models from the Piper Voices repository and place them in the model directory.",
        code: "# Each voice needs two files:\n# <name>.onnx\n# <name>.onnx.json",
      },
      {
        title: "Verify Setup",
        description:
          "Run a health check on the Providers page. Piper should show healthy if at least one model file is present.",
      },
    ],
    envVars: [
      { name: "PIPER_ENABLED", required: false, defaultValue: "true", description: "Enable or disable Piper" },
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
    ],
    tips: [
      "Use medium quality models for the best speed/quality balance",
      "Piper supports 30+ languages -- download models for each language you need",
      "Very low memory footprint, works on Raspberry Pi",
    ],
  },
  {
    name: "elevenlabs",
    displayName: "ElevenLabs",
    type: "cloud",
    description:
      "Industry-leading cloud TTS with the most natural-sounding voices. Supports instant voice cloning and 29 languages.",
    website: "https://elevenlabs.io",
    steps: [
      {
        title: "Create an ElevenLabs Account",
        description: "Sign up at elevenlabs.io. A free tier with 10,000 characters/month is available.",
      },
      {
        title: "Get Your API Key",
        description:
          "Go to Profile Settings > API Keys and copy your key.",
      },
      {
        title: "Configure in Atlas Vox",
        description:
          "Go to Providers > ElevenLabs > Settings. Enter your API key and click Save.",
      },
      {
        title: "Run Health Check",
        description:
          "Click the Health Check button. If the API key is valid, the status should change to healthy.",
      },
      {
        title: "Test Synthesis",
        description:
          "Click Test to run a quick synthesis and verify audio output.",
      },
    ],
    envVars: [
      { name: "ELEVENLABS_API_KEY", required: true, defaultValue: "", description: "Your ElevenLabs API key" },
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
    ],
  },
  {
    name: "azure_speech",
    displayName: "Azure Speech",
    type: "cloud",
    description:
      "Microsoft Azure Cognitive Services TTS with 400+ neural voices, full SSML support, and enterprise reliability.",
    website: "https://azure.microsoft.com/en-us/products/ai-services/text-to-speech",
    steps: [
      {
        title: "Create an Azure Account",
        description: "Sign up at azure.microsoft.com. A free tier with 500K characters/month is available.",
      },
      {
        title: "Create a Speech Resource",
        description:
          "In the Azure Portal, create a new Speech resource. Note the region you select.",
      },
      {
        title: "Get Your Key and Region",
        description:
          "Go to your Speech resource > Keys and Endpoint. Copy Key 1 and the Region.",
      },
      {
        title: "Configure in Atlas Vox",
        description:
          "Go to Providers > Azure Speech > Settings. Enter the subscription key and region. Click Save.",
      },
      {
        title: "Run Health Check",
        description: "Click Health Check to verify the credentials work.",
      },
    ],
    envVars: [
      { name: "AZURE_SPEECH_KEY", required: true, defaultValue: "", description: "Azure subscription key" },
      { name: "AZURE_SPEECH_REGION", required: true, defaultValue: "eastus", description: "Azure region" },
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
      "400+ neural voices across 140+ languages",
      "Only provider with full SSML support",
      "Use en-US-JennyNeural for natural conversational English",
      "eastus region typically has lowest latency for US users",
    ],
  },
  {
    name: "coqui_xtts",
    displayName: "Coqui XTTS v2",
    type: "local-gpu",
    description:
      "State-of-the-art voice cloning from just 6 seconds of audio. Supports 17 languages with zero-shot synthesis.",
    website: "https://github.com/coqui-ai/TTS",
    steps: [
      {
        title: "Enable GPU Mode (Recommended)",
        description:
          "For usable speed, GPU mode is strongly recommended. Set the environment variable or use the GPU Docker setup.",
        code: "COQUI_XTTS_GPU_MODE=docker_gpu\n# Or use: make docker-gpu-up",
      },
      {
        title: "Model Downloads Automatically",
        description:
          "The XTTS v2 model (~1.8 GB) downloads on first use. Ensure internet access from the container.",
      },
      {
        title: "Run Health Check",
        description:
          "Go to Providers > Coqui XTTS > Health Check. First check will be slow (model loading).",
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
      "Supports 17 languages including English, Spanish, French, German, Chinese, Japanese",
      "Clean audio without background noise is critical for good cloning",
    ],
  },
  {
    name: "styletts2",
    displayName: "StyleTTS2",
    type: "local-gpu",
    description:
      "Style diffusion and adversarial training for human-level speech quality. Zero-shot voice transfer.",
    website: "https://github.com/yl4579/StyleTTS2",
    steps: [
      {
        title: "Enable GPU Mode",
        description: "StyleTTS2 is impractical on CPU. Use GPU mode.",
        code: "STYLETTS2_GPU_MODE=docker_gpu",
      },
      {
        title: "Verify Dependencies",
        description:
          "espeak-ng and NLTK punkt data are required. Both are installed automatically in Docker.",
      },
      {
        title: "Run Health Check",
        description: "First health check may be slow as the model loads. Subsequent checks are faster.",
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
      "English-only, but achieves the highest quality MOS scores",
      "Style transfer lets you apply one voice's style to another voice's identity",
      "CPU mode is very slow -- GPU is strongly recommended",
    ],
  },
  {
    name: "cosyvoice",
    displayName: "CosyVoice",
    type: "local-gpu",
    description:
      "Alibaba's multilingual TTS with natural prosody. Supports 9 languages with ~150ms streaming latency.",
    website: "https://github.com/FunAudioLLM/CosyVoice",
    steps: [
      {
        title: "Enable GPU Mode",
        description: "GPU mode is recommended for acceptable performance.",
        code: "COSYVOICE_GPU_MODE=docker_gpu",
      },
      {
        title: "Install from GitHub",
        description:
          "CosyVoice is installed from its GitHub repository during Docker build.",
      },
      {
        title: "Run Health Check",
        description: "Verify the provider is operational via the Providers page.",
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
      "Health check passes",
    ],
    tips: [
      "Excellent for Chinese and Asian language TTS",
      "~150ms first-chunk latency in streaming mode on GPU",
      "Handles code-switching between languages naturally",
    ],
  },
  {
    name: "dia",
    displayName: "Dia",
    type: "local-gpu",
    description:
      "Nari Labs dialogue TTS with 1.6B parameters. Generates natural multi-speaker conversations with non-verbal sounds.",
    website: "https://github.com/nari-labs/dia",
    steps: [
      {
        title: "Enable GPU Mode",
        description: "Dia's 1.6B model requires GPU. Minimum 6 GB VRAM.",
        code: "DIA_GPU_MODE=docker_gpu",
      },
      {
        title: "Use Dialogue Format",
        description:
          "Use [S1] and [S2] tags for speakers. Non-verbal sounds go in parentheses: (laughs), (sighs).",
        code: '[S1] Hello, how are you?\n[S2] Great! (laughs) And you?',
      },
      {
        title: "Run Health Check",
        description: "Model downloads on first use (~3 GB). Health check will be slow initially.",
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
      "Model downloaded successfully",
      "Health check passes",
    ],
    tips: [
      "Use [S1] and [S2] tags for different speakers",
      "Supports non-verbal sounds: (laughs), (sighs), (clears throat)",
      "Great for podcast and conversation generation",
      "CPU mode is impractical for this model size",
    ],
  },
  {
    name: "dia2",
    displayName: "Dia2",
    type: "local-gpu",
    description:
      "Next-gen dialogue model with 2B parameters and streaming support. Real-time conversation generation.",
    website: "https://github.com/nari-labs/dia",
    steps: [
      {
        title: "Enable GPU Mode",
        description: "Dia2's 2B model requires GPU. Minimum 8 GB VRAM.",
        code: "DIA2_GPU_MODE=docker_gpu",
      },
      {
        title: "Model Downloads on First Use",
        description: "The 2B parameter model is approximately 4 GB. Ensure sufficient disk space.",
      },
      {
        title: "Run Health Check",
        description: "First health check will be slow. Subsequent checks are faster.",
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
    ],
    tips: [
      "Primary advantage over Dia: streaming support",
      "2B parameters produce higher quality than Dia's 1.6B",
      "CPU mode is not practical for this model",
    ],
  },
];

/* ---------- page ---------- */

export default function DocsPage() {
  const [selectedProvider, setSelectedProvider] = useState(PROVIDER_GUIDES[0].name);

  useEffect(() => {
    logger.info("page_mounted");
  }, []);

  const guide = PROVIDER_GUIDES.find((g) => g.name === selectedProvider) ?? PROVIDER_GUIDES[0];

  const providerOptions = PROVIDER_GUIDES.map((g) => ({
    value: g.name,
    label: g.displayName,
  }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Provider Setup Guides</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Step-by-step instructions for configuring each TTS provider
        </p>
      </div>

      {/* Provider selector */}
      <Card>
        <div className="max-w-xs">
          <Select
            label="Select Provider"
            value={selectedProvider}
            onChange={(e) => { logger.info("provider_selected", { provider: e.target.value }); setSelectedProvider(e.target.value); }}
            options={providerOptions}
          />
        </div>
      </Card>

      {/* Provider header */}
      <Card>
        <div className="flex items-start gap-4">
          <ProviderLogo name={guide.name} size={40} />
          <div className="flex-1">
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold">{guide.displayName}</h2>
              <Badge
                status={
                  guide.type === "cloud" ? "cloud" : guide.type === "local-cpu" ? "ready" : "training"
                }
              />
            </div>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{guide.description}</p>
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

      {/* Setup steps */}
      <Card>
        <h3 className="mb-4 text-lg font-semibold">Setup Steps</h3>
        <div className="space-y-4">
          {guide.steps.map((step, i) => (
            <div key={i} className="flex gap-4">
              <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-100 text-sm font-bold text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                {i + 1}
              </div>
              <div className="flex-1">
                <h4 className="font-medium">{step.title}</h4>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{step.description}</p>
                {step.code && (
                  <pre className="mt-2 rounded bg-gray-50 p-3 text-xs dark:bg-gray-900 overflow-x-auto whitespace-pre-wrap">
                    {step.code}
                  </pre>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Environment variables */}
      <Card>
        <h3 className="mb-4 text-lg font-semibold">Environment Variables</h3>
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
                    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">{v.name}</code>
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
      </Card>

      {/* Checklist */}
      <Card>
        <h3 className="mb-4 text-lg font-semibold">Configuration Checklist</h3>
        <div className="space-y-2">
          {guide.checklist.map((item, i) => (
            <div key={i} className="flex items-center gap-3 text-sm">
              <Circle className="h-4 w-4 shrink-0 text-[var(--color-text-secondary)]" />
              <span>{item}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Tips */}
      <Card>
        <h3 className="mb-4 text-lg font-semibold">Tips & Best Practices</h3>
        <ul className="space-y-2">
          {guide.tips.map((tip, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-[var(--color-text-secondary)]">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
              <span>{tip}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
