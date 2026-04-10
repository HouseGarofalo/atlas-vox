import { useState, useRef, useEffect, useLayoutEffect } from "react";
import { createPortal } from "react-dom";
import { Palette, Check, ChevronDown, Sparkles } from "lucide-react";
import { clsx } from "clsx";
import { useDesignStore } from "../../stores/designStore";
import { THEMES } from "../../themes";
import { createLogger } from "../../utils/logger";

const logger = createLogger("ThemeQuickSwitcher");

export function ThemeQuickSwitcher() {
  const { tokens, setTheme, getCurrentTheme } = useDesignStore();
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; right: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const current = getCurrentTheme();

  // Compute menu position from the trigger button's bounding rect
  useLayoutEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    setCoords({
      top: rect.bottom + 8, // 8px gap below the button
      right: window.innerWidth - rect.right, // right-align to the button
    });
  }, [open]);

  // Recompute on window resize while open
  useEffect(() => {
    if (!open) return;
    const onResize = () => {
      if (!triggerRef.current) return;
      const rect = triggerRef.current.getBoundingClientRect();
      setCoords({
        top: rect.bottom + 8,
        right: window.innerWidth - rect.right,
      });
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
    };
  }, [open]);

  // Close on outside click (check both the trigger and the portal menu)
  useEffect(() => {
    if (!open) return;
    const onClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        menuRef.current &&
        !menuRef.current.contains(target) &&
        triggerRef.current &&
        !triggerRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [open]);

  const primaryHsl = `hsl(${current.primary.h}, ${current.primary.s}%, ${current.primary.l}%)`;

  const menu = open && coords ? (
    <div
      ref={menuRef}
      className={clsx(
        "fixed w-80",
        "rounded-2xl border border-[var(--color-border)] shadow-2xl",
        "bg-[var(--color-bg)] backdrop-blur-xl overflow-hidden",
        "animate-fade-in-up"
      )}
      style={{
        top: `${coords.top}px`,
        right: `${coords.right}px`,
        zIndex: 9999,
      }}
      role="menu"
    >
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--color-border)] bg-gradient-to-r from-primary-500/5 to-electric-500/5">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-500" />
          <span className="text-xs font-mono uppercase tracking-wider text-[var(--color-text-secondary)]">
            Theme Library
          </span>
        </div>
        <div className="text-sm font-display font-bold text-[var(--color-text)] mt-1">
          {THEMES.length} signature themes
        </div>
      </div>

      {/* Scrollable theme list */}
      <div className="max-h-[420px] overflow-y-auto p-2">
        {THEMES.map((theme) => {
          const isActive = tokens.themeId === theme.id;
          const pHsl = `hsl(${theme.primary.h}, ${theme.primary.s}%, ${theme.primary.l}%)`;
          const sHsl = `hsl(${theme.secondary.h}, ${theme.secondary.s}%, ${theme.secondary.l}%)`;
          const aHsl = `hsl(${theme.accent.h}, ${theme.accent.s}%, ${theme.accent.l}%)`;

          return (
            <button
              key={theme.id}
              onClick={() => {
                setTheme(theme.id);
                setOpen(false);
              }}
              className={clsx(
                "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200",
                "hover:bg-[var(--color-hover)]",
                isActive && "bg-primary-500/10"
              )}
              role="menuitem"
            >
              {/* Color swatch stack */}
              <div className="flex shrink-0 items-center -space-x-1">
                <div
                  className="h-7 w-7 rounded-full border-2 border-[var(--color-bg)] shadow-sm"
                  style={{ background: pHsl }}
                />
                <div
                  className="h-7 w-7 rounded-full border-2 border-[var(--color-bg)] shadow-sm"
                  style={{ background: sHsl }}
                />
                <div
                  className="h-7 w-7 rounded-full border-2 border-[var(--color-bg)] shadow-sm"
                  style={{ background: aHsl }}
                />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0 text-left">
                <div className="text-sm font-display font-semibold text-[var(--color-text)] truncate">
                  {theme.name}
                </div>
                <div className="text-[10px] text-[var(--color-text-secondary)] uppercase tracking-wider font-mono truncate">
                  {theme.mood}
                </div>
              </div>

              {/* Active checkmark */}
              {isActive && (
                <div
                  className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center"
                  style={{ background: pHsl }}
                >
                  <Check className="w-3.5 h-3.5 text-white" strokeWidth={3} />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  ) : null;

  return (
    <>
      {/* Trigger button */}
      <button
        ref={triggerRef}
        onClick={() => {
          setOpen(!open);
          logger.info("toggle", { open: !open });
        }}
        className={clsx(
          "group relative flex items-center gap-2 rounded-xl px-3 py-2.5 transition-all duration-200",
          "text-[var(--color-text-secondary)] hover:text-[var(--color-text)]",
          "border border-transparent hover:border-primary-500/20 hover:bg-primary-500/10",
          open && "border-primary-500/30 bg-primary-500/10 text-[var(--color-text)]"
        )}
        aria-label="Switch theme"
        aria-expanded={open}
      >
        <Palette className="h-4 w-4" />
        <div className="flex items-center gap-1.5">
          <div
            className="h-3 w-3 rounded-full border border-white/30 shadow-sm"
            style={{ background: primaryHsl }}
          />
          <span className="hidden sm:inline text-xs font-medium">{current.name}</span>
        </div>
        <ChevronDown
          className={clsx("h-3 w-3 transition-transform duration-200", open && "rotate-180")}
        />
      </button>

      {/* Portal-rendered menu escapes the header's stacking context */}
      {menu && createPortal(menu, document.body)}
    </>
  );
}

export default ThemeQuickSwitcher;
