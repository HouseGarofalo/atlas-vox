import { Moon, Sun } from "lucide-react";
import { useSettingsStore } from "../../stores/settingsStore";

export default function Header() {
  const { theme, toggleTheme } = useSettingsStore();

  return (
    <header className="flex h-16 items-center justify-between border-b border-[var(--color-border)] px-6">
      <div />
      <button
        onClick={toggleTheme}
        className="rounded-lg p-2 text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
        aria-label="Toggle theme"
      >
        {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
      </button>
    </header>
  );
}
