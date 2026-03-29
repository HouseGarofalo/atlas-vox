import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../stores/providerStore', () => ({
  useProviderStore: vi.fn(),
}));

vi.mock('../../stores/adminStore', () => ({
  useAdminStore: vi.fn(),
}));

vi.mock('../../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

vi.mock('../../data/providerMetadata', () => ({
  PROVIDER_METADATA: {},
}));

import { useProviderStore } from '../../stores/providerStore';
import { useAdminStore } from '../../stores/adminStore';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProvidersPage from '../../pages/ProvidersPage';

const mockFetchProviders = vi.fn().mockResolvedValue(undefined);
const mockCheckAllHealth = vi.fn().mockResolvedValue(undefined);
const mockCheckHealth = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    providers: [],
    loading: false,
    fetchProviders: mockFetchProviders,
    checkAllHealth: mockCheckAllHealth,
    checkHealth: mockCheckHealth,
  });

  (useAdminStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    saveProviderConfig: vi.fn(),
    providerConfigs: {},
    loadingConfig: {},
    savingConfig: {},
    testResults: {},
    testingProvider: {},
    fetchProviderConfig: vi.fn(),
    testProvider: vi.fn(),
  });
});

describe('ProvidersPage', () => {
  it('renders the providers heading', () => {
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Providers')).toBeInTheDocument();
  });

  it('renders provider cards when providers exist', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [
        {
          name: 'kokoro',
          display_name: 'Kokoro',
          provider_type: 'local',
          enabled: true,
          gpu_mode: 'none',
          capabilities: null,
          health: { healthy: true, latency_ms: 10, error: null },
        },
      ],
      loading: false,
      fetchProviders: mockFetchProviders,
      checkAllHealth: mockCheckAllHealth,
      checkHealth: mockCheckHealth,
    });

    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Kokoro')).toBeInTheDocument();
  });

  it('shows health status badges', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [
        {
          name: 'kokoro',
          display_name: 'Kokoro',
          provider_type: 'local',
          enabled: true,
          gpu_mode: 'none',
          capabilities: null,
          health: { healthy: true, latency_ms: 10, error: null },
        },
      ],
      loading: false,
      fetchProviders: mockFetchProviders,
      checkAllHealth: mockCheckAllHealth,
      checkHealth: mockCheckHealth,
    });

    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('healthy')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [],
      loading: true,
      fetchProviders: mockFetchProviders,
      checkAllHealth: mockCheckAllHealth,
      checkHealth: mockCheckHealth,
    });

    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('shows refresh button', () => {
    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Refresh All')).toBeInTheDocument();
  });

  it('does NOT call checkAllHealth on mount', () => {
    // Reset mocks and re-configure to track checkAllHealth
    vi.clearAllMocks();
    const localMockCheckAllHealth = vi.fn();
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [],
      loading: false,
      error: null,
      fetchProviders: vi.fn().mockResolvedValue(undefined),
      checkHealth: vi.fn(),
      checkAllHealth: localMockCheckAllHealth,
    });

    (useAdminStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      saveProviderConfig: vi.fn(),
      providerConfigs: {},
      loadingConfig: {},
      savingConfig: {},
      testResults: {},
      testingProvider: {},
      fetchProviderConfig: vi.fn(),
      testProvider: vi.fn(),
    });

    render(
      <MemoryRouter>
        <ProvidersPage />
      </MemoryRouter>,
    );
    // ProvidersPage only calls fetchProviders() on mount, not checkAllHealth
    expect(localMockCheckAllHealth).not.toHaveBeenCalled();
  });
});
