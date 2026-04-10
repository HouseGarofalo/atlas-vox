import { Palette, Type, Square, Sparkles, RotateCcw, Monitor, Smartphone, Tablet, Radio, Zap } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Select } from "../components/ui/Select";
import { Slider } from "../components/ui/Slider";
import { Card } from "../components/ui/Card";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import AudioReactiveBackground from "../components/audio/AudioReactiveBackground";
import RotaryKnob from "../components/audio/RotaryKnob";
import VUMeter from "../components/audio/VUMeter";
import WaveformVisualizer from "../components/audio/WaveformVisualizer";
import AudioLoadingSpinner from "../components/audio/AudioLoadingSpinner";
import ThemePicker from "../components/theme/ThemePicker";
import { useDesignStore, type DesignTokens } from "../stores/designStore";
import { useSettingsStore } from "../stores/settingsStore";

export default function DesignSystemPage() {
  const { tokens, setToken, resetTokens, getCurrentTheme } = useDesignStore();
  const { theme, toggleTheme } = useSettingsStore();
  const activeTheme = getCurrentTheme();

  return (
    <div className="relative min-h-screen">
      {/* Audio-reactive background */}
      <AudioReactiveBackground intensity="subtle" />

      <div className="relative z-10 space-y-8">
        {/* Studio Header */}
        <div className="flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-display font-bold text-gradient mb-2">
                Design System Console
              </h1>
              <p className="text-[var(--color-text-secondary)] font-medium">
                Real-time interface customization and visual control center
              </p>
            </div>

            <div className="flex items-center gap-4">
              <Card variant="console" className="px-4 py-2">
                <div className="flex items-center gap-3">
                  <Radio className="h-4 w-4 text-secondary-400" />
                  <span className="font-mono text-sm text-white">LIVE</span>
                  <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />
                </div>
              </Card>

              <Button variant="secondary" onClick={resetTokens} audioReactive>
                <RotateCcw className="h-4 w-4" />
                Reset to Defaults
              </Button>
            </div>
          </div>
        </div>

        {/* Theme Library */}
        <CollapsiblePanel
          title="Theme Library"
          icon={<Sparkles className="h-5 w-5 text-secondary-400" />}
          badge={
            <span className="text-xs font-mono text-[var(--color-text-secondary)] px-2 py-0.5 rounded-full bg-primary-500/10 border border-primary-500/20">
              {activeTheme.name}
            </span>
          }
          defaultOpen={true}
        >
          <div className="space-y-6">
            {/* Active theme highlight */}
            <Card variant="console" className="p-4">
              <div className="flex items-center gap-4">
                <div
                  className="h-12 w-12 rounded-xl shadow-lg shrink-0"
                  style={{ background: activeTheme.previewGradient }}
                />
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-mono text-studio-silver uppercase tracking-wider">
                    Currently Active
                  </div>
                  <div className="text-lg font-display font-bold text-white truncate">
                    {activeTheme.name}
                  </div>
                  <div className="text-sm text-studio-silver truncate">
                    {activeTheme.tagline}
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-2">
                  <div className="text-xs font-mono text-studio-silver">MOOD</div>
                  <span
                    className="text-xs font-mono px-2 py-1 rounded-full border border-primary-500/30 text-primary-400"
                  >
                    {activeTheme.mood}
                  </span>
                </div>
              </div>
            </Card>

            <ThemePicker />
          </div>
        </CollapsiblePanel>

        <div className="grid grid-cols-1 gap-8 xl:grid-cols-2">
          {/* Color Control Console */}
          <CollapsiblePanel
            title="Color Mixing Console"
            icon={<Palette className="h-5 w-5 text-primary-400" />}
            defaultOpen={true}
          >
            <Card variant="console" className="p-6 space-y-6">
              {/* Theme Mode Toggle */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">Color Mode</p>
                  <p className="text-xs text-studio-silver font-mono">
                    {theme === "dark" ? "DARK MODE" : "LIGHT MODE"}
                  </p>
                </div>
                <div className="flex gap-1 rounded-xl border border-studio-slate/30 p-1 bg-studio-obsidian/30">
                  <button
                    onClick={() => theme === "dark" && toggleTheme()}
                    className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition-all duration-200 ${
                      theme === "light"
                        ? "bg-secondary-400 text-studio-obsidian shadow-lg"
                        : "text-studio-silver hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <Monitor className="h-3.5 w-3.5" /> Light
                  </button>
                  <button
                    onClick={() => theme === "light" && toggleTheme()}
                    className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition-all duration-200 ${
                      theme === "dark"
                        ? "bg-primary-500 text-white shadow-lg"
                        : "text-studio-silver hover:text-white hover:bg-white/5"
                    }`}
                  >
                    <Monitor className="h-3.5 w-3.5" /> Dark
                  </button>
                </div>
              </div>

              {/* Accent Color Controls */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-white">Primary Accent</label>
                  <div
                    className="h-8 w-8 rounded-full border-2 border-white/20 shadow-lg"
                    style={{
                      background: `hsl(${tokens.accentHue}, ${tokens.accentSaturation}%, 52%)`
                    }}
                  />
                </div>

                {/* Hue slider with rainbow background */}
                <div className="space-y-2">
                  <input
                    type="range"
                    min={0}
                    max={360}
                    step={1}
                    value={tokens.accentHue}
                    onChange={(e) => setToken("accentHue", Number(e.target.value))}
                    className="w-full h-4 rounded-full cursor-pointer appearance-none"
                    style={{
                      background: "linear-gradient(to right, hsl(0,90%,52%), hsl(60,90%,52%), hsl(120,90%,52%), hsl(180,90%,52%), hsl(240,90%,52%), hsl(300,90%,52%), hsl(360,90%,52%))"
                    }}
                  />
                  <div className="flex justify-between text-xs font-mono text-studio-silver">
                    <span>0°</span>
                    <span>{tokens.accentHue}°</span>
                    <span>360°</span>
                  </div>
                </div>

                {/* Saturation control */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-studio-silver uppercase tracking-wider">
                    Saturation
                  </label>
                  <Slider
                    id="saturation"
                    min={0}
                    max={100}
                    step={1}
                    value={tokens.accentSaturation}
                    onChange={(e) => setToken("accentSaturation", Number(e.target.value))}
                    displayValue={`${tokens.accentSaturation}%`}
                    className="bg-studio-obsidian/50"
                  />
                </div>

                {/* Color preview swatches */}
                <div className="space-y-3">
                  <p className="text-xs font-medium text-studio-silver uppercase tracking-wider">
                    Palette Preview
                  </p>
                  <div className="flex gap-1 flex-wrap">
                    {[50, 100, 200, 300, 400, 500, 600, 700, 800, 900].map((shade) => {
                      const l = shade <= 100 ? 97 - (shade / 100) * 4 : shade <= 400 ? 93 - ((shade - 100) / 300) * 29 : shade <= 600 ? 64 - ((shade - 400) / 200) * 20 : 44 - ((shade - 600) / 300) * 20;
                      return (
                        <div
                          key={shade}
                          className="h-10 w-10 rounded-lg shadow-lg border border-white/10 hover:scale-110 transition-transform cursor-pointer"
                          style={{
                            background: `hsl(${tokens.accentHue}, ${tokens.accentSaturation}%, ${l}%)`
                          }}
                          title={`${shade}`}
                        />
                      );
                    })}
                  </div>
                </div>
              </div>
            </Card>
          </CollapsiblePanel>

          {/* Typography & Layout Console */}
          <CollapsiblePanel
            title="Typography & Layout"
            icon={<Type className="h-5 w-5 text-electric-400" />}
            defaultOpen={true}
          >
            <Card variant="console" className="p-6 space-y-6">
              {/* Font Controls */}
              <div className="grid grid-cols-1 gap-4">
                <Select
                  label="Font Family"
                  value={tokens.fontFamily}
                  onChange={(e) => setToken("fontFamily", e.target.value as DesignTokens["fontFamily"])}
                  options={[
                    { value: "system", label: "System Default" },
                    { value: "inter", label: "Inter (Modern)" },
                    { value: "mono", label: "Monospace (Code)" },
                    { value: "serif", label: "Serif (Editorial)" },
                  ]}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />

                <div className="grid grid-cols-2 gap-4">
                  <Select
                    label="Font Size"
                    value={tokens.fontSize}
                    onChange={(e) => setToken("fontSize", e.target.value as DesignTokens["fontSize"])}
                    options={[
                      { value: "compact", label: "Compact (14px)" },
                      { value: "default", label: "Default (16px)" },
                      { value: "large", label: "Large (18px)" },
                    ]}
                    className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                  />

                  <Select
                    label="Density"
                    value={tokens.density}
                    onChange={(e) => setToken("density", e.target.value as DesignTokens["density"])}
                    options={[
                      { value: "compact", label: "Compact" },
                      { value: "default", label: "Default" },
                      { value: "spacious", label: "Spacious" },
                    ]}
                    className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                  />
                </div>
              </div>

              {/* Typography Preview */}
              <div className="rounded-xl border border-studio-slate/20 p-6 bg-studio-charcoal/20 space-y-4">
                <div className="text-xs font-mono text-studio-silver uppercase tracking-wider mb-3">
                  Typography Preview
                </div>
                <h3 className="text-2xl font-display font-bold text-gradient">
                  Studio Heading
                </h3>
                <p className="text-base text-[var(--color-text)]">
                  The audio engineering interface combines precision with creative expression.
                  Every knob, fader, and button serves the pursuit of perfect sound.
                </p>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Technical precision meets artistic vision in the modern digital audio workspace.
                </p>
                <div className="flex items-center gap-3 mt-4">
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)]">
                    SAMPLE RATE: 48kHz | BIT DEPTH: 24-bit | LATENCY: 2.3ms
                  </span>
                </div>
              </div>

              {/* Layout Controls */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-studio-silver uppercase tracking-wider">
                    Sidebar Width
                  </label>
                  <RotaryKnob
                    value={tokens.sidebarWidth}
                    onChange={(value) => setToken("sidebarWidth", value)}
                    min={200}
                    max={320}
                    step={8}
                    label=""
                    colorFrom="hsl(var(--electric-500))"
                    colorTo="hsl(var(--electric-600))"
                    size="sm"
                  />
                  <div className="text-center text-xs font-mono text-studio-silver">
                    {tokens.sidebarWidth}px
                  </div>
                </div>

                <Select
                  label="Content Max Width"
                  value={tokens.contentMaxWidth}
                  onChange={(e) => setToken("contentMaxWidth", e.target.value as DesignTokens["contentMaxWidth"])}
                  options={[
                    { value: "full", label: "Full Width" },
                    { value: "6xl", label: "Extra Wide" },
                    { value: "4xl", label: "Wide" },
                    { value: "2xl", label: "Medium" },
                    { value: "xl", label: "Narrow" },
                  ]}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />
              </div>

              {/* Device Preview */}
              <div className="flex items-center justify-center gap-8 py-6 rounded-xl border border-studio-slate/20 bg-studio-obsidian/20">
                <div className="flex flex-col items-center gap-2 text-studio-silver transition-colors hover:text-white">
                  <Smartphone className="h-6 w-6" />
                  <span className="text-xs font-mono">MOBILE</span>
                </div>
                <div className="flex flex-col items-center gap-2 text-studio-silver transition-colors hover:text-white">
                  <Tablet className="h-6 w-6" />
                  <span className="text-xs font-mono">TABLET</span>
                </div>
                <div className="flex flex-col items-center gap-2 text-studio-silver transition-colors hover:text-white">
                  <Monitor className="h-6 w-6" />
                  <span className="text-xs font-mono">DESKTOP</span>
                </div>
              </div>
            </Card>
          </CollapsiblePanel>

          {/* Component Studio */}
          <CollapsiblePanel
            title="Component Studio"
            icon={<Square className="h-5 w-5 text-electric-400" />}
            defaultOpen={true}
          >
            <Card variant="console" className="p-6 space-y-6">
              <div className="grid grid-cols-1 gap-4">
                <Select
                  label="Border Radius"
                  value={tokens.borderRadius}
                  onChange={(e) => setToken("borderRadius", e.target.value as DesignTokens["borderRadius"])}
                  options={[
                    { value: "none", label: "Sharp (0px)" },
                    { value: "sm", label: "Small (8px)" },
                    { value: "md", label: "Medium (12px)" },
                    { value: "lg", label: "Large (16px)" },
                    { value: "xl", label: "Extra Large (24px)" },
                    { value: "full", label: "Pill Shape" },
                  ]}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />

                <Select
                  label="Card Style"
                  value={tokens.cardStyle}
                  onChange={(e) => setToken("cardStyle", e.target.value as DesignTokens["cardStyle"])}
                  options={[
                    { value: "bordered", label: "Bordered" },
                    { value: "raised", label: "Raised (Shadow)" },
                    { value: "flat", label: "Flat (Minimal)" },
                    { value: "glass", label: "Glassmorphism" },
                    { value: "console", label: "Studio Console" },
                  ]}
                  className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
                />
              </div>

              {/* System Toggles */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">Animations</p>
                    <p className="text-xs text-studio-silver">Enable transitions and animations</p>
                  </div>
                  <div
                    role="switch"
                    aria-checked={tokens.animationsEnabled}
                    tabIndex={0}
                    className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300 cursor-pointer ${
                      tokens.animationsEnabled
                        ? "bg-gradient-studio shadow-lg"
                        : "bg-studio-slate/50"
                    }`}
                    onClick={() => setToken("animationsEnabled", !tokens.animationsEnabled)}
                  >
                    <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform shadow-lg ${tokens.animationsEnabled ? "translate-x-6" : "translate-x-1"}`} />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-white">Panels Default Open</p>
                    <p className="text-xs text-studio-silver">Start collapsible panels expanded</p>
                  </div>
                  <div
                    role="switch"
                    aria-checked={tokens.panelDefaultOpen}
                    tabIndex={0}
                    className={`relative inline-flex h-7 w-12 items-center rounded-full transition-all duration-300 cursor-pointer ${
                      tokens.panelDefaultOpen
                        ? "bg-gradient-studio shadow-lg"
                        : "bg-studio-slate/50"
                    }`}
                    onClick={() => setToken("panelDefaultOpen", !tokens.panelDefaultOpen)}
                  >
                    <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform shadow-lg ${tokens.panelDefaultOpen ? "translate-x-6" : "translate-x-1"}`} />
                  </div>
                </div>
              </div>

              {/* Component Preview Showcase */}
              <div className="space-y-4">
                <div className="text-xs font-mono text-studio-silver uppercase tracking-wider">
                  Component Preview
                </div>

                {/* Button showcase */}
                <div className="flex flex-wrap gap-3">
                  <Button size="sm" variant="primary">Primary</Button>
                  <Button size="sm" variant="secondary">Secondary</Button>
                  <Button size="sm" variant="electric">Electric</Button>
                  <Button size="sm" variant="glass">Glass</Button>
                  <Button size="sm" variant="console">Console</Button>
                </div>

                {/* Input showcase */}
                <input
                  type="text"
                  placeholder="Studio input preview..."
                  className="w-full h-12 rounded-xl bg-studio-obsidian/50 border border-studio-slate/30 px-4 text-white placeholder:text-studio-silver/50 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/20"
                  readOnly
                />

                {/* Audio components showcase */}
                <div className="grid grid-cols-3 gap-4 p-4 rounded-xl bg-studio-obsidian/30 border border-studio-slate/20">
                  <div className="text-center">
                    <div className="text-xs font-mono text-studio-silver mb-2">VU METER</div>
                    <div className="flex justify-center">
                      <VUMeter level={75} barCount={5} height={20} />
                    </div>
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-mono text-studio-silver mb-2">WAVEFORM</div>
                    <WaveformVisualizer height={20} barCount={8} animated color="primary" />
                  </div>
                  <div className="text-center">
                    <div className="text-xs font-mono text-studio-silver mb-2">SPINNER</div>
                    <div className="flex justify-center">
                      <AudioLoadingSpinner size="sm" color="primary" />
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </CollapsiblePanel>
        </div>

        {/* Live Preview Section */}
        <CollapsiblePanel
          title="Live Component Testing"
          icon={<Zap className="h-5 w-5 text-secondary-400" />}
          defaultOpen={false}
        >
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Card variants */}
            <div className="space-y-4">
              <h3 className="text-lg font-display font-bold text-[var(--color-text)] mb-4">
                Card Variants
              </h3>
              <Card variant="studio" className="p-4">
                <h4 className="font-medium text-[var(--color-text)] mb-2">Studio Card</h4>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Premium glassmorphism with audio-reactive background
                </p>
                <div className="mt-3">
                  <WaveformVisualizer height={16} barCount={10} animated color="primary" />
                </div>
              </Card>

              <Card variant="console" className="p-4">
                <h4 className="font-medium text-white mb-2">Console Card</h4>
                <p className="text-sm text-studio-silver">
                  Professional studio equipment aesthetic
                </p>
                <div className="mt-3">
                  <VUMeter level={60} barCount={8} height={16} />
                </div>
              </Card>

              <Card variant="glass" className="p-4">
                <h4 className="font-medium text-[var(--color-text)] mb-2">Glass Card</h4>
                <p className="text-sm text-[var(--color-text-secondary)]">
                  Translucent blur effect with elegant borders
                </p>
              </Card>
            </div>

            {/* Interactive controls */}
            <div className="space-y-4">
              <h3 className="text-lg font-display font-bold text-[var(--color-text)] mb-4">
                Interactive Controls
              </h3>

              <Card variant="console" className="p-6">
                <div className="grid grid-cols-2 gap-6">
                  <RotaryKnob
                    value={50}
                    onChange={() => {}}
                    label="Gain"
                    colorFrom="hsl(var(--primary-500))"
                    colorTo="hsl(var(--primary-600))"
                    size="md"
                  />
                  <RotaryKnob
                    value={75}
                    onChange={() => {}}
                    label="Filter"
                    colorFrom="hsl(var(--electric-500))"
                    colorTo="hsl(var(--electric-600))"
                    size="md"
                  />
                </div>
              </Card>

              <Card className="p-4">
                <div className="space-y-4">
                  <h4 className="font-medium text-[var(--color-text)]">Progress Variants</h4>
                  <div className="space-y-3">
                    <div className="h-3 rounded-full bg-[var(--color-bg-secondary)] overflow-hidden">
                      <div className="h-full bg-gradient-studio w-3/4 transition-all duration-500" />
                    </div>
                    <div className="h-4 rounded-xl bg-studio-obsidian/30 overflow-hidden border border-studio-slate/20">
                      <div className="h-full bg-gradient-to-r from-primary-500 to-electric-500 w-2/3 transition-all duration-500" />
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </CollapsiblePanel>
      </div>
    </div>
  );
}
