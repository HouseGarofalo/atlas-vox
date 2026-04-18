/**
 * AzureLoginSection — Azure Entra ID device-code login flow UI.
 *
 * Extracted from ProvidersPage.tsx as part of P2-20 (decompose large pages).
 * Behaviour preserved exactly: polling intervals, expiry calculations, copy,
 * logout, re-login.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Clock, Copy, ExternalLink, Loader2, LogIn, LogOut, Shield } from "lucide-react";
import { Button } from "../../components/ui/Button";
import { api } from "../../services/api";
import { createLogger } from "../../utils/logger";
import type { AzureAuthStatus } from "../../types";

const logger = createLogger("AzureLoginSection");

export function AzureLoginSection() {
  const [authStatus, setAuthStatus] = useState<AzureAuthStatus | null>(null);
  const [initiating, setInitiating] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>();
  const fetchingRef = useRef(false); // guard against concurrent fetches

  // Fetch status on mount and set up polling when device code is pending
  const fetchStatus = useCallback(async () => {
    if (fetchingRef.current) return null; // skip if already in-flight
    fetchingRef.current = true;
    try {
      const status = await api.getAzureLoginStatus();
      setAuthStatus(status);
      setError(status.error ?? null);
      return status;
    } catch (err) {
      logger.warn("azure_status_fetch_failed", { error: String(err) });
      return null;
    } finally {
      fetchingRef.current = false;
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchStatus]);

  // Start polling when device code is pending
  useEffect(() => {
    if (authStatus?.device_code_pending) {
      pollRef.current = setInterval(async () => {
        const status = await fetchStatus();
        if (status && !status.device_code_pending) {
          if (pollRef.current) clearInterval(pollRef.current);
        }
      }, 3000);
      return () => {
        if (pollRef.current) clearInterval(pollRef.current);
      };
    }
  }, [authStatus?.device_code_pending, fetchStatus]);

  // Poll periodically when authenticated to track token expiry
  useEffect(() => {
    if (authStatus?.authenticated && !authStatus?.device_code_pending) {
      // Poll every 60s to keep expiry countdown accurate
      const expiryPoll = setInterval(() => {
        fetchStatus();
      }, 60000);
      return () => clearInterval(expiryPoll);
    }
  }, [authStatus?.authenticated, authStatus?.device_code_pending, fetchStatus]);

  // Determine if token is near expiry (< 5 minutes)
  const isNearExpiry = authStatus?.authenticated
    && authStatus.expires_in_seconds != null
    && authStatus.expires_in_seconds < 300
    && authStatus.expires_in_seconds > 0;

  const isExpired = authStatus?.authenticated
    && authStatus.expires_in_seconds != null
    && authStatus.expires_in_seconds <= 0;

  const handleInitiateLogin = useCallback(async () => {
    setInitiating(true);
    setError(null);
    try {
      await api.initiateAzureLogin();
      // Poll for status after initiating
      await fetchStatus();
    } catch (err) {
      setError(String(err));
    } finally {
      setInitiating(false);
    }
  }, [fetchStatus]);

  const handleLogout = useCallback(async () => {
    setLoggingOut(true);
    try {
      await api.azureLogout();
      await fetchStatus();
    } catch (err) {
      setError(String(err));
    } finally {
      setLoggingOut(false);
    }
  }, [fetchStatus]);

  const handleCopyCode = useCallback((code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const formatExpiry = (seconds: number | null) => {
    if (!seconds || seconds <= 0) return "expired";
    const mins = Math.floor(seconds / 60);
    const hrs = Math.floor(mins / 60);
    if (hrs > 0) return `${hrs}h ${mins % 60}m`;
    return `${mins}m`;
  };

  // Auth status badge
  const statusBadge = isExpired
    ? "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300"
    : isNearExpiry
      ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
      : authStatus?.authenticated
        ? "bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300"
        : authStatus?.device_code_pending
          ? "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300"
          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300";

  const statusLabel = isExpired
    ? "Expired"
    : isNearExpiry
      ? "Expiring Soon"
      : authStatus?.authenticated
        ? "Authenticated"
        : authStatus?.device_code_pending
          ? "Pending..."
          : "Not Authenticated";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Shield className="h-4 w-4 text-[var(--color-text-secondary)]" />
        <h4 className="text-sm font-medium text-[var(--color-text-secondary)]">Azure Entra ID Login</h4>
        <span className={`rounded px-1.5 py-0.5 text-[10px] font-medium ${statusBadge}`}>
          {statusLabel}
        </span>
      </div>

      {/* Authenticated state */}
      {authStatus?.authenticated && (
        <div className={`rounded-lg border px-4 py-3 space-y-2 ${
          isExpired
            ? "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
            : isNearExpiry
              ? "border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20"
              : "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
        }`}>
          {/* Expiry warning banner */}
          {(isNearExpiry || isExpired) && (
            <div className={`flex items-center gap-2 text-xs font-medium rounded px-2 py-1.5 mb-1 ${
              isExpired
                ? "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200"
                : "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
            }`}>
              <Clock className="h-3.5 w-3.5" />
              {isExpired
                ? "Token has expired. Please re-login to continue using Azure Speech."
                : `Token expires in ${formatExpiry(authStatus.expires_in_seconds ?? null)}. Re-login to refresh.`}
            </div>
          )}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              {authStatus.user_display_name && (
                <p className={`text-sm font-medium ${
                  isExpired ? "text-red-800 dark:text-red-200"
                    : isNearExpiry ? "text-amber-800 dark:text-amber-200"
                      : "text-green-800 dark:text-green-200"
                }`}>
                  {authStatus.user_display_name}
                </p>
              )}
              {authStatus.user_email && (
                <p className={`text-xs ${
                  isExpired ? "text-red-600 dark:text-red-400"
                    : isNearExpiry ? "text-amber-600 dark:text-amber-400"
                      : "text-green-600 dark:text-green-400"
                }`}>
                  {authStatus.user_email}
                </p>
              )}
              <div className={`flex items-center gap-1.5 text-xs ${
                isExpired ? "text-red-600 dark:text-red-400"
                  : isNearExpiry ? "text-amber-600 dark:text-amber-400"
                    : "text-green-600 dark:text-green-400"
              }`}>
                <Clock className="h-3 w-3" />
                <span>
                  via {authStatus.auth_method ?? "unknown"} · expires in {formatExpiry(authStatus.expires_in_seconds ?? null)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              {(isNearExpiry || isExpired) && (
                <Button size="sm" variant="secondary" onClick={handleInitiateLogin} disabled={initiating}>
                  {initiating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogIn className="h-3.5 w-3.5" />}
                  Re-login
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={handleLogout} disabled={loggingOut}>
                {loggingOut ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogOut className="h-3.5 w-3.5" />}
                Logout
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Device code pending state */}
      {authStatus?.device_code_pending && authStatus.device_code_info && (
        <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 px-4 py-3 space-y-3">
          <p className="text-sm text-amber-800 dark:text-amber-200">
            Open the link below and enter the code to sign in:
          </p>
          <div className="flex items-center gap-3">
            <div className="flex-1 flex items-center gap-2">
              <code className="rounded bg-white dark:bg-gray-800 px-3 py-1.5 text-lg font-mono font-bold tracking-wider text-amber-800 dark:text-amber-200 border border-amber-300 dark:border-amber-700">
                {authStatus.device_code_info.user_code}
              </code>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleCopyCode(authStatus.device_code_info!.user_code)}
                title="Copy code"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-green-500" /> : <Copy className="h-3.5 w-3.5" />}
              </Button>
            </div>
            <a
              href={authStatus.device_code_info.verification_uri}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 rounded-lg bg-amber-600 hover:bg-amber-700 text-white px-3 py-1.5 text-sm font-medium transition-colors"
            >
              Open Login Page <ExternalLink className="h-3 w-3" />
            </a>
          </div>
          <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Waiting for sign-in... ({formatExpiry(authStatus.device_code_info.expires_in_seconds)} remaining)</span>
          </div>
        </div>
      )}

      {/* Not authenticated — show login button */}
      {!authStatus?.authenticated && !authStatus?.device_code_pending && (
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="secondary"
            onClick={handleInitiateLogin}
            disabled={initiating}
          >
            {initiating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <LogIn className="h-3.5 w-3.5" />}
            Login with Azure
          </Button>
          <span className="text-xs text-[var(--color-text-secondary)]">
            Sign in with your Microsoft account for token-based auth
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 px-3 py-2 text-xs text-red-700 dark:text-red-300">
          {error}
        </div>
      )}
    </div>
  );
}
