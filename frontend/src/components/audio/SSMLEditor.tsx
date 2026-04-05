import { useState, useCallback, lazy, Suspense, Component, type ReactNode } from "react";
import { Code, FileText, AlertTriangle } from "lucide-react";
import { createLogger } from "../../utils/logger";

const MonacoEditor = lazy(() => import("@monaco-editor/react"));

const logger = createLogger("SSMLEditor");

interface SSMLEditorProps {
  value: string;
  onChange: (value: string) => void;
  minHeight?: number;
}

const SSML_TEMPLATE = `<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <voice name="default">
    <prosody rate="medium" pitch="medium">
      Enter your text here.
    </prosody>
  </voice>
</speak>`;

/** Catches lazy-load failures and falls back to a plain textarea. */
class MonacoErrorBoundary extends Component<
  { children: ReactNode; value: string; onChange: (v: string) => void; minHeight: number },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(err: Error) { logger.error("monaco_load_failed", { error: err.message }); }
  render() {
    if (this.state.failed) {
      return (
        <div className="space-y-2">
          <div className="flex items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-200">
            <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
            SSML editor unavailable — using plain text editor
          </div>
          <textarea
            value={this.props.value}
            onChange={(e) => this.props.onChange(e.target.value)}
            placeholder="Enter SSML markup..."
            rows={8}
            className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm font-mono text-[var(--color-text)] placeholder-[var(--color-text-secondary)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
            style={{ minHeight: this.props.minHeight }}
          />
        </div>
      );
    }
    return this.props.children;
  }
}

export function SSMLEditor({ value, onChange, minHeight = 200 }: SSMLEditorProps) {
  const [mode, setMode] = useState<"text" | "ssml">("text");

  const handleToggle = useCallback(() => {
    const next = mode === "text" ? "ssml" : "text";
    logger.info("mode_toggle", { from: mode, to: next });
    if (next === "ssml" && !value.trim()) {
      onChange(SSML_TEMPLATE);
    }
    setMode(next);
  }, [mode, value, onChange]);

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">
          {mode === "ssml" ? "SSML Editor" : "Text Input"}
        </label>
        <button
          onClick={handleToggle}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--color-border)] px-2.5 py-1 text-xs font-medium text-[var(--color-text-secondary)] hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          {mode === "ssml" ? (
            <><FileText className="h-3 w-3" /> Switch to Text</>
          ) : (
            <><Code className="h-3 w-3" /> Switch to SSML</>
          )}
        </button>
      </div>
      {mode === "ssml" ? (
        <MonacoErrorBoundary value={value} onChange={onChange} minHeight={minHeight}>
          <Suspense fallback={
            <div className="flex items-center justify-center rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)]" style={{ minHeight }}>
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary-500 border-t-transparent" />
            </div>
          }>
            <div className="rounded-lg border border-[var(--color-border)] overflow-hidden" style={{ minHeight }}>
              <MonacoEditor
                height={minHeight}
                language="xml"
                value={value}
                onChange={(v) => onChange(v ?? "")}
                theme="vs-dark"
                options={{
                  minimap: { enabled: false },
                  lineNumbers: "on",
                  fontSize: 13,
                  wordWrap: "on",
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 2,
                }}
              />
            </div>
          </Suspense>
        </MonacoErrorBoundary>
      ) : (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Enter text to synthesize..."
          rows={6}
          className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm text-[var(--color-text)] placeholder-[var(--color-text-secondary)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          style={{ minHeight }}
        />
      )}
    </div>
  );
}
