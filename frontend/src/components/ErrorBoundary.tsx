import { Component, type ErrorInfo, type ReactNode } from "react";
import { createLogger } from "../utils/logger";

const logger = createLogger("ErrorBoundary");

interface Props {
  children: ReactNode;
  /**
   * Custom fallback. When provided, this completely replaces the default
   * recovery UI and is responsible for offering its own retry affordance.
   */
  fallback?: ReactNode;
  /**
   * Called when the user hits "Try Again". Useful if the parent wants to
   * re-run a data fetch or reset store state in addition to re-rendering.
   */
  onReset?: () => void;
  /**
   * Short label shown in the default fallback (e.g. "dashboard", "profiles")
   * so users know which page failed when multiple boundaries exist.
   */
  context?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  componentStack: string | null;
  copied: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
    error: null,
    componentStack: null,
    copied: false,
  };

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    logger.error("Uncaught error in component tree", {
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack ?? undefined,
      context: this.props.context,
    });
    this.setState({ componentStack: errorInfo.componentStack ?? null });
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null, componentStack: null, copied: false });
    this.props.onReset?.();
  };

  private handleCopy = async () => {
    const { error, componentStack } = this.state;
    const payload = [
      `Context: ${this.props.context ?? "unknown"}`,
      `Error: ${error?.message ?? "unknown"}`,
      "",
      "Stack:",
      error?.stack ?? "(no stack)",
      "",
      "Component stack:",
      componentStack ?? "(no component stack)",
      "",
      `User agent: ${navigator.userAgent}`,
      `URL: ${window.location.href}`,
      `When: ${new Date().toISOString()}`,
    ].join("\n");
    try {
      await navigator.clipboard.writeText(payload);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 2000);
    } catch (err) {
      logger.warn("clipboard_failed", { error: String(err) });
    }
  };

  render() {
    if (!this.state.hasError) return this.props.children;
    if (this.props.fallback) return this.props.fallback;

    const isDev = typeof import.meta !== "undefined" && import.meta.env?.DEV;

    return (
      <div
        role="alert"
        aria-live="assertive"
        data-testid="error-boundary-fallback"
        className="flex items-center justify-center min-h-[200px] p-8"
      >
        <div className="max-w-lg w-full text-center space-y-3">
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            Something went wrong
            {this.props.context ? (
              <span className="text-[var(--color-text-secondary)] font-normal">
                {" "}
                in the {this.props.context}
              </span>
            ) : null}
          </h2>
          <p className="text-sm text-[var(--color-text-secondary)] break-words">
            {this.state.error?.message ?? "Unknown error"}
          </p>
          {isDev && this.state.error?.stack && (
            <details className="text-left rounded-md border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-2">
              <summary className="text-xs text-[var(--color-text-secondary)] cursor-pointer">
                Stack trace (dev only)
              </summary>
              <pre className="mt-2 text-[10px] text-[var(--color-text-secondary)] overflow-auto max-h-48 whitespace-pre-wrap">
                {this.state.error.stack}
              </pre>
            </details>
          )}
          <div className="flex items-center justify-center gap-2 pt-2">
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-primary-500 text-white rounded-[var(--radius)] hover:bg-primary-600 text-sm transition-colors"
            >
              Try again
            </button>
            <a
              href="/"
              className="px-4 py-2 rounded-[var(--radius)] border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-bg-secondary)] text-sm transition-colors"
            >
              Back to dashboard
            </a>
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 rounded-[var(--radius)] border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-bg-secondary)] text-sm transition-colors"
            >
              Reload
            </button>
            <button
              onClick={this.handleCopy}
              className="px-4 py-2 rounded-[var(--radius)] border border-[var(--color-border)] text-[var(--color-text)] hover:bg-[var(--color-bg-secondary)] text-sm transition-colors"
              aria-live="polite"
            >
              {this.state.copied ? "Copied!" : "Copy details"}
            </button>
          </div>
        </div>
      </div>
    );
  }
}
