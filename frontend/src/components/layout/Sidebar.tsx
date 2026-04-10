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
  ShieldCheck,
  Clock,
  BookOpen,
  Menu,
  X,
} from "lucide-react";
import { clsx } from "clsx";
import { useState } from "react";
import VUMeter from "../audio/VUMeter";
import { createLogger } from "../../utils/logger";

const logger = createLogger("Sidebar");

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard", channel: 1 },
  { to: "/profiles", icon: Mic, label: "Voice Profiles", channel: 2 },
  { to: "/library", icon: Library, label: "Voice Library", channel: 3 },
  { to: "/training", icon: GraduationCap, label: "Training Studio", channel: 4 },
  { to: "/clone", icon: Copy, label: "Clone Voice", channel: 5 },
  { to: "/synthesis", icon: AudioLines, label: "Synthesis Lab", channel: 6 },
  { to: "/audio-design", icon: Wand2, label: "Audio Design", channel: 7 },
  { to: "/compare", icon: GitCompareArrows, label: "Comparison", channel: 8 },
  { to: "/history", icon: Clock, label: "History", channel: 9 },
  { to: "/pronunciation", icon: BookOpen, label: "Pronunciation", channel: 10 },
  { to: "/providers", icon: Settings2, label: "Providers", channel: 11 },
  { to: "/api-keys", icon: Key, label: "API Keys", channel: 12 },
  { to: "/settings", icon: Settings, label: "Settings", channel: 13 },
  { to: "/admin", icon: ShieldCheck, label: "Admin", channel: 14 },
  { to: "/design", icon: Palette, label: "Design System", channel: 15 },
  { to: "/healing", icon: Shield, label: "Self-Healing", channel: 16 },
  { to: "/help", icon: HelpCircle, label: "Help", channel: 17 },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);

  // Static decorative VU levels — only animate when real audio is playing
  const vuLevels: Record<number, number> = {
    1: 35, 2: 52, 3: 28, 4: 45, 5: 60, 6: 38, 7: 55, 8: 42,
    9: 30, 10: 48, 11: 58, 12: 33, 13: 50, 14: 25, 15: 62, 16: 40, 17: 44,
  };

  return (
    <>
      {/* Mobile menu button */}
      <button
        className="fixed top-4 left-4 z-50 rounded-xl bg-gradient-console p-3 shadow-console md:hidden border border-studio-slate"
        onClick={() => {
          logger.info("mobile_menu_toggle", { opened: !open });
          setOpen(!open);
        }}
        aria-label="Toggle menu"
      >
        {open ? (
          <X className="h-5 w-5 text-studio-silver" />
        ) : (
          <Menu className="h-5 w-5 text-studio-silver" />
        )}
      </button>

      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-studio-obsidian/70 backdrop-blur-sm md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      {/* Audio Mixer Sidebar */}
      <aside
        role="navigation"
        aria-label="Main navigation"
        className={clsx(
          "sidebar fixed z-40 flex h-full flex-col transition-transform duration-300 md:translate-x-0",
          "bg-gradient-to-b from-studio-obsidian via-studio-charcoal to-studio-obsidian",
          "border-r border-studio-slate/30 shadow-console",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Studio Console Header */}
        <div className="flex h-20 items-center gap-4 px-6 border-b border-studio-slate/20">
          <div className="relative">
            {/* Main logo with gradient */}
            <div className="w-12 h-12 bg-gradient-studio rounded-xl shadow-lg flex items-center justify-center">
              <AudioLines className="h-7 w-7 text-white" />
            </div>

            {/* Master VU meter LEDs */}
            <div className="absolute -right-1 -bottom-1 flex gap-1">
              <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />
              <div className="w-2 h-2 bg-led-yellow rounded-full opacity-60" />
              <div className="w-2 h-2 bg-led-red rounded-full opacity-30" />
            </div>
          </div>

          <div className="flex-1">
            <h1 className="font-display font-bold text-xl text-white">
              Atlas Vox
            </h1>
            <p className="text-xs text-studio-silver font-mono tracking-wide uppercase">
              Audio Studio
            </p>
          </div>

          {/* Master level indicator */}
          <div className="flex flex-col items-center gap-1">
            <div className="text-[10px] text-studio-silver font-mono">MSTR</div>
            <VUMeter level={75} barCount={5} height={16} />
          </div>
        </div>

        {/* Channel Strip Navigation */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto" aria-label="Primary">
          {navItems.map(({ to, icon: Icon, label, channel }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => {
                logger.info("nav_click", { to, label, channel });
                setOpen(false);
              }}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center gap-3 rounded-xl px-4 py-3 transition-all duration-300",
                  "border border-transparent hover:border-primary-500/30",
                  "relative overflow-hidden",
                  isActive
                    ? [
                        "bg-gradient-to-r from-primary-500/20 via-primary-400/15 to-electric-500/20",
                        "border-primary-500/40 text-white shadow-lg",
                        "shadow-primary-500/20"
                      ]
                    : [
                        "text-studio-silver hover:text-white",
                        "hover:bg-white/5 hover:shadow-md"
                      ]
                )
              }
            >
              {({ isActive }) => (
                <>
                  {/* Channel indicator LED */}
                  <div className="flex flex-col items-center gap-1 min-w-0">
                    <div
                      className={clsx(
                        "w-3 h-3 rounded-full transition-all duration-300",
                        isActive
                          ? "bg-primary-500 shadow-lg shadow-primary-500/50 animate-led-pulse"
                          : "bg-studio-slate/50 group-hover:bg-studio-silver/70"
                      )}
                    />
                    <span className="text-[10px] font-mono text-studio-silver/70">
                      {channel.toString().padStart(2, '0')}
                    </span>
                  </div>

                  <Icon className="w-5 h-5 shrink-0" />

                  <div className="flex-1 min-w-0">
                    <span className="font-medium truncate block">{label}</span>
                    {/* Channel gain indicator */}
                    <div className="text-[10px] font-mono text-studio-silver/70 mt-0.5">
                      {vuLevels[channel] ? `${vuLevels[channel].toFixed(0)}%` : "---"}
                    </div>
                  </div>

                  {/* Mini VU meter for active channels */}
                  <div className="min-w-0">
                    <VUMeter
                      level={vuLevels[channel] || 0}
                      barCount={3}
                      height={12}
                    />
                  </div>

                  {/* Active channel glow effect */}
                  <div
                    className={clsx(
                      "absolute inset-0 bg-gradient-to-r from-primary-500/10 to-electric-500/10",
                      "opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"
                    )}
                  />
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Master Section */}
        <div className="p-4 border-t border-studio-slate/20">
          <div className="text-center space-y-2">
            <div className="text-[10px] font-mono text-studio-silver uppercase tracking-wider">
              Master Output
            </div>

            {/* Master VU Meter */}
            <div className="flex justify-center">
              <VUMeter level={85} barCount={12} height={24} />
            </div>

            {/* Digital readout */}
            <div className="font-mono text-xs text-led-green bg-studio-obsidian/50 rounded px-2 py-1 border border-studio-slate/30">
              ATLAS VOX
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}
