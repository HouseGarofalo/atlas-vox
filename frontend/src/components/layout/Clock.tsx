import { useState, useEffect } from "react";

/**
 * Self-contained clock component.
 *
 * Isolates the 1-second setInterval state update so that only this
 * component re-renders — not the entire Header (and by extension every
 * page, which was causing every input in the app to lose focus).
 */
export default function Clock() {
  const [time, setTime] = useState(() => new Date().toLocaleTimeString());

  useEffect(() => {
    const interval = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="hidden lg:block font-mono text-sm text-[var(--color-text-secondary)] bg-[var(--color-bg-secondary)] px-3 py-1 rounded-lg border border-[var(--color-border)]">
      {time}
    </div>
  );
}
