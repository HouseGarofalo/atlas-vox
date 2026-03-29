import { lazy, Suspense, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import AppLayout from "./components/layout/AppLayout";
import { ErrorBoundary } from "./components/ErrorBoundary";
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
const AdminPage = lazy(() => import("./pages/AdminPage"));
const DesignSystemPage = lazy(() => import("./pages/DesignSystemPage"));
const HealingPage = lazy(() => import("./pages/HealingPage"));

function App() {
  useEffect(() => {
    logger.info("app_mounted");
  }, []);

  return (
    <>
      <Toaster position="top-right" richColors />
      <ErrorBoundary>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            index
            element={
              <Suspense fallback={<PageLoader />}>
                <DashboardPage />
              </Suspense>
            }
          />
          <Route
            path="profiles"
            element={
              <Suspense fallback={<PageLoader />}>
                <ProfilesPage />
              </Suspense>
            }
          />
          <Route
            path="library"
            element={
              <Suspense fallback={<PageLoader />}>
                <VoiceLibraryPage />
              </Suspense>
            }
          />
          <Route
            path="training"
            element={
              <Suspense fallback={<PageLoader />}>
                <TrainingStudioPage />
              </Suspense>
            }
          />
          <Route
            path="synthesis"
            element={
              <Suspense fallback={<PageLoader />}>
                <SynthesisLabPage />
              </Suspense>
            }
          />
          <Route
            path="compare"
            element={
              <Suspense fallback={<PageLoader />}>
                <ComparisonPage />
              </Suspense>
            }
          />
          <Route
            path="providers"
            element={
              <Suspense fallback={<PageLoader />}>
                <ProvidersPage />
              </Suspense>
            }
          />
          <Route
            path="api-keys"
            element={
              <Suspense fallback={<PageLoader />}>
                <ApiKeysPage />
              </Suspense>
            }
          />
          <Route
            path="settings"
            element={
              <Suspense fallback={<PageLoader />}>
                <SettingsPage />
              </Suspense>
            }
          />
          <Route
            path="help"
            element={
              <Suspense fallback={<PageLoader />}>
                <HelpPage />
              </Suspense>
            }
          />
          <Route
            path="docs"
            element={
              <Suspense fallback={<PageLoader />}>
                <DocsPage />
              </Suspense>
            }
          />
          <Route
            path="admin"
            element={
              <Suspense fallback={<PageLoader />}>
                <AdminPage />
              </Suspense>
            }
          />
          <Route
            path="design"
            element={
              <Suspense fallback={<PageLoader />}>
                <DesignSystemPage />
              </Suspense>
            }
          />
          <Route
            path="healing"
            element={
              <Suspense fallback={<PageLoader />}>
                <HealingPage />
              </Suspense>
            }
          />
        </Route>
      </Routes>
      </ErrorBoundary>
    </>
  );
}

function PageLoader() {
  return (
    <div className="flex h-64 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-500 border-t-transparent" />
    </div>
  );
}

export default App;
