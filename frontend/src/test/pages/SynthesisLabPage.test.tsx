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

vi.mock('../../services/api', () => ({
  api: {
    listPresets: vi.fn().mockResolvedValue({ presets: [] }),
  },
}));

vi.mock('../../components/audio/AudioPlayer', () => ({
  AudioPlayer: ({ src }: { src: string }) => <div data-testid="audio-player">{src}</div>,
}));

import { useProfileStore } from '../../stores/profileStore';
import { useSynthesisStore } from '../../stores/synthesisStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SynthesisLabPage from '../../pages/SynthesisLabPage';

const mockFetchProfiles = vi.fn().mockResolvedValue(undefined);
const mockSynthesize = vi.fn().mockResolvedValue(undefined);
const mockFetchHistory = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    profiles: [],
    fetchProfiles: mockFetchProfiles,
  });

  (useSynthesisStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    lastResult: null,
    loading: false,
    synthesize: mockSynthesize,
    fetchHistory: mockFetchHistory,
    history: [],
  });
});

describe('SynthesisLabPage', () => {
  it('renders the synthesis lab heading', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Synthesis Lab')).toBeInTheDocument();
  });

  it('renders text area for input', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByPlaceholderText('Enter text to synthesize...')).toBeInTheDocument();
  });

  it('text area accepts input', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    const textarea = screen.getByPlaceholderText('Enter text to synthesize...');
    fireEvent.change(textarea, { target: { value: 'Hello world' } });
    expect(textarea).toHaveValue('Hello world');
  });

  it('renders voice profile selector', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Profile')).toBeInTheDocument();
  });

  it('renders speed, pitch, and volume sliders', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Speed')).toBeInTheDocument();
    expect(screen.getByText('Pitch')).toBeInTheDocument();
    expect(screen.getByText('Volume')).toBeInTheDocument();
  });

  it('synthesize button is present', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Synthesize')).toBeInTheDocument();
  });

  it('synthesize button is disabled when no text or profile', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    const btn = screen.getByText('Synthesize');
    expect(btn.closest('button')).toBeDisabled();
  });

  it('shows character count', () => {
    render(
      <MemoryRouter>
        <SynthesisLabPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('0 / 10000 characters')).toBeInTheDocument();
  });
});
