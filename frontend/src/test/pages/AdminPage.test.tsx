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

vi.mock('../../components/admin/ProviderConfigCard', () => ({
  default: ({ provider }: { provider: { name: string; display_name: string } }) => (
    <div data-testid={`provider-config-${provider.name}`}>{provider.display_name}</div>
  ),
}));

import { useProviderStore } from '../../stores/providerStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AdminPage from '../../pages/AdminPage';

const mockFetchProviders = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    providers: [],
    loading: false,
    fetchProviders: mockFetchProviders,
  });
});

describe('AdminPage', () => {
  it('renders admin heading', () => {
    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Admin')).toBeInTheDocument();
  });

  it('renders refresh button', () => {
    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Refresh')).toBeInTheDocument();
  });

  it('shows no providers message when empty', () => {
    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('No providers found.')).toBeInTheDocument();
  });

  it('renders provider config cards when providers exist', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [
        { name: 'kokoro', display_name: 'Kokoro', enabled: true, health: null },
      ],
      loading: false,
      fetchProviders: mockFetchProviders,
    });

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('provider-config-kokoro')).toBeInTheDocument();
  });

  it('calls fetchProviders on mount', () => {
    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    expect(mockFetchProviders).toHaveBeenCalled();
  });

  it('clicking refresh calls fetchProviders again', () => {
    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    mockFetchProviders.mockClear();
    fireEvent.click(screen.getByText('Refresh'));
    expect(mockFetchProviders).toHaveBeenCalled();
  });

  it('disables refresh button while loading', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [],
      loading: true,
      fetchProviders: mockFetchProviders,
    });

    render(
      <MemoryRouter>
        <AdminPage />
      </MemoryRouter>,
    );
    const refreshBtn = screen.getByText('Refresh').closest('button');
    expect(refreshBtn).toBeDisabled();
  });
});
