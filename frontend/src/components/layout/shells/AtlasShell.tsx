import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
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
  BookOpen,
  Settings2,
  Key,
  Settings,
  Palette,
  Shield,
  HelpCircle,
  Radio,
  Target,
} from "lucide-react";
import { clsx } from "clsx";
import Header from "../Header";

/**
 * ATLAS Tactical Shell — NORAD mission command
 * - Grid overlay background
 * - Status strip with DEFCON-style indicators
 * - Callsign sidebar with mission clock
 * - Target/grid reticle corner elements
 * - Compact monospace everywhere
 * - Military/tactical badge system
 */

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "OPS", code: "OP-1" },
  { to: "/profiles", icon: Mic, label: "VOICE", code: "VC-2" },
  { to: "/library", icon: Library, label: "DB", code: "DB-3" },
  { to: "/training", icon: GraduationCap, label: "TRAIN", code: "TR-4" },
  { to: "/clone", icon: Copy, label: "CLONE", code: "CL-5" },
  { to: "/synthesis", icon: AudioLines, label: "SYNTH", code: "SY-6" },
  { to: "/audio-design", icon: Wand2, label: "DSGN", code: "DG-7" },
  { to: "/compare", icon: GitCompareArrows, label: "CMPR", code: "CP-8" },
  { to: "/history", icon: Clock, label: "HIST", code: "HS-9" },
  { to: "/pronunciation", icon: BookOpen, label: "PRN", code: "PR-A" },
  { to: "/providers", icon: Settings2, label: "PROV", code: "PV-B" },
  { to: "/api-keys", icon: Key, label: "KEYS", code: "KY-C" },
  { to: "/settings", icon: Settings, label: "CFG", code: "CF-D" },
  { to: "/design", icon: Palette, label: "THM", code: "TH-E" },
  { to: "/healing", icon: Shield, label: "HEAL", code: "HL-F" },
  { to: "/help", icon: HelpCircle, label: "HELP", code: "HP-G" },
];

export default function AtlasShell() {
  const [clock, setClock] = useState("");
  const [defcon] = useState(5);
  const [mission] = useState("ATX-0471");

  useEffect(() => {
    const update = () =>
      setClock(
        new Date().toLocaleTimeString("en-US", { hour12: false, timeZone: "UTC" }) + " Z"
      );
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)] relative">
      {/* GRID OVERLAY */}
      <div
        className="pointer-events-none fixed inset-0 opacity-20"
        style={{
          backgroundImage:
            "linear-gradient(hsl(var(--studio-primary) / 0.15) 1px, transparent 1px), linear-gradient(90deg, hsl(var(--studio-primary) / 0.15) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* ================= TOP STATUS BAR ================= */}
      <div className="relative z-10 border-b-2 border-primary-500/60 bg-[var(--color-bg-secondary)]">
        <div className="flex items-stretch font-mono text-[11px]">
          {/* CALLSIGN BLOCK */}
          <div className="px-4 py-2 border-r border-primary-500/30 bg-primary-500/10">
            <div className="text-[9px] text-[var(--color-text-secondary)] tracking-widest">
              CALLSIGN
            </div>
            <div className="font-bold text-primary-500">ATLAS-01</div>
          </div>

          {/* MISSION ID */}
          <div className="px-4 py-2 border-r border-primary-500/30">
            <div className="text-[9px] text-[var(--color-text-secondary)] tracking-widest">
              MISSION
            </div>
            <div className="font-bold text-[var(--color-text)]">{mission}</div>
          </div>

          {/* DEFCON */}
          <div className="px-4 py-2 border-r border-primary-500/30">
            <div className="text-[9px] text-[var(--color-text-secondary)] tracking-widest">
              DEFCON
            </div>
            <div className="font-bold text-led-green flex items-center gap-1">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-led-green animate-led-pulse" />
              {defcon}
            </div>
          </div>

          {/* CLOCK (pushes to center) */}
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-[9px] text-[var(--color-text-secondary)] tracking-widest">
                MISSION TIME (UTC)
              </div>
              <div className="font-bold text-primary-500 text-sm tracking-[0.2em]">
                {clock}
              </div>
            </div>
          </div>

          {/* STATUS LIGHTS */}
          <div className="flex items-center gap-3 px-4 border-l border-primary-500/30">
            <StatusLed label="COMM" color="green" />
            <StatusLed label="NAV" color="green" />
            <StatusLed label="PWR" color="green" />
            <StatusLed label="SEC" color="yellow" />
          </div>
        </div>
      </div>

      <div className="relative flex flex-1 overflow-hidden z-10">
        {/* ================= LEFT TACTICAL NAV ================= */}
        <aside className="w-52 shrink-0 bg-[var(--color-bg-secondary)] border-r-2 border-primary-500/40 flex flex-col">
          <div className="px-3 py-2 border-b border-primary-500/30 bg-primary-500/5">
            <div className="flex items-center gap-2">
              <Target className="w-3 h-3 text-primary-500" />
              <span className="text-[10px] font-mono font-bold text-primary-500 tracking-widest">
                OPERATIONS
              </span>
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto">
            {navItems.map(({ to, icon: Icon, label, code }, i) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2 px-3 py-2 text-[11px] font-mono border-l-4 transition-all",
                    isActive
                      ? "border-primary-500 bg-primary-500/15 text-primary-500"
                      : "border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-hover)] hover:text-[var(--color-text)]"
                  )
                }
              >
                <span className="text-[9px] opacity-50 w-5">
                  {(i + 1).toString().padStart(2, "0")}
                </span>
                <Icon className="w-3.5 h-3.5 shrink-0" />
                <span className="font-bold flex-1 tracking-wider">{label}</span>
                <span className="text-[9px] opacity-60">{code}</span>
              </NavLink>
            ))}
          </nav>

          {/* MISSION READINESS */}
          <div className="border-t-2 border-primary-500/40 bg-primary-500/5 p-3 space-y-1">
            <div className="flex items-center gap-2 text-[10px] font-mono">
              <Radio className="w-3 h-3 text-primary-500" />
              <span className="text-[var(--color-text-secondary)]">READINESS</span>
              <span className="ml-auto font-bold text-led-green">READY</span>
            </div>
            <div className="h-1 bg-[var(--color-bg)] border border-primary-500/30">
              <div className="h-full bg-led-green" style={{ width: "94%" }} />
            </div>
          </div>
        </aside>

        {/* CONTENT */}
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main id="main-content" className="flex-1 overflow-y-auto p-4" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}

function StatusLed({ label, color }: { label: string; color: "green" | "yellow" | "red" }) {
  const colorMap = {
    green: "bg-led-green",
    yellow: "bg-led-yellow",
    red: "bg-led-red",
  };
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={clsx(
          "w-1.5 h-1.5 rounded-full animate-led-pulse shadow-[0_0_6px_currentColor]",
          colorMap[color]
        )}
      />
      <span className="text-[9px] font-mono text-[var(--color-text-secondary)] tracking-wider">
        {label}
      </span>
    </div>
  );
}
