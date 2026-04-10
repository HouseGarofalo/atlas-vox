import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../stores/voiceLibraryStore', () => ({
  useVoiceLibraryStore: vi.fn(),
}));

vi.mock('../../stores/profileStore', () => ({
  useProfileStore: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  api: {
    previewVoice: vi.fn(),
  },
}));

vi.mock('../../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

vi.mock('../../hooks/useAudioPlayer', () => ({
  useAudioPlayer: () => ({
    isPlaying: false,
    currentUrl: null,
    loading: false,
    duration: 0,
    currentTime: 0,
    play: vi.fn(),
    pause: vi.fn(),
    stop: vi.fn(),
    toggle: vi.fn(),
    seek: vi.fn(),
    setVolume: vi.fn(),
    setPlaybackRate: vi.fn(),
  }),
}));

vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock('react-virtuoso', () => ({
  VirtuosoGrid: ({ totalCount, itemContent }: { totalCount: number; itemContent: (index: number) => React.ReactNode }) => (
    <div data-testid="virtuoso-grid">
      {Array.from({ length: totalCount }).map((_, i) => (
        <div key={i}>{itemContent(i)}</div>
      ))}
    </div>
  ),
}));

import { useVoiceLibraryStore } from '../../stores/voiceLibraryStore';
import { useProfileStore } from '../../stores/profileStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import VoiceLibraryPage from '../../pages/VoiceLibraryPage';

const mockFetchAllVoices = vi.fn().mockResolvedValue(undefined);
const mockSetFilter = vi.fn();
const mockCreateProfile = vi.fn().mockResolvedValue({ name: 'Test' });

beforeEach(() => {
  vi.clearAllMocks();

  (useVoiceLibraryStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    voices: [],
    loading: false,
    error: null,
    filters: { search: '', provider: null, language: null, gender: null },
    fetchAllVoices: mockFetchAllVoices,
    setFilter: mockSetFilter,
    filteredVoices: () => [],
  });

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    createProfile: mockCreateProfile,
  });
});

describe('VoiceLibraryPage', () => {
  it('renders voice library heading', () => {
    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Library')).toBeInTheDocument();
  });

  it('renders search input', () => {
    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText(/Search voices/i)).toBeInTheDocument();
  });

  it('renders filter dropdowns', () => {
    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('All Providers')).toBeInTheDocument();
    expect(screen.getByText('All Languages')).toBeInTheDocument();
    expect(screen.getByText('All Genders')).toBeInTheDocument();
  });

  it('shows loading skeleton when loading', () => {
    (useVoiceLibraryStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      voices: [],
      loading: true,
      error: null,
      filters: { search: '', provider: null, language: null, gender: null },
      fetchAllVoices: mockFetchAllVoices,
      setFilter: mockSetFilter,
      filteredVoices: () => [],
    });

    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    // Loading skeleton cards have animate-pulse class
    const skeletonCards = document.querySelectorAll('.animate-pulse');
    expect(skeletonCards.length).toBeGreaterThan(0);
  });

  it('shows empty state when no voices and not loading', () => {
    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('No Voices Available')).toBeInTheDocument();
  });

  it('renders voice cards when voices exist', () => {
    (useVoiceLibraryStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      voices: [
        {
          voice_id: 'af_heart',
          name: 'Heart',
          language: 'en',
          provider: 'kokoro',
          provider_display: 'Kokoro',
        },
      ],
      loading: false,
      error: null,
      filters: { search: '', provider: null, language: null, gender: null },
      fetchAllVoices: mockFetchAllVoices,
      setFilter: mockSetFilter,
      filteredVoices: () => [
        {
          voice_id: 'af_heart',
          name: 'Heart',
          language: 'en',
          provider: 'kokoro',
          provider_display: 'Kokoro',
        },
      ],
    });

    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Heart')).toBeInTheDocument();
    expect(screen.getByText('Create Profile')).toBeInTheDocument();
  });

  it('shows error state', () => {
    (useVoiceLibraryStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      voices: [],
      loading: false,
      error: 'Network error',
      filters: { search: '', provider: null, language: null, gender: null },
      fetchAllVoices: mockFetchAllVoices,
      setFilter: mockSetFilter,
      filteredVoices: () => [],
    });

    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByText('Failed to load voice library: Network error'),
    ).toBeInTheDocument();
  });

  it('calls fetchAllVoices on mount', () => {
    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );
    expect(mockFetchAllVoices).toHaveBeenCalled();
  });

  it('debounces search input', () => {
    vi.useFakeTimers();

    render(
      <MemoryRouter>
        <VoiceLibraryPage />
      </MemoryRouter>,
    );

    const searchInput = screen.getByPlaceholderText(/Search voices/i);
    fireEvent.change(searchInput, { target: { value: 'test' } });

    // setFilter should NOT have been called yet with the search value
    // (it may have been called with other filter types on mount, so check specifically)
    expect(mockSetFilter).not.toHaveBeenCalledWith('search', 'test');

    // Advance timers by 300ms (the debounce delay)
    vi.advanceTimersByTime(300);

    // Now setFilter should have been called with the search value
    expect(mockSetFilter).toHaveBeenCalledWith('search', 'test');

    vi.useRealTimers();
  });
});
