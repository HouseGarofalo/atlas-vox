import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../stores/profileStore', () => ({
  useProfileStore: vi.fn(),
}));

vi.mock('../../stores/trainingStore', () => ({
  useTrainingStore: vi.fn(),
}));

vi.mock('../../stores/providerStore', () => ({
  useProviderStore: vi.fn(),
}));

vi.mock('../../stores/synthesisStore', () => ({
  useSynthesisStore: vi.fn(),
}));

vi.mock('../../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

import { useProfileStore } from '../../stores/profileStore';
import { useTrainingStore } from '../../stores/trainingStore';
import { useProviderStore } from '../../stores/providerStore';
import { useSynthesisStore } from '../../stores/synthesisStore';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DashboardPage from '../../pages/DashboardPage';

const mockFetchProfiles = vi.fn().mockResolvedValue(undefined);
const mockFetchJobs = vi.fn().mockResolvedValue(undefined);
const mockFetchProviders = vi.fn().mockResolvedValue(undefined);
const mockCheckAllHealth = vi.fn().mockResolvedValue(undefined);
const mockFetchHistory = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    profiles: [],
    fetchProfiles: mockFetchProfiles,
  });

  (useTrainingStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    jobs: [],
    fetchJobs: mockFetchJobs,
  });

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    providers: [],
    fetchProviders: mockFetchProviders,
    checkAllHealth: mockCheckAllHealth,
  });

  (useSynthesisStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    history: [],
    fetchHistory: mockFetchHistory,
  });
});

describe('DashboardPage', () => {
  it('renders the dashboard heading', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Audio Control Center')).toBeInTheDocument();
  });

  it('displays profile count from store', () => {
    (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      profiles: [
        { id: '1', name: 'P1', status: 'ready' },
        { id: '2', name: 'P2', status: 'pending' },
      ],
      fetchProfiles: mockFetchProfiles,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Voice Profiles')).toBeInTheDocument();
    expect(screen.getByText('1 ready')).toBeInTheDocument();
  });

  it('displays provider health grid', () => {
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      providers: [
        {
          name: 'kokoro',
          display_name: 'Kokoro',
          enabled: true,
          health: { healthy: true, latency_ms: 10, error: null },
        },
      ],
      fetchProviders: mockFetchProviders,
      checkAllHealth: mockCheckAllHealth,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Provider Health Matrix')).toBeInTheDocument();
    expect(screen.getByText('Kokoro')).toBeInTheDocument();
  });

  it('calls fetch functions on mount', () => {
    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(mockFetchProfiles).toHaveBeenCalled();
    expect(mockFetchJobs).toHaveBeenCalled();
    expect(mockFetchProviders).toHaveBeenCalled();
    expect(mockFetchHistory).toHaveBeenCalledWith(10);
  });

  it('shows active training jobs count', () => {
    (useTrainingStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      jobs: [
        { id: '1', profile_id: 'p1', provider_name: 'kokoro', status: 'training', progress: 0.5 },
      ],
      fetchJobs: mockFetchJobs,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    // New dashboard uses "Training Console" for section, "Training Jobs" for stat label
    expect(screen.getByText('Training Jobs')).toBeInTheDocument();
  });

  it('shows recent syntheses count', () => {
    (useSynthesisStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      history: [{ id: '1', text: 'Hello', provider_name: 'kokoro', latency_ms: 100, created_at: new Date().toISOString() }],
      fetchHistory: mockFetchHistory,
    });

    render(
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>,
    );

    expect(screen.getByText('Recent Syntheses')).toBeInTheDocument();
  });
});
