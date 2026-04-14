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
  Clock,
  Settings,
  Palette,
  HelpCircle,
  Settings2,
  BookOpen,
  Key,
  Shield,
} from "lucide-react";
import { clsx } from "clsx";
import Header from "../Header";

/**
 * Bento Shell — Apple-style tiled layout
 * - Vertical icon rail (not a full sidebar)
 * - Huge rounded cards with generous gaps
 * - Soft aurora background
 * - Content gets generous padding
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
  { to: "/history", icon: Clock, label: "History" },
  { to: "/pronunciation", icon: BookOpen, label: "Pronunciation" },
  { to: "/providers", icon: Settings2, label: "Providers" },
  { to: "/api-keys", icon: Key, label: "Keys" },
  { to: "/settings", icon: Settings, label: "Settings" },
  { to: "/design", icon: Palette, label: "Themes" },
  { to: "/healing", icon: Shield, label: "Healing" },
  { to: "/help", icon: HelpCircle, label: "Help" },
];

export default function BentoShell() {
  return (
    <div className="min-h-screen flex bg-[var(--color-bg)] relative">
      {/* Soft aurora glow background */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-0 overflow-hidden">
        <div
          className="absolute -top-40 -left-40 w-96 h-96 rounded-full blur-3xl opacity-30"
          style={{ background: "hsl(var(--studio-primary))" }}
        />
        <div
          className="absolute top-1/2 right-0 w-96 h-96 rounded-full blur-3xl opacity-20"
          style={{ background: "hsl(var(--studio-secondary))" }}
        />
        <div
          className="absolute bottom-0 left-1/3 w-96 h-96 rounded-full blur-3xl opacity-25"
          style={{ background: "hsl(var(--studio-accent))" }}
        />
      </div>

      {/* SLIM ICON RAIL */}
      <aside className="relative z-10 w-20 shrink-0 flex flex-col items-center py-6 gap-2">
        {/* Logo */}
        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-primary-500 to-accent-500 shadow-xl mb-4 flex items-center justify-center">
          <AudioLines className="w-6 h-6 text-white" />
        </div>

        {/* Nav icons */}
        <nav aria-label="Primary navigation" className="flex flex-col items-center gap-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              title={label}
              className={({ isActive }) =>
                clsx(
                  "group relative w-12 h-12 rounded-2xl flex items-center justify-center transition-all duration-300",
                  isActive
                    ? "bg-white/80 dark:bg-studio-charcoal/80 shadow-lg text-primary-500 scale-110 backdrop-blur-xl"
                    : "text-[var(--color-text-secondary)] hover:bg-white/40 dark:hover:bg-studio-charcoal/40 hover:scale-105 backdrop-blur-sm"
                )
              }
            >
              <Icon className="w-5 h-5" />
              {/* Tooltip */}
              <div className="absolute left-full ml-3 px-3 py-1.5 rounded-xl bg-[var(--color-bg-secondary)]/95 backdrop-blur border border-[var(--color-border)] text-xs font-medium opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap shadow-lg z-30">
                {label}
              </div>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* CONTENT */}
      <div className="relative z-10 flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-end px-8 py-4">
          <Header />
        </div>
        <main id="main-content" className="flex-1 overflow-y-auto px-8 pb-8" tabIndex={-1}>
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
