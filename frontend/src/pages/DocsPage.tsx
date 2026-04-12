import { useState, useMemo } from "react";
import {
  BookOpen,
  Rocket,
  Footprints,
  Terminal,
  Code2,
  Settings,
  Layers,
  Plug,
  ShieldCheck,
  Server,
  Wrench,
  Info,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { Select } from "../components/ui/Select";
import MarkdownRenderer from "../components/docs/MarkdownRenderer";
import { useMarkdown } from "../hooks/useMarkdown";
import { createLogger } from "../utils/logger";

const logger = createLogger("DocsPage");

/* ================================================================
   Tab & group definitions
   ================================================================ */

interface TabDef {
  key: string;
  label: string;
  icon: typeof BookOpen;
  group: "guide" | "reference" | "technical" | "support";
  /** Path to the markdown file in public/docs/ */
  mdPath: string;
  /** If true, this tab has interactive features beyond pure markdown */
  interactive?: boolean;
}

const TABS: TabDef[] = [
  { key: "getting-started", label: "Getting Started", icon: Rocket, group: "guide", mdPath: "/docs/getting-started.md" },
  { key: "user-guide", label: "User Guide", icon: BookOpen, group: "guide", mdPath: "/docs/user-guide.md" },
  { key: "walkthroughs", label: "Walkthroughs", icon: Footprints, group: "guide", mdPath: "/docs/walkthroughs.md" },
  { key: "cli", label: "CLI", icon: Terminal, group: "reference", mdPath: "/docs/cli.md" },
  { key: "api", label: "API", icon: Code2, group: "reference", mdPath: "/docs/api.md" },
  { key: "providers", label: "Providers", icon: Settings, group: "reference", mdPath: "/docs/providers/index.md", interactive: true },
  { key: "architecture", label: "Architecture", icon: Layers, group: "technical", mdPath: "/docs/architecture.md" },
  { key: "configuration", label: "Configuration", icon: Settings, group: "technical", mdPath: "/docs/configuration.md" },
  { key: "mcp", label: "MCP", icon: Plug, group: "technical", mdPath: "/docs/mcp.md" },
  { key: "self-healing", label: "Self-Healing", icon: ShieldCheck, group: "technical", mdPath: "/docs/self-healing.md" },
  { key: "deployment", label: "Deployment", icon: Server, group: "technical", mdPath: "/docs/deployment.md" },
  { key: "troubleshooting", label: "Troubleshooting", icon: Wrench, group: "support", mdPath: "/docs/troubleshooting.md" },
  { key: "about", label: "About", icon: Info, group: "support", mdPath: "/docs/about.md" },
];

const GROUPS = [
  { key: "guide" as const, label: "Guide" },
  { key: "reference" as const, label: "Reference" },
  { key: "technical" as const, label: "Technical" },
  { key: "support" as const, label: "Support" },
];

const PROVIDER_NAMES = [
  { value: "kokoro", label: "Kokoro" },
  { value: "piper", label: "Piper" },
  { value: "elevenlabs", label: "ElevenLabs" },
  { value: "azure_speech", label: "Azure AI Speech" },
  { value: "coqui_xtts", label: "Coqui XTTS v2" },
  { value: "styletts2", label: "StyleTTS2" },
  { value: "cosyvoice", label: "CosyVoice" },
  { value: "dia", label: "Dia" },
  { value: "dia2", label: "Dia2" },
];

/* ================================================================
   Markdown tab — pure markdown render with loading state
   ================================================================ */

function MarkdownTab({ path }: { path: string }) {
  const { content, loading, error } = useMarkdown(path);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-16">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        <span className="ml-3 text-[var(--color-text-secondary)]">Loading documentation...</span>
      </div>
    );
  }

  if (error || !content) {
    return (
      <Card className="p-8 text-center">
        <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-3" />
        <p className="text-[var(--color-text-secondary)]">
          {error || "Documentation not available."}
        </p>
      </Card>
    );
  }

  return <MarkdownRenderer content={content} />;
}

/* ================================================================
   Provider Guides tab — interactive wrapper with provider selector
   ================================================================ */

function ProviderGuidesTab() {
  const [selectedProvider, setSelectedProvider] = useState("kokoro");
  const indexMd = useMarkdown("/docs/providers/index.md");
  const providerMd = useMarkdown(`/docs/providers/${selectedProvider}.md`);

  return (
    <div className="space-y-6">
      {/* Provider overview */}
      {indexMd.content && (
        <MarkdownRenderer content={indexMd.content} />
      )}

      {/* Provider selector */}
      <Card className="p-4">
        <Select
          label="Select Provider"
          value={selectedProvider}
          onChange={(e) => {
            setSelectedProvider(e.target.value);
            logger.info("provider_doc_selected", { provider: e.target.value });
          }}
          options={PROVIDER_NAMES}
        />
      </Card>

      {/* Selected provider guide */}
      {providerMd.loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
        </div>
      ) : providerMd.content ? (
        <MarkdownRenderer content={providerMd.content} />
      ) : null}
    </div>
  );
}

/* ================================================================
   Main DocsPage component
   ================================================================ */

export default function DocsPage() {
  const [activeGroup, setActiveGroup] = useState<"guide" | "reference" | "technical" | "support">("guide");
  const [activeTab, setActiveTab] = useState("getting-started");

  const visibleTabs = useMemo(
    () => TABS.filter((t) => t.group === activeGroup),
    [activeGroup],
  );

  const currentTab = TABS.find((t) => t.key === activeTab);

  const handleGroupChange = (group: typeof activeGroup) => {
    setActiveGroup(group);
    // Select first tab in the new group
    const firstTab = TABS.find((t) => t.group === group);
    if (firstTab) setActiveTab(firstTab.key);
  };

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-display font-bold text-[var(--color-text)]">
          Documentation
        </h1>
        <p className="text-[var(--color-text-secondary)] mt-2">
          Guides, references, and technical documentation for Atlas Vox.
        </p>
      </div>

      {/* Group Selector */}
      <div className="flex items-center gap-2">
        {GROUPS.map((g) => (
          <button
            key={g.key}
            onClick={() => handleGroupChange(g.key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
              activeGroup === g.key
                ? "bg-primary-500 text-white shadow-lg"
                : "bg-[var(--color-bg-secondary)] text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-tertiary)]"
            }`}
          >
            {g.label}
          </button>
        ))}
      </div>

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-[var(--color-border)] pb-1 overflow-x-auto">
        {visibleTabs.map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-t-lg transition-all duration-200 ${
                activeTab === tab.key
                  ? "bg-[var(--color-bg-secondary)] text-primary-500 border-b-2 border-primary-500"
                  : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)] hover:bg-[var(--color-bg-secondary)]"
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Content Area */}
      <div className="min-h-[400px]">
        {currentTab?.key === "providers" ? (
          <ProviderGuidesTab />
        ) : currentTab ? (
          <MarkdownTab path={currentTab.mdPath} />
        ) : null}
      </div>
    </div>
  );
}
