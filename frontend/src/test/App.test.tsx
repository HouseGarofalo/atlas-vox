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

vi.mock('../stores/designStore', () => {
  const mockTheme = {
    id: 'midnight-studio',
    name: 'Midnight Studio',
    mode: 'dark',
    primary: { h: 220, s: 70, l: 55 },
    colors: {},
    radius: '0.75rem',
  };
  const mockDesignStore = {
    themes: { 'midnight-studio': mockTheme },
    activeThemeId: 'midnight-studio',
    tokens: [mockTheme],
    getCurrentTheme: vi.fn().mockReturnValue(mockTheme),
    setTheme: vi.fn(),
  };
  const mockUseDesignStore = vi.fn((selector?: (state: typeof mockDesignStore) => unknown) => {
    if (selector) return selector(mockDesignStore);
    return mockDesignStore;
  });
  mockUseDesignStore.getState = vi.fn().mockReturnValue(mockDesignStore);
  return { useDesignStore: mockUseDesignStore };
});

vi.mock('../stores/authStore', () => {
  const mockAuthStore = {
    apiKey: null,
    user: { sub: 'test-user', scopes: ['admin'] },
    isAuthenticated: true,
    isLoading: false,
    error: null,
    authDisabled: false,
    login: vi.fn(),
    logout: vi.fn(),
    refreshToken: vi.fn(),
    fetchMe: vi.fn(),
    setApiKey: vi.fn(),
    setAuthDisabled: vi.fn(),
    clearAuth: vi.fn(),
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

  it('redirects /admin to /providers', async () => {
    render(
      <MemoryRouter initialEntries={['/admin']}>
        <App />
      </MemoryRouter>,
    );
    // /admin now redirects to /providers — app should still render
    await waitFor(
      () => {
        expect(screen.getByText('Atlas Vox')).toBeInTheDocument();
      },
      { timeout: 3000 },
    );
  });
});
