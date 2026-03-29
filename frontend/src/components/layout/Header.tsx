import { Moon, Sun, Paintbrush } from "lucide-react";
import { Link } from "react-router-dom";
import { useSettingsStore } from "../../stores/settingsStore";

export default function Header() {
  const { theme, toggleTheme } = useSettingsStore();

  return (
    <header className="flex h-14 sm:h-16 items-center justify-between border-b border-[var(--color-border)] px-4 sm:px-6 bg-[var(--color-bg)]">
      <div className="md:hidden" /> {/* Spacer for mobile hamburger */}
      <div className="flex items-center gap-2">
        <Link
          to="/design"
          className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Design System"
          title="Design System"
        >
          <Paintbrush className="h-4 w-4" />
        </Link>
        <button
          onClick={toggleTheme}
          className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          aria-label="Toggle theme"
        >
          {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </button>
      </div>
    </header>
  );
}
