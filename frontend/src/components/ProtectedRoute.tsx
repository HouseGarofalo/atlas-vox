import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("ProtectedRoute");

interface ProtectedRouteProps {
  /** If set, the user must have this scope (or "admin") to access children. */
  requiredScope?: string;
}

/**
 * Route guard that checks authentication state and optional scope requirements.
 *
 * When AUTH_DISABLED is true on the backend, the frontend skips auth checks.
 * The authDisabled flag is determined by checking if the user has been auto-set
 * or if there's no login page configured.
 *
 * Usage:
 *   <Route element={<ProtectedRoute />}>              — auth only
 *   <Route element={<ProtectedRoute requiredScope="admin" />}> — auth + scope
 */
export default function ProtectedRoute({ requiredScope }: ProtectedRouteProps) {
  const { isAuthenticated, hasScope } = useAuthStore();
  const location = useLocation();

  // If not authenticated, redirect to login
  if (!isAuthenticated) {
    logger.info("auth_redirect", { from: location.pathname });
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // If a required scope is specified, check that the user has it
  if (requiredScope && !hasScope(requiredScope)) {
    logger.warn("scope_denied", { from: location.pathname, requiredScope });
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="text-center">
          <h1
            className="mb-2 text-2xl font-bold"
            style={{ color: "var(--color-text)" }}
          >
            Access Denied
          </h1>
          <p
            className="mb-4 text-sm"
            style={{ color: "var(--color-text-secondary)" }}
          >
            You do not have the required permissions to access this page.
          </p>
          <button
            onClick={() => window.history.back()}
            className="rounded-lg bg-primary-600 px-4 py-2 text-sm font-medium text-white hover:bg-primary-700"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return <Outlet />;
}
