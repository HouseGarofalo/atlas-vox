import { useState, useMemo } from "react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import {
  Search,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  BookOpen,
  Rocket,
  Footprints,
  Terminal,
  Wrench,
  Code2,
  Info,
  Copy,
  Check,
} from "lucide-react";
import {
  Layers,
  Settings,
  Plug,
  ShieldCheck,
  Server,
} from "lucide-react";
import { createLogger } from "../utils/logger";
import {
  ProviderGuidesTab,
  ArchitectureTab,
  ConfigurationTab,
  MCPIntegrationTab,
  SelfHealingTab as SelfHealingDocsTab,
  DeploymentTab,
} from "./DocsPage";

const logger = createLogger("HelpPage");

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FaqItem {
  question: string;
  answer: string;
  category: string;
}

interface GettingStartedStep {
  step: number;
  title: string;
  description: string;
  command?: string;
  note?: string;
}

interface GuideSection {
  title: string;
  content: string;
}

interface Walkthrough {
  title: string;
  description: string;
  steps: string[];
}

interface CliCommand {
  name: string;
  syntax: string;
  description: string;
  options: { flag: string; description: string }[];
  example: string;
}

interface ApiExample {
  title: string;
  method: "GET" | "POST" | "PUT" | "DELETE" | "PATCH";
  endpoint: string;
  body?: string;
  response: string;
}

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const TABS = [
  { key: "getting-started", label: "Getting Started", icon: Rocket, group: "guide" },
  { key: "user-guide", label: "User Guide", icon: BookOpen, group: "guide" },
  { key: "walkthroughs", label: "Walkthroughs", icon: Footprints, group: "guide" },
  { key: "cli", label: "CLI", icon: Terminal, group: "reference" },
  { key: "api", label: "API", icon: Code2, group: "reference" },
  { key: "providers", label: "Providers", icon: Settings, group: "reference" },
  { key: "architecture", label: "Architecture", icon: Layers, group: "technical" },
  { key: "configuration", label: "Configuration", icon: Settings, group: "technical" },
  { key: "mcp", label: "MCP", icon: Plug, group: "technical" },
  { key: "self-healing", label: "Self-Healing", icon: ShieldCheck, group: "technical" },
  { key: "deployment", label: "Deployment", icon: Server, group: "technical" },
  { key: "troubleshooting", label: "Troubleshooting", icon: Wrench, group: "support" },
  { key: "about", label: "About", icon: Info, group: "support" },
] as const;

const GROUPS = [
  { key: "guide", label: "Guide" },
  { key: "reference", label: "Reference" },
  { key: "technical", label: "Technical" },
  { key: "support", label: "Support" },
] as const;

type TabKey = (typeof TABS)[number]["key"];

const FAQ_CATEGORIES = [
  "All",
  "Installation",
  "Providers",
  "Audio",
  "Training",
  "Synthesis",
  "Database",
  "Self-Healing",
  "Performance",
] as const;

/* ---------- Getting Started ---------- */

const GETTING_STARTED_STEPS: GettingStartedStep[] = [
  {
    step: 1,
    title: "Install Prerequisites",
    description:
      "Ensure you have the required tools installed on your system before proceeding.",
    command: "python --version   # 3.11+\nnode --version      # 20+\nredis-server --version",
    note: "Docker is recommended as an alternative -- it bundles everything automatically.",
  },
  {
    step: 2,
    title: "Clone and Configure",
    description:
      "Clone the repository and copy the example environment file. Adjust settings as needed.",
    command: "git clone https://github.com/HouseGarofalo/atlas-vox.git\ncd atlas-vox\ncp .env.example .env",
    note: "Default settings work out of the box for local development.",
  },
  {
    step: 3,
    title: "Start with Docker (Recommended)",
    description:
      "Docker Compose starts the backend, frontend, Redis, and a Celery worker in one command.",
    command: "make docker-up",
    note: "For GPU support: make docker-gpu-up (requires NVIDIA Container Toolkit).",
  },
  {
    step: 4,
    title: "Or Start Locally",
    description:
      "If you prefer a local development setup without Docker, start each service individually.",
    command:
      "# Terminal 1 -- Backend\ncd backend && uvicorn app.main:app --reload --port 8100\n\n# Terminal 2 -- Frontend\ncd frontend && npm install && npm run dev\n\n# Terminal 3 -- Celery worker\ncd backend && celery -A app.tasks.celery_app worker --loglevel=info",
    note: "Redis must be running on localhost:6379 (database 1).",
  },
  {
    step: 5,
    title: "Verify Installation",
    description:
      "Open the Web UI and check the Dashboard. Healthy providers show a green badge. CPU-only providers (Kokoro, Piper) are green immediately.",
    command: "http://localhost:3000   # dev frontend\nhttp://localhost:3100   # Docker frontend\nhttp://localhost:8100/docs   # Swagger API docs",
    note: "Cloud providers (ElevenLabs, Azure) need API keys configured before they go green.",
  },
  {
    step: 6,
    title: "Synthesize Your First Voice",
    description:
      "Go to the Synthesis Lab, select the default Kokoro provider, type a sentence, and click Synthesize. You should hear audio playback within seconds.",
    note: "Browse the Voice Library for 400+ built-in voices across all providers.",
  },
];

/* ---------- User Guide ---------- */

const GUIDE_SECTIONS: GuideSection[] = [
  {
    title: "Dashboard",
    content:
      "The Dashboard is your operational overview. It shows four stats cards (total profiles, active training jobs, recent syntheses, active providers), a provider health grid with live status badges, a list of active training jobs with progress bars, and a scrollable recent synthesis history. The health grid auto-refreshes and links to each provider's detail page.",
  },
  {
    title: "Voice Profiles",
    content:
      "Voice Profiles are identities bound to a specific provider. Each profile has a lifecycle: pending (created, no training), training (job in progress), ready (usable for synthesis), error (training failed), and archived (soft-deleted). You can create profiles manually or from a Voice Library entry. Profiles store metadata like language, description, and the provider-specific voice ID. The Training tab on each profile shows version history.",
  },
  {
    title: "Voice Library",
    content:
      "The Voice Library aggregates all available voices across all healthy providers (400+ voices). Filter by provider, language, or gender. Preview a voice with one click. Click 'Use Voice' to jump to the Synthesis Lab pre-configured, or 'Create Profile' to create a persistent profile from that voice.",
  },
  {
    title: "Training Studio",
    content:
      "The Training Studio manages the full voice-cloning pipeline: upload audio samples (WAV, MP3, FLAC, OGG, M4A) or record directly in the browser, run preprocessing (noise reduction, normalization, silence trimming), configure training parameters (epochs, learning rate, batch size), then launch training. Progress updates arrive via WebSocket in real-time with epoch-level granularity. Completed models appear as new versions on the parent profile.",
  },
  {
    title: "Synthesis Lab",
    content:
      "The primary synthesis interface. Enter plain text or switch to the Monaco-based SSML editor (Azure only). Select a profile and adjust speed (0.5-2.0x), pitch (-20 to +20), and volume (0.0-2.0). Choose an output format (WAV, MP3, OGG). Use persona presets for quick parameter tuning. Results play inline with a wavesurfer.js waveform and can be downloaded.",
  },
  {
    title: "Comparison",
    content:
      "Select 2-5 voice profiles, enter the same text, and generate synthesis results side-by-side. Each result shows the waveform, latency, and audio format. Useful for A/B testing providers, evaluating training quality, or selecting the best voice for a project.",
  },
  {
    title: "Providers",
    content:
      "Lists all 9 TTS providers with capabilities, health status, and configuration. Expand a provider to see its settings form (API keys for cloud, GPU toggle for local), run a health check, or trigger a test synthesis. Provider cards show supported features: streaming, SSML, voice cloning, multi-language, and emotion control.",
  },
  {
    title: "API Keys",
    content:
      "Create scoped API keys for programmatic access. Available scopes: read (list/get resources), write (create/update/delete), synthesize (run synthesis), train (start training), admin (full access). Keys use the format avx_* and are hashed with Argon2id on the server. When AUTH_DISABLED=true (default for local dev), API keys are not enforced.",
  },
  {
    title: "Settings",
    content:
      "Toggle between light and dark themes, set your default TTS provider and audio output format. Preferences are persisted in browser localStorage and apply immediately.",
  },
  {
    title: "Design System",
    content:
      "Customize the look and feel of Atlas Vox in real time with 15 design tokens: accent hue, accent saturation, font family (system, Inter, monospace, serif), font size, density, sidebar width, content max width, border radius, card style (bordered, raised, flat, glassmorphism), and animation toggles. Choose from 8 theme presets (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif) or create your own combination. All changes persist across sessions.",
  },
  {
    title: "Self-Healing System",
    content:
      "The self-healing subsystem continuously monitors provider health and system resources. It uses configurable detection rules (consecutive failures, latency thresholds, error rate windows) to identify problems, then runs automated remediation actions (restart provider, clear cache, switch to fallback). The incident log shows all detected issues and their resolution. An MCP bridge exposes self-healing status to external agents.",
  },
  {
    title: "Docs Page",
    content:
      "An in-app documentation browser with provider-specific guides (setup, capabilities, pricing), architecture diagrams, and configuration reference. Content is rendered from markdown and stays in sync with the repository docs/ folder.",
  },
  {
    title: "Help Center",
    content:
      "This page. Seven tabs covering getting started, feature guides, step-by-step walkthroughs, CLI reference, troubleshooting FAQ, API reference, and project information.",
  },
  {
    title: "Admin (Legacy)",
    content:
      "The legacy admin page provides a raw view of system state: database stats, Redis connection, Celery workers, and task queue depth. It is superseded by the Dashboard and Self-Healing pages but remains available for debugging.",
  },
  {
    title: "Persona Presets Reference",
    content:
      "Six built-in persona presets for the Synthesis Lab: Friendly (speed 1.0, pitch +2, volume 1.0), Professional (0.95, 0, 1.0), Energetic (1.15, +5, 1.1), Calm (0.85, -3, 0.9), Authoritative (0.9, -5, 1.15), and Soothing (0.8, -2, 0.85). Presets apply immediately when selected and can be fine-tuned with the sliders.",
  },
];

/* ---------- Walkthroughs ---------- */

const WALKTHROUGHS: Walkthrough[] = [
  {
    title: "First Synthesis",
    description: "Generate your first TTS audio in under a minute.",
    steps: [
      "Open the Synthesis Lab from the sidebar.",
      "Select the default Kokoro provider profile (pre-configured).",
      "Type or paste text into the input area (up to 5000 characters).",
      "Click 'Synthesize' and wait for the waveform to appear.",
      "Click the play button to listen, or click the download icon to save the WAV file.",
    ],
  },
  {
    title: "Voice Cloning with Coqui XTTS",
    description: "Clone a voice from a short audio sample.",
    steps: [
      "Navigate to Providers and ensure Coqui XTTS shows a green health badge. Enable GPU mode for best quality.",
      "Go to Voice Profiles and click 'New Profile'. Select Coqui XTTS as the provider.",
      "On the profile page, open the Samples tab and upload 1-3 audio clips (6+ seconds each, clean speech, minimal background noise).",
      "Click 'Preprocess' to normalize audio levels and trim silence.",
      "Click 'Start Training' and monitor the progress bar. Training takes 5-15 minutes on GPU.",
      "Once status changes to 'ready', go to the Synthesis Lab and select your new profile to synthesize with your cloned voice.",
    ],
  },
  {
    title: "Comparing Voices",
    description: "A/B test multiple voices with the same text.",
    steps: [
      "Open the Comparison page from the sidebar.",
      "Select 2-5 voice profiles from the multi-select dropdown.",
      "Enter the text you want to compare (the same text is synthesized by each profile).",
      "Click 'Compare' and review the side-by-side results. Each card shows the waveform, latency, and a play button.",
    ],
  },
  {
    title: "Azure Speech Setup",
    description: "Configure the Azure AI Speech cloud provider.",
    steps: [
      "In the Azure Portal, create a 'Speech' resource (Cognitive Services). Choose a supported region (e.g., eastus).",
      "After deployment, go to Keys and Endpoint. Copy Key 1 and the Region name.",
      "In Atlas Vox, go to Providers > Azure Speech > Settings.",
      "Paste the API key into the 'API Key' field and enter the region (e.g., eastus) in the 'Region' field. Click Save.",
      "Click 'Health Check' -- it should turn green. Azure Speech supports SSML, neural voices, and multiple languages.",
    ],
  },
  {
    title: "ElevenLabs Setup",
    description: "Configure the ElevenLabs cloud provider.",
    steps: [
      "Sign up at elevenlabs.io and navigate to your Profile Settings page.",
      "Copy your API key from the API Keys section.",
      "In Atlas Vox, go to Providers > ElevenLabs > Settings. Paste your API key and click Save.",
      "Run a Health Check to verify. ElevenLabs offers a free tier with limited characters per month.",
    ],
  },
  {
    title: "OpenAI-Compatible API Usage",
    description: "Use Atlas Vox as a drop-in replacement for the OpenAI TTS API.",
    steps: [
      "Atlas Vox exposes an OpenAI-compatible endpoint at /v1/audio/speech.",
      "Use any OpenAI TTS client library by pointing it to your Atlas Vox server:\n\ncurl http://localhost:8100/v1/audio/speech \\\n  -H \"Content-Type: application/json\" \\\n  -d '{\"model\": \"kokoro\", \"input\": \"Hello from Atlas Vox!\", \"voice\": \"af_heart\"}' \\\n  --output speech.wav",
      "The 'model' field maps to a provider name, and 'voice' maps to a voice ID from that provider. Supported response_format values: wav, mp3, opus, flac.",
    ],
  },
  {
    title: "Design Customization",
    description: "Personalize the Atlas Vox interface with the Design System.",
    steps: [
      "Open the Design System page from the sidebar (palette icon).",
      "Start with a preset: click one of the 8 theme cards (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif).",
      "Fine-tune individual tokens using the sliders and dropdowns: accent color hue/saturation, font family, density, card style, border radius, and more.",
      "All changes apply instantly and persist across browser sessions. Click 'Reset to Defaults' to return to the Blue preset.",
    ],
  },
];

/* ---------- CLI Commands ---------- */

const CLI_COMMANDS: CliCommand[] = [
  {
    name: "synthesize",
    syntax: "atlas-vox synthesize TEXT",
    description: "Synthesize text to speech and save the output audio file.",
    options: [
      { flag: "--provider, -p", description: "Provider name (default: kokoro)" },
      { flag: "--voice, -v", description: "Voice ID" },
      { flag: "--output, -o", description: "Output file path (default: output.wav)" },
      { flag: "--format, -f", description: "Audio format: wav, mp3, ogg" },
      { flag: "--speed", description: "Speed multiplier (0.5-2.0)" },
      { flag: "--pitch", description: "Pitch adjustment (-20 to +20)" },
    ],
    example: 'atlas-vox synthesize "Hello world" -p kokoro -v af_heart -o hello.wav',
  },
  {
    name: "providers",
    syntax: "atlas-vox providers [SUBCOMMAND]",
    description: "List, inspect, and health-check TTS providers.",
    options: [
      { flag: "list", description: "Show all providers with status" },
      { flag: "health [NAME]", description: "Run health check on a provider" },
      { flag: "config NAME", description: "Show provider configuration" },
    ],
    example: "atlas-vox providers list\natlas-vox providers health kokoro",
  },
  {
    name: "profiles",
    syntax: "atlas-vox profiles [SUBCOMMAND]",
    description: "Manage voice profiles.",
    options: [
      { flag: "list", description: "List all profiles" },
      { flag: "create NAME --provider PROV", description: "Create a new profile" },
      { flag: "show ID", description: "Show profile details" },
      { flag: "delete ID", description: "Delete a profile" },
    ],
    example: "atlas-vox profiles list\natlas-vox profiles create myvoice --provider kokoro",
  },
  {
    name: "train",
    syntax: "atlas-vox train PROFILE_ID",
    description: "Start a training job for a voice profile.",
    options: [
      { flag: "--epochs, -e", description: "Number of training epochs (default: 100)" },
      { flag: "--learning-rate, -lr", description: "Learning rate (default: 0.0001)" },
      { flag: "--batch-size, -b", description: "Batch size (default: 4)" },
      { flag: "--wait, -w", description: "Wait for training to complete" },
    ],
    example: "atlas-vox train abc-123 --epochs 200 --wait",
  },
  {
    name: "compare",
    syntax: "atlas-vox compare TEXT --profiles ID1 ID2 [ID3...]",
    description: "Synthesize the same text with multiple profiles for comparison.",
    options: [
      { flag: "--profiles", description: "Comma-separated profile IDs (2-5)" },
      { flag: "--output-dir, -o", description: "Directory to save audio files" },
    ],
    example: 'atlas-vox compare "Test phrase" --profiles id1,id2,id3 -o ./comparison/',
  },
  {
    name: "presets",
    syntax: "atlas-vox presets [SUBCOMMAND]",
    description: "Manage synthesis presets (persona parameter sets).",
    options: [
      { flag: "list", description: "Show all presets" },
      { flag: "show NAME", description: "Show preset details" },
    ],
    example: "atlas-vox presets list",
  },
  {
    name: "init",
    syntax: "atlas-vox init",
    description: "Initialize the Atlas Vox database and default configuration.",
    options: [
      { flag: "--force", description: "Re-initialize even if database exists" },
    ],
    example: "atlas-vox init --force",
  },
  {
    name: "serve",
    syntax: "atlas-vox serve",
    description: "Start the Atlas Vox API server (alternative to uvicorn).",
    options: [
      { flag: "--host", description: "Bind address (default: 0.0.0.0)" },
      { flag: "--port", description: "Port number (default: 8100)" },
      { flag: "--reload", description: "Enable auto-reload for development" },
      { flag: "--workers", description: "Number of worker processes" },
    ],
    example: "atlas-vox serve --port 8100 --reload",
  },
];

/* ---------- FAQ / Troubleshooting ---------- */

const FAQ_ITEMS: FaqItem[] = [
  // Installation (4)
  { category: "Installation", question: "How do I start Atlas Vox with Docker?", answer: 'Run "make docker-up" from the project root. This starts the backend, frontend, Redis, and a Celery worker. The Web UI is at http://localhost:3100.' },
  { category: "Installation", question: "Docker build fails during pip install", answer: 'Rebuild with no cache: "docker compose -f docker/docker-compose.yml build --no-cache backend". Usually caused by network issues or PyPI rate limiting.' },
  { category: "Installation", question: "Port 3100 or 8100 is already in use", answer: "Edit docker/.env and change BACKEND_PORT / FRONTEND_PORT. Then restart with make docker-up." },
  { category: "Installation", question: "Redis connection fails on startup", answer: "Atlas Vox uses Redis database 1 (redis://localhost:6379/1) to avoid collision with other services on database 0. Ensure Redis is running: 'redis-server' or check Docker." },
  // Providers (5)
  { category: "Providers", question: "A provider shows as 'unhealthy' on the dashboard", answer: "Go to Providers, expand the provider, and click Health Check to see the specific error. Common causes: missing API key (cloud), missing model files (local), or GPU not available." },
  { category: "Providers", question: "How do I configure ElevenLabs?", answer: "Get your API key from elevenlabs.io/settings. Go to Providers > ElevenLabs > Settings, enter the API key, click Save, then run a Health Check." },
  { category: "Providers", question: "How do I configure Azure Speech?", answer: "Create a Speech resource in the Azure Portal. Copy Key 1 and Region from Keys and Endpoint. Enter them in Providers > Azure Speech > Settings." },
  { category: "Providers", question: "How do I enable GPU mode for local providers?", answer: 'Run "make docker-gpu-up" instead of "make docker-up". This starts a GPU worker with CUDA 12.1 and auto-enables GPU mode for Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2.' },
  { category: "Providers", question: "Can I use multiple cloud providers at the same time?", answer: "Yes. Each provider is independent. Configure API keys for both ElevenLabs and Azure Speech, and you can use either from the Synthesis Lab or Comparison page." },
  // Audio (3)
  { category: "Audio", question: "Synthesis succeeds but no audio plays", answer: "Check the audio URL in the response. Try accessing it directly: http://localhost:8100/api/v1/audio/<filename>. Verify browser console for errors. Try WAV format instead of MP3/OGG." },
  { category: "Audio", question: "Audio upload is rejected as unsupported format", answer: "Atlas Vox supports WAV, MP3, FLAC, OGG, and M4A. Convert your file with: ffmpeg -i input.webm output.wav" },
  { category: "Audio", question: "Audio sounds distorted or clipped", answer: "Check the volume slider (should be between 0.8 and 1.2 for most cases). If using a cloned voice, ensure training samples were clean without clipping. Re-preprocess with noise reduction enabled." },
  // Training (3)
  { category: "Training", question: "Training job stuck at 'queued'", answer: "The Celery worker is not running or not connected to Redis. In Docker: docker compose -f docker/docker-compose.yml logs worker. For local dev, start Celery manually." },
  { category: "Training", question: "Training fails immediately", answer: "Ensure you have uploaded and preprocessed audio samples before starting training. Check the training job error message for the specific cause (common: insufficient samples or corrupted audio)." },
  { category: "Training", question: "How many audio samples do I need for voice cloning?", answer: "Minimum: 1 sample of 6+ seconds (Coqui XTTS). For best quality: 10-30 minutes of clean speech split into 5-15 second segments. More data generally produces better results up to about 1 hour." },
  // Synthesis (3)
  { category: "Synthesis", question: "Synthesis returns an empty audio file", answer: "The provider may have returned an error silently. Check backend logs: docker compose logs backend | tail -50. Common cause: text too short (some providers need at least a few words) or invalid voice ID." },
  { category: "Synthesis", question: "SSML is not being interpreted", answer: "SSML is only supported by Azure Speech. Switch to the Azure Speech provider and ensure you are in SSML mode (click 'Switch to SSML' in the Synthesis Lab). Validate your SSML markup." },
  { category: "Synthesis", question: "Streaming synthesis is choppy", answer: "Streaming quality depends on network and provider. Use a wired connection for cloud providers. For local providers, ensure the GPU is not overloaded. Reduce text length for smoother streaming." },
  // Database (2)
  { category: "Database", question: "Getting 'no such table' errors", answer: 'Run "make migrate" to apply database migrations. For a fresh start, delete atlas_vox.db and restart -- tables are created automatically.' },
  { category: "Database", question: "Can I switch from SQLite to PostgreSQL?", answer: "Yes. Set DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname in your .env file. Run make migrate to create tables. PostgreSQL is recommended for production deployments." },
  // Self-Healing (2)
  { category: "Self-Healing", question: "What triggers self-healing remediation?", answer: "Configurable rules: consecutive health check failures (default: 3), average latency exceeding threshold (default: 5000ms), error rate above threshold in a time window (default: 50% in 5 minutes). Each rule can be customized per provider." },
  { category: "Self-Healing", question: "A provider keeps restarting due to self-healing", answer: "Check the incident log for the root cause. Common: GPU out of memory (reduce batch size or switch to CPU), missing model files (re-download), or rate limiting (increase cooldown). Disable auto-remediation for that provider temporarily via the Self-Healing settings." },
  // Performance (3)
  { category: "Performance", question: "Synthesis is very slow (10+ seconds)", answer: "GPU-oriented models (Coqui XTTS, StyleTTS2, Dia) on CPU are slow. Switch to GPU mode, or use Kokoro/Piper for fast CPU synthesis (typically <1 second)." },
  { category: "Performance", question: "GPU memory errors (CUDA out of memory)", answer: "VRAM requirements: Dia2 needs 8 GB+, Dia needs 6 GB+, Coqui XTTS needs 4 GB+, StyleTTS2 needs 3 GB+, CosyVoice needs 4 GB+. Close other GPU applications, use shorter text, or switch to CPU mode." },
  { category: "Performance", question: "Getting '429 Too Many Requests' errors", answer: "Rate limits: synthesis 10/min, training 5/min, comparison 5/min, OpenAI-compatible 20/min. Wait a minute and try again, or reduce request frequency." },
];

/* ---------- API Reference ---------- */

const API_EXAMPLES: ApiExample[] = [
  { title: "Health Check", method: "GET", endpoint: "/api/v1/health", response: '{\n  "status": "healthy",\n  "checks": { "database": "ok", "redis": "ok", "storage": "ok" },\n  "version": "0.1.0"\n}' },
  { title: "List Profiles", method: "GET", endpoint: "/api/v1/profiles", response: '{\n  "profiles": [{ "id": "abc-123", "name": "My Voice", "status": "ready", ... }],\n  "count": 5\n}' },
  { title: "Create Profile", method: "POST", endpoint: "/api/v1/profiles", body: '{\n  "name": "My Voice",\n  "provider_name": "kokoro",\n  "language": "en"\n}', response: '{\n  "id": "abc-123",\n  "name": "My Voice",\n  "status": "pending",\n  "provider_name": "kokoro"\n}' },
  { title: "Get Profile", method: "GET", endpoint: "/api/v1/profiles/{id}", response: '{\n  "id": "abc-123",\n  "name": "My Voice",\n  "status": "ready",\n  "provider_name": "kokoro",\n  "voice_id": "af_heart",\n  "language": "en",\n  "created_at": "2025-01-15T10:30:00Z"\n}' },
  { title: "Synthesize", method: "POST", endpoint: "/api/v1/synthesize", body: '{\n  "text": "Hello world!",\n  "profile_id": "abc-123",\n  "output_format": "wav"\n}', response: '{\n  "audio_url": "/api/v1/audio/out_abc123.wav",\n  "latency_ms": 89,\n  "format": "wav"\n}' },
  { title: "Stream Synthesis", method: "POST", endpoint: "/api/v1/synthesize/stream", body: '{\n  "text": "Streaming audio output...",\n  "profile_id": "abc-123"\n}', response: '-- Binary audio stream (chunked transfer encoding)\n-- Content-Type: audio/wav' },
  { title: "Batch Synthesis", method: "POST", endpoint: "/api/v1/synthesize/batch", body: '{\n  "items": [\n    { "text": "First sentence.", "profile_id": "abc-123" },\n    { "text": "Second sentence.", "profile_id": "abc-123" }\n  ]\n}', response: '{\n  "results": [\n    { "audio_url": "/api/v1/audio/batch_1.wav", "latency_ms": 85 },\n    { "audio_url": "/api/v1/audio/batch_2.wav", "latency_ms": 91 }\n  ]\n}' },
  { title: "Compare Voices", method: "POST", endpoint: "/api/v1/compare", body: '{\n  "text": "Test phrase",\n  "profile_ids": ["id1", "id2", "id3"]\n}', response: '{\n  "text": "Test phrase",\n  "results": [\n    { "profile_id": "id1", "audio_url": "...", "latency_ms": 80 },\n    { "profile_id": "id2", "audio_url": "...", "latency_ms": 120 }\n  ]\n}' },
  { title: "List Providers", method: "GET", endpoint: "/api/v1/providers", response: '{\n  "providers": [\n    { "name": "kokoro", "status": "healthy", "capabilities": { ... } }\n  ],\n  "count": 9\n}' },
  { title: "List Voices", method: "GET", endpoint: "/api/v1/voices?provider=kokoro", response: '{\n  "voices": [{ "id": "af_heart", "name": "Heart", "language": "en", ... }],\n  "count": 54\n}' },
  { title: "List Presets", method: "GET", endpoint: "/api/v1/presets", response: '{\n  "presets": [\n    { "name": "Friendly", "speed": 1.0, "pitch": 2, "volume": 1.0 },\n    { "name": "Professional", "speed": 0.95, "pitch": 0, "volume": 1.0 }\n  ]\n}' },
  { title: "Create API Key", method: "POST", endpoint: "/api/v1/api-keys", body: '{\n  "name": "CI Pipeline",\n  "scopes": ["read", "synthesize"]\n}', response: '{\n  "id": "key-456",\n  "name": "CI Pipeline",\n  "key": "avx_abc123...",\n  "scopes": ["read", "synthesize"],\n  "created_at": "2025-01-15T10:30:00Z"\n}' },
];

/* ---------- About data ---------- */

const ABOUT_INFO = [
  { label: "Version", value: "0.1.0" },
  { label: "TTS Providers", value: "9" },
  { label: "Interfaces", value: "Web UI, REST API, CLI, MCP Server" },
  { label: "Backend", value: "Python 3.11 + FastAPI + SQLAlchemy + Celery" },
  { label: "Frontend", value: "React 18 + TypeScript + Vite + Tailwind CSS" },
  { label: "Database", value: "SQLite (dev) / PostgreSQL (prod)" },
  { label: "Task Queue", value: "Celery + Redis" },
  { label: "License", value: "MIT" },
];

const PROVIDER_TABLE = [
  { name: "Kokoro", type: "Local CPU", model: "82M params", voices: "54", languages: "en, ja, zh, ko, fr, de, it, pt, es, hi", streaming: "No", cloning: "No", pricing: "Open Source" },
  { name: "Piper", type: "Local CPU", model: "ONNX VITS", voices: "200+", languages: "30+", streaming: "No", cloning: "No", pricing: "Open Source" },
  { name: "ElevenLabs", type: "Cloud", model: "Proprietary", voices: "100+", languages: "29", streaming: "Yes", cloning: "Yes", pricing: "Freemium" },
  { name: "Azure Speech", type: "Cloud", model: "Neural TTS", voices: "400+", languages: "140+", streaming: "Yes", cloning: "No", pricing: "Paid" },
  { name: "Coqui XTTS v2", type: "Local GPU", model: "~1.5B params", voices: "Custom", languages: "17", streaming: "Yes", cloning: "Yes", pricing: "Open Source" },
  { name: "StyleTTS2", type: "Local GPU", model: "~200M params", voices: "Custom", languages: "en", streaming: "No", cloning: "Yes", pricing: "Open Source" },
  { name: "CosyVoice", type: "Local GPU", model: "300M params", voices: "Custom", languages: "en, zh, ja, ko", streaming: "Yes", cloning: "Yes", pricing: "Open Source" },
  { name: "Dia", type: "Local GPU", model: "1.6B params", voices: "2", languages: "en", streaming: "No", cloning: "No", pricing: "Open Source" },
  { name: "Dia2", type: "Local GPU", model: "2B params", voices: "2", languages: "en", streaming: "Yes", cloning: "No", pricing: "Open Source" },
];

const DOC_LINKS = [
  { label: "Swagger API Docs", href: "/docs" },
  { label: "ReDoc API Reference", href: "/redoc" },
  { label: "GitHub Repository", href: "https://github.com/HouseGarofalo/atlas-vox" },
  { label: "Product Requirements Document", href: "/docs/prp/PRD.md" },
];

const PERSONA_PRESETS = [
  { name: "Friendly", speed: "1.0x", pitch: "+2", volume: "1.0", character: "Warm and approachable" },
  { name: "Professional", speed: "0.95x", pitch: "0", volume: "1.0", character: "Clear and authoritative" },
  { name: "Energetic", speed: "1.15x", pitch: "+5", volume: "1.1", character: "Upbeat and enthusiastic" },
  { name: "Calm", speed: "0.85x", pitch: "-3", volume: "0.9", character: "Soothing and relaxed" },
  { name: "Authoritative", speed: "0.9x", pitch: "-5", volume: "1.15", character: "Commanding and confident" },
  { name: "Soothing", speed: "0.8x", pitch: "-2", volume: "0.85", character: "Gentle and comforting" },
];

const RATE_LIMITS = [
  { endpoint: "POST /api/v1/synthesize", limit: "10 req/min" },
  { endpoint: "POST /api/v1/synthesize/stream", limit: "10 req/min" },
  { endpoint: "POST /api/v1/synthesize/batch", limit: "5 req/min" },
  { endpoint: "POST /api/v1/compare", limit: "5 req/min" },
  { endpoint: "POST /api/v1/training", limit: "5 req/min" },
  { endpoint: "POST /v1/audio/speech (OpenAI)", limit: "20 req/min" },
  { endpoint: "GET /api/v1/* (reads)", limit: "60 req/min" },
  { endpoint: "POST /api/v1/* (writes)", limit: "30 req/min" },
];

/* ------------------------------------------------------------------ */
/*  Reusable sub-components                                            */
/* ------------------------------------------------------------------ */

function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="group relative mt-2 rounded-lg bg-gray-50 dark:bg-gray-900 border border-[var(--color-border)]">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--color-border)]">
        <span className="text-[10px] uppercase tracking-wider text-[var(--color-text-tertiary)]">{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] text-[var(--color-text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
          aria-label="Copy code"
        >
          {copied ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-xs leading-relaxed">{code}</pre>
    </div>
  );
}

function FaqCard({ item, open, onToggle }: { item: FaqItem; open: boolean; onToggle: () => void }) {
  const badgeStatus: Record<string, string> = {
    Installation: "pending",
    Providers: "cloud",
    Audio: "ready",
    Training: "training",
    Synthesis: "local",
    Database: "archived",
    "Self-Healing": "gpu",
    Performance: "unhealthy",
  };

  return (
    <div className="rounded-lg border border-[var(--color-border)] transition-colors hover:border-primary-300 dark:hover:border-primary-700">
      <button onClick={onToggle} className="flex w-full items-center justify-between p-4 text-left">
        <div className="flex items-center gap-3 min-w-0">
          <Badge status={badgeStatus[item.category] || "pending"} className="shrink-0 text-[10px]" />
          <span className="font-medium truncate">{item.question}</span>
        </div>
        {open ? <ChevronDown className="h-4 w-4 shrink-0 ml-2" /> : <ChevronRight className="h-4 w-4 shrink-0 ml-2" />}
      </button>
      {open && (
        <div className="border-t border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-text-secondary)]">
          {item.answer}
        </div>
      )}
    </div>
  );
}

function DataTable({ headers, rows }: { headers: string[]; rows: (string | React.ReactNode)[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
            {headers.map((h) => (
              <th key={h} className="pb-2 pr-4 font-medium whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[var(--color-border)] last:border-0">
              {row.map((cell, j) => (
                <td key={j} className={`py-2 pr-4 ${j === 0 ? "font-medium" : ""}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    POST: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    PUT: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    PATCH: "bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300",
    DELETE: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${colors[method] || colors.GET}`}>
      {method}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Tab renderers                                                      */
/* ------------------------------------------------------------------ */

function GettingStartedTab() {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Welcome to Atlas Vox</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Atlas Vox is a self-hosted voice training and customization platform with 9 TTS providers,
          4 interfaces (Web UI, REST API, CLI, MCP Server), and a complete voice-cloning pipeline.
          Follow these steps to get up and running.
        </p>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
          {[
            { label: "Python 3.11+", badge: "required" },
            { label: "Node.js 20+", badge: "required" },
            { label: "Redis 7+", badge: "required" },
          ].map((p) => (
            <div key={p.label} className="flex items-center justify-between rounded-lg border border-[var(--color-border)] px-3 py-2">
              <span className="text-sm font-medium">{p.label}</span>
              <Badge status="training" className="text-[10px]" />
            </div>
          ))}
        </div>
      </Card>

      <div className="space-y-3">
        {GETTING_STARTED_STEPS.map((step) => (
          <Card key={step.step}>
            <div className="flex items-start gap-4">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white">
                {step.step}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-semibold">{step.title}</h3>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{step.description}</p>
                {step.command && <CodeBlock code={step.command} />}
                {step.note && (
                  <p className="mt-2 text-xs text-[var(--color-text-secondary)] italic">{step.note}</p>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function UserGuideTab() {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Feature Guide</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Overview of every section in the Atlas Vox interface. Click any panel to expand or collapse.
        </p>
      </Card>

      {GUIDE_SECTIONS.map((section) => (
        <CollapsiblePanel key={section.title} title={section.title} defaultOpen={false}>
          <p className="text-sm text-[var(--color-text-secondary)]">{section.content}</p>
        </CollapsiblePanel>
      ))}

      <Card>
        <h3 className="mb-3 font-semibold">Persona Presets</h3>
        <DataTable
          headers={["Preset", "Speed", "Pitch", "Volume", "Character"]}
          rows={PERSONA_PRESETS.map((p) => [
            p.name,
            p.speed,
            p.pitch,
            p.volume,
            <span key={p.name} className="text-[var(--color-text-secondary)]">{p.character}</span>,
          ])}
        />
      </Card>

      <Card>
        <h3 className="mb-3 font-semibold">Voice Profile Lifecycle</h3>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          {["pending", "training", "ready", "error", "archived"].map((s, i) => (
            <span key={s} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-[var(--color-text-tertiary)]">&rarr;</span>}
              <Badge status={s} />
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs text-[var(--color-text-secondary)]">
          Profiles start as pending, transition to training when a job is submitted, become ready on success,
          or error on failure. Archived profiles are soft-deleted and can be restored.
        </p>
      </Card>
    </div>
  );
}

function WalkthroughsTab() {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">Step-by-Step Walkthroughs</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          {WALKTHROUGHS.length} tutorials covering common workflows from first synthesis to advanced configuration.
        </p>
      </Card>

      {WALKTHROUGHS.map((wt, wtIdx) => (
        <CollapsiblePanel
          key={wt.title}
          title={`${wtIdx + 1}. ${wt.title}`}
          defaultOpen={wtIdx === 0}
          badge={<span className="text-xs text-[var(--color-text-secondary)]">{wt.steps.length} steps</span>}
        >
          <p className="mb-3 text-sm text-[var(--color-text-secondary)]">{wt.description}</p>
          <ol className="space-y-3">
            {wt.steps.map((step, stepIdx) => (
              <li key={stepIdx} className="flex items-start gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary-100 text-xs font-semibold text-primary-700 dark:bg-primary-900 dark:text-primary-300">
                  {stepIdx + 1}
                </span>
                <div className="flex-1 min-w-0 text-sm text-[var(--color-text-secondary)]">
                  {step.includes("\n\n") ? (
                    <>
                      <p>{step.split("\n\n")[0]}</p>
                      {step.split("\n\n").slice(1).map((block, bi) => (
                        <CodeBlock key={bi} code={block} />
                      ))}
                    </>
                  ) : (
                    <p>{step}</p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </CollapsiblePanel>
      ))}
    </div>
  );
}

function CliTab() {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="mb-2 text-lg font-semibold">CLI Reference</h2>
        <p className="text-sm text-[var(--color-text-secondary)]">
          Atlas Vox includes a CLI built with Typer and Rich. Install with{" "}
          <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">pip install -e .</code>
          {" "}and run commands with the <code className="rounded bg-gray-100 px-1.5 py-0.5 text-xs dark:bg-gray-800">atlas-vox</code> entry point.
        </p>
        <CodeBlock code="atlas-vox --help" />
      </Card>

      {CLI_COMMANDS.map((cmd) => (
        <CollapsiblePanel key={cmd.name} title={cmd.name} defaultOpen={false}>
          <p className="text-sm text-[var(--color-text-secondary)] mb-3">{cmd.description}</p>
          <CodeBlock code={cmd.syntax} />
          {cmd.options.length > 0 && (
            <div className="mt-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)] mb-2">Options</h4>
              <DataTable
                headers={["Flag", "Description"]}
                rows={cmd.options.map((o) => [
                  <code key={o.flag} className="text-xs">{o.flag}</code>,
                  o.description,
                ])}
              />
            </div>
          )}
          <div className="mt-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-tertiary)] mb-2">Example</h4>
            <CodeBlock code={cmd.example} />
          </div>
        </CollapsiblePanel>
      ))}
    </div>
  );
}

function TroubleshootingTab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [category, setCategory] = useState<string>("All");
  const [openFaqs, setOpenFaqs] = useState<Set<number>>(new Set());

  const filteredFaqs = useMemo(() => {
    let items = FAQ_ITEMS;
    if (category !== "All") {
      items = items.filter((item) => item.category === category);
    }
    if (searchTerm.trim()) {
      const lower = searchTerm.toLowerCase();
      items = items.filter(
        (item) =>
          item.question.toLowerCase().includes(lower) ||
          item.answer.toLowerCase().includes(lower) ||
          item.category.toLowerCase().includes(lower)
      );
    }
    return items;
  }, [searchTerm, category]);

  const toggleFaq = (index: number) => {
    setOpenFaqs((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {/* Search and filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-secondary)]" />
          <input
            type="text"
            placeholder="Search troubleshooting topics..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              if (e.target.value) logger.debug("faq_search", { term_length: e.target.value.length });
            }}
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {FAQ_CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategory(cat)}
              className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                category === cat
                  ? "bg-primary-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Count */}
      <p className="text-xs text-[var(--color-text-secondary)]">
        Showing {filteredFaqs.length} of {FAQ_ITEMS.length} topics
      </p>

      {/* FAQ list */}
      {filteredFaqs.length === 0 ? (
        <Card className="py-8 text-center">
          <p className="text-[var(--color-text-secondary)]">No matching troubleshooting topics found.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredFaqs.map((item, i) => (
            <FaqCard key={`${item.category}-${i}`} item={item} open={openFaqs.has(i)} onToggle={() => toggleFaq(i)} />
          ))}
        </div>
      )}
    </div>
  );
}

function ApiTab() {
  return (
    <div className="space-y-4">
      {/* Links */}
      <Card>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold">Interactive API Documentation</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Full Swagger UI and ReDoc are available from your running instance.
            </p>
          </div>
          <div className="flex gap-2 shrink-0">
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-primary-500 px-3 py-2 text-sm font-medium text-white hover:bg-primary-600"
            >
              Swagger UI <ExternalLink className="h-3.5 w-3.5" />
            </a>
            <a
              href="/redoc"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              ReDoc <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </div>
        </div>
      </Card>

      {/* Base URL and auth */}
      <Card>
        <h3 className="mb-2 font-semibold">Base URL and Authentication</h3>
        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
          Base URL: <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">http://localhost:8100/api/v1</code>
        </p>
        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
          Authentication: Bearer token via the <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">Authorization</code> header.
          When <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">AUTH_DISABLED=true</code> (default), no token is required.
        </p>
        <CodeBlock
          code={'curl -H "Authorization: Bearer avx_your_key_here" \\\n     http://localhost:8100/api/v1/profiles'}
        />
      </Card>

      {/* Endpoints */}
      <Card>
        <h3 className="mb-4 font-semibold">Endpoint Examples ({API_EXAMPLES.length})</h3>
        <div className="space-y-4">
          {API_EXAMPLES.map((ex) => (
            <div key={ex.title} className="rounded-lg border border-[var(--color-border)] p-3">
              <div className="flex items-center gap-2 mb-2">
                <MethodBadge method={ex.method} />
                <code className="text-sm font-medium">{ex.endpoint}</code>
                <span className="ml-auto text-xs text-[var(--color-text-secondary)]">{ex.title}</span>
              </div>
              {ex.body && (
                <div className="mb-2">
                  <p className="text-xs text-[var(--color-text-secondary)] mb-1">Request body:</p>
                  <pre className="rounded bg-gray-50 p-2 text-xs dark:bg-gray-900 overflow-x-auto">{ex.body}</pre>
                </div>
              )}
              <div>
                <p className="text-xs text-[var(--color-text-secondary)] mb-1">Response:</p>
                <pre className="rounded bg-gray-50 p-2 text-xs dark:bg-gray-900 overflow-x-auto">{ex.response}</pre>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* OpenAI compat */}
      <Card>
        <h3 className="mb-2 font-semibold">OpenAI-Compatible Endpoint</h3>
        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
          Atlas Vox exposes an OpenAI-compatible TTS endpoint at{" "}
          <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">/v1/audio/speech</code>.
          Point any OpenAI TTS client to your Atlas Vox server.
        </p>
        <CodeBlock
          code={`curl http://localhost:8100/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "kokoro",
    "input": "Hello from Atlas Vox!",
    "voice": "af_heart",
    "response_format": "wav"
  }' \\
  --output speech.wav`}
        />
        <p className="mt-3 text-xs text-[var(--color-text-secondary)]">
          The <code className="rounded bg-gray-100 px-1 dark:bg-gray-800">model</code> field maps to a provider name.
          The <code className="rounded bg-gray-100 px-1 dark:bg-gray-800">voice</code> field maps to a voice ID.
          Supported response_format values: wav, mp3, opus, flac.
        </p>
      </Card>

      {/* Webhooks */}
      <Card>
        <h3 className="mb-2 font-semibold">Webhooks</h3>
        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
          Register webhook URLs to receive notifications for training job events and synthesis completions.
        </p>
        <CodeBlock
          code={`POST /api/v1/webhooks
{
  "url": "https://your-server.com/hook",
  "events": ["training.completed", "training.failed", "synthesis.completed"],
  "secret": "your_webhook_secret"
}`}
          language="json"
        />
      </Card>

      {/* Rate limits */}
      <Card>
        <h3 className="mb-3 font-semibold">Rate Limits</h3>
        <DataTable
          headers={["Endpoint", "Limit"]}
          rows={RATE_LIMITS.map((r) => [
            <code key={r.endpoint} className="text-xs">{r.endpoint}</code>,
            r.limit,
          ])}
        />
      </Card>
    </div>
  );
}

function AboutTab() {
  return (
    <div className="space-y-4">
      {/* Version info */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold">About Atlas Vox</h2>
        <div className="space-y-0 text-sm">
          {ABOUT_INFO.map((item, i) => (
            <div
              key={item.label}
              className={`flex justify-between py-2.5 ${i < ABOUT_INFO.length - 1 ? "border-b border-[var(--color-border)]" : ""}`}
            >
              <span className="text-[var(--color-text-secondary)]">{item.label}</span>
              <span className="font-medium text-right">{item.value}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Provider comparison */}
      <Card>
        <h3 className="mb-3 font-semibold">TTS Provider Comparison</h3>
        <DataTable
          headers={["Provider", "Type", "Model", "Voices", "Languages", "Streaming", "Cloning", "Pricing"]}
          rows={PROVIDER_TABLE.map((p) => [
            p.name,
            <Badge key={`${p.name}-type`} status={p.type.includes("CPU") ? "local" : p.type.includes("GPU") ? "gpu" : "cloud"} className="text-[10px]" />,
            p.model,
            p.voices,
            p.languages,
            p.streaming === "Yes" ? <Badge key={`${p.name}-stream`} status="ready" className="text-[10px]" /> : <span className="text-[var(--color-text-tertiary)]">--</span>,
            p.cloning === "Yes" ? <Badge key={`${p.name}-clone`} status="ready" className="text-[10px]" /> : <span className="text-[var(--color-text-tertiary)]">--</span>,
            <Badge key={`${p.name}-price`} status={p.pricing === "Open Source" ? "ready" : p.pricing === "Freemium" ? "pending" : "training"} className="text-[10px]" />,
          ])}
        />
      </Card>

      {/* Tech stack */}
      <Card>
        <h3 className="mb-3 font-semibold">Technology Stack</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
          {[
            { area: "Backend Framework", tech: "FastAPI + Pydantic v2" },
            { area: "ORM", tech: "SQLAlchemy (async)" },
            { area: "Task Queue", tech: "Celery + Redis" },
            { area: "Migrations", tech: "Alembic" },
            { area: "Logging", tech: "structlog (JSON)" },
            { area: "Frontend Framework", tech: "React 18 + TypeScript 5" },
            { area: "Build Tool", tech: "Vite" },
            { area: "CSS", tech: "Tailwind CSS" },
            { area: "State Management", tech: "Zustand" },
            { area: "Audio Visualization", tech: "wavesurfer.js" },
            { area: "Code Editor", tech: "Monaco Editor" },
            { area: "CLI", tech: "Typer + Rich" },
            { area: "MCP Transport", tech: "JSONRPC 2.0 + SSE" },
            { area: "Authentication", tech: "Argon2id + Bearer tokens" },
          ].map((item) => (
            <div key={item.area} className="flex justify-between border-b border-[var(--color-border)] pb-2">
              <span className="text-[var(--color-text-secondary)]">{item.area}</span>
              <span className="font-medium">{item.tech}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Doc links */}
      <Card>
        <h3 className="mb-3 font-semibold">Documentation Links</h3>
        <div className="space-y-2">
          {DOC_LINKS.map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between rounded-lg border border-[var(--color-border)] p-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <span>{link.label}</span>
              <ExternalLink className="h-4 w-4 text-[var(--color-text-secondary)]" />
            </a>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main page component                                                */
/* ------------------------------------------------------------------ */

const TAB_COMPONENTS: Record<TabKey, React.FC> = {
  "getting-started": GettingStartedTab,
  "user-guide": UserGuideTab,
  walkthroughs: WalkthroughsTab,
  cli: CliTab,
  troubleshooting: TroubleshootingTab,
  api: ApiTab,
  about: AboutTab,
  providers: ProviderGuidesTab,
  architecture: ArchitectureTab,
  configuration: ConfigurationTab,
  mcp: MCPIntegrationTab,
  "self-healing": SelfHealingDocsTab,
  deployment: DeploymentTab,
};

type GroupKey = (typeof GROUPS)[number]["key"];

export default function HelpPage() {
  const [activeGroup, setActiveGroup] = useState<GroupKey>("guide");
  const [activeTab, setActiveTab] = useState<TabKey>("getting-started");

  const groupTabs = TABS.filter((t) => t.group === activeGroup);
  const ActiveComponent = TAB_COMPONENTS[activeTab];

  const handleGroupChange = (group: GroupKey) => {
    setActiveGroup(group);
    const firstTab = TABS.find((t) => t.group === group);
    if (firstTab) setActiveTab(firstTab.key);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Help & Documentation</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Guides, technical reference, troubleshooting, and API documentation
        </p>
      </div>

      {/* Group selector */}
      <div className="flex gap-2">
        {GROUPS.map((group) => (
          <button
            key={group.key}
            onClick={() => handleGroupChange(group.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              activeGroup === group.key
                ? "bg-primary-500 text-white shadow-sm"
                : "bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {group.label}
          </button>
        ))}
      </div>

      {/* Tab bar within selected group */}
      <div className="flex gap-1 overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-sidebar)] p-1 scrollbar-thin">
        {groupTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => {
                logger.info("tab_change", { tab: tab.key });
                setActiveTab(tab.key);
              }}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                activeTab === tab.key
                  ? "bg-primary-500/20 text-primary-600 dark:text-primary-400"
                  : "text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Active tab content */}
      <ActiveComponent />
    </div>
  );
}
