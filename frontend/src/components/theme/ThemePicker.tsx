import { Check, Sparkles } from "lucide-react";
import { clsx } from "clsx";
import { useDesignStore } from "../../stores/designStore";
import { THEMES, type Theme } from "../../themes";
import { createLogger } from "../../utils/logger";

const logger = createLogger("ThemePicker");

interface ThemePickerProps {
  className?: string;
  compact?: boolean;
}

export function ThemePicker({ className, compact = false }: ThemePickerProps) {
  const { tokens, setTheme } = useDesignStore();
  const activeId = tokens.themeId;

  const handleSelect = (theme: Theme) => {
    logger.info("theme_select", { id: theme.id, name: theme.name });
    setTheme(theme.id);
  };

  return (
    <div className={clsx("space-y-4", className)}>
      {!compact && (
        <div className="flex items-center gap-2 text-xs font-mono text-studio-silver uppercase tracking-wider">
          <Sparkles className="h-3.5 w-3.5" />
          <span>12 signature themes</span>
        </div>
      )}

      <div
        className={clsx(
          "grid gap-4",
          compact
            ? "grid-cols-2 sm:grid-cols-3"
            : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        )}
      >
        {THEMES.map((theme) => (
          <ThemeCard
            key={theme.id}
            theme={theme}
            isActive={activeId === theme.id}
            onSelect={() => handleSelect(theme)}
            compact={compact}
          />
        ))}
      </div>
    </div>
  );
}

interface ThemeCardProps {
  theme: Theme;
  isActive: boolean;
  onSelect: () => void;
  compact?: boolean;
}

function ThemeCard({ theme, isActive, onSelect, compact }: ThemeCardProps) {
  // Build HSL strings for the live preview
  const primaryHsl = `hsl(${theme.primary.h}, ${theme.primary.s}%, ${theme.primary.l}%)`;
  const secondaryHsl = `hsl(${theme.secondary.h}, ${theme.secondary.s}%, ${theme.secondary.l}%)`;
  const accentHsl = `hsl(${theme.accent.h}, ${theme.accent.s}%, ${theme.accent.l}%)`;
  const obsidianHsl = `hsl(${theme.neutrals.dark.obsidian})`;
  const charcoalHsl = `hsl(${theme.neutrals.dark.charcoal})`;

  // Derive preview background from theme neutrals
  const previewBg = `linear-gradient(135deg, ${obsidianHsl} 0%, ${charcoalHsl} 100%)`;

  // Generate a sample waveform data pattern unique per theme (deterministic)
  const waveData = Array.from({ length: 14 }, (_, i) => {
    const seed = theme.id.charCodeAt(i % theme.id.length);
    return (Math.sin(i * 0.5 + seed * 0.1) * 0.4 + 0.6);
  });

  return (
    <button
      onClick={onSelect}
      className={clsx(
        "group relative overflow-hidden rounded-2xl text-left transition-all duration-500",
        "border-2 focus:outline-none focus:ring-2 focus:ring-offset-2",
        isActive
          ? "border-transparent shadow-2xl scale-[1.02]"
          : "border-[var(--color-border)] hover:scale-[1.02] hover:shadow-xl"
      )}
      style={{
        background: previewBg,
        borderColor: isActive ? primaryHsl : undefined,
        boxShadow: isActive
          ? `0 20px 50px -12px ${primaryHsl}80, 0 0 0 2px ${primaryHsl}`
          : undefined,
      }}
      aria-pressed={isActive}
      aria-label={`Apply ${theme.name} theme`}
    >
      {/* Preview gradient overlay */}
      <div
        className="absolute inset-0 opacity-30 group-hover:opacity-50 transition-opacity duration-500"
        style={{ background: theme.previewGradient }}
      />

      {/* Corner color chips - like a paint swatch */}
      <div className="absolute -top-2 -right-2 w-32 h-32 pointer-events-none">
        <div
          className="absolute top-6 right-6 w-14 h-14 rounded-full blur-2xl opacity-60"
          style={{ background: primaryHsl }}
        />
        <div
          className="absolute top-12 right-2 w-10 h-10 rounded-full blur-xl opacity-60"
          style={{ background: secondaryHsl }}
        />
        <div
          className="absolute top-2 right-14 w-8 h-8 rounded-full blur-xl opacity-60"
          style={{ background: accentHsl }}
        />
      </div>

      <div className="relative z-10 p-5 space-y-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <div
              className="font-display font-bold text-lg leading-tight truncate"
              style={{ color: "hsl(0 0% 98%)" }}
            >
              {theme.name}
            </div>
            {!compact && (
              <div
                className="text-xs mt-1 opacity-80 truncate"
                style={{ color: "hsl(0 0% 85%)" }}
              >
                {theme.tagline}
              </div>
            )}
          </div>

          {/* Active checkmark */}
          {isActive && (
            <div
              className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center shadow-lg"
              style={{ background: primaryHsl }}
            >
              <Check className="w-4 h-4 text-white" strokeWidth={3} />
            </div>
          )}
        </div>

        {/* Color triad swatches */}
        <div className="flex items-center gap-2">
          <div
            className="h-8 flex-1 rounded-lg shadow-md border border-white/20"
            style={{ background: primaryHsl }}
            title={`Primary: ${primaryHsl}`}
          />
          <div
            className="h-8 flex-1 rounded-lg shadow-md border border-white/20"
            style={{ background: secondaryHsl }}
            title={`Secondary: ${secondaryHsl}`}
          />
          <div
            className="h-8 flex-1 rounded-lg shadow-md border border-white/20"
            style={{ background: accentHsl }}
            title={`Accent: ${accentHsl}`}
          />
        </div>

        {/* Mini waveform preview using theme colors */}
        {!compact && (
          <div className="flex items-end justify-center gap-1 h-8">
            {waveData.map((h, i) => {
              // Cycle through the 3 theme colors
              const color =
                i % 3 === 0 ? primaryHsl : i % 3 === 1 ? secondaryHsl : accentHsl;
              return (
                <div
                  key={i}
                  className="flex-1 rounded-full group-hover:animate-pulse transition-all duration-500"
                  style={{
                    background: color,
                    height: `${h * 100}%`,
                    maxWidth: "4px",
                    animationDelay: `${i * 0.05}s`,
                  }}
                />
              );
            })}
          </div>
        )}

        {/* Mood tag */}
        {!compact && (
          <div className="flex items-center justify-between">
            <span
              className="text-[10px] uppercase tracking-wider font-mono opacity-60"
              style={{ color: "hsl(0 0% 85%)" }}
            >
              {theme.mood}
            </span>
            <span
              className="text-[10px] font-mono px-2 py-0.5 rounded-full border"
              style={{
                color: primaryHsl,
                borderColor: `${primaryHsl}60`,
                background: `${primaryHsl}15`,
              }}
            >
              {theme.preferredMode === "both" ? "LIGHT/DARK" : theme.preferredMode.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* Active state glow line at bottom */}
      {isActive && (
        <div
          className="absolute bottom-0 left-0 right-0 h-1"
          style={{
            background: theme.previewGradient,
          }}
        />
      )}
    </button>
  );
}

export default ThemePicker;
