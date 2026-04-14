import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
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
    <div className="flex min-h-screen items-center justify-center bg-[var(--color-bg-secondary)]">
      <div className="w-full max-w-md rounded-xl bg-[var(--color-bg)] p-8 shadow-lg">
        <h1 className="mb-6 text-2xl font-display font-bold text-[var(--color-text)]">Atlas Vox</h1>

        {/* Mode toggle */}
        <div className="mb-4 flex gap-2">
          <Button
            variant={mode === "credentials" ? "primary" : "ghost"}
            size="sm"
            className="flex-1"
            onClick={() => { setMode("credentials"); setError(""); }}
          >
            Email &amp; Password
          </Button>
          <Button
            variant={mode === "apikey" ? "primary" : "ghost"}
            size="sm"
            className="flex-1"
            onClick={() => { setMode("apikey"); setError(""); }}
          >
            API Key
          </Button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-[var(--color-error-bg)] border border-[var(--color-error-border)] p-3 text-sm text-[var(--color-error)]">
            {error}
          </div>
        )}

        {mode === "credentials" ? (
          <div className="space-y-3">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(""); }}
              placeholder="you@example.com"
              autoComplete="email"
              disabled={isLoading}
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => { setPassword(e.target.value); setError(""); }}
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isLoading}
              onKeyDown={(e) => e.key === "Enter" && handleCredentialLogin()}
            />
            <Button
              className="w-full"
              onClick={handleCredentialLogin}
              loading={isLoading}
            >
              Sign In
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            <Input
              label="API Key"
              type="password"
              value={apiKeyInput}
              onChange={(e) => { setApiKeyInput(e.target.value); setError(""); }}
              placeholder="av_xxxxxxxxxxxx"
              disabled={isLoading}
              onKeyDown={(e) => e.key === "Enter" && handleApiKeyLogin()}
            />
            <Button
              className="w-full"
              onClick={handleApiKeyLogin}
              loading={isLoading}
            >
              Sign In with API Key
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
