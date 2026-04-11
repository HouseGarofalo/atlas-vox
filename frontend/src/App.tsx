import { lazy, Suspense, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
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
const SynthesisLabPage = lazy(() => import("./pages/SynthesisLabPage"));
const ComparisonPage = lazy(() => import("./pages/ComparisonPage"));
const ProvidersPage = lazy(() => import("./pages/ProvidersPage"));
const ApiKeysPage = lazy(() => import("./pages/ApiKeysPage"));
const SettingsPage = lazy(() => import("./pages/SettingsPage"));
const VoiceLibraryPage = lazy(() => import("./pages/VoiceLibraryPage"));
const HelpPage = lazy(() => import("./pages/HelpPage"));
const DocsPage = lazy(() => import("./pages/DocsPage"));
// AdminPage superseded by ProvidersPage — /admin redirects to /providers
const AdminPage = lazy(() => import("./pages/AdminPage"));
const DesignSystemPage = lazy(() => import("./pages/DesignSystemPage"));
const HealingPage = lazy(() => import("./pages/HealingPage"));
const AudioDesignPage = lazy(() => import("./pages/AudioDesignPage"));
const HistoryPage = lazy(() => import("./pages/HistoryPage"));
const CloneWizardPage = lazy(() => import("./pages/CloneWizardPage"));
const PronunciationPage = lazy(() => import("./pages/PronunciationPage"));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage"));
const LoginPage = lazy(() => import("./pages/LoginPage"));

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

function App() {
  useEffect(() => {
    logger.info("app_mounted");

    // Auto-authenticate when AUTH_DISABLED=true on backend,
    // or try to restore session via httpOnly cookie
    const { isAuthenticated, setAuthDisabled, fetchMe } = useAuthStore.getState();
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
        });
    }
  }, []);

  return (
    <>
      <Toaster position="top-right" richColors />
      <Routes>
        <Route path="/login" element={<Suspense fallback={<PageLoader />}><LoginPage /></Suspense>} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppLayout />}>
            <Route index element={<Page component={DashboardPage} />} />
            <Route path="profiles" element={<Page component={ProfilesPage} />} />
            <Route path="library" element={<Page component={VoiceLibraryPage} />} />
            <Route path="training" element={<Page component={TrainingStudioPage} />} />
            <Route path="synthesis" element={<Page component={SynthesisLabPage} />} />
            <Route path="audio-design" element={<Page component={AudioDesignPage} />} />
            <Route path="compare" element={<Page component={ComparisonPage} />} />
            <Route path="providers" element={<Page component={ProvidersPage} />} />
            <Route path="api-keys" element={<Page component={ApiKeysPage} />} />
            <Route path="settings" element={<Page component={SettingsPage} />} />
            <Route path="help" element={<Page component={HelpPage} />} />
            <Route path="docs" element={<Page component={DocsPage} />} />
            <Route path="admin" element={<Page component={AdminPage} />} />
            <Route path="design" element={<Page component={DesignSystemPage} />} />
            <Route path="healing" element={<Page component={HealingPage} />} />
            <Route path="history" element={<Page component={HistoryPage} />} />
            <Route path="clone" element={<Page component={CloneWizardPage} />} />
            <Route path="pronunciation" element={<Page component={PronunciationPage} />} />
            <Route path="*" element={<Page component={NotFoundPage} />} />
          </Route>
        </Route>
      </Routes>
    </>
  );
}

/** Wraps a lazy page in both Suspense and a per-page ErrorBoundary. */
function Page({ component: Component }: { component: React.LazyExoticComponent<() => JSX.Element> }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<PageLoader />}>
        <Component />
      </Suspense>
    </ErrorBoundary>
  );
}

export default App;
