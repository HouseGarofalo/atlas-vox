import { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("LoginPage");

export default function LoginPage() {
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const { setToken: storeSetToken, setApiKey } = useAuthStore();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/";

  const handleLogin = () => {
    if (!token.trim()) {
      setError("Please enter a token or API key");
      return;
    }
    logger.info("login_attempt");
    try {
      if (token.includes(".")) {
        storeSetToken(token.trim());
      } else {
        setApiKey(token.trim());
      }
      navigate(from, { replace: true });
    } catch {
      setError("Invalid token");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 dark:bg-gray-900">
      <div className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg dark:bg-gray-800">
        <h1 className="mb-6 text-2xl font-bold text-gray-900 dark:text-white">Atlas Vox</h1>
        <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">
          Enter your JWT token or API key to continue.
        </p>
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-400">
            {error}
          </div>
        )}
        <input
          type="password"
          value={token}
          onChange={(e) => { setToken(e.target.value); setError(""); }}
          placeholder="JWT token or API key"
          className="mb-4 w-full rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          onKeyDown={(e) => e.key === "Enter" && handleLogin()}
          aria-label="Authentication token"
        />
        <button
          onClick={handleLogin}
          className="w-full rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500/50"
        >
          Sign In
        </button>
      </div>
    </div>
  );
}