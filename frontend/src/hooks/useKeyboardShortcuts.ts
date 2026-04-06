/**
 * Global keyboard shortcuts for Atlas Vox.
 *
 * Shortcuts:
 *   Ctrl+K / Cmd+K  — Focus search (if search input exists on page)
 *   ?               — Show shortcuts help (when not in an input)
 *   Escape          — Close modals
 */

import { useEffect } from "react";

interface ShortcutHandler {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  handler: () => void;
  description: string;
}

const isInputFocused = () => {
  const tag = document.activeElement?.tagName?.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" ||
         document.activeElement?.getAttribute("contenteditable") === "true";
};

export function useKeyboardShortcuts(shortcuts: ShortcutHandler[]) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      for (const s of shortcuts) {
        const ctrlMatch = s.ctrl ? (e.ctrlKey || e.metaKey) : !(e.ctrlKey || e.metaKey);
        const shiftMatch = s.shift ? e.shiftKey : !e.shiftKey;

        if (e.key === s.key && ctrlMatch && shiftMatch) {
          // Don't trigger plain key shortcuts when typing in inputs
          if (!s.ctrl && !s.shift && isInputFocused()) continue;

          e.preventDefault();
          s.handler();
          return;
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [shortcuts]);
}

/** All available shortcuts for the help modal. */
export const GLOBAL_SHORTCUTS = [
  { key: "k", ctrl: true, description: "Focus search" },
  { key: "/", description: "Focus search" },
  { key: "Escape", description: "Close modal / clear" },
  { key: "?", description: "Show keyboard shortcuts" },
];
