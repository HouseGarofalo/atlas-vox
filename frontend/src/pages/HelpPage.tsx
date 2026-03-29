import { useState, useMemo, type ReactNode } from "react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import {
  Search,
  ExternalLink,
  Rocket,
  BookOpen,
  Footprints,
  Terminal,
  AlertTriangle,
  Code2,
  Info,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Mic,
  AudioLines,
  Users,
  Cpu,
  Cloud,
  Key,
  Settings,
  Palette,
  Shield,
  FileText,
  HelpCircle,
  Wrench,
  BarChart3,
  Globe,
  Zap,
  Volume2,
  Play,
  ArrowRight,
} from "lucide-react";
import { createLogger } from "../utils/logger";

const logger = createLogger("HelpPage");

/* ================================================================
   TYPES
   ================================================================ */

interface FaqItem {
  question: string;
  answer: string;
  category: string;
  severity: "easy" | "moderate" | "complex";
}

/* ================================================================
   CONSTANTS
   ================================================================ */

const TABS = [
  "Getting Started",
  "User Guide",
  "Walkthroughs",
  "CLI Reference",
  "Troubleshooting",
  "API Reference",
  "About",
] as const;
type Tab = (typeof TABS)[number];

const TAB_ICONS: Record<Tab, ReactNode> = {
  "Getting Started": <Rocket className="h-4 w-4" />,
  "User Guide": <BookOpen className="h-4 w-4" />,
  Walkthroughs: <Footprints className="h-4 w-4" />,
  "CLI Reference": <Terminal className="h-4 w-4" />,
  Troubleshooting: <AlertTriangle className="h-4 w-4" />,
  "API Reference": <Code2 className="h-4 w-4" />,
  About: <Info className="h-4 w-4" />,
};

/* ================================================================
   FAQ DATA
   ================================================================ */

const FAQ_ITEMS: FaqItem[] = [
  // Installation (5)
  {
    category: "Installation",
    severity: "moderate",
    question: "Docker build fails during pip install",
    answer:
      "This is usually caused by network issues or PyPI rate limiting. Rebuild with no cache:\n\ndocker compose -f docker/docker-compose.yml build --no-cache backend\n\nIf behind a corporate proxy, set HTTP_PROXY and HTTPS_PROXY build args in docker-compose.yml.",
  },
  {
    category: "Installation",
    severity: "easy",
    question: "Port 3100 or 8100 is already in use",
    answer:
      "Edit docker/.env and change BACKEND_PORT and FRONTEND_PORT to different values (e.g., 8200 and 3200). Then restart with make docker-up. On Linux/macOS you can find what's using the port: lsof -i :8100",
  },
  {
    category: "Installation",
    severity: "easy",
    question: "Redis connection fails on startup",
    answer:
      "Atlas Vox uses Redis database 1 (redis://localhost:6379/1) to avoid collision with other services on database 0. Ensure Redis is running: redis-server (or check Docker). Verify connectivity: python -c \"import redis; print(redis.Redis(db=1).ping())\"",
  },
  {
    category: "Installation",
    severity: "moderate",
    question: "espeak-ng is missing (Piper/Kokoro won't start)",
    answer:
      "Some local TTS providers depend on espeak-ng for phonemization. Install it:\n\n- Ubuntu/Debian: sudo apt install espeak-ng\n- macOS: brew install espeak-ng\n- Windows: download from https://github.com/espeak-ng/espeak-ng/releases\n\nThe Docker image includes it automatically.",
  },
  {
    category: "Installation",
    severity: "easy",
    question: "Python version mismatch (requires 3.11+)",
    answer:
      "Atlas Vox requires Python 3.11 or newer. Check your version: python --version. Use pyenv to install the right version:\n\npyenv install 3.11.9\npyenv local 3.11.9\n\nOr use the Docker setup which includes the correct Python version.",
  },
  // Providers (5)
  {
    category: "Providers",
    severity: "easy",
    question: "A provider shows as 'unhealthy' on the dashboard",
    answer:
      "Go to the Providers page, expand the provider card, and click Health Check to see the specific error. Common causes: missing API key (cloud providers like ElevenLabs, Azure), missing model files (local providers on first run), or GPU not available (for GPU-mode providers).",
  },
  {
    category: "Providers",
    severity: "easy",
    question: "Missing API key for cloud providers",
    answer:
      "Cloud providers (ElevenLabs, Azure Speech) require API keys. Navigate to Providers, expand the provider, enter your API key in the Settings section, and click Save. Then run Health Check to verify. Keys are stored encrypted in the database.",
  },
  {
    category: "Providers",
    severity: "moderate",
    question: "How do I enable GPU mode for local providers?",
    answer:
      "Run make docker-gpu-up instead of make docker-up. This starts a GPU worker container with CUDA 12.1 and automatically enables GPU mode for Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2. Requires an NVIDIA GPU with compatible drivers. Verify GPU access: nvidia-smi",
  },
  {
    category: "Providers",
    severity: "moderate",
    question: "Model download is stuck or very slow",
    answer:
      "Large models (Dia2: ~8GB, Coqui XTTS: ~6GB) can take a while on first download. Models are cached in ~/.cache/atlas-vox/models/. If the download stalls, delete the partial file and restart. You can also pre-download models: atlas-vox providers download <name>",
  },
  {
    category: "Providers",
    severity: "complex",
    question: "Provider timeout errors during synthesis",
    answer:
      "Default timeout is 30 seconds. Large texts or slow hardware can exceed this. Increase the timeout in your provider config or environment: SYNTHESIS_TIMEOUT=60. For GPU providers running on CPU, performance is 10-50x slower -- switch to GPU mode or use a CPU-optimized provider (Kokoro, Piper).",
  },
  // Audio (3)
  {
    category: "Audio",
    severity: "easy",
    question: "Synthesis succeeds but no audio plays in browser",
    answer:
      "Check the browser console for errors. Try accessing the audio URL directly: http://localhost:8100/api/v1/audio/<filename>. Some browsers block autoplay -- click the waveform to start playback. If using MP3/OGG, try WAV format as it has the widest browser support.",
  },
  {
    category: "Audio",
    severity: "easy",
    question: "Audio upload is rejected as unsupported format",
    answer:
      "Atlas Vox supports WAV, MP3, FLAC, OGG, and M4A formats. Convert other formats using ffmpeg:\n\nffmpeg -i input.webm output.wav\nffmpeg -i input.aac -ar 22050 output.wav",
  },
  {
    category: "Audio",
    severity: "moderate",
    question: "Preprocessing fails with 'audio too short' error",
    answer:
      "Training audio must be at least 3 seconds long after trimming silence. Record or upload longer clips. Preprocessing trims leading/trailing silence, applies noise reduction, and normalizes volume. If your audio has long pauses, they may be trimmed, making it too short.",
  },
  // Training (3)
  {
    category: "Training",
    severity: "moderate",
    question: "Training job stuck at 'queued' status",
    answer:
      "This means the Celery worker is not running or not connected to Redis. In Docker, check worker logs: docker compose -f docker/docker-compose.yml logs worker. For local dev, start a Celery worker manually:\n\ncelery -A app.tasks.celery_app worker --loglevel=info\n\nVerify Redis is accessible on redis://localhost:6379/1.",
  },
  {
    category: "Training",
    severity: "moderate",
    question: "Training fails immediately after starting",
    answer:
      "Ensure you have uploaded AND preprocessed audio samples before starting training. The most common causes: (1) no preprocessed samples exist for the profile, (2) the provider doesn't support training (check capabilities), (3) GPU out of memory (try reducing batch size or use fewer samples).",
  },
  {
    category: "Training",
    severity: "easy",
    question: "WebSocket disconnects during training monitoring",
    answer:
      "Training continues in the background even if the WebSocket disconnects. Refresh the page to reconnect. If the WebSocket keeps dropping, check for proxy/firewall issues. The backend sends heartbeat pings every 30 seconds -- ensure nothing is closing idle connections.",
  },
  // Synthesis (2)
  {
    category: "Synthesis",
    severity: "moderate",
    question: "Synthesis is very slow (10+ seconds per request)",
    answer:
      "If using GPU-oriented models (Coqui XTTS, StyleTTS2, Dia, Dia2) on CPU, performance will be 10-50x slower. Solutions: (1) switch to GPU mode with make docker-gpu-up, (2) use CPU-optimized providers like Kokoro or Piper for fast synthesis, (3) reduce text length -- long passages synthesize slower.",
  },
  {
    category: "Synthesis",
    severity: "easy",
    question: "Getting '429 Too Many Requests' rate limit errors",
    answer:
      "Atlas Vox rate-limits expensive endpoints to prevent abuse: synthesis (10/min), training (5/min), comparison (5/min), OpenAI-compatible (20/min). Wait 60 seconds and retry, or reduce request frequency. Rate limits reset every minute. For bulk synthesis, use the CLI with --batch flag.",
  },
  // Database (2)
  {
    category: "Database",
    severity: "easy",
    question: "'No such table' errors on startup",
    answer:
      "Run make migrate to apply database migrations. For a fresh start, delete atlas_vox.db and restart the backend -- tables are created automatically on first launch. If using PostgreSQL, ensure the database exists and connection string is correct.",
  },
  {
    category: "Database",
    severity: "complex",
    question: "Alembic migration errors or conflicts",
    answer:
      "If migrations fail due to conflicts: (1) check alembic history: alembic history, (2) stamp the current state: alembic stamp head, (3) create a new migration: alembic revision --autogenerate -m 'fix'. For a clean reset, drop all tables and re-run: alembic upgrade head. Always back up your database before destructive operations.",
  },
  // Self-Healing (2)
  {
    category: "Self-Healing",
    severity: "moderate",
    question: "How do I test the self-healing system?",
    answer:
      "Navigate to the Self-Healing page. The system monitors provider health, training job failures, and resource usage. To test: (1) stop a provider's service intentionally, (2) watch the detection rule trigger, (3) observe the automatic remediation action (restart, fallback, or alert). Check the incident log for details.",
  },
  {
    category: "Self-Healing",
    severity: "complex",
    question: "Self-healing triggers false positive restarts",
    answer:
      "Adjust detection thresholds in the Self-Healing settings. Default health check interval is 30 seconds with 3 failures before triggering. Increase the failure threshold or interval if your providers have intermittent connectivity. You can also exclude specific providers from auto-remediation.",
  },
];

/* ================================================================
   HELPER COMPONENTS
   ================================================================ */

function CodeBlock({ children, title }: { children: string; title?: string }) {
  return (
    <div className="my-2 overflow-x-auto rounded-lg bg-gray-900 text-gray-100">
      {title && (
        <div className="border-b border-gray-700 px-4 py-2 text-xs font-medium text-gray-400">
          {title}
        </div>
      )}
      <pre className="p-4 text-sm leading-relaxed">
        <code>{children}</code>
      </pre>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: "easy" | "moderate" | "complex" }) {
  const map = {
    easy: "ready",
    moderate: "archived",
    complex: "error",
  };
  return <Badge status={map[severity]} className="text-[10px]" />;
}

function StepNumber({ n }: { n: number }) {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white">
      {n}
    </div>
  );
}

function SectionLabel({ icon, text }: { icon: ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-2 text-sm font-medium text-[var(--color-text-secondary)]">
      {icon}
      <span>{text}</span>
    </div>
  );
}

function InlineCode({ children }: { children: string }) {
  return (
    <code className="rounded bg-gray-100 px-1.5 py-0.5 text-sm dark:bg-gray-800">
      {children}
    </code>
  );
}

function MethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    POST: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    PUT: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    DELETE: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    PATCH: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  };
  return (
    <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${colors[method] || colors.GET}`}>
      {method}
    </span>
  );
}

/* ================================================================
   TAB: GETTING STARTED
   ================================================================ */

function GettingStartedTab() {
  return (
    <div className="space-y-4">
      {/* Welcome */}
      <Card>
        <div className="flex items-start gap-3">
          <Rocket className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold">Welcome to Atlas Vox</h2>
            <p className="mt-2 text-sm leading-relaxed text-[var(--color-text-secondary)]">
              Atlas Vox is a self-hosted voice training and customization platform that brings
              together 9 text-to-speech providers under a single, unified interface. It supports
              voice cloning, real-time synthesis, side-by-side comparison, and a complete training
              pipeline -- all accessible through the Web UI, REST API, CLI, and MCP server.
            </p>
          </div>
        </div>
      </Card>

      {/* Prerequisites */}
      <CollapsiblePanel
        title="Prerequisites"
        icon={<CheckCircle2 className="h-4 w-4 text-green-500" />}
        defaultOpen={true}
      >
        <div className="space-y-2 text-sm">
          <p className="text-[var(--color-text-secondary)] mb-3">
            Ensure you have the following installed before starting:
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              { name: "Python 3.11+", required: true, note: "Backend runtime" },
              { name: "Node.js 20+", required: true, note: "Frontend build" },
              { name: "Redis", required: true, note: "Task queue & caching" },
              { name: "Docker & Docker Compose", required: false, note: "Recommended for easy setup" },
              { name: "NVIDIA GPU + CUDA 12.1", required: false, note: "For GPU providers" },
              { name: "ffmpeg", required: false, note: "Audio format conversion" },
            ].map((item) => (
              <div
                key={item.name}
                className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] p-3"
              >
                {item.required ? (
                  <CheckCircle2 className="h-4 w-4 shrink-0 text-green-500" />
                ) : (
                  <Info className="h-4 w-4 shrink-0 text-blue-500" />
                )}
                <div>
                  <div className="font-medium">{item.name}</div>
                  <div className="text-xs text-[var(--color-text-secondary)]">
                    {item.required ? "Required" : "Optional"} -- {item.note}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </CollapsiblePanel>

      {/* Quickstart */}
      <CollapsiblePanel
        title="6-Step Quickstart"
        icon={<Zap className="h-4 w-4 text-amber-500" />}
        defaultOpen={true}
      >
        <div className="space-y-4">
          {/* Step 1 */}
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h3 className="font-semibold">Clone and navigate to the project</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Clone the repository and enter the project directory.
              </p>
              <CodeBlock>{`git clone https://github.com/HouseGarofalo/atlas-vox.git
cd atlas-vox`}</CodeBlock>
            </div>
          </div>

          {/* Step 2 */}
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h3 className="font-semibold">Start services</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Use Docker Compose for the easiest setup, or run locally for development.
              </p>
              <CodeBlock title="Docker (recommended)">{`make docker-up`}</CodeBlock>
              <CodeBlock title="Local development">{`make dev`}</CodeBlock>
              <p className="mt-1 text-xs italic text-[var(--color-text-secondary)]">
                For GPU support: <InlineCode>make docker-gpu-up</InlineCode>
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h3 className="font-semibold">Open the Web UI</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Access the dashboard in your browser.
              </p>
              <CodeBlock>{`http://localhost:3100`}</CodeBlock>
              <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
                API documentation is at{" "}
                <InlineCode>http://localhost:8100/docs</InlineCode>
              </p>
            </div>
          </div>

          {/* Step 4 */}
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h3 className="font-semibold">Check provider health on the Dashboard</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                The Dashboard shows a provider health grid. CPU-only providers (Kokoro, Piper)
                should show as <Badge status="healthy" className="text-[10px]" /> immediately.
                Cloud providers need API keys configured first.
              </p>
            </div>
          </div>

          {/* Step 5 */}
          <div className="flex items-start gap-4">
            <StepNumber n={5} />
            <div className="flex-1">
              <h3 className="font-semibold">Create your first voice profile</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Go to Voice Profiles and create a new profile. Select a provider, give it a
                descriptive name, and choose a language. Or browse the Voice Library first to
                find a voice you like.
              </p>
            </div>
          </div>

          {/* Step 6 */}
          <div className="flex items-start gap-4">
            <StepNumber n={6} />
            <div className="flex-1">
              <h3 className="font-semibold">Synthesize your first speech</h3>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Navigate to the Synthesis Lab, select your profile, type some text, and click
                Synthesize. Listen to the result with the built-in waveform audio player.
              </p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* What's Next */}
      <Card>
        <h3 className="font-semibold mb-3">What's Next?</h3>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { tab: "User Guide", desc: "Learn every feature in detail", icon: <BookOpen className="h-4 w-4" /> },
            { tab: "Walkthroughs", desc: "Step-by-step tutorials", icon: <Footprints className="h-4 w-4" /> },
            { tab: "CLI Reference", desc: "Command-line usage", icon: <Terminal className="h-4 w-4" /> },
            { tab: "Troubleshooting", desc: "Common issues & fixes", icon: <AlertTriangle className="h-4 w-4" /> },
            { tab: "API Reference", desc: "REST API endpoints", icon: <Code2 className="h-4 w-4" /> },
            { tab: "About", desc: "Tech stack & providers", icon: <Info className="h-4 w-4" /> },
          ].map((item) => (
            <div
              key={item.tab}
              className="flex items-center gap-3 rounded-lg border border-[var(--color-border)] p-3 text-sm"
            >
              <span className="text-primary-500">{item.icon}</span>
              <div>
                <div className="font-medium">{item.tab}</div>
                <div className="text-xs text-[var(--color-text-secondary)]">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ================================================================
   TAB: USER GUIDE
   ================================================================ */

function UserGuideTab() {
  return (
    <div className="space-y-3">
      <Card>
        <div className="flex items-start gap-3">
          <BookOpen className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold">Feature Guide</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Comprehensive documentation for every page and feature in Atlas Vox.
            </p>
          </div>
        </div>
      </Card>

      {/* Dashboard */}
      <CollapsiblePanel
        title="Dashboard"
        icon={<BarChart3 className="h-4 w-4 text-blue-500" />}
        defaultOpen={false}
        id="guide-dashboard"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Dashboard is your home screen, providing an at-a-glance overview of the entire platform.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Stat Cards</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Card</th>
                  <th className="pb-2 font-medium">Shows</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--color-border)]">
                  <td className="py-2 font-medium">Voice Profiles</td>
                  <td className="py-2">Total number of voice profiles across all providers</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]">
                  <td className="py-2 font-medium">Active Jobs</td>
                  <td className="py-2">Currently running or queued training jobs</td>
                </tr>
                <tr className="border-b border-[var(--color-border)]">
                  <td className="py-2 font-medium">Recent Syntheses</td>
                  <td className="py-2">Synthesis requests in the last 24 hours</td>
                </tr>
                <tr className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 font-medium">Active Providers</td>
                  <td className="py-2">Number of healthy and configured providers</td>
                </tr>
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Provider Health Grid</h4>
          <p>
            Each provider is shown as a card with a color-coded status:{" "}
            <Badge status="healthy" className="text-[10px]" /> means operational,{" "}
            <Badge status="unhealthy" className="text-[10px]" /> means the health check failed,{" "}
            <Badge status="pending" className="text-[10px]" /> means not yet checked. Click any
            provider to go to its configuration page.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Training Job Status</h4>
          <p>
            Active training jobs are listed with real-time progress bars. Status values:{" "}
            <Badge status="queued" className="text-[10px]" /> (waiting for a Celery worker),{" "}
            <Badge status="training" className="text-[10px]" /> (in progress),{" "}
            <Badge status="completed" className="text-[10px]" /> (finished successfully),{" "}
            <Badge status="failed" className="text-[10px]" /> (error occurred).
          </p>
        </div>
      </CollapsiblePanel>

      {/* Voice Profiles */}
      <CollapsiblePanel
        title="Voice Profiles"
        icon={<Users className="h-4 w-4 text-violet-500" />}
        defaultOpen={false}
        id="guide-profiles"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            Voice Profiles are the core identity unit in Atlas Vox. Each profile is bound to a
            single TTS provider and represents a unique voice configuration.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Profile Status Lifecycle</h4>
          <div className="flex flex-wrap items-center gap-2 my-2">
            <Badge status="pending" /> <ArrowRight className="h-3 w-3" />
            <Badge status="training" /> <ArrowRight className="h-3 w-3" />
            <Badge status="ready" />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Meaning</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2"><Badge status="pending" /></td><td className="py-2">Newly created, no training started</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2"><Badge status="training" /></td><td className="py-2">Training job is running</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2"><Badge status="ready" /></td><td className="py-2">Training complete, ready for synthesis</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2"><Badge status="error" /></td><td className="py-2">Training failed (check job logs)</td></tr>
                <tr><td className="py-2"><Badge status="archived" /></td><td className="py-2">Deactivated, preserved for reference</td></tr>
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Creating Profiles</h4>
          <p>
            Profiles can be created two ways: (1) clicking "New Profile" and selecting a provider
            and voice, or (2) from the Voice Library by clicking "Create Profile" on any discovered
            voice. Profiles created from the library pre-populate the provider and voice ID.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Managing Versions</h4>
          <p>
            Each training run produces a new model version. You can switch between versions, compare
            them side-by-side, and roll back to a previous version if the latest training didn't improve quality.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Voice Library */}
      <CollapsiblePanel
        title="Voice Library"
        icon={<AudioLines className="h-4 w-4 text-emerald-500" />}
        defaultOpen={false}
        id="guide-library"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Voice Library aggregates all available voices across every configured provider,
            giving you a unified catalog of voices to browse and preview.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Filtering</h4>
          <p>
            Use the filter controls at the top to narrow results by provider (e.g., only Kokoro voices),
            language (e.g., English, Japanese), or gender. The search bar performs fuzzy matching on
            voice name and description.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Previewing Voices</h4>
          <p>
            Click the play button on any voice card to hear a sample synthesis. The preview uses
            a standard sentence to give you a consistent comparison point across voices.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Creating Profiles from Library</h4>
          <p>
            Click "Create Profile" on any voice card to instantly create a voice profile with that
            voice's provider and ID pre-populated. You'll be redirected to the profile detail page
            to customize settings.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Training Studio */}
      <CollapsiblePanel
        title="Training Studio"
        icon={<Mic className="h-4 w-4 text-red-500" />}
        defaultOpen={false}
        id="guide-training"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Training Studio is where you clone voices. The full workflow: select a profile,
            upload or record audio, preprocess it, start training, and monitor progress in real time.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">1. Select Profile</h4>
          <p>Choose which voice profile to train. Only profiles with status "pending" or "ready" can start new training runs.</p>
          <h4 className="font-semibold text-[var(--color-text)]">2. Upload or Record Audio</h4>
          <p>
            Upload audio files (WAV, MP3, FLAC, OGG, M4A) or record directly in the browser using
            the built-in audio recorder. Minimum 6 seconds of clear speech is recommended. More
            audio (1-5 minutes) produces better voice cloning results.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">3. Preprocessing</h4>
          <p>Click "Preprocess" to prepare audio samples. The pipeline applies:</p>
          <ul className="ml-4 list-disc space-y-1">
            <li><strong>Noise reduction</strong> -- removes background noise</li>
            <li><strong>Volume normalization</strong> -- ensures consistent loudness</li>
            <li><strong>Silence trimming</strong> -- removes leading/trailing silence</li>
            <li><strong>Format standardization</strong> -- converts to the provider's required format</li>
          </ul>
          <h4 className="font-semibold text-[var(--color-text)]">4. Start Training</h4>
          <p>
            Click "Start Training" to submit a Celery task. The job enters a queue and starts when a
            worker picks it up. Training duration depends on the provider and amount of audio.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">5. Monitor via WebSocket</h4>
          <p>
            Training progress updates are streamed in real time via WebSocket. You'll see a progress
            bar, current epoch, loss values, and estimated time remaining. The profile status automatically
            changes to "ready" when training completes.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Requirements per Provider</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Provider</th>
                  <th className="pb-2 font-medium">Min Audio</th>
                  <th className="pb-2 font-medium">GPU Required</th>
                  <th className="pb-2 font-medium">VRAM</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2">Coqui XTTS v2</td><td className="py-2">6 seconds</td><td className="py-2">Recommended</td><td className="py-2">4 GB+</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2">StyleTTS2</td><td className="py-2">30 seconds</td><td className="py-2">Recommended</td><td className="py-2">4 GB+</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2">ElevenLabs</td><td className="py-2">1 minute</td><td className="py-2">No (cloud)</td><td className="py-2">N/A</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2">Dia / Dia2</td><td className="py-2">30 seconds</td><td className="py-2">Yes</td><td className="py-2">6-8 GB+</td></tr>
                <tr><td className="py-2">CosyVoice</td><td className="py-2">10 seconds</td><td className="py-2">Recommended</td><td className="py-2">4 GB+</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Synthesis Lab */}
      <CollapsiblePanel
        title="Synthesis Lab"
        icon={<Volume2 className="h-4 w-4 text-amber-500" />}
        defaultOpen={false}
        id="guide-synthesis"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Synthesis Lab is your primary workspace for generating speech. Enter text, pick a
            voice profile, adjust parameters, and synthesize.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Text Input</h4>
          <p>
            Type or paste text into the input area. There's no hard character limit, but longer
            texts take proportionally longer to synthesize. Most providers handle up to ~5,000
            characters per request.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">SSML Editor Toggle</h4>
          <p>
            Click "Switch to SSML" to open the Monaco-based XML editor. SSML gives fine-grained
            control over pronunciation, pauses, emphasis, and prosody. Supported by Azure Speech;
            other providers ignore SSML tags and synthesize plain text content.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Speed / Pitch / Volume Controls</h4>
          <p>
            Sliders let you adjust synthesis parameters. Speed (0.5x-2.0x), Pitch (-10 to +10 semitones),
            Volume (0.0-1.5). Not all providers support all parameters -- unsupported controls are
            dimmed with a tooltip explaining why.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Persona Presets</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Preset</th>
                  <th className="pb-2 font-medium">Speed</th>
                  <th className="pb-2 font-medium">Pitch</th>
                  <th className="pb-2 font-medium">Volume</th>
                  <th className="pb-2 font-medium">Character</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { name: "Friendly", speed: "1.0x", pitch: "+2", volume: "1.0", char: "Warm and approachable" },
                  { name: "Professional", speed: "0.95x", pitch: "0", volume: "1.0", char: "Clear and authoritative" },
                  { name: "Energetic", speed: "1.15x", pitch: "+5", volume: "1.1", char: "Upbeat and enthusiastic" },
                  { name: "Calm", speed: "0.85x", pitch: "-3", volume: "0.9", char: "Soothing and relaxed" },
                  { name: "Authoritative", speed: "0.9x", pitch: "-5", volume: "1.15", char: "Commanding and confident" },
                  { name: "Soothing", speed: "0.8x", pitch: "-2", volume: "0.85", char: "Gentle and comforting" },
                ].map((p) => (
                  <tr key={p.name} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-2 font-medium">{p.name}</td>
                    <td className="py-2">{p.speed}</td>
                    <td className="py-2">{p.pitch}</td>
                    <td className="py-2">{p.volume}</td>
                    <td className="py-2 text-[var(--color-text-secondary)]">{p.char}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Output Formats</h4>
          <p>
            Choose from WAV (uncompressed, highest quality), MP3 (compressed, smaller files), or
            OGG (compressed, open format). WAV is recommended for further processing; MP3/OGG for
            sharing or embedding.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Comparison */}
      <CollapsiblePanel
        title="Comparison"
        icon={<BarChart3 className="h-4 w-4 text-cyan-500" />}
        defaultOpen={false}
        id="guide-comparison"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Comparison page lets you synthesize the same text with multiple voice profiles
            side-by-side, making it easy to evaluate different voices, providers, or training
            versions.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">How it works</h4>
          <ol className="ml-4 list-decimal space-y-1">
            <li>Enter the text you want to compare</li>
            <li>Select 2 or more voice profiles from the dropdown</li>
            <li>Click "Compare" to synthesize all versions simultaneously</li>
            <li>Listen to each result with the inline audio player</li>
            <li>Review latency metrics for each provider</li>
          </ol>
          <h4 className="font-semibold text-[var(--color-text)]">Interpreting Results</h4>
          <p>
            Each result card shows the profile name, provider, audio player, and synthesis latency in
            milliseconds. Lower latency means faster synthesis. Use this to compare quality, speed,
            and naturalness across providers.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Providers */}
      <CollapsiblePanel
        title="Providers"
        icon={<Cpu className="h-4 w-4 text-indigo-500" />}
        defaultOpen={false}
        id="guide-providers"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Providers page lists all 9 TTS engines with their capabilities, health status,
            and configuration options.
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Provider</th>
                  <th className="pb-2 font-medium">Type</th>
                  <th className="pb-2 font-medium">Key Feature</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { name: "Kokoro", type: "local", feat: "CPU-only, 54 built-in voices, default provider" },
                  { name: "Piper", type: "local", feat: "ONNX runtime, Home Assistant compatible" },
                  { name: "ElevenLabs", type: "cloud", feat: "Cloud API, voice cloning, high quality" },
                  { name: "Azure Speech", type: "cloud", feat: "SSML support, 400+ neural voices" },
                  { name: "Coqui XTTS v2", type: "gpu", feat: "Voice cloning from 6s audio" },
                  { name: "StyleTTS2", type: "gpu", feat: "Zero-shot, style diffusion" },
                  { name: "CosyVoice", type: "gpu", feat: "Multilingual, streaming capable" },
                  { name: "Dia", type: "gpu", feat: "Dialogue generation, 1.6B params" },
                  { name: "Dia2", type: "gpu", feat: "Next-gen dialogue, streaming, 2B params" },
                ].map((p) => (
                  <tr key={p.name} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-2 font-medium">{p.name}</td>
                    <td className="py-2"><Badge status={p.type} className="text-[10px]" /></td>
                    <td className="py-2">{p.feat}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Configuration</h4>
          <p>
            Expand any provider card to access: API key input (cloud providers), GPU mode toggle
            (local providers), model path configuration, and Health Check / Test Synthesis buttons.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Health Checks</h4>
          <p>
            Click "Health Check" to verify the provider is operational. This tests connectivity,
            model loading, and API authentication. Results are shown inline with specific error
            messages if unhealthy.
          </p>
        </div>
      </CollapsiblePanel>

      {/* API Keys */}
      <CollapsiblePanel
        title="API Keys"
        icon={<Key className="h-4 w-4 text-yellow-500" />}
        defaultOpen={false}
        id="guide-apikeys"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            API Keys provide programmatic access to Atlas Vox. When AUTH_DISABLED=true (default
            for single-user mode), keys are not required but can still be created for external integrations.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Scopes</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Scope</th>
                  <th className="pb-2 font-medium">Permissions</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2 font-medium">read</td><td className="py-2">View profiles, voices, providers, history</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2 font-medium">write</td><td className="py-2">Create/update profiles, upload samples</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2 font-medium">synthesize</td><td className="py-2">Generate speech via API</td></tr>
                <tr className="border-b border-[var(--color-border)]"><td className="py-2 font-medium">train</td><td className="py-2">Start training jobs, manage samples</td></tr>
                <tr><td className="py-2 font-medium">admin</td><td className="py-2">Full access including key management</td></tr>
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Key Format & Security</h4>
          <p>
            Keys use the format <InlineCode>avx_</InlineCode> followed by random characters.
            Keys are hashed with Argon2id before storage -- the raw key is shown only once at
            creation time. Copy it immediately; it cannot be recovered.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Settings */}
      <CollapsiblePanel
        title="Settings"
        icon={<Settings className="h-4 w-4 text-gray-500" />}
        defaultOpen={false}
        id="guide-settings"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Settings page lets you configure application-wide preferences. All settings persist
            in browser local storage.
          </p>
          <ul className="ml-4 list-disc space-y-1">
            <li><strong>Theme</strong>: Toggle between light and dark mode</li>
            <li><strong>Default Provider</strong>: Set which provider is pre-selected in the Synthesis Lab</li>
            <li><strong>Audio Format</strong>: Choose default output format (WAV, MP3, OGG)</li>
          </ul>
        </div>
      </CollapsiblePanel>

      {/* Design System */}
      <CollapsiblePanel
        title="Design System"
        icon={<Palette className="h-4 w-4 text-pink-500" />}
        defaultOpen={false}
        id="guide-design"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Design System page lets you customize the entire look and feel of Atlas Vox in
            real time. Changes are applied instantly and persist across sessions via local storage.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Design Tokens (15)</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left">
                  <th className="pb-2 font-medium">Token</th>
                  <th className="pb-2 font-medium">What it controls</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ["Accent Hue", "Primary color hue (0-360 degrees)"],
                  ["Accent Saturation", "Color intensity (0-100%)"],
                  ["Font Family", "System, Inter, monospace, or serif"],
                  ["Font Size", "Base font size (12-18px)"],
                  ["Density", "Spacing between elements (compact, normal, spacious)"],
                  ["Sidebar Width", "Navigation sidebar width in pixels"],
                  ["Content Max Width", "Maximum content area width"],
                  ["Border Radius", "Corner rounding (0-16px)"],
                  ["Card Style", "Bordered, raised, flat, or glassmorphism"],
                  ["Header Height", "Top header bar height"],
                  ["Animation Speed", "Transition duration multiplier"],
                  ["Animations Enabled", "Toggle all CSS transitions"],
                  ["Shadow Intensity", "Depth of card and modal shadows"],
                  ["Border Width", "Thickness of element borders"],
                  ["Focus Ring Width", "Accessibility focus indicator size"],
                ].map(([token, desc]) => (
                  <tr key={token} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-1.5 font-medium">{token}</td>
                    <td className="py-1.5">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <h4 className="font-semibold text-[var(--color-text)]">Theme Presets (8)</h4>
          <div className="flex flex-wrap gap-2">
            {["Blue", "Emerald", "Violet", "Sunset", "Rose", "Mono", "Minimal", "Spacious Serif"].map((p) => (
              <Badge key={p} status="pending" className="text-[10px]" />
            ))}
          </div>
          <p className="text-xs">
            Blue (default), Emerald, Violet, Sunset, Rose, Mono, Minimal, and Spacious Serif.
            Selecting a preset applies a curated set of token values. You can then fine-tune individual
            tokens after applying a preset.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Self-Healing */}
      <CollapsiblePanel
        title="Self-Healing"
        icon={<Shield className="h-4 w-4 text-green-500" />}
        defaultOpen={false}
        id="guide-selfhealing"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Self-Healing system continuously monitors provider health, training job stability,
            and system resources. It automatically detects and remediates issues without manual
            intervention.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">What it Monitors</h4>
          <ul className="ml-4 list-disc space-y-1">
            <li>Provider health check results (every 30 seconds)</li>
            <li>Training job failure rates</li>
            <li>Memory and disk usage</li>
            <li>Redis and database connectivity</li>
          </ul>
          <h4 className="font-semibold text-[var(--color-text)]">Detection Rules</h4>
          <p>
            Rules define conditions that trigger remediation: e.g., "3 consecutive health check
            failures" or "training failure rate above 50% in the last hour."
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Remediation Actions</h4>
          <ul className="ml-4 list-disc space-y-1">
            <li><strong>Restart</strong>: Restart the provider process</li>
            <li><strong>Fallback</strong>: Route requests to an alternative provider</li>
            <li><strong>Alert</strong>: Send webhook notification (no auto-fix)</li>
            <li><strong>Throttle</strong>: Reduce request rate to an overwhelmed provider</li>
          </ul>
          <h4 className="font-semibold text-[var(--color-text)]">MCP Bridge</h4>
          <p>
            The self-healing system is accessible via the MCP server, allowing AI agents to
            query health status, review incidents, and trigger manual remediations.
          </p>
          <h4 className="font-semibold text-[var(--color-text)]">Incident Log</h4>
          <p>
            All detected issues and remediation actions are logged with timestamps, severity,
            and outcomes. The log is searchable and exportable for post-incident review.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Docs Page */}
      <CollapsiblePanel
        title="Docs (Provider Setup Guides)"
        icon={<FileText className="h-4 w-4 text-teal-500" />}
        defaultOpen={false}
        id="guide-docs"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Docs page provides detailed provider-specific setup guides. Each guide walks you
            through creating accounts, obtaining API keys, configuring the provider in Atlas Vox,
            and verifying the integration with a test synthesis.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Help Page */}
      <CollapsiblePanel
        title="Help (This Page)"
        icon={<HelpCircle className="h-4 w-4 text-blue-500" />}
        defaultOpen={false}
        id="guide-help"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            You're looking at it. The Help page is the comprehensive in-app documentation center
            with getting started guides, user guides for every page, step-by-step walkthroughs,
            CLI reference, searchable troubleshooting FAQ, API reference, and project information.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Admin */}
      <CollapsiblePanel
        title="Admin Panel"
        icon={<Wrench className="h-4 w-4 text-orange-500" />}
        defaultOpen={false}
        id="guide-admin"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            The Admin panel provides low-level configuration for providers. It displays provider
            config cards with raw JSON configuration, model paths, and advanced settings not
            exposed in the main Providers page. This is primarily for power users and debugging.
          </p>
        </div>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   TAB: WALKTHROUGHS
   ================================================================ */

function WalkthroughsTab() {
  return (
    <div className="space-y-3">
      <Card>
        <div className="flex items-start gap-3">
          <Footprints className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold">Step-by-Step Tutorials</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Follow these guided walkthroughs to learn key workflows from start to finish.
            </p>
          </div>
        </div>
      </Card>

      {/* Walkthrough 1: First Synthesis */}
      <CollapsiblePanel
        title="Your First Synthesis"
        icon={<Play className="h-4 w-4 text-green-500" />}
        defaultOpen={false}
        id="walk-first-synth"
        badge={<Badge status="ready" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Generate your first speech output in under 2 minutes.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Open the Synthesis Lab</h4>
              <p>Click "Synthesis Lab" in the left sidebar. You'll see a text input area, voice selector, and parameter controls.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Select a voice profile</h4>
              <p>Choose a profile from the dropdown. If you don't have any profiles yet, the default Kokoro voice is available out of the box.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Enter text</h4>
              <p>Type or paste text into the input area. Start with something short like "Hello, welcome to Atlas Vox."</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Adjust parameters (optional)</h4>
              <p>Use the speed, pitch, and volume sliders, or select a persona preset like "Friendly" or "Professional."</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={5} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Click Synthesize and listen</h4>
              <p>Click the Synthesize button. The waveform player will appear with your generated audio. Click the waveform to play.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 2: Cloning a Voice */}
      <CollapsiblePanel
        title="Cloning a Voice"
        icon={<Mic className="h-4 w-4 text-red-500" />}
        defaultOpen={false}
        id="walk-clone"
        badge={<Badge status="training" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Clone a voice from your own audio samples using the training pipeline.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Create a voice profile</h4>
              <p>Go to Voice Profiles, click "New Profile." Select a cloning-capable provider (Coqui XTTS, ElevenLabs, or StyleTTS2). Name it descriptively.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Upload audio samples</h4>
              <p>Navigate to Training Studio, select your profile. Upload WAV/MP3 files of the target voice, or record directly in the browser. Aim for 1-5 minutes of clear speech.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Preprocess the audio</h4>
              <p>Click "Preprocess All." This applies noise reduction, normalization, and silence trimming. Wait for all samples to show a green checkmark.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Start training</h4>
              <p>Click "Start Training." The job enters the Celery queue. Monitor progress in real time via the WebSocket-powered progress bar.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={5} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Synthesize with your clone</h4>
              <p>Once training completes (profile status changes to "ready"), go to Synthesis Lab, select your trained profile, and generate speech with your cloned voice.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 3: Comparing Voices */}
      <CollapsiblePanel
        title="Comparing Voices Side-by-Side"
        icon={<BarChart3 className="h-4 w-4 text-cyan-500" />}
        defaultOpen={false}
        id="walk-compare"
        badge={<Badge status="pending" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Evaluate multiple voices with the same text to find the best one for your use case.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Open the Comparison page</h4>
              <p>Click "Comparison" in the sidebar.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Enter comparison text</h4>
              <p>Type a representative sentence that tests the qualities you care about (pronunciation, tone, pacing).</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Select 3+ voice profiles</h4>
              <p>Use the multi-select dropdown to choose profiles from different providers. Try mixing cloud and local providers for interesting comparisons.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Run comparison</h4>
              <p>Click "Compare." All selected profiles synthesize simultaneously. Results appear as cards with audio players and latency metrics.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={5} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Evaluate results</h4>
              <p>Listen to each version back-to-back. Compare naturalness, pronunciation accuracy, emotional tone, and synthesis speed (latency).</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 4: Setting Up Azure Speech */}
      <CollapsiblePanel
        title="Setting Up Azure Speech"
        icon={<Cloud className="h-4 w-4 text-blue-500" />}
        defaultOpen={false}
        id="walk-azure"
        badge={<Badge status="cloud" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Configure Azure Cognitive Services Speech for high-quality neural TTS with SSML support.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Create an Azure Speech resource</h4>
              <p>Log in to the Azure Portal. Go to "Create a resource" and search for "Speech." Create a Speech resource in your preferred region.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Copy your key and region</h4>
              <p>In the Speech resource, go to "Keys and Endpoint." Copy Key 1 and the Region value (e.g., "eastus").</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Configure in Atlas Vox</h4>
              <p>Go to Providers, expand "Azure Speech," enter the API Key and Region in the Settings fields, and click Save.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Test the connection</h4>
              <p>Click "Health Check" to verify. Then click "Test Synthesis" to generate a sample. If successful, the provider status will change to healthy.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 5: Setting Up ElevenLabs */}
      <CollapsiblePanel
        title="Setting Up ElevenLabs"
        icon={<Cloud className="h-4 w-4 text-purple-500" />}
        defaultOpen={false}
        id="walk-elevenlabs"
        badge={<Badge status="cloud" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Connect ElevenLabs for premium cloud-based voice synthesis and cloning.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Create an ElevenLabs account</h4>
              <p>Go to elevenlabs.io and sign up. The free tier includes limited characters per month.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Get your API key</h4>
              <p>Go to elevenlabs.io/settings (or Profile Settings). Copy your API key from the "API Keys" section.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Configure in Atlas Vox</h4>
              <p>Go to Providers, expand "ElevenLabs," paste your API key in the Settings field, and click Save.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Verify with test synthesis</h4>
              <p>Click "Health Check" then "Test Synthesis." You should hear a sample generated by ElevenLabs. Your Voice Library will now include ElevenLabs voices.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 6: OpenAI-Compatible API */}
      <CollapsiblePanel
        title="Using the OpenAI-Compatible API"
        icon={<Code2 className="h-4 w-4 text-emerald-500" />}
        defaultOpen={false}
        id="walk-openai"
        badge={<Badge status="ready" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Atlas Vox exposes an OpenAI-compatible endpoint so you can use it as a drop-in replacement for the OpenAI TTS API.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Endpoint URL</h4>
              <p>The OpenAI-compatible endpoint is at:</p>
              <CodeBlock>{`POST http://localhost:8100/v1/audio/speech`}</CodeBlock>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Basic cURL example</h4>
              <CodeBlock title="cURL">{`curl -X POST http://localhost:8100/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "kokoro",
    "input": "Hello from Atlas Vox!",
    "voice": "af_heart"
  }' \\
  --output speech.mp3`}</CodeBlock>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">With OpenAI Python SDK</h4>
              <CodeBlock title="Python">{`from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8100/v1",
    api_key="not-needed"  # if AUTH_DISABLED=true
)

response = client.audio.speech.create(
    model="kokoro",
    voice="af_heart",
    input="Hello from Atlas Vox!"
)
response.stream_to_file("output.mp3")`}</CodeBlock>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Available models</h4>
              <p>The "model" field maps to Atlas Vox provider names: kokoro, piper, elevenlabs, azure_speech, coqui_xtts, styletts2, cosyvoice, dia, dia2.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>

      {/* Walkthrough 7: Customizing the Design */}
      <CollapsiblePanel
        title="Customizing the Design"
        icon={<Palette className="h-4 w-4 text-pink-500" />}
        defaultOpen={false}
        id="walk-design"
        badge={<Badge status="pending" className="text-[10px]" />}
      >
        <div className="space-y-4 text-sm text-[var(--color-text-secondary)]">
          <p>Make Atlas Vox look exactly how you want with the built-in design system.</p>
          <div className="flex items-start gap-4">
            <StepNumber n={1} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Open Design System</h4>
              <p>Click "Design System" in the sidebar. You'll see live-preview controls for every visual token.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={2} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Pick a theme preset</h4>
              <p>Start with a preset (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif) to establish a base look.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={3} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Adjust accent color</h4>
              <p>Use the Hue and Saturation sliders to fine-tune the primary accent color. Changes are reflected instantly across the entire UI.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={4} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Change fonts and density</h4>
              <p>Select a font family (System, Inter, Monospace, Serif), adjust font size, and toggle between compact/normal/spacious density.</p>
            </div>
          </div>
          <div className="flex items-start gap-4">
            <StepNumber n={5} />
            <div className="flex-1">
              <h4 className="font-semibold text-[var(--color-text)]">Verify and save</h4>
              <p>Browse other pages to see your design applied everywhere. Changes persist automatically in local storage -- no save button needed.</p>
            </div>
          </div>
        </div>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   TAB: CLI REFERENCE
   ================================================================ */

function CLIReferenceTab() {
  const commands = [
    {
      name: "atlas-vox init",
      desc: "Initialize a new Atlas Vox project with default configuration",
      syntax: "atlas-vox init [--dir <path>]",
      options: [["--dir", "Target directory (default: current)"]],
      example: "atlas-vox init --dir ./my-project",
    },
    {
      name: "atlas-vox serve",
      desc: "Start the Atlas Vox backend server",
      syntax: "atlas-vox serve [--port <port>] [--host <host>] [--mcp]",
      options: [
        ["--port", "Port number (default: 8100)"],
        ["--host", "Bind address (default: 0.0.0.0)"],
        ["--mcp", "Enable MCP server alongside REST API"],
      ],
      example: "atlas-vox serve --port 9000 --mcp",
    },
    {
      name: "atlas-vox profiles list",
      desc: "List all voice profiles",
      syntax: "atlas-vox profiles list [--provider <name>] [--status <status>]",
      options: [
        ["--provider", "Filter by provider name"],
        ["--status", "Filter by status (pending, training, ready, error, archived)"],
      ],
      example: "atlas-vox profiles list --status ready",
    },
    {
      name: "atlas-vox profiles create",
      desc: "Create a new voice profile",
      syntax: "atlas-vox profiles create <name> --provider <name> [--language <code>]",
      options: [
        ["--provider", "TTS provider (required)"],
        ["--language", "Language code (default: en)"],
      ],
      example: 'atlas-vox profiles create "My Voice" --provider kokoro --language en',
    },
    {
      name: "atlas-vox profiles delete",
      desc: "Delete a voice profile",
      syntax: "atlas-vox profiles delete <profile_id>",
      options: [],
      example: "atlas-vox profiles delete abc-123-def",
    },
    {
      name: "atlas-vox profiles export",
      desc: "Export a voice profile to a file",
      syntax: "atlas-vox profiles export <profile_id> [--output <file>]",
      options: [["--output", "Output file path (default: <name>.json)"]],
      example: "atlas-vox profiles export abc-123 --output my-voice.json",
    },
    {
      name: "atlas-vox profiles import",
      desc: "Import a voice profile from a file",
      syntax: "atlas-vox profiles import <file>",
      options: [],
      example: "atlas-vox profiles import my-voice.json",
    },
    {
      name: "atlas-vox synthesize",
      desc: "Synthesize text to speech",
      syntax: "atlas-vox synthesize <text> --voice <id> --output <file> [--speed <float>] [--format <fmt>]",
      options: [
        ["--voice", "Profile ID or voice name (required)"],
        ["--output", "Output audio file path (required)"],
        ["--speed", "Speech speed multiplier (default: 1.0)"],
        ["--format", "Output format: wav, mp3, ogg (default: wav)"],
      ],
      example: 'atlas-vox synthesize "Hello world" --voice abc-123 --output hello.wav',
    },
    {
      name: "atlas-vox train upload",
      desc: "Upload audio samples for training",
      syntax: "atlas-vox train upload <profile_id> <files...>",
      options: [],
      example: "atlas-vox train upload abc-123 samples/*.wav",
    },
    {
      name: "atlas-vox train start",
      desc: "Start a training job",
      syntax: "atlas-vox train start <profile_id> [--epochs <n>]",
      options: [["--epochs", "Number of training epochs"]],
      example: "atlas-vox train start abc-123 --epochs 100",
    },
    {
      name: "atlas-vox train status",
      desc: "Check training job status",
      syntax: "atlas-vox train status <job_id>",
      options: [],
      example: "atlas-vox train status job-456",
    },
    {
      name: "atlas-vox providers list",
      desc: "List all TTS providers and their status",
      syntax: "atlas-vox providers list",
      options: [],
      example: "atlas-vox providers list",
    },
    {
      name: "atlas-vox providers health",
      desc: "Run health checks on all providers",
      syntax: "atlas-vox providers health [--provider <name>]",
      options: [["--provider", "Check a specific provider only"]],
      example: "atlas-vox providers health --provider kokoro",
    },
    {
      name: "atlas-vox compare",
      desc: "Compare synthesis across multiple voices",
      syntax: "atlas-vox compare <text> --voice <id1> --voice <id2> [--voice <idN>]",
      options: [["--voice", "Profile IDs to compare (at least 2)"]],
      example: 'atlas-vox compare "Test phrase" --voice abc-123 --voice def-456 --voice ghi-789',
    },
    {
      name: "atlas-vox presets list",
      desc: "List available persona presets",
      syntax: "atlas-vox presets list",
      options: [],
      example: "atlas-vox presets list",
    },
    {
      name: "atlas-vox presets create",
      desc: "Create a custom persona preset",
      syntax: "atlas-vox presets create <name> --speed <float> --pitch <int> --volume <float>",
      options: [
        ["--speed", "Speech speed (0.5-2.0)"],
        ["--pitch", "Pitch adjustment (-10 to +10)"],
        ["--volume", "Volume level (0.0-1.5)"],
      ],
      example: 'atlas-vox presets create "Narrator" --speed 0.9 --pitch -3 --volume 1.1',
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-start gap-3">
          <Terminal className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold">CLI Reference</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Complete command reference for the <InlineCode>atlas-vox</InlineCode> CLI.
              Install with <InlineCode>pip install -e .</InlineCode> from the backend directory.
            </p>
          </div>
        </div>
      </Card>

      {commands.map((cmd) => (
        <CollapsiblePanel
          key={cmd.name}
          title={cmd.name}
          icon={<Terminal className="h-4 w-4 text-gray-500" />}
          defaultOpen={false}
          id={`cli-${cmd.name.replace(/\s+/g, "-")}`}
        >
          <div className="space-y-3 text-sm">
            <p className="text-[var(--color-text-secondary)]">{cmd.desc}</p>
            <div>
              <SectionLabel icon={<Code2 className="h-3.5 w-3.5" />} text="Syntax" />
              <CodeBlock>{cmd.syntax}</CodeBlock>
            </div>
            {cmd.options.length > 0 && (
              <div>
                <SectionLabel icon={<Settings className="h-3.5 w-3.5" />} text="Options" />
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--color-border)] text-left">
                        <th className="pb-2 font-medium">Flag</th>
                        <th className="pb-2 font-medium">Description</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cmd.options.map(([flag, desc]) => (
                        <tr key={flag} className="border-b border-[var(--color-border)] last:border-0">
                          <td className="py-1.5"><InlineCode>{flag}</InlineCode></td>
                          <td className="py-1.5 text-[var(--color-text-secondary)]">{desc}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
            <div>
              <SectionLabel icon={<Play className="h-3.5 w-3.5" />} text="Example" />
              <CodeBlock>{cmd.example}</CodeBlock>
            </div>
          </div>
        </CollapsiblePanel>
      ))}
    </div>
  );
}

/* ================================================================
   TAB: TROUBLESHOOTING
   ================================================================ */

function TroubleshootingTab() {
  const [searchTerm, setSearchTerm] = useState("");
  const [openFaqs, setOpenFaqs] = useState<Set<number>>(new Set());
  const [categoryFilter, setCategoryFilter] = useState<string>("All");

  const categories = useMemo(() => {
    const cats = new Set(FAQ_ITEMS.map((i) => i.category));
    return ["All", ...Array.from(cats)];
  }, []);

  const filteredFaqs = useMemo(() => {
    let items = FAQ_ITEMS;
    if (categoryFilter !== "All") {
      items = items.filter((i) => i.category === categoryFilter);
    }
    if (searchTerm.trim()) {
      const lower = searchTerm.toLowerCase();
      items = items.filter(
        (i) =>
          i.question.toLowerCase().includes(lower) ||
          i.answer.toLowerCase().includes(lower) ||
          i.category.toLowerCase().includes(lower)
      );
    }
    return items;
  }, [searchTerm, categoryFilter]);

  const toggleFaq = (index: number) => {
    setOpenFaqs((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const severityIcon = (s: "easy" | "moderate" | "complex") => {
    if (s === "easy") return <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />;
    if (s === "moderate") return <AlertCircle className="h-4 w-4 text-yellow-500 shrink-0" />;
    return <XCircle className="h-4 w-4 text-red-500 shrink-0" />;
  };

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex items-start gap-3">
          <AlertTriangle className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
          <div>
            <h2 className="text-lg font-semibold">Troubleshooting FAQ</h2>
            <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
              Search {FAQ_ITEMS.length} common issues across {categories.length - 1} categories.
              Severity:{" "}
              <span className="inline-flex items-center gap-1"><CheckCircle2 className="h-3 w-3 text-green-500" /> Easy fix</span>{" | "}
              <span className="inline-flex items-center gap-1"><AlertCircle className="h-3 w-3 text-yellow-500" /> Moderate</span>{" | "}
              <span className="inline-flex items-center gap-1"><XCircle className="h-3 w-3 text-red-500" /> Complex</span>
            </p>
          </div>
        </div>
      </Card>

      {/* Search + Filter */}
      <div className="flex flex-col gap-3 sm:flex-row">
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
        <div className="flex gap-1 overflow-x-auto">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium transition-colors ${
                categoryFilter === cat
                  ? "bg-primary-500 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* FAQ Items */}
      {filteredFaqs.length === 0 ? (
        <Card className="py-8 text-center">
          <p className="text-[var(--color-text-secondary)]">No matching troubleshooting topics found.</p>
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredFaqs.map((item) => {
            const globalIndex = FAQ_ITEMS.indexOf(item);
            const isOpen = openFaqs.has(globalIndex);
            return (
              <div
                key={globalIndex}
                className="rounded-lg border border-[var(--color-border)] transition-colors hover:border-primary-300 dark:hover:border-primary-700"
              >
                <button
                  onClick={() => toggleFaq(globalIndex)}
                  className="flex w-full items-center justify-between p-4 text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {severityIcon(item.severity)}
                    <div className="min-w-0">
                      <span className="font-medium block truncate sm:whitespace-normal">{item.question}</span>
                      <span className="text-xs text-[var(--color-text-secondary)]">{item.category}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <SeverityBadge severity={item.severity} />
                    {isOpen ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </div>
                </button>
                {isOpen && (
                  <div className="border-t border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-text-secondary)] whitespace-pre-line">
                    {item.answer}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   TAB: API REFERENCE
   ================================================================ */

function APIReferenceTab() {
  const endpoints = [
    {
      title: "Health Check",
      method: "GET",
      path: "/api/v1/health",
      desc: "Check system health including database, Redis, and storage status.",
      body: null,
      response: `{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "redis": "ok",
    "storage": "ok"
  },
  "version": "0.1.0"
}`,
    },
    {
      title: "List Profiles",
      method: "GET",
      path: "/api/v1/profiles",
      desc: "Retrieve all voice profiles with optional filtering.",
      body: null,
      response: `{
  "profiles": [
    {
      "id": "abc-123",
      "name": "My Voice",
      "provider_name": "kokoro",
      "status": "ready",
      "language": "en"
    }
  ],
  "count": 1
}`,
    },
    {
      title: "Create Profile",
      method: "POST",
      path: "/api/v1/profiles",
      desc: "Create a new voice profile.",
      body: `{
  "name": "My Voice",
  "provider_name": "kokoro",
  "language": "en"
}`,
      response: `{
  "id": "abc-123",
  "name": "My Voice",
  "provider_name": "kokoro",
  "status": "pending",
  "language": "en",
  "created_at": "2025-01-01T00:00:00Z"
}`,
    },
    {
      title: "Synthesize Speech",
      method: "POST",
      path: "/api/v1/synthesize",
      desc: "Generate speech from text using a voice profile.",
      body: `{
  "text": "Hello world!",
  "profile_id": "abc-123",
  "speed": 1.0,
  "pitch": 0,
  "output_format": "wav"
}`,
      response: `{
  "audio_url": "/api/v1/audio/output_abc123.wav",
  "latency_ms": 89,
  "provider": "kokoro",
  "format": "wav"
}`,
    },
    {
      title: "List Providers",
      method: "GET",
      path: "/api/v1/providers",
      desc: "List all TTS providers with capabilities and health status.",
      body: null,
      response: `{
  "providers": [
    {
      "name": "kokoro",
      "display_name": "Kokoro TTS",
      "type": "local",
      "healthy": true,
      "capabilities": {
        "streaming": false,
        "ssml": false,
        "voice_cloning": false
      }
    }
  ],
  "count": 9
}`,
    },
    {
      title: "List Voices",
      method: "GET",
      path: "/api/v1/voices",
      desc: "List all available voices across providers.",
      body: null,
      response: `{
  "voices": [
    {
      "id": "af_heart",
      "name": "Heart",
      "provider": "kokoro",
      "language": "en",
      "gender": "female"
    }
  ],
  "count": 458
}`,
    },
    {
      title: "Compare Voices",
      method: "POST",
      path: "/api/v1/compare",
      desc: "Synthesize text with multiple profiles for side-by-side comparison.",
      body: `{
  "text": "Test phrase for comparison",
  "profile_ids": ["id1", "id2", "id3"]
}`,
      response: `{
  "text": "Test phrase for comparison",
  "results": [
    {
      "profile_id": "id1",
      "audio_url": "/api/v1/audio/cmp_1.wav",
      "latency_ms": 92
    }
  ]
}`,
    },
    {
      title: "Upload Audio Sample",
      method: "POST",
      path: "/api/v1/samples/upload",
      desc: "Upload audio samples for voice training (multipart/form-data).",
      body: `Content-Type: multipart/form-data
Fields: profile_id, file (audio file)`,
      response: `{
  "id": "sample-789",
  "profile_id": "abc-123",
  "filename": "recording.wav",
  "duration_seconds": 12.5,
  "status": "uploaded"
}`,
    },
    {
      title: "Start Training",
      method: "POST",
      path: "/api/v1/training/start",
      desc: "Start a voice training job for a profile.",
      body: `{
  "profile_id": "abc-123",
  "config": {
    "epochs": 100
  }
}`,
      response: `{
  "job_id": "job-456",
  "profile_id": "abc-123",
  "status": "queued",
  "created_at": "2025-01-01T00:00:00Z"
}`,
    },
    {
      title: "OpenAI-Compatible TTS",
      method: "POST",
      path: "/v1/audio/speech",
      desc: "OpenAI-compatible text-to-speech endpoint. Drop-in replacement for the OpenAI TTS API.",
      body: `{
  "model": "kokoro",
  "input": "Hello from Atlas Vox!",
  "voice": "af_heart",
  "response_format": "mp3",
  "speed": 1.0
}`,
      response: `Binary audio data (Content-Type: audio/mpeg)`,
    },
  ];

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3">
            <Code2 className="mt-0.5 h-5 w-5 text-primary-500 shrink-0" />
            <div>
              <h2 className="text-lg font-semibold">REST API Reference</h2>
              <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                Base URL: <InlineCode>http://localhost:8100</InlineCode>{" "}
                | Auth: <InlineCode>Authorization: Bearer &lt;api_key&gt;</InlineCode>{" "}
                (optional when AUTH_DISABLED=true)
              </p>
            </div>
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

      {/* Rate Limits */}
      <CollapsiblePanel
        title="Rate Limits"
        icon={<Shield className="h-4 w-4 text-amber-500" />}
        defaultOpen={false}
        id="api-ratelimits"
      >
        <div className="overflow-x-auto text-sm">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left">
                <th className="pb-2 font-medium">Endpoint Group</th>
                <th className="pb-2 font-medium">Limit</th>
                <th className="pb-2 font-medium">Window</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[var(--color-border)]"><td className="py-2">Synthesis</td><td className="py-2">10 requests</td><td className="py-2">per minute</td></tr>
              <tr className="border-b border-[var(--color-border)]"><td className="py-2">Training</td><td className="py-2">5 requests</td><td className="py-2">per minute</td></tr>
              <tr className="border-b border-[var(--color-border)]"><td className="py-2">Comparison</td><td className="py-2">5 requests</td><td className="py-2">per minute</td></tr>
              <tr className="border-b border-[var(--color-border)]"><td className="py-2">OpenAI-compatible</td><td className="py-2">20 requests</td><td className="py-2">per minute</td></tr>
              <tr><td className="py-2">Read endpoints</td><td className="py-2">60 requests</td><td className="py-2">per minute</td></tr>
            </tbody>
          </table>
          <p className="mt-2 text-xs text-[var(--color-text-secondary)]">
            Rate-limited responses return HTTP 429 with a Retry-After header.
          </p>
        </div>
      </CollapsiblePanel>

      {/* Endpoints */}
      {endpoints.map((ep) => (
        <CollapsiblePanel
          key={ep.path + ep.method}
          title={ep.title}
          icon={<MethodBadge method={ep.method} />}
          defaultOpen={false}
          id={`api-${ep.title.replace(/\s+/g, "-").toLowerCase()}`}
          badge={
            <code className="text-xs font-medium text-[var(--color-text-secondary)]">
              {ep.path}
            </code>
          }
        >
          <div className="space-y-3 text-sm">
            <p className="text-[var(--color-text-secondary)]">{ep.desc}</p>
            <div className="flex items-center gap-2">
              <MethodBadge method={ep.method} />
              <InlineCode>{ep.path}</InlineCode>
            </div>
            {ep.body && (
              <div>
                <p className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">Request body:</p>
                <CodeBlock>{ep.body}</CodeBlock>
              </div>
            )}
            <div>
              <p className="text-xs font-medium text-[var(--color-text-secondary)] mb-1">Response:</p>
              <CodeBlock>{ep.response}</CodeBlock>
            </div>
          </div>
        </CollapsiblePanel>
      ))}

      {/* OpenAI Compatibility */}
      <CollapsiblePanel
        title="OpenAI API Compatibility"
        icon={<Globe className="h-4 w-4 text-emerald-500" />}
        defaultOpen={false}
        id="api-openai-compat"
      >
        <div className="space-y-3 text-sm text-[var(--color-text-secondary)]">
          <p>
            Atlas Vox implements the OpenAI <InlineCode>/v1/audio/speech</InlineCode> endpoint,
            making it a drop-in replacement for the OpenAI TTS API. Use any OpenAI SDK by pointing
            it at your Atlas Vox instance.
          </p>
          <CodeBlock title="cURL example">{`curl -X POST http://localhost:8100/v1/audio/speech \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer avx_your_key_here" \\
  -d '{
    "model": "kokoro",
    "input": "Atlas Vox speaks!",
    "voice": "af_heart",
    "response_format": "mp3",
    "speed": 1.0
  }' \\
  --output speech.mp3`}</CodeBlock>
          <h4 className="font-semibold text-[var(--color-text)]">Model mapping</h4>
          <p>
            The <InlineCode>model</InlineCode> field maps to Atlas Vox providers:{" "}
            kokoro, piper, elevenlabs, azure_speech, coqui_xtts, styletts2, cosyvoice, dia, dia2.
          </p>
        </div>
      </CollapsiblePanel>
    </div>
  );
}

/* ================================================================
   TAB: ABOUT
   ================================================================ */

function AboutTab() {
  return (
    <div className="space-y-4">
      {/* Version Info */}
      <Card>
        <h2 className="mb-4 text-lg font-semibold flex items-center gap-2">
          <Info className="h-5 w-5 text-primary-500" />
          About Atlas Vox
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <tbody>
              {[
                ["Version", "0.1.0"],
                ["TTS Providers", "9"],
                ["Interfaces", "Web UI, REST API, CLI, MCP Server"],
                ["Backend", "Python 3.11 + FastAPI + SQLAlchemy + Celery"],
                ["Frontend", "React 18 + TypeScript 5 + Vite + Tailwind CSS"],
                ["State Management", "Zustand"],
                ["Audio Visualization", "wavesurfer.js"],
                ["SSML Editor", "Monaco Editor"],
                ["Database", "SQLite (dev) / PostgreSQL (prod)"],
                ["Task Queue", "Celery + Redis"],
                ["Logging", "structlog (JSON format)"],
                ["License", "MIT"],
              ].map(([label, value]) => (
                <tr key={label} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2.5 text-[var(--color-text-secondary)] w-1/3">{label}</td>
                  <td className="py-2.5 font-medium">{value}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Provider Comparison */}
      <CollapsiblePanel
        title="Provider Comparison"
        icon={<Cpu className="h-4 w-4 text-indigo-500" />}
        defaultOpen={true}
        id="about-providers"
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 font-medium">Provider</th>
                <th className="pb-2 font-medium">Type</th>
                <th className="pb-2 font-medium">Cloning</th>
                <th className="pb-2 font-medium">Streaming</th>
                <th className="pb-2 font-medium">SSML</th>
                <th className="pb-2 font-medium">GPU</th>
                <th className="pb-2 font-medium">Languages</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: "Kokoro", type: "local", clone: false, stream: false, ssml: false, gpu: "No (CPU)", langs: "English, Japanese" },
                { name: "Piper", type: "local", clone: false, stream: false, ssml: false, gpu: "No (CPU)", langs: "20+ languages" },
                { name: "ElevenLabs", type: "cloud", clone: true, stream: true, ssml: false, gpu: "N/A (cloud)", langs: "29 languages" },
                { name: "Azure Speech", type: "cloud", clone: false, stream: true, ssml: true, gpu: "N/A (cloud)", langs: "140+ languages" },
                { name: "Coqui XTTS v2", type: "gpu", clone: true, stream: true, ssml: false, gpu: "Configurable", langs: "17 languages" },
                { name: "StyleTTS2", type: "gpu", clone: true, stream: false, ssml: false, gpu: "Configurable", langs: "English" },
                { name: "CosyVoice", type: "gpu", clone: true, stream: true, ssml: false, gpu: "Configurable", langs: "Chinese, English, Japanese, Korean" },
                { name: "Dia", type: "gpu", clone: false, stream: false, ssml: false, gpu: "Configurable", langs: "English" },
                { name: "Dia2", type: "gpu", clone: false, stream: true, ssml: false, gpu: "Configurable", langs: "English" },
              ].map((p) => (
                <tr key={p.name} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 font-medium">{p.name}</td>
                  <td className="py-2"><Badge status={p.type} className="text-[10px]" /></td>
                  <td className="py-2">
                    {p.clone ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-gray-400" />
                    )}
                  </td>
                  <td className="py-2">
                    {p.stream ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-gray-400" />
                    )}
                  </td>
                  <td className="py-2">
                    {p.ssml ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-gray-400" />
                    )}
                  </td>
                  <td className="py-2 text-xs">{p.gpu}</td>
                  <td className="py-2 text-xs">{p.langs}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CollapsiblePanel>

      {/* Documentation Links */}
      <Card>
        <h3 className="mb-3 text-lg font-semibold flex items-center gap-2">
          <ExternalLink className="h-5 w-5 text-primary-500" />
          Documentation Links
        </h3>
        <div className="space-y-2">
          {[
            { label: "Swagger API Docs", href: "/docs", desc: "Interactive API explorer" },
            { label: "ReDoc API Reference", href: "/redoc", desc: "Clean API documentation" },
            { label: "GitHub Repository", href: "https://github.com/HouseGarofalo/atlas-vox", desc: "Source code and issues" },
          ].map((link) => (
            <a
              key={link.label}
              href={link.href}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between rounded-lg border border-[var(--color-border)] p-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <div>
                <span className="font-medium">{link.label}</span>
                <span className="ml-2 text-xs text-[var(--color-text-secondary)]">{link.desc}</span>
              </div>
              <ExternalLink className="h-4 w-4 text-[var(--color-text-secondary)] shrink-0" />
            </a>
          ))}
        </div>
      </Card>
    </div>
  );
}

/* ================================================================
   MAIN PAGE COMPONENT
   ================================================================ */

// Need these two icons for the FAQ chevrons (used in TroubleshootingTab inline)
import { ChevronDown, ChevronRight } from "lucide-react";

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Getting Started");

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Documentation Center</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Guides, tutorials, CLI reference, troubleshooting, and API documentation for Atlas Vox
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-sidebar)] p-1">
        {TABS.map((tab) => (
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
            {TAB_ICONS[tab]}
            <span className="hidden sm:inline">{tab}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Getting Started" && <GettingStartedTab />}
      {activeTab === "User Guide" && <UserGuideTab />}
      {activeTab === "Walkthroughs" && <WalkthroughsTab />}
      {activeTab === "CLI Reference" && <CLIReferenceTab />}
      {activeTab === "Troubleshooting" && <TroubleshootingTab />}
      {activeTab === "API Reference" && <APIReferenceTab />}
      {activeTab === "About" && <AboutTab />}
    </div>
  );
}
