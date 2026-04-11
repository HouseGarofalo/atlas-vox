import { useDesignStore } from "../../stores/designStore";
import StudioShell from "./shells/StudioShell";
import MinimalShell from "./shells/MinimalShell";
import CommandShell from "./shells/CommandShell";
import JarvisShell from "./shells/JarvisShell";
import AtlasShell from "./shells/AtlasShell";
import BentoShell from "./shells/BentoShell";

/**
 * AppLayout dispatches to one of six completely different app shells
 * based on the active theme's `layout` field. Each shell is a distinct
 * React component tree with its own nav, header, and chrome.
 */
export default function AppLayout() {
  const theme = useDesignStore((state) => state.themes[state.activeThemeId]);

  // Skip-to-content link is rendered by all shells indirectly via the main tag.
  // Render a top-level skip link here so it's always accessible regardless of shell.
  const skipLink = (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[200] focus:rounded-xl focus:bg-primary-500 focus:px-6 focus:py-3 focus:text-white focus:shadow-xl focus:outline-none font-medium"
    >
      Skip to main content
    </a>
  );

  let shell;
  switch (theme.layout) {
    case "minimal":
      shell = <MinimalShell />;
      break;
    case "command":
      shell = <CommandShell />;
      break;
    case "jarvis":
      shell = <JarvisShell />;
      break;
    case "atlas":
      shell = <AtlasShell />;
      break;
    case "bento":
      shell = <BentoShell />;
      break;
    case "studio":
    default:
      shell = <StudioShell />;
      break;
  }

  return (
    <>
      {skipLink}
      {shell}
    </>
  );
}
