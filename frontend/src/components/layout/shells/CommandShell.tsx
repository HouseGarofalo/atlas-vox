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
  Activity,
  TrendingUp,
} from "lucide-react";
import { clsx } from "clsx";
import Header from "../Header";

/**
 * Command Shell — Bloomberg Terminal / trading floor aesthetic
 * - Dense left nav with callsigns
 * - Ticker strip at top showing live metrics
 * - Status readouts in header
 * - Monospace everywhere
 * - Data-first presentation
 */

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "DASH", code: "D-01" },
  { to: "/profiles", icon: Mic, label: "PROF", code: "P-02" },
  { to: "/library", icon: Library, label: "LIB", code: "L-03" },
  { to: "/training", icon: GraduationCap, label: "TRN", code: "T-04" },
  { to: "/clone", icon: Copy, label: "CLN", code: "C-05" },
  { to: "/synthesis", icon: AudioLines, label: "SYN", code: "S-06" },
  { to: "/audio-design", icon: Wand2, label: "DSGN", code: "D-07" },
  { to: "/compare", icon: GitCompareArrows, label: "CMP", code: "C-08" },
  { to: "/history", icon: Clock, label: "HIST", code: "H-09" },
  { to: "/pronunciation", icon: BookOpen, label: "PRN", code: "P-10" },
  { to: "/providers", icon: Settings2, label: "PRV", code: "P-11" },
  { to: "/api-keys", icon: Key, label: "KEY", code: "K-12" },
  { to: "/settings", icon: Settings, label: "CFG", code: "C-13" },
  { to: "/design", icon: Palette, label: "THM", code: "T-14" },
  { to: "/healing", icon: Shield, label: "HEAL", code: "H-15" },
  { to: "/help", icon: HelpCircle, label: "HELP", code: "H-16" },
];

export default function CommandShell() {
  const [metrics, setMetrics] = useState({
    latency: 42,
    throughput: 1287,
    cpu: 34,
    mem: 68,
    uptime: "42:17:03",
    queue: 3,
  });

  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics((m) => ({
        latency: Math.round(30 + Math.random() * 30),
        throughput: Math.round(1200 + Math.random() * 200),
        cpu: Math.round(25 + Math.random() * 30),
        mem: Math.round(60 + Math.random() * 20),
        uptime: m.uptime,
        queue: Math.round(Math.random() * 10),
      }));
    }, 1500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-bg)] font-mono">
      {/* TICKER STRIP */}
      <div className="bg-[var(--color-bg-secondary)] border-b border-[var(--color-border)] px-4 py-1.5 text-[11px] overflow-hidden">
        <div className="flex items-center gap-6 whitespace-nowrap">
          <span className="text-primary-500 font-bold">ATLAS-VOX // SYS</span>
          <span className="text-[var(--color-text-secondary)]">
            LATENCY <span className="text-primary-500 font-bold">{metrics.latency}ms</span>
          </span>
          <span className="text-[var(--color-text-secondary)]">
            TPUT <span className="text-secondary-500 font-bold">{metrics.throughput}/s</span>
          </span>
          <span className="text-[var(--color-text-secondary)]">
            CPU <span className="text-electric-500 font-bold">{metrics.cpu}%</span>
          </span>
          <span className="text-[var(--color-text-secondary)]">
            MEM <span className="text-electric-500 font-bold">{metrics.mem}%</span>
          </span>
          <span className="text-[var(--color-text-secondary)]">
            QUEUE <span className="text-secondary-500 font-bold">{metrics.queue}</span>
          </span>
          <span className="text-[var(--color-text-secondary)]">
            UP <span className="text-primary-500 font-bold">{metrics.uptime}</span>
          </span>
          <span className="ml-auto text-primary-500 flex items-center gap-1">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-led-green animate-led-pulse" />
            LIVE
          </span>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* DENSE LEFT NAV */}
        <aside className="w-48 shrink-0 bg-[var(--color-bg-secondary)] border-r border-[var(--color-border)] flex flex-col">
          <div className="px-3 py-2 border-b border-[var(--color-border)]">
            <div className="text-[10px] text-[var(--color-text-secondary)]">CALLSIGN</div>
            <div className="text-sm font-bold text-primary-500">ATLAS-VOX.01</div>
          </div>

          <nav aria-label="Primary navigation" className="flex-1 overflow-y-auto py-1">
            {navItems.map(({ to, icon: Icon, label, code }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-2 px-3 py-1.5 text-[11px] border-l-2 transition-all",
                    isActive
                      ? "border-primary-500 bg-primary-500/10 text-[var(--color-text)]"
                      : "border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-hover)] hover:text-[var(--color-text)]"
                  )
                }
              >
                <Icon className="w-3 h-3 shrink-0" />
                <span className="font-bold flex-1">{label}</span>
                <span className="text-[9px] opacity-60">{code}</span>
              </NavLink>
            ))}
          </nav>

          {/* STATUS PANEL */}
          <div className="border-t border-[var(--color-border)] px-3 py-2 text-[10px] space-y-1">
            <div className="flex justify-between">
              <span className="text-[var(--color-text-secondary)]">STATUS</span>
              <span className="text-primary-500 font-bold">OPERATIONAL</span>
            </div>
            <div className="flex justify-between">
              <span className="text-[var(--color-text-secondary)]">SEC</span>
              <span className="text-led-green font-bold">● NOMINAL</span>
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

        {/* RIGHT METRICS PANEL */}
        <aside className="hidden xl:flex w-56 shrink-0 bg-[var(--color-bg-secondary)] border-l border-[var(--color-border)] flex-col p-3 gap-3">
          <div className="text-[10px] text-[var(--color-text-secondary)] border-b border-[var(--color-border)] pb-2">
            LIVE TELEMETRY
          </div>

          <MetricBar label="SYN/SEC" value={metrics.throughput / 20} color="primary" />
          <MetricBar label="CPU LOAD" value={metrics.cpu} color="electric" />
          <MetricBar label="MEM USE" value={metrics.mem} color="secondary" />

          <div className="mt-auto text-[9px] text-[var(--color-text-secondary)] space-y-1 border-t border-[var(--color-border)] pt-2">
            <div className="flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-primary-500" />
              <span>TREND: UP 12%</span>
            </div>
            <div className="flex items-center gap-1">
              <Activity className="w-3 h-3 text-electric-500" />
              <span>PULSE: STABLE</span>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

function MetricBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: "primary" | "secondary" | "electric";
}) {
  const colorMap = {
    primary: "bg-primary-500",
    secondary: "bg-secondary-500",
    electric: "bg-electric-500",
  };
  const textColorMap = {
    primary: "text-primary-500",
    secondary: "text-secondary-500",
    electric: "text-electric-500",
  };
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-[10px]">
        <span className="text-[var(--color-text-secondary)]">{label}</span>
        <span className={`font-bold ${textColorMap[color]}`}>{value.toFixed(0)}%</span>
      </div>
      <div className="h-1 bg-[var(--color-bg)] border border-[var(--color-border)]">
        <div
          className={`h-full ${colorMap[color]} transition-all`}
          style={{ width: `${Math.min(100, value)}%` }}
        />
      </div>
    </div>
  );
}
