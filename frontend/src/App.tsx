import { lazy, Suspense, useEffect } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import AppLayout from "./components/layout/AppLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { useAuthStore } from "./stores/authStore";
import { createLogger } from "./utils/logger";

const logger = createLogger("App");

const DashboardPage = lazy(() => import("./pages/DashboardPage"));
const ProfilesPage = lazy(() => import("./pages/ProfilesPage"));
const TrainingStudioPage = lazy(() => import("./pages/TrainingStudioPage"));
const SynthesisLabPage = lazy(() => import("./pages/synthesis/SynthesisLabPage"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage"));
const ProvidersPage = lazy(() => import("./pages/ProvidersPage"));
const ApiKeysPage = lazy(() => import("./pages/ApiKeysPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const VoiceLibraryPage = lazy(() => import("./pages/VoiceLibraryPage"));
// HelpPage removed — /help redirects to /docs
const DocsPage = lazy(() => import("./pages/DocsPage"));
// AdminPage removed — /admin redirects to /providers
const DesignSystemPage = lazy(() => import("./pages/DesignSystemPage"));
const HealingPage = lazy(() => import("./pages/HealingPage"));
const AudioDesignPage = lazy(() => import("./pages/AudioDesignPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const CloneWizardPage = lazy(() => import("./pages/CloneWizardPage"));
const PronunciationPage = lazy(() => import("./pages/PronunciationPage"));
const QualityDashboardPage = lazy(() => import("./pages/QualityDashboardPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

function PageLoader() {
  return (
    <div className="space-y-6 p-6 animate-pulse">
      <div className="space-y-3">
        <div className="h-8 w-64 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
        <div className="h-4 w-96 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {Array.from({ length: 4 }, (_, i) => (
          <div key={i} className="rounded-[var(--radius)] border border-[var(--color-border)] p-6 space-y-4">
            <div className="h-4 w-3/4 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
            <div className="h-3 w-full bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
            <div className="h-3 w-5/6 bg-[var(--color-border)] rounded-[var(--radius-sm)]" />
          </div>
        ))}
      </div>
    </div>
  );
}

function App() {
  useEffect(() => {
    logger.info("app_mounted");

    // Auto-authenticate when AUTH_DISABLED=true on backend,
    // or try to restore session via httpOnly cookie
    const { isAuthenticated, setAuthDisabled, fetchMe, setInitialized } = useAuthStore.getState();
    if (!isAuthenticated) {
      fetch("/api/v1/auth/status", { credentials: "include" })
        .then(res => res.json())
        .then(data => {
          if (data.auth_disabled) {
            setAuthDisabled();
            logger.info("auto_authenticated", { reason: "AUTH_DISABLED" });
          } else {
            // Try restoring session from existing httpOnly cookie
            fetchMe()
              .then(() => logger.info("session_restored"))
              .catch(() => logger.info("auth_required"));
          }
        })
        .catch(() => {
          // Backend not reachable — user must login
          logger.info("auth_check_failed");
        })
        .finally(() => {
          setInitialized();
        });
    } else {
      setInitialized();
    }
  }, []);

  return (
    <>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route path="/login" element={<Suspense fallback={<PageLoader />}><LoginPage /></Suspense>} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<Page component={DashboardPage} context="dashboard" />} />
            <Route path="profiles" element={<Page component={ProfilesPage} context="profiles page" />} />
            <Route path="library" element={<Page component={VoiceLibraryPage} context="voice library" />} />
            <Route path="training" element={<Page component={TrainingStudioPage} context="training studio" />} />
            <Route path="synthesis" element={<Page component={SynthesisLabPage} context="synthesis lab" />} />
            <Route path="audio-design" element={<Page component={AudioDesignPage} context="audio design" />} />
            <Route path="compare" element={<Page component={ComparisonPage} context="comparison page" />} />
            <Route path="providers" element={<Page component={ProvidersPage} context="providers page" />} />
            <Route path="api-keys" element={<Page component={ApiKeysPage} context="API keys page" />} />
            <Route path="settings" element={<Page component={SettingsPage} context="settings page" />} />
            <Route path="help" element={<Navigate to="/docs" replace />} />
            <Route path="docs" element={<Page component={DocsPage} context="docs" />} />
            <Route path="admin" element={<Navigate to="/providers" replace />} />
            <Route path="design" element={<Page component={DesignSystemPage} context="design system" />} />
            <Route path="healing" element={<Page component={HealingPage} context="healing page" />} />
            <Route path="history" element={<Page component={HistoryPage} context="history page" />} />
            <Route path="clone" element={<Page component={CloneWizardPage} context="clone wizard" />} />
            <Route path="pronunciation" element={<Page component={PronunciationPage} context="pronunciation editor" />} />
            <Route path="profiles/:id/quality" element={<Page component={QualityDashboardPage} context="quality dashboard" />} />
            <Route path="*" element={<Page component={NotFoundPage} context="404 page" />} />
          </Route>
        </Route>
      </Routes>
    </>
  );
}

/** Wraps a lazy page in both Suspense and a per-page ErrorBoundary.
 *
 * The ``context`` prop flows into the fallback copy ("Something went wrong in
 * the profiles page") so users know which page failed when the sidebar
 * stays rendered around a localized error.
 */
function Page({
  component: Component,
  context,
}: {
  component: React.LazyExoticComponent<() => JSX.Element>;
  context?: string;
}) {
  return (
    <ErrorBoundary context={context}>
      <Suspense fallback={<PageLoader />}>
        <Component />
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
