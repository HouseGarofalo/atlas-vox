import { useCallback } from "react";
import { Palette, Type, Layout, Square, Sparkles, RotateCcw, Monitor, Smartphone, Tablet } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { Slider } from "../components/ui/Slider";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useDesignStore, type DesignTokens } from "../stores/designStore";
import { useSettingsStore } from "../stores/settingsStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("DesignSystemPage");

const PRESET_THEMES: { name: string; tokens: Partial<DesignTokens> }[] = [
  {
    name: "Default Blue",
    tokens: { accentHue: 217, accentSaturation: 91, borderRadius: "lg", fontFamily: "system", fontSize: "default", density: "default", cardStyle: "bordered" },
  },
  {
    name: "Emerald",
    tokens: { accentHue: 160, accentSaturation: 84, borderRadius: "lg", fontFamily: "system", cardStyle: "bordered" },
  },
  {
    name: "Violet",
    tokens: { accentHue: 270, accentSaturation: 76, borderRadius: "xl", fontFamily: "system", cardStyle: "glass" },
  },
  {
    name: "Sunset",
    tokens: { accentHue: 25, accentSaturation: 95, borderRadius: "md", fontFamily: "system", cardStyle: "raised" },
  },
  {
    name: "Rose",
    tokens: { accentHue: 340, accentSaturation: 82, borderRadius: "lg", fontFamily: "inter", cardStyle: "bordered" },
  },
  {
    name: "Mono",
    tokens: { accentHue: 220, accentSaturation: 10, borderRadius: "sm", fontFamily: "mono", fontSize: "compact", density: "compact", cardStyle: "flat" },
  },
  {
    name: "Minimal",
    tokens: { accentHue: 0, accentSaturation: 0, borderRadius: "none", fontFamily: "system", cardStyle: "flat", density: "compact" },
  },
  {
    name: "Spacious Serif",
    tokens: { accentHue: 30, accentSaturation: 60, borderRadius: "md", fontFamily: "serif", fontSize: "large", density: "spacious", cardStyle: "raised" },
  },
];

export default function DesignSystemPage() {
  const { tokens, setToken, setTokens, resetTokens } = useDesignStore();
  const { theme, toggleTheme } = useSettingsStore();

  const applyPreset = useCallback(
    (preset: (typeof PRESET_THEMES)[number]) => {
      logger.info("preset_apply", { name: preset.name });
      setTokens(preset.tokens);
    },
    [setTokens]
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Design System</h1>
          <p className="text-sm text-[var(--color-text-secondary)] mt-1">
            Customize the look and feel of Atlas Vox in real time
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={resetTokens}>
            <RotateCcw className="h-4 w-4" /> Reset
          </Button>
        </div>
      </div>

      {/* Theme Presets */}
      <CollapsiblePanel
        title="Theme Presets"
        icon={<Sparkles className="h-4 w-4 text-yellow-500" />}
        id="design-presets"
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {PRESET_THEMES.map((preset) => (
            <button
              key={preset.name}
              onClick={() => applyPreset(preset)}
              className="group relative flex flex-col items-center gap-2 rounded-[var(--radius)] border border-[var(--color-border)] p-3 sm:p-4 text-center transition-all hover:border-[var(--accent-500)] hover:shadow-md"
            >
              {/* Color preview swatch */}
              <div className="flex gap-1">
                <div
                  className="h-6 w-6 rounded-full border border-white/20 shadow-sm"
                  style={{ background: `hsl(${preset.tokens.accentHue ?? 217}, ${preset.tokens.accentSaturation ?? 91}%, 52%)` }}
                />
                <div
                  className="h-6 w-6 rounded-full border border-white/20 shadow-sm"
                  style={{ background: `hsl(${preset.tokens.accentHue ?? 217}, ${preset.tokens.accentSaturation ?? 91}%, 35%)` }}
                />
              </div>
              <span className="text-xs font-medium">{preset.name}</span>
            </button>
          ))}
        </div>
      </CollapsiblePanel>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Color */}
        <CollapsiblePanel
          title="Colors"
          icon={<Palette className="h-4 w-4 text-pink-500" />}
          id="design-colors"
        >
          <div className="space-y-5">
            {/* Dark/Light mode */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Color Mode</p>
                <p className="text-xs text-[var(--color-text-secondary)]">{theme === "dark" ? "Dark" : "Light"} mode</p>
              </div>
              <div className="flex gap-1 rounded-lg border border-[var(--color-border)] p-0.5">
                <button
                  onClick={() => theme === "dark" && toggleTheme()}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${theme === "light" ? "bg-[var(--color-bg-secondary)] shadow-sm" : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"}`}
                >
                  <Monitor className="h-3.5 w-3.5" /> Light
                </button>
                <button
                  onClick={() => theme === "light" && toggleTheme()}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${theme === "dark" ? "bg-[var(--color-bg-secondary)] shadow-sm" : "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"}`}
                >
                  <Monitor className="h-3.5 w-3.5" /> Dark
                </button>
              </div>
            </div>

            {/* Accent Hue */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">Accent Color</label>
                <div
                  className="h-6 w-6 rounded-full border-2 border-white shadow-md"
                  style={{ background: `hsl(${tokens.accentHue}, ${tokens.accentSaturation}%, 52%)` }}
                />
              </div>
              <input
                type="range"
                min={0}
                max={360}
                step={1}
                value={tokens.accentHue}
                onChange={(e) => setToken("accentHue", Number(e.target.value))}
                className="w-full h-3 rounded-full cursor-pointer appearance-none"
                style={{
                  background: "linear-gradient(to right, hsl(0,90%,52%), hsl(60,90%,52%), hsl(120,90%,52%), hsl(180,90%,52%), hsl(240,90%,52%), hsl(300,90%,52%), hsl(360,90%,52%))",
                }}
              />
              <p className="text-xs text-[var(--color-text-secondary)]">Hue: {tokens.accentHue}&deg;</p>
            </div>

            {/* Accent Saturation */}
            <Slider
              label="Saturation"
              id="saturation"
              min={0}
              max={100}
              step={1}
              value={tokens.accentSaturation}
              onChange={(e) => setToken("accentSaturation", Number(e.target.value))}
              displayValue={`${tokens.accentSaturation}%`}
            />

            {/* Preview swatches */}
            <div className="space-y-2">
              <p className="text-xs font-medium text-[var(--color-text-secondary)]">Preview</p>
              <div className="flex gap-1 flex-wrap">
                {[50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((shade) => {
                  const l = shade <= 100 ? 97 - (shade / 100) * 4 : shade <= 400 ? 93 - ((shade - 100) / 300) * 29 : shade <= 600 ? 64 - ((shade - 400) / 200) * 20 : 44 - ((shade - 600) / 300) * 20;
                  return (
                    <div
                      key={shade}
                      className="h-8 w-8 rounded-md shadow-sm border border-white/10"
                      style={{ background: `hsl(${tokens.accentHue}, ${tokens.accentSaturation}%, ${l}%)` }}
                      title={`${shade}`}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </CollapsiblePanel>

        {/* Typography */}
        <CollapsiblePanel
          title="Typography"
          icon={<Type className="h-4 w-4 text-blue-500" />}
          id="design-typography"
        >
          <div className="space-y-5">
            <Select
              label="Font Family"
              value={tokens.fontFamily}
              onChange={(e) => setToken("fontFamily", e.target.value as DesignTokens["fontFamily"])}
              options={[
                { value: "system", label: "System Default" },
                { value: "inter", label: "Inter" },
                { value: "mono", label: "Monospace" },
                { value: "serif", label: "Serif" },
              ]}
            />
            <Select
              label="Font Size"
              value={tokens.fontSize}
              onChange={(e) => setToken("fontSize", e.target.value as DesignTokens["fontSize"])}
              options={[
                { value: "compact", label: "Compact (14px)" },
                { value: "default", label: "Default (16px)" },
                { value: "large", label: "Large (18px)" },
              ]}
            />
            {/* Preview */}
            <div className="rounded-[var(--radius)] border border-[var(--color-border)] p-4 space-y-2">
              <p className="text-xs text-[var(--color-text-secondary)]">Preview</p>
              <h3 className="text-lg font-bold">Heading Text</h3>
              <p className="text-sm">Body text looks like this. The quick brown fox jumps over the lazy dog.</p>
              <p className="text-xs text-[var(--color-text-secondary)]">Small caption text for labels and metadata.</p>
            </div>
          </div>
        </CollapsiblePanel>

        {/* Layout & Spacing */}
        <CollapsiblePanel
          title="Layout & Spacing"
          icon={<Layout className="h-4 w-4 text-green-500" />}
          id="design-layout"
        >
          <div className="space-y-5">
            <Select
              label="Density"
              value={tokens.density}
              onChange={(e) => setToken("density", e.target.value as DesignTokens["density"])}
              options={[
                { value: "compact", label: "Compact" },
                { value: "default", label: "Default" },
                { value: "spacious", label: "Spacious" },
              ]}
            />
            <Slider
              label="Sidebar Width"
              id="sidebar-width"
              min={200}
              max={320}
              step={8}
              value={tokens.sidebarWidth}
              onChange={(e) => setToken("sidebarWidth", Number(e.target.value))}
              displayValue={`${tokens.sidebarWidth}px`}
            />
            <Select
              label="Content Max Width"
              value={tokens.contentMaxWidth}
              onChange={(e) => setToken("contentMaxWidth", e.target.value as DesignTokens["contentMaxWidth"])}
              options={[
                { value: "full", label: "Full Width" },
                { value: "6xl", label: "Extra Wide (2048px)" },
                { value: "4xl", label: "Wide (1792px)" },
                { value: "2xl", label: "Medium (1536px)" },
                { value: "xl", label: "Narrow (1280px)" },
              ]}
            />
            {/* Device preview icons */}
            <div className="flex items-center justify-center gap-6 py-3 rounded-[var(--radius)] border border-[var(--color-border)]">
              <div className="flex flex-col items-center gap-1 text-[var(--color-text-secondary)]">
                <Smartphone className="h-5 w-5" />
                <span className="text-[10px]">Mobile</span>
              </div>
              <div className="flex flex-col items-center gap-1 text-[var(--color-text-secondary)]">
                <Tablet className="h-5 w-5" />
                <span className="text-[10px]">Tablet</span>
              </div>
              <div className="flex flex-col items-center gap-1 text-[var(--color-text-secondary)]">
                <Monitor className="h-5 w-5" />
                <span className="text-[10px]">Desktop</span>
              </div>
            </div>
          </div>
        </CollapsiblePanel>

        {/* Components */}
        <CollapsiblePanel
          title="Components"
          icon={<Square className="h-4 w-4 text-orange-500" />}
          id="design-components"
        >
          <div className="space-y-5">
            <Select
              label="Border Radius"
              value={tokens.borderRadius}
              onChange={(e) => setToken("borderRadius", e.target.value as DesignTokens["borderRadius"])}
              options={[
                { value: "none", label: "None (sharp corners)" },
                { value: "sm", label: "Small (4px)" },
                { value: "md", label: "Medium (8px)" },
                { value: "lg", label: "Large (12px)" },
                { value: "xl", label: "Extra Large (16px)" },
                { value: "full", label: "Full (pill shape)" },
              ]}
            />
            <Select
              label="Card Style"
              value={tokens.cardStyle}
              onChange={(e) => setToken("cardStyle", e.target.value as DesignTokens["cardStyle"])}
              options={[
                { value: "bordered", label: "Bordered" },
                { value: "raised", label: "Raised (shadow)" },
                { value: "flat", label: "Flat (no border)" },
                { value: "glass", label: "Glassmorphism" },
              ]}
            />
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Animations</p>
                <p className="text-xs text-[var(--color-text-secondary)]">Enable transitions and animations</p>
              </div>
              <div
                role="switch"
                aria-checked={tokens.animationsEnabled}
                tabIndex={0}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${tokens.animationsEnabled ? "bg-[var(--accent-500)]" : "bg-gray-300 dark:bg-gray-600"}`}
                onClick={() => setToken("animationsEnabled", !tokens.animationsEnabled)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setToken("animationsEnabled", !tokens.animationsEnabled);
                  }
                }}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${tokens.animationsEnabled ? "translate-x-6" : "translate-x-1"}`} />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Panels Default Open</p>
                <p className="text-xs text-[var(--color-text-secondary)]">Start collapsible panels expanded</p>
              </div>
              <div
                role="switch"
                aria-checked={tokens.panelDefaultOpen}
                tabIndex={0}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors cursor-pointer ${tokens.panelDefaultOpen ? "bg-[var(--accent-500)]" : "bg-gray-300 dark:bg-gray-600"}`}
                onClick={() => setToken("panelDefaultOpen", !tokens.panelDefaultOpen)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setToken("panelDefaultOpen", !tokens.panelDefaultOpen);
                  }
                }}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform shadow-sm ${tokens.panelDefaultOpen ? "translate-x-6" : "translate-x-1"}`} />
              </div>
            </div>

            {/* Component preview */}
            <div className="space-y-3">
              <p className="text-xs font-medium text-[var(--color-text-secondary)]">Component Preview</p>
              <div className="flex flex-wrap gap-2">
                <Button size="sm">Primary</Button>
                <Button size="sm" variant="secondary">Secondary</Button>
                <Button size="sm" variant="danger">Danger</Button>
                <Button size="sm" variant="ghost">Ghost</Button>
              </div>
              <input
                type="text"
                placeholder="Input preview..."
                className="h-10 w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)]"
                readOnly
              />
            </div>
          </div>
        </CollapsiblePanel>
      </div>
    </div>
  );
}
