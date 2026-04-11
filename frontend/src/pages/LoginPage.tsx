import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("LoginPage");

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [mode, setMode] = useState<"credentials" | "apikey">("credentials");
  const [error, setError] = useState("");
  const { login, setApiKey, isLoading } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  const handleCredentialLogin = async () => {
    if (!email.trim() || !password.trim()) {
      setError("Please enter email and password");
      return;
    }
    logger.info("login_attempt", { mode: "credentials" });
    try {
      await login(email.trim(), password.trim());
      navigate(from, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  };

  const handleApiKeyLogin = async () => {
    if (!apiKeyInput.trim()) {
      setError("Please enter an API key");
      return;
    }
    logger.info("login_attempt", { mode: "apikey" });
    try {
      await setApiKey(apiKeyInput.trim());
      navigate(from, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Invalid API key");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
      <div className="w-full max-w-md rounded-xl p-8 shadow-lg" style={{ backgroundColor: 'var(--color-bg)' }}>
        <h1 className="mb-6 text-2xl font-bold" style={{ color: 'var(--color-text)' }}>Atlas Vox</h1>

        {/* Mode toggle */}
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => { setMode("credentials"); setError(""); }}
            className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === "credentials"
                ? "bg-primary-600 text-white"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            Email &amp; Password
          </button>
          <button
            onClick={() => { setMode("apikey"); setError(""); }}
            className={`flex-1 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
              mode === "apikey"
                ? "bg-primary-600 text-white"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400"
            }`}
          >
            API Key
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
            {error}
          </div>
        )}

        {mode === "credentials" ? (
          <>
            <input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(""); }}
              placeholder="Email"
              className="mb-3 w-full rounded-lg px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)', borderWidth: '1px', borderStyle: 'solid', borderColor: 'var(--color-border)' }}
              aria-label="Email"
              autoComplete="email"
              disabled={isLoading}
            />
            <input
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(""); }}
              placeholder="Password"
              className="mb-4 w-full rounded-lg px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)', borderWidth: '1px', borderStyle: 'solid', borderColor: 'var(--color-border)' }}
              onKeyDown={(e) => e.key === "Enter" && handleCredentialLogin()}
              aria-label="Password"
              autoComplete="current-password"
              disabled={isLoading}
            />
            <button
              onClick={handleCredentialLogin}
              disabled={isLoading}
              className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </>
        ) : (
          <>
            <input
              type="password"
              value={apiKeyInput}
              onChange={(e) => { setApiKeyInput(e.target.value); setError(""); }}
              placeholder="API key"
              className="mb-4 w-full rounded-lg px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)', borderWidth: '1px', borderStyle: 'solid', borderColor: 'var(--color-border)' }}
              onKeyDown={(e) => e.key === "Enter" && handleApiKeyLogin()}
              aria-label="API key"
              disabled={isLoading}
            />
            <button
              onClick={handleApiKeyLogin}
              disabled={isLoading}
              className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50 disabled:opacity-50"
            >
              {isLoading ? "Validating..." : "Sign In with API Key"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
