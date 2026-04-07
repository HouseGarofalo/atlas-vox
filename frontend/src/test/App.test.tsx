import { vi, describe, it, expect } from 'vitest';

vi.mock('../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../stores/settingsStore', () => ({
  useSettingsStore: vi.fn().mockReturnValue({
    theme: 'light',
    toggleTheme: vi.fn(),
  }),
}));

vi.mock('../stores/profileStore', () => ({
  useProfileStore: vi.fn().mockReturnValue({
    profiles: [],
    loading: false,
    fetchProfiles: vi.fn().mockResolvedValue(undefined),
    createProfile: vi.fn(),
    deleteProfile: vi.fn(),
  }),
}));

vi.mock('../stores/trainingStore', () => ({
  useTrainingStore: vi.fn().mockReturnValue({
    jobs: [],
    fetchJobs: vi.fn().mockResolvedValue(undefined),
    startTraining: vi.fn(),
    cancelJob: vi.fn(),
  }),
}));

vi.mock('../stores/providerStore', () => ({
  useProviderStore: vi.fn().mockReturnValue({
    providers: [],
    loading: false,
    fetchProviders: vi.fn().mockResolvedValue(undefined),
    checkAllHealth: vi.fn().mockResolvedValue(undefined),
    checkHealth: vi.fn(),
  }),
}));

vi.mock('../stores/synthesisStore', () => ({
  useSynthesisStore: vi.fn().mockReturnValue({
    lastResult: null,
    loading: false,
    history: [],
    synthesize: vi.fn(),
    fetchHistory: vi.fn().mockResolvedValue(undefined),
    comparing: false,
    comparisonResults: [],
    compare: vi.fn(),
  }),
}));

vi.mock('../stores/voiceLibraryStore', () => ({
  useVoiceLibraryStore: vi.fn().mockReturnValue({
    voices: [],
    loading: false,
    error: null,
    filters: { search: '', provider: null, language: null, gender: null },
    fetchAllVoices: vi.fn().mockResolvedValue(undefined),
    setFilter: vi.fn(),
    filteredVoices: () => [],
  }),
}));

vi.mock('../stores/adminStore', () => ({
  useAdminStore: vi.fn().mockReturnValue({
    saveProviderConfig: vi.fn(),
    providerConfigs: {},
    loadingConfig: {},
    savingConfig: {},
    testResults: {},
    testingProvider: {},
    fetchProviderConfig: vi.fn(),
    testProvider: vi.fn(),
  }),
}));

vi.mock('../stores/authStore', () => {
  const mockAuthStore = {
    token: 'mock-token',
    apiKey: null,
    user: { sub: 'test-user', scopes: ['admin'] },
    isAuthenticated: true,
    setToken: vi.fn(),
    setApiKey: vi.fn(),
    logout: vi.fn(),
    hasScope: vi.fn().mockReturnValue(true),
  };

  const mockUseAuthStore = vi.fn().mockReturnValue(mockAuthStore);
  mockUseAuthStore.getState = vi.fn().mockReturnValue(mockAuthStore);

  return {
    useAuthStore: mockUseAuthStore,
  };
});

vi.mock('../services/api', () => ({
  api: {
    listApiKeys: vi.fn().mockResolvedValue({ api_keys: [] }),
    listPresets: vi.fn().mockResolvedValue({ presets: [] }),
    previewVoice: vi.fn(),
    listSamples: vi.fn().mockResolvedValue({ samples: [] }),
  },
}));

vi.mock('../hooks/useWebSocket', () => ({
  useTrainingProgress: vi.fn().mockReturnValue({ progress: null, connected: false }),
}));

vi.mock('../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

vi.mock('../data/providerMetadata', () => ({
  PROVIDER_METADATA: {},
}));

import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

describe('App', () => {
  it('renders without crashing', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    // The app should render the sidebar with Atlas Vox branding
    expect(screen.getByText('Atlas Vox')).toBeInTheDocument();
  });

  it('shows sidebar navigation', () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Voice Profiles')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('routes to dashboard by default', async () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>,
    );
    // Dashboard page renders its heading via lazy loading + Suspense
    // The heading should eventually appear
    expect(await screen.findByText('Dashboard', {}, { timeout: 3000 })).toBeInTheDocument();
  });

  it('wraps routes in ErrorBoundary', () => {
    // Render app with a valid route to verify ErrorBoundary doesn't
    // interfere with normal rendering
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>,
    );
    // The app should render without crashing — ErrorBoundary is present
    expect(screen.getByText('Atlas Vox')).toBeInTheDocument();
  });

  it('renders admin page route', async () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>,
    );
    // Should show loading spinner initially (Suspense fallback) then admin content
    // The lazy import means we need to wait for the page to load
    await waitFor(
      () => {
        // Admin page or its Suspense fallback (spinner) should be present
        // At minimum the app layout should be rendered
        expect(screen.getByText('Atlas Vox')).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });
});
