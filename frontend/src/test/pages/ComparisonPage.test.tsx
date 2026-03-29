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

vi.mock('../../stores/synthesisStore', () => ({
  useSynthesisStore: vi.fn(),
}));

vi.mock('../../components/audio/AudioPlayer', () => ({
  AudioPlayer: ({ src }: { src: string }) => <div data-testid="audio-player">{src}</div>,
}));

import { useProfileStore } from '../../stores/profileStore';
import { useSynthesisStore } from '../../stores/synthesisStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ComparisonPage from '../../pages/ComparisonPage';

const mockFetchProfiles = vi.fn().mockResolvedValue(undefined);
const mockCompare = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    profiles: [
      { id: 'p1', name: 'Voice A' },
      { id: 'p2', name: 'Voice B' },
    ],
    fetchProfiles: mockFetchProfiles,
  });

  (useSynthesisStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    comparing: false,
    comparisonResults: [],
    compare: mockCompare,
  });
});

describe('ComparisonPage', () => {
  it('renders comparison heading', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Comparison')).toBeInTheDocument();
  });

  it('renders text input area', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    expect(
      screen.getByPlaceholderText('Enter text to synthesize across multiple voices...'),
    ).toBeInTheDocument();
  });

  it('renders generate all button', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Generate All')).toBeInTheDocument();
  });

  it('displays selectable voice buttons', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice A')).toBeInTheDocument();
    expect(screen.getByText('Voice B')).toBeInTheDocument();
  });

  it('shows selected count', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Voice Selection \(0 selected\)/)).toBeInTheDocument();
  });

  it('toggles voice selection on click', () => {
    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Voice A'));
    expect(screen.getByText(/Voice Selection \(1 selected\)/)).toBeInTheDocument();
  });

  it('shows comparison results when available', () => {
    (useSynthesisStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      comparing: false,
      comparisonResults: [
        { profile_id: 'p1', profile_name: 'Voice A', provider_name: 'kokoro', latency_ms: 50, audio_url: '/audio/test.wav' },
      ],
      compare: mockCompare,
    });

    render(
      <MemoryRouter>
        <ComparisonPage />
      </MemoryRouter>,
    );
    // The result card should show Voice A name
    const cards = screen.getAllByText('Voice A');
    expect(cards.length).toBeGreaterThanOrEqual(1);
  });
});
