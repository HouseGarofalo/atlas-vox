import { Moon, Sun, Paintbrush, Volume2 } from "lucide-react";
import { Link } from "react-router-dom";
import { useState, useEffect } from "react";
import { useSettingsStore } from "../../stores/settingsStore";
import VUMeter from "../audio/VUMeter";
import ThemeQuickSwitcher from "../theme/ThemeQuickSwitcher";

export default function Header() {
  const { theme, toggleTheme } = useSettingsStore();
  const [clockTime, setClockTime] = useState(() => new Date().toLocaleTimeString());

  // Static decorative VU level — only animate when real audio is playing
  const vuLevel = 45;

  // Update clock every second
  useEffect(() => {
    const interval = setInterval(() => {
      setClockTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header className="flex h-16 lg:h-18 items-center justify-between border-b border-[var(--color-border)] px-6 bg-[var(--color-bg)]/80 backdrop-blur-md">
      {/* Mobile hamburger spacer */}
      <div className="md:hidden w-8" />

      {/* System Status */}
      <div className="flex items-center gap-6">
        {/* System status indicator */}
        <div className="hidden sm:flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-led-green animate-led-pulse" />
            <span className="text-xs font-mono text-[var(--color-text-secondary)] uppercase tracking-wider">
              System Online
            </span>
          </div>

          {/* System VU meter */}
          <div className="flex items-center gap-2">
            <Volume2 className="h-3 w-3 text-[var(--color-text-secondary)]" />
            <VUMeter level={vuLevel} barCount={6} height={14} />
          </div>
        </div>

        {/* Digital clock */}
        <div className="hidden lg:block font-mono text-sm text-[var(--color-text-secondary)] bg-[var(--color-bg-secondary)] px-3 py-1 rounded-lg border border-[var(--color-border)]">
          {clockTime}
        </div>
      </div>

      {/* Control Panel */}
      <div className="flex items-center gap-2">
        {/* Theme Quick Switcher */}
        <ThemeQuickSwitcher />

        {/* Design System Access */}
        <Link
          to="/design"
          className="group relative rounded-xl p-3 text-[var(--color-text-secondary)] hover:text-primary-500 transition-all duration-200 hover:bg-primary-500/10 border border-transparent hover:border-primary-500/20"
          aria-label="Design System"
          title="Design System"
        >
          <Paintbrush className="h-4 w-4" />
          <div className="absolute inset-0 bg-gradient-studio opacity-0 group-hover:opacity-10 rounded-xl transition-opacity duration-200" />
        </Link>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="group relative rounded-xl p-3 text-[var(--color-text-secondary)] hover:text-secondary-500 transition-all duration-200 hover:bg-secondary-400/10 border border-transparent hover:border-secondary-400/20"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? (
            <Sun className="h-5 w-5" />
          ) : (
            <Moon className="h-5 w-5" />
          )}
          <div className="absolute inset-0 bg-gradient-gold opacity-0 group-hover:opacity-10 rounded-xl transition-opacity duration-200" />
        </button>
      </div>
    </header>
  );
}
