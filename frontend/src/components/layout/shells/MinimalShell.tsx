import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Mic,
  Library,
  GraduationCap,
  AudioLines,
  Wand2,
  Copy,
  GitCompareArrows,
  Settings,
  Key,
  HelpCircle,
  Clock,
  BookOpen,
  Shield,
  Palette,
  Settings2,
} from "lucide-react";
import { clsx } from "clsx";
import Header from "../Header";

/**
 * Minimal Shell — Linear/Notion inspired
 * - Top horizontal nav instead of sidebar
 * - Generous whitespace
 * - Typography-first content
 * - No decorative audio elements
 */

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Overview" },
  { to: "/profiles", icon: Mic, label: "Profiles" },
  { to: "/library", icon: Library, label: "Library" },
  { to: "/training", icon: GraduationCap, label: "Training" },
  { to: "/clone", icon: Copy, label: "Clone" },
  { to: "/synthesis", icon: AudioLines, label: "Synthesis" },
  { to: "/audio-design", icon: Wand2, label: "Design" },
  { to: "/compare", icon: GitCompareArrows, label: "Compare" },
];

const moreItems = [
  { to: "/history", icon: Clock, label: "History" },
  { to: "/pronunciation", icon: BookOpen, label: "Pronunciation" },
  { to: "/providers", icon: Settings2, label: "Providers" },
  { to: "/api-keys", icon: Key, label: "API Keys" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/design", icon: Palette, label: "Themes" },
  { to: "/healing", icon: Shield, label: "Self-Healing" },
  { to: "/help", icon: HelpCircle, label: "Help" },
];

export default function MinimalShell() {
  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)]">
      {/* Top Brand Bar */}
      <div className="border-b border-[var(--color-border)] px-8 py-4">
        <div className="mx-auto max-w-7xl flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-accent-500" />
            <span className="font-display font-bold text-xl tracking-tight text-[var(--color-text)]">
              Atlas Vox
            </span>
          </div>
          <Header />
        </div>
      </div>

      {/* Horizontal Nav */}
      <nav className="border-b border-[var(--color-border)] px-8">
        <div className="mx-auto max-w-7xl flex items-center gap-1 overflow-x-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors",
                  isActive
                    ? "border-primary-500 text-[var(--color-text)]"
                    : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
                )
              }
            >
              <Icon className="w-4 h-4" />
              {label}
            </NavLink>
          ))}

          <div className="ml-auto flex items-center gap-1">
            {moreItems.slice(0, 4).map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2 px-3 py-3 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors",
                    isActive
                      ? "border-primary-500 text-[var(--color-text)]"
                      : "border-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
                  )
                }
              >
                <Icon className="w-4 h-4" />
                <span className="hidden lg:inline">{label}</span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main id="main-content" className="flex-1 px-8 py-12" tabIndex={-1}>
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
