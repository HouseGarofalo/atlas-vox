import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../stores/authStore";
import { createLogger } from "../utils/logger";

const logger = createLogger("ProtectedRoute");

/**
 * Route guard that checks authentication state.
 * When AUTH_DISABLED is true on the backend, the frontend skips auth checks.
 * The authDisabled flag is determined by checking if the user has been auto-set
 * or if there's no login page configured.
 */
export default function ProtectedRoute() {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  // If not authenticated, redirect to a login placeholder
  // In practice, when AUTH_DISABLED=true, the app auto-sets isAuthenticated=true
  if (!isAuthenticated) {
    logger.info("auth_redirect", { from: location.pathname });
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <Outlet />;
}