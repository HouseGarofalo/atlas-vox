import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Mic,
  Library,
  GraduationCap,
  AudioLines,
  Wand2,
  GitCompareArrows,
  Clock,
  Settings2,
  HelpCircle,
  Palette,
} from "lucide-react";
import { clsx } from "clsx";
import Header from "../Header";

/**
 * JARVIS Shell — Iron Man HUD
 * - Orbital nav elements at edges
 * - Corner brackets on viewport
 * - Scanline overlay
 * - Floating hologram nav at bottom
 * - All UPPERCASE
 * - Rotating orbital ring behind logo
 */

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "OVERVIEW" },
  { to: "/profiles", icon: Mic, label: "PROFILES" },
  { to: "/library", icon: Library, label: "ARCHIVES" },
  { to: "/training", icon: GraduationCap, label: "TRAINING" },
  { to: "/synthesis", icon: AudioLines, label: "SYNTHESIS" },
  { to: "/audio-design", icon: Wand2, label: "DESIGN" },
  { to: "/compare", icon: GitCompareArrows, label: "COMPARE" },
  { to: "/history", icon: Clock, label: "HISTORY" },
  { to: "/providers", icon: Settings2, label: "PROVIDERS" },
  { to: "/design", icon: Palette, label: "THEMES" },
  { to: "/help", icon: HelpCircle, label: "HELP" },
];

export default function JarvisShell() {
  const [clock, setClock] = useState("");
  useEffect(() => {
    const update = () => setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)] relative overflow-hidden">
      {/* ================= VIEWPORT CORNER BRACKETS ================= */}
      <div aria-hidden="true" className="pointer-events-none fixed inset-4 z-[5]">
        <CornerBracket position="top-left" />
        <CornerBracket position="top-right" />
        <CornerBracket position="bottom-left" />
        <CornerBracket position="bottom-right" />
      </div>

      {/* ================= TOP HUD BAR ================= */}
      <div className="relative z-10 px-8 py-4 flex items-center justify-between border-b border-primary-500/20">
        <div className="flex items-center gap-4">
          {/* Orbital ring logo */}
          <div className="relative w-12 h-12">
            <div
              className="absolute inset-0 rounded-full border border-primary-500/40 animate-spin"
              style={{ animationDuration: "8s" }}
            />
            <div
              className="absolute inset-1 rounded-full border border-primary-500/30 animate-spin"
              style={{ animationDuration: "12s", animationDirection: "reverse" }}
            />
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-primary-500 shadow-[0_0_20px_currentColor]" />
            </div>
          </div>
          <div>
            <div className="text-[10px] text-primary-500/80 tracking-[0.2em] font-mono">
              J.A.R.V.I.S. PROTOCOL
            </div>
            <div className="font-display font-light text-xl tracking-[0.15em] text-[var(--color-text)]">
              ATLAS VOX
            </div>
          </div>
        </div>

        {/* Central mission clock */}
        <div className="hidden md:flex flex-col items-center">
          <div className="text-[10px] text-primary-500/80 font-mono tracking-widest">
            SYSTEM TIME
          </div>
          <div className="font-mono text-2xl text-primary-500 tracking-[0.2em]">
            {clock}
          </div>
          <div className="flex items-center gap-2 text-[9px] text-primary-500/60 font-mono tracking-wider">
            <span className="inline-block w-1 h-1 rounded-full bg-primary-500 animate-led-pulse" />
            ALL SYSTEMS NOMINAL
          </div>
        </div>

        <Header />
      </div>

      {/* ================= CONTENT ================= */}
      <main id="main-content" className="relative flex-1 overflow-y-auto z-10 px-8 py-8 pb-32" tabIndex={-1}>
        <div className="mx-auto max-w-7xl">
          <Outlet />
        </div>
      </main>

      {/* ================= FLOATING HOLOGRAM NAV DOCK ================= */}
      <nav aria-label="Primary navigation" className="fixed bottom-6 left-1/2 -translate-x-1/2 z-20">
        <div className="relative">
          {/* Hologram base glow */}
          <div className="absolute -inset-2 rounded-full bg-primary-500/10 blur-xl" />

          <div
            className="relative flex items-center gap-1 px-3 py-2 rounded-full backdrop-blur-xl border border-primary-500/30"
            style={{
              background: "hsl(var(--studio-obsidian) / 0.7)",
              boxShadow: "0 0 40px hsl(var(--studio-primary) / 0.3), inset 0 1px 0 hsl(var(--studio-primary) / 0.2)",
            }}
          >
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  clsx(
                    "group relative flex flex-col items-center justify-center w-12 h-12 rounded-full transition-all duration-300",
                    isActive
                      ? "bg-primary-500/20 text-primary-500 shadow-[0_0_20px_hsl(var(--studio-primary)/0.6)]"
                      : "text-primary-500/50 hover:text-primary-500 hover:bg-primary-500/10"
                  )
                }
                title={label}
              >
                <Icon className="w-4 h-4" />
                {/* Tooltip */}
                <div className="absolute bottom-full mb-2 px-2 py-1 rounded bg-[var(--color-bg)] border border-primary-500/30 text-[10px] font-mono tracking-wider opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap">
                  {label}
                </div>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>

      {/* ================= SCAN LINE ANIMATION ================= */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 z-[3] opacity-20"
        style={{
          background: `repeating-linear-gradient(
            0deg,
            transparent 0,
            transparent 3px,
            hsl(var(--studio-primary) / 0.05) 3px,
            hsl(var(--studio-primary) / 0.05) 4px
          )`,
        }}
      />
    </div>
  );
}

function CornerBracket({
  position,
}: {
  position: "top-left" | "top-right" | "bottom-left" | "bottom-right";
}) {
  const posClass = {
    "top-left": "top-0 left-0",
    "top-right": "top-0 right-0",
    "bottom-left": "bottom-0 left-0",
    "bottom-right": "bottom-0 right-0",
  }[position];

  const isTop = position.startsWith("top");
  const isLeft = position.endsWith("left");

  return (
    <div className={`absolute ${posClass} w-8 h-8`}>
      <div
        className="absolute bg-primary-500"
        style={{
          width: "100%",
          height: "2px",
          top: isTop ? 0 : "auto",
          bottom: isTop ? "auto" : 0,
          boxShadow: "0 0 10px hsl(var(--studio-primary))",
        }}
      />
      <div
        className="absolute bg-primary-500"
        style={{
          width: "2px",
          height: "100%",
          left: isLeft ? 0 : "auto",
          right: isLeft ? "auto" : 0,
          boxShadow: "0 0 10px hsl(var(--studio-primary))",
        }}
      />
    </div>
  );
}
