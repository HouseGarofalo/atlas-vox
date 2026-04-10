import { Outlet } from "react-router-dom";
import Sidebar from "../Sidebar";
import Header from "../Header";
import AudioReactiveBackground from "../../audio/AudioReactiveBackground";

/**
 * Studio Shell — the original Atlas Vox sidebar with channel-strip VU meters.
 * This is the default layout for Studio Classic and related themes.
 */
export default function StudioShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-gradient-to-br from-[var(--color-bg)] via-[var(--color-bg-secondary)] to-[var(--color-bg-tertiary)]">
      <AudioReactiveBackground intensity="subtle" />

      <Sidebar />

      <div className="flex flex-1 flex-col overflow-hidden sidebar-offset relative z-10">
        <Header />
        <main id="main-content" className="flex-1 overflow-y-auto p-6 lg:p-8" tabIndex={-1}>
          <div
            style={{ maxWidth: "var(--content-max-width)" }}
            className="mx-auto space-y-8"
          >
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
