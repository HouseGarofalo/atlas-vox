import { useState, useMemo } from "react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { ChevronDown, ChevronRight, Search, ExternalLink } from "lucide-react";
import { createLogger } from "../utils/logger";

const logger = createLogger("HelpPage");

/* ---------- types ---------- */

interface FaqItem {
  question: string;
  answer: string;
  category: string;
}

/* ---------- data ---------- */

const TABS = ["Getting Started", "User Guide", "Troubleshooting", "API Reference", "About"] as const;
type Tab = (typeof TABS)[number];

const FAQ_ITEMS: FaqItem[] = [
  {
    category: "Installation",
    question: "How do I start Atlas Vox with Docker?",
    answer:
      'Run "make docker-up" from the project root. This starts the backend, frontend, Redis, and a Celery worker. The Web UI is available at http://localhost:3100.',
  },
  {
    category: "Installation",
    question: "Docker build fails during pip install",
    answer:
      'Try rebuilding with no cache: "docker compose -f docker/docker-compose.yml build --no-cache backend". This is usually caused by network issues or PyPI rate limiting.',
  },
  {
    category: "Installation",
    question: "Port 3100 or 8100 is already in use",
    answer:
      "Edit docker/.env and change BACKEND_PORT and FRONTEND_PORT to different values. Then restart with make docker-up.",
  },
  {
    category: "Providers",
    question: "A provider shows as 'unhealthy' on the dashboard",
    answer:
      "Go to the Providers page, expand the provider, and click Health Check to see the specific error. Common causes: missing API key (cloud providers), missing model files (local providers), or GPU not available.",
  },
  {
    category: "Providers",
    question: "How do I configure ElevenLabs?",
    answer:
      'Get your API key from elevenlabs.io/settings. Go to Providers > ElevenLabs > Settings and enter the API key. Click Save, then run a Health Check to verify.',
  },
  {
    category: "Providers",
    question: "How do I configure Azure Speech?",
    answer:
      "Create a Speech resource in the Azure Portal. Copy the Key and Region from Keys and Endpoint. Enter them in Providers > Azure Speech > Settings.",
  },
  {
    category: "Providers",
    question: "How do I enable GPU mode for local providers?",
    answer:
      'Run "make docker-gpu-up" instead of "make docker-up". This starts a GPU worker with CUDA 12.1 and automatically sets GPU mode for Coqui XTTS, StyleTTS2, CosyVoice, Dia, and Dia2.',
  },
  {
    category: "Audio",
    question: "Synthesis succeeds but no audio plays",
    answer:
      "Check the audio URL in the response. Try accessing it directly: http://localhost:8100/api/v1/audio/<filename>. Check browser console for errors. Try WAV format instead of MP3/OGG.",
  },
  {
    category: "Audio",
    question: "Audio upload is rejected as unsupported format",
    answer:
      "Atlas Vox supports WAV, MP3, FLAC, OGG, and M4A formats. Convert your file: ffmpeg -i input.webm output.wav",
  },
  {
    category: "Training",
    question: "Training job stuck at 'queued'",
    answer:
      'This means the Celery worker is not running or not connected to Redis. In Docker, check worker logs: "docker compose -f docker/docker-compose.yml logs worker". For local dev, start a Celery worker manually.',
  },
  {
    category: "Training",
    question: "Training fails immediately",
    answer:
      "Ensure you have uploaded and preprocessed audio samples before starting training. Check the error message in the training job details for the specific cause.",
  },
  {
    category: "Performance",
    question: "Synthesis is very slow (10+ seconds)",
    answer:
      "If using GPU-oriented models (Coqui XTTS, StyleTTS2, Dia) on CPU, performance will be poor. Switch to GPU mode, or use Kokoro/Piper for fast CPU synthesis.",
  },
  {
    category: "Performance",
    question: "GPU memory errors (CUDA out of memory)",
    answer:
      "Dia2 needs 8 GB+ VRAM, Dia needs 6 GB+, Coqui XTTS needs 4 GB+. Close other GPU applications, use shorter text, or switch to CPU mode for that provider.",
  },
  {
    category: "Database",
    question: "Getting 'no such table' errors",
    answer:
      'Run "make migrate" to apply database migrations. For a fresh start, delete atlas_vox.db and restart the backend - tables are created automatically.',
  },
  {
    category: "Performance",
    question: "Getting '429 Too Many Requests' errors",
    answer:
      "Atlas Vox has rate limiting on expensive endpoints: synthesis (10/min), training (5/min), comparison (5/min), OpenAI-compatible (20/min). Wait a minute and try again, or reduce request frequency.",
  },
  {
    category: "Installation",
    question: "Redis connection fails on startup",
    answer:
      "Atlas Vox uses Redis database 1 (redis://localhost:6379/1) to avoid collision with ATLAS on database 0. Ensure Redis is running: 'redis-server' or check Docker. Verify with: python -c \"import redis; redis.Redis(db=1).ping()\"",
  },
  {
    category: "Installation",
    question: "How do I run Atlas Vox alongside ATLAS?",
    answer:
      "Atlas Vox is configured to coexist with ATLAS. It uses port 8100 (ATLAS uses 8000), Redis database 1 (ATLAS uses db0), and a separate SQLite file. Both can run simultaneously with no conflicts.",
  },
];

const GETTING_STARTED_STEPS = [
  {
    step: 1,
    title: "Start Atlas Vox",
    description: "Run the platform with Docker Compose. All dependencies are handled automatically.",
    command: "make docker-up",
    note: "For GPU support: make docker-gpu-up",
  },
  {
    step: 2,
    title: "Open the Web UI",
    description: "Access the dashboard at the default URL.",
    command: "http://localhost:3000 (dev) or http://localhost:3100 (Docker)",
    note: "API docs at http://localhost:8100/docs",
  },
  {
    step: 3,
    title: "Check Provider Health",
    description:
      "Visit the Dashboard to see which providers are healthy. CPU-only providers (Kokoro, Piper) should be green immediately.",
    note: "Cloud providers need API keys configured first",
  },
  {
    step: 4,
    title: "Configure Cloud Providers (Optional)",
    description:
      "If you want to use ElevenLabs or Azure Speech, go to the Providers page and enter your API credentials.",
    note: "Both offer free tiers",
  },
  {
    step: 5,
    title: "Create a Voice Profile",
    description:
      "Go to Voice Profiles and create a new profile. Choose a provider and give it a descriptive name.",
    note: "Or browse the Voice Library to find a voice first",
  },
  {
    step: 6,
    title: "Synthesize Speech",
    description:
      "Go to the Synthesis Lab, select your profile, enter text, and click Synthesize. Listen to the result with the built-in audio player.",
  },
];

const GUIDE_SECTIONS = [
  {
    title: "Dashboard",
    content:
      "The Dashboard shows stats cards (profiles, active jobs, recent syntheses, active providers) and a provider health grid. Active training jobs and recent synthesis history appear below.",
  },
  {
    title: "Voice Library",
    content:
      "Browse all available voices across providers. Filter by provider or language. Click 'Create Profile' on any voice to create a new voice profile with that voice.",
  },
  {
    title: "Voice Profiles",
    content:
      "Profiles are voice identities bound to a provider. Create profiles, upload training samples, and track training versions. Profiles have statuses: pending, training, ready, error, archived.",
  },
  {
    title: "Providers",
    content:
      "View all 9 TTS providers with capabilities, health status, and configuration. Expand a provider to configure API keys, GPU mode, and run test synthesis. Providers: Kokoro (CPU), Piper (CPU), ElevenLabs (cloud), Azure Speech (cloud), Coqui XTTS (GPU), StyleTTS2 (GPU), CosyVoice (GPU), Dia (GPU), Dia2 (GPU).",
  },
  {
    title: "Training Studio",
    content:
      "Upload audio samples (WAV, MP3, FLAC, OGG, M4A) or record directly in the browser. Run preprocessing (noise reduction, normalization) then start training. Progress updates via WebSocket in real-time.",
  },
  {
    title: "Synthesis Lab",
    content:
      "Enter text, select a profile, adjust speed/pitch/volume, and synthesize. Use persona presets (Friendly, Professional, Energetic, Calm, Authoritative, Soothing) for quick parameter tuning. Azure profiles support SSML. Output formats: WAV, MP3, OGG.",
  },
  {
    title: "Comparison",
    content:
      "Synthesize the same text with multiple profiles side-by-side. Useful for A/B testing providers, evaluating training results, or choosing the best voice for a use case.",
  },
  {
    title: "API Keys",
    content:
      "Create scoped API keys for programmatic access. Scopes: read, write, synthesize, train, admin. Keys use the format avx_ + random characters, hashed with Argon2id. When AUTH_DISABLED=true (default), keys are not required.",
  },
  {
    title: "Settings",
    content:
      "Toggle light/dark theme, set default provider and audio format. Preferences persist in browser local storage.",
  },
  {
    title: "Design System",
    content:
      "Customize the look and feel of Atlas Vox in real time. Choose from 8 theme presets (Blue, Emerald, Violet, Sunset, Rose, Mono, Minimal, Spacious Serif) or fine-tune accent color hue/saturation, font family (system, Inter, monospace, serif), font size, density, sidebar width, content max width, border radius, card style (bordered, raised, flat, glassmorphism), and animation toggles. Changes persist across sessions.",
  },
  {
    title: "SSML Editor",
    content:
      "The Synthesis Lab includes a Monaco-based SSML editor. Click 'Switch to SSML' to toggle between plain text and XML SSML mode. SSML is supported by Azure Speech for fine-grained control over pronunciation, pauses, emphasis, and prosody.",
  },
  {
    title: "Waveform Visualization",
    content:
      "Audio playback uses wavesurfer.js for interactive waveform display. Click anywhere on the waveform to seek. The play/pause button and mute controls work alongside the visual timeline.",
  },
];

const API_EXAMPLES = [
  {
    title: "Health Check",
    method: "GET",
    endpoint: "/api/v1/health",
    response: '{ "status": "healthy", "checks": { "database": "ok", "redis": "ok", "storage": "ok" }, "version": "0.1.0" }',
  },
  {
    title: "List Profiles",
    method: "GET",
    endpoint: "/api/v1/profiles",
    response: '{ "profiles": [...], "count": 5 }',
  },
  {
    title: "Create Profile",
    method: "POST",
    endpoint: "/api/v1/profiles",
    body: '{ "name": "My Voice", "provider_name": "kokoro", "language": "en" }',
    response: '{ "id": "abc-123", "name": "My Voice", "status": "pending", ... }',
  },
  {
    title: "Synthesize",
    method: "POST",
    endpoint: "/api/v1/synthesize",
    body: '{ "text": "Hello world!", "profile_id": "abc-123" }',
    response: '{ "audio_url": "/api/v1/audio/out.wav", "latency_ms": 89 }',
  },
  {
    title: "List Providers",
    method: "GET",
    endpoint: "/api/v1/providers",
    response: '{ "providers": [...], "count": 9 }',
  },
  {
    title: "List All Voices",
    method: "GET",
    endpoint: "/api/v1/voices",
    response: '{ "voices": [...], "count": 458 }',
  },
  {
    title: "Compare Voices",
    method: "POST",
    endpoint: "/api/v1/compare",
    body: '{ "text": "Test phrase", "profile_ids": ["id1", "id2"] }',
    response: '{ "text": "Test phrase", "results": [...] }',
  },
];

/* ---------- sub-components ---------- */

function FaqCard({ item, open, onToggle }: { item: FaqItem; open: boolean; onToggle: () => void }) {
  return (
    <div
      className="rounded-lg border border-[var(--color-border)] transition-colors hover:border-primary-300 dark:hover:border-primary-700"
    >
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <Badge status={item.category === "Installation" ? "pending" : item.category === "Providers" ? "cloud" : item.category === "Audio" ? "ready" : item.category === "Training" ? "training" : item.category === "Performance" ? "unhealthy" : "pending"} />
          <span className="font-medium">{item.question}</span>
        </div>
        {open ? <ChevronDown className="h-4 w-4 shrink-0" /> : <ChevronRight className="h-4 w-4 shrink-0" />}
      </button>
      {open && (
        <div className="border-t border-[var(--color-border)] px-4 py-3 text-sm text-[var(--color-text-secondary)]">
          {item.answer}
        </div>
      )}
    </div>
  );
}

/* ---------- page ---------- */

export default function HelpPage() {
  const [activeTab, setActiveTab] = useState<Tab>("Getting Started");
  const [openFaqs, setOpenFaqs] = useState<Set<number>>(new Set());
  const [searchTerm, setSearchTerm] = useState("");

  const filteredFaqs = useMemo(() => {
    if (!searchTerm.trim()) return FAQ_ITEMS;
    const lower = searchTerm.toLowerCase();
    return FAQ_ITEMS.filter(
      (item) =>
        item.question.toLowerCase().includes(lower) ||
        item.answer.toLowerCase().includes(lower) ||
        item.category.toLowerCase().includes(lower)
    );
  }, [searchTerm]);

  const toggleFaq = (index: number) => {
    setOpenFaqs((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Help Center</h1>
        <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
          Guides, troubleshooting, and API reference for Atlas Vox
        </p>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-sidebar)] p-1">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => { logger.info("tab_change", { tab }); setActiveTab(tab); }}
            className={`whitespace-nowrap rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-primary-500 text-white"
                : "text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "Getting Started" && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-2 text-lg font-semibold">Welcome to Atlas Vox</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Atlas Vox is a self-hosted voice training and customization platform with 9 TTS providers,
              4 interfaces (Web UI, API, CLI, MCP), and a complete training pipeline. Follow these steps
              to get up and running.
            </p>
          </Card>

          <div className="space-y-3">
            {GETTING_STARTED_STEPS.map((step) => (
              <Card key={step.step}>
                <div className="flex items-start gap-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-500 text-sm font-bold text-white">
                    {step.step}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold">{step.title}</h3>
                    <p className="mt-1 text-sm text-[var(--color-text-secondary)]">{step.description}</p>
                    {step.command && (
                      <code className="mt-2 block rounded bg-gray-100 px-3 py-2 text-sm dark:bg-gray-800">
                        {step.command}
                      </code>
                    )}
                    {step.note && (
                      <p className="mt-2 text-xs text-[var(--color-text-secondary)] italic">{step.note}</p>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {activeTab === "User Guide" && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-2 text-lg font-semibold">Feature Guide</h2>
            <p className="text-sm text-[var(--color-text-secondary)]">
              Overview of every section in the Atlas Vox interface.
            </p>
          </Card>
          {GUIDE_SECTIONS.map((section) => (
            <Card key={section.title}>
              <h3 className="mb-2 font-semibold">{section.title}</h3>
              <p className="text-sm text-[var(--color-text-secondary)]">{section.content}</p>
            </Card>
          ))}

          <Card>
            <h3 className="mb-2 font-semibold">Persona Presets</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                    <th className="pb-2 font-medium">Preset</th>
                    <th className="pb-2 font-medium">Speed</th>
                    <th className="pb-2 font-medium">Pitch</th>
                    <th className="pb-2 font-medium">Volume</th>
                    <th className="pb-2 font-medium">Character</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: "Friendly", speed: "1.0x", pitch: "+2", volume: "1.0", character: "Warm and approachable" },
                    { name: "Professional", speed: "0.95x", pitch: "0", volume: "1.0", character: "Clear and authoritative" },
                    { name: "Energetic", speed: "1.15x", pitch: "+5", volume: "1.1", character: "Upbeat and enthusiastic" },
                    { name: "Calm", speed: "0.85x", pitch: "-3", volume: "0.9", character: "Soothing and relaxed" },
                    { name: "Authoritative", speed: "0.9x", pitch: "-5", volume: "1.15", character: "Commanding and confident" },
                    { name: "Soothing", speed: "0.8x", pitch: "-2", volume: "0.85", character: "Gentle and comforting" },
                  ].map((p) => (
                    <tr key={p.name} className="border-b border-[var(--color-border)] last:border-0">
                      <td className="py-2 font-medium">{p.name}</td>
                      <td className="py-2">{p.speed}</td>
                      <td className="py-2">{p.pitch}</td>
                      <td className="py-2">{p.volume}</td>
                      <td className="py-2 text-[var(--color-text-secondary)]">{p.character}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}

      {activeTab === "Troubleshooting" && (
        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-text-secondary)]" />
            <input
              type="text"
              placeholder="Search troubleshooting topics..."
              value={searchTerm}
              onChange={(e) => { setSearchTerm(e.target.value); if (e.target.value) logger.debug("faq_search", { term_length: e.target.value.length }); }}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] py-2.5 pl-10 pr-4 text-sm focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            />
          </div>

          {filteredFaqs.length === 0 ? (
            <Card className="py-8 text-center">
              <p className="text-[var(--color-text-secondary)]">No matching troubleshooting topics found.</p>
            </Card>
          ) : (
            <div className="space-y-2">
              {filteredFaqs.map((item, i) => (
                <FaqCard
                  key={i}
                  item={item}
                  open={openFaqs.has(i)}
                  onToggle={() => toggleFaq(i)}
                />
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === "API Reference" && (
        <div className="space-y-4">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold">Interactive API Documentation</h2>
                <p className="mt-1 text-sm text-[var(--color-text-secondary)]">
                  Full Swagger UI and ReDoc available at these URLs.
                </p>
              </div>
              <div className="flex gap-2">
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

          <Card>
            <h2 className="mb-3 text-lg font-semibold">Quick API Examples</h2>
            <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
              Base URL: <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-800">/api/v1</code>
              {" "}| Authentication: Bearer token (optional when AUTH_DISABLED=true)
            </p>
            <div className="space-y-4">
              {API_EXAMPLES.map((ex) => (
                <div key={ex.title} className="rounded-lg border border-[var(--color-border)] p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`rounded px-1.5 py-0.5 text-xs font-bold ${
                      ex.method === "GET"
                        ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                        : "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300"
                    }`}>
                      {ex.method}
                    </span>
                    <code className="text-sm font-medium">{ex.endpoint}</code>
                    <span className="ml-auto text-xs text-[var(--color-text-secondary)]">{ex.title}</span>
                  </div>
                  {ex.body && (
                    <div className="mb-2">
                      <p className="text-xs text-[var(--color-text-secondary)] mb-1">Request body:</p>
                      <pre className="rounded bg-gray-50 p-2 text-xs dark:bg-gray-900 overflow-x-auto">
                        {ex.body}
                      </pre>
                    </div>
                  )}
                  <div>
                    <p className="text-xs text-[var(--color-text-secondary)] mb-1">Response:</p>
                    <pre className="rounded bg-gray-50 p-2 text-xs dark:bg-gray-900 overflow-x-auto">
                      {ex.response}
                    </pre>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === "About" && (
        <div className="space-y-4">
          <Card>
            <h2 className="mb-4 text-lg font-semibold">About Atlas Vox</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">Version</span>
                <span className="font-medium">0.1.0</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">TTS Providers</span>
                <span className="font-medium">9</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">Interfaces</span>
                <span className="font-medium">Web UI, REST API, CLI, MCP Server</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">Backend</span>
                <span className="font-medium">Python 3.11 + FastAPI + SQLAlchemy</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">Frontend</span>
                <span className="font-medium">React 18 + TypeScript + Tailwind CSS</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[var(--color-border)]">
                <span className="text-[var(--color-text-secondary)]">Database</span>
                <span className="font-medium">SQLite (dev) / PostgreSQL (prod)</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-[var(--color-text-secondary)]">License</span>
                <span className="font-medium">MIT</span>
              </div>
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold">Documentation Links</h2>
            <div className="space-y-2">
              {[
                { label: "Swagger API Docs", href: "/docs", external: true },
                { label: "ReDoc API Reference", href: "/redoc", external: true },
                { label: "GitHub Repository", href: "https://github.com/HouseGarofalo/atlas-vox", external: true },
              ].map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  target={link.external ? "_blank" : undefined}
                  rel={link.external ? "noopener noreferrer" : undefined}
                  className="flex items-center justify-between rounded-lg border border-[var(--color-border)] p-3 text-sm hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  <span>{link.label}</span>
                  <ExternalLink className="h-4 w-4 text-[var(--color-text-secondary)]" />
                </a>
              ))}
            </div>
          </Card>

          <Card>
            <h2 className="mb-3 text-lg font-semibold">TTS Providers</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                    <th className="pb-2 font-medium">Provider</th>
                    <th className="pb-2 font-medium">Type</th>
                    <th className="pb-2 font-medium">Model</th>
                    <th className="pb-2 font-medium">Pricing</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    { name: "Kokoro", type: "Local CPU", model: "82M params", pricing: "Open Source" },
                    { name: "Piper", type: "Local CPU", model: "ONNX VITS", pricing: "Open Source" },
                    { name: "ElevenLabs", type: "Cloud", model: "Proprietary", pricing: "Freemium" },
                    { name: "Azure Speech", type: "Cloud", model: "Neural TTS", pricing: "Paid" },
                    { name: "Coqui XTTS v2", type: "Local GPU", model: "~1.5B params", pricing: "Open Source" },
                    { name: "StyleTTS2", type: "Local GPU", model: "~200M params", pricing: "Open Source" },
                    { name: "CosyVoice", type: "Local GPU", model: "300M params", pricing: "Open Source" },
                    { name: "Dia", type: "Local GPU", model: "1.6B params", pricing: "Open Source" },
                    { name: "Dia2", type: "Local GPU", model: "2B params", pricing: "Open Source" },
                  ].map((p) => (
                    <tr key={p.name} className="border-b border-[var(--color-border)] last:border-0">
                      <td className="py-2 font-medium">{p.name}</td>
                      <td className="py-2">{p.type}</td>
                      <td className="py-2">{p.model}</td>
                      <td className="py-2">
                        <Badge status={p.pricing === "Open Source" ? "ready" : p.pricing === "Freemium" ? "pending" : "training"} className="text-[10px]" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
