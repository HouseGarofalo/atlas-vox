import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Mic,
  Library,
  GraduationCap,
  AudioLines,
  Wand2,
  Copy,
  GitCompareArrows,
  Settings2,
  Key,
  Settings,
  Palette,
  HelpCircle,
  Shield,
  Clock,
  BookOpen,
  Menu,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";
import { createLogger } from "../../utils/logger";

const logger = createLogger("Sidebar");

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/profiles", icon: Mic, label: "Voice Profiles" },
  { to: "/library", icon: Library, label: "Voice Library" },
  { to: "/training", icon: GraduationCap, label: "Training Studio" },
  { to: "/clone", icon: Copy, label: "Clone Voice" },
  { to: "/synthesis", icon: AudioLines, label: "Synthesis Lab" },
  { to: "/audio-design", icon: Wand2, label: "Audio Design" },
  { to: "/compare", icon: GitCompareArrows, label: "Comparison" },
  { to: "/history", icon: Clock, label: "History" },
  { to: "/pronunciation", icon: BookOpen, label: "Pronunciation" },
  { to: "/providers", icon: Settings2, label: "Providers" },
  { to: "/api-keys", icon: Key, label: "API Keys" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/design", icon: Palette, label: "Design System" },
  { to: "/healing", icon: Shield, label: "Self-Healing" },
  { to: "/help", icon: HelpCircle, label: "Help" },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="fixed top-4 left-4 z-50 rounded-lg bg-[var(--color-bg)] p-2 shadow-md md:hidden"
        onClick={() => { logger.info("mobile_menu_toggle", { opened: !open }); setOpen(!open); }}
        aria-label="Toggle menu"
      >
        {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        role="navigation"
        aria-label="Main navigation"
        className={clsx(
          "sidebar fixed z-40 flex h-full flex-col border-r border-[var(--color-border)] bg-[var(--color-sidebar)] transition-transform duration-200 md:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center gap-2 px-6">
          <AudioLines className="h-7 w-7 text-primary-500" />
          <span className="text-lg font-bold">Atlas Vox</span>
        </div>
        <nav className="flex-1 space-y-1 px-3 py-4" aria-label="Primary">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => { logger.info("nav_click", { to, label }); setOpen(false); }}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary-500/10 text-primary-600 dark:text-primary-400"
                    : "text-[var(--color-text-secondary)] hover:bg-gray-100 dark:hover:bg-gray-800"
                )
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
