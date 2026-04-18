import { useState, useCallback, useEffect, useRef, lazy, Suspense, Component, type ReactNode } from "react";
import { Code, FileText, AlertTriangle } from "lucide-react";
import { createLogger } from "../../utils/logger";
import { SSML_TAGS, tagsForProvider, findTag } from "./ssmlSchema";
import { validateSSML, type SSMLDiagnostic } from "./ssmlValidator";

const MonacoEditor = lazy(() => import("@monaco-editor/react"));

const logger = createLogger("SSMLEditor");

interface SSMLEditorProps {
  value: string;
  onChange: (value: string) => void;
  minHeight?: number;
  /**
   * Current provider name — drives autocomplete (which tags to suggest)
   * and validation (which tags to warn about as unsupported).
   */
  providerName?: string | null;
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

export function SSMLEditor({ value, onChange, minHeight = 200, providerName }: SSMLEditorProps) {
  const [mode, setMode] = useState<"text" | "ssml">("text");
  const [diagnostics, setDiagnostics] = useState<SSMLDiagnostic[]>([]);
  const editorRef = useRef<unknown>(null);
  const monacoRef = useRef<unknown>(null);
  const completionDisposableRef = useRef<{ dispose: () => void } | null>(null);

  const handleToggle = useCallback(() => {
    const next = mode === "text" ? "ssml" : "text";
    logger.info("mode_toggle", { from: mode, to: next });
    if (next === "ssml" && !value.trim()) {
      onChange(SSML_TEMPLATE);
    }
    setMode(next);
  }, [mode, value, onChange]);

  // Re-run validation whenever SSML text or provider changes.
  useEffect(() => {
    if (mode !== "ssml") {
      setDiagnostics([]);
      return;
    }
    const diags = validateSSML(value, providerName ?? null);
    setDiagnostics(diags);
  }, [value, providerName, mode]);

  // Sync diagnostics into Monaco as markers so they render inline.
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current || mode !== "ssml") return;
    type MonacoNs = {
      editor: {
        getModels: () => Array<{ uri: unknown }>;
        setModelMarkers: (model: unknown, owner: string, markers: unknown[]) => void;
        MarkerSeverity: Record<string, number>;
      };
    };
    const monaco = monacoRef.current as MonacoNs;
    type EditorT = { getModel: () => unknown };
    const model = (editorRef.current as EditorT).getModel();
    if (!model) return;
    const sevMap = {
      error: monaco.editor.MarkerSeverity.Error,
      warning: monaco.editor.MarkerSeverity.Warning,
      info: monaco.editor.MarkerSeverity.Info,
    };
    const markers = diagnostics.map((d) => ({
      message: d.message,
      severity: sevMap[d.severity],
      startLineNumber: d.startLine,
      startColumn: d.startColumn,
      endLineNumber: d.endLine,
      endColumn: d.endColumn,
    }));
    monaco.editor.setModelMarkers(model, "ssml", markers);
  }, [diagnostics, mode]);

  // (Re-)register completion provider whenever the allowed tag list changes.
  useEffect(() => {
    if (!monacoRef.current || mode !== "ssml") return;
    type MonacoNs = {
      languages: {
        registerCompletionItemProvider: (
          lang: string,
          provider: unknown,
        ) => { dispose: () => void };
        registerHoverProvider: (
          lang: string,
          provider: unknown,
        ) => { dispose: () => void };
        CompletionItemKind: Record<string, number>;
      };
    };
    const monaco = monacoRef.current as MonacoNs;
    const allowedTags = tagsForProvider(providerName ?? null);

    // Tear down previous registration first.
    completionDisposableRef.current?.dispose();

    const completionProvider = {
      triggerCharacters: ["<", " ", "\""],
      provideCompletionItems: (
        model: { getLineContent: (l: number) => string; getWordUntilPosition: (p: unknown) => { startColumn: number; endColumn: number } },
        position: { lineNumber: number; column: number },
      ) => {
        const lineText = model.getLineContent(position.lineNumber).slice(0, position.column - 1);
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endLineNumber: position.lineNumber,
          endColumn: word.endColumn,
        };

        // If the cursor is inside an open tag after "<", suggest tag names.
        const lastOpen = lineText.lastIndexOf("<");
        const lastClose = lineText.lastIndexOf(">");
        const insideTag = lastOpen > lastClose;

        if (insideTag) {
          // Try to detect whether we're naming the tag or completing an attribute.
          const afterOpen = lineText.slice(lastOpen + 1);
          const tagMatch = afterOpen.match(/^\/?\s*([a-zA-Z][a-zA-Z0-9:_-]*)/);
          if (tagMatch && afterOpen.includes(" ")) {
            // Completing attributes for <tagMatch[1]>.
            const tag = findTag(tagMatch[1]);
            if (tag) {
              return {
                suggestions: tag.attributes.map((a) => ({
                  label: a.name,
                  kind: monaco.languages.CompletionItemKind.Property,
                  insertText: `${a.name}="$1"`,
                  insertTextRules: 4, // InsertAsSnippet
                  detail: a.description,
                  documentation: a.values?.length
                    ? { value: "**Values:** " + a.values.join(", ") }
                    : undefined,
                  range,
                })),
              };
            }
          }
          // Suggest tag names.
          return {
            suggestions: allowedTags.map((t) => ({
              label: t.name,
              kind: monaco.languages.CompletionItemKind.Class,
              insertText: t.name,
              detail: t.description,
              documentation: {
                value: `**<${t.name}>**\n\n${t.description}\n\n${t.attributes.length ? "Attributes: " + t.attributes.map((a) => a.name).join(", ") : ""}`,
              },
              range,
            })),
          };
        }

        // Outside a tag: suggest a fresh < + tag snippet.
        return {
          suggestions: allowedTags.map((t) => ({
            label: `<${t.name}>`,
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: t.name === "break"
              ? `<break time="500ms"/>`
              : `<${t.name}>$0</${t.name}>`,
            insertTextRules: 4,
            detail: t.description,
            range,
          })),
        };
      },
    };

    const hoverProvider = {
      provideHover: (
        model: { getWordAtPosition: (p: unknown) => { word: string; startColumn: number; endColumn: number } | null },
        position: { lineNumber: number; column: number },
      ) => {
        const word = model.getWordAtPosition(position);
        if (!word) return null;
        const tag = findTag(word.word);
        if (!tag) return null;
        return {
          range: {
            startLineNumber: position.lineNumber,
            startColumn: word.startColumn,
            endLineNumber: position.lineNumber,
            endColumn: word.endColumn,
          },
          contents: [
            { value: `**<${tag.name}>**` },
            { value: tag.description },
            tag.attributes.length
              ? { value: "**Attributes:** " + tag.attributes.map((a) => a.name).join(", ") }
              : { value: "_No attributes_" },
          ],
        };
      },
    };

    const comp = monaco.languages.registerCompletionItemProvider("xml", completionProvider);
    const hov = monaco.languages.registerHoverProvider("xml", hoverProvider);
    completionDisposableRef.current = {
      dispose: () => {
        comp.dispose();
        hov.dispose();
      },
    };
    return () => completionDisposableRef.current?.dispose();
  }, [providerName, mode]);

  const errorCount = diagnostics.filter((d) => d.severity === "error").length;
  const warningCount = diagnostics.filter((d) => d.severity === "warning").length;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">
          {mode === "ssml" ? "SSML Editor" : "Text Input"}
        </label>
        <div className="flex items-center gap-3">
          {mode === "ssml" && (errorCount > 0 || warningCount > 0) && (
            <span
              data-testid="ssml-diagnostic-summary"
              className={`inline-flex items-center gap-1 text-xs ${errorCount > 0 ? "text-red-500" : "text-amber-500"}`}
            >
              <AlertTriangle className="h-3 w-3" />
              {errorCount > 0 ? `${errorCount} error${errorCount > 1 ? "s" : ""}` : null}
              {errorCount > 0 && warningCount > 0 ? ", " : null}
              {warningCount > 0 ? `${warningCount} warning${warningCount > 1 ? "s" : ""}` : null}
            </span>
          )}
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
                onMount={(editor, monaco) => {
                  editorRef.current = editor;
                  monacoRef.current = monaco;
                }}
                options={{
                  minimap: { enabled: false },
                  lineNumbers: "on",
                  fontSize: 13,
                  wordWrap: "on",
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 2,
                  quickSuggestions: { other: true, comments: false, strings: true },
                  suggestOnTriggerCharacters: true,
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
      {mode === "ssml" && errorCount + warningCount > 0 && (
        <ul
          data-testid="ssml-diagnostics-list"
          className="mt-1 max-h-32 overflow-y-auto rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] px-3 py-2 text-xs"
        >
          {diagnostics.slice(0, 10).map((d, i) => (
            <li
              key={`${d.startLine}-${d.startColumn}-${i}`}
              className={
                d.severity === "error"
                  ? "text-red-500"
                  : d.severity === "warning"
                    ? "text-amber-500"
                    : "text-[var(--color-text-secondary)]"
              }
            >
              Line {d.startLine}: {d.message}
            </li>
          ))}
          {diagnostics.length > 10 && (
            <li className="text-[var(--color-text-tertiary)]">
              …and {diagnostics.length - 10} more
            </li>
          )}
        </ul>
      )}
    </div>
  );
}

// Export schema for consumers that want to drive their own UI from it.
export { SSML_TAGS } from "./ssmlSchema";
