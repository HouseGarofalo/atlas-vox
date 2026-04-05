import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../stores/audioDesignStore', () => ({
  useAudioDesignStore: vi.fn(),
}));

vi.mock('../../stores/providerStore', () => ({
  useProviderStore: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  api: {
    fullAudioUrl: vi.fn((url: string) => `http://localhost:8000${url}`),
    listPresets: vi.fn().mockResolvedValue({ presets: [] }),
    speechToSpeech: vi.fn().mockResolvedValue({}),
    designVoice: vi.fn().mockResolvedValue({ previews: [] }),
    generateSoundEffect: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../../components/audio/AudioTimeline', () => ({
  AudioTimeline: ({ src }: { src: string }) => (
    <div data-testid="audio-timeline">{src}</div>
  ),
}));

import { useAudioDesignStore } from '../../stores/audioDesignStore';
import { useProviderStore } from '../../stores/providerStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AudioDesignPage from '../../pages/AudioDesignPage';

// ── shared mock data ────────────────────────────────────────────────────────

const mockClip = {
  file_id: 'clip-001',
  filename: 'clip-001.wav',
  original_filename: 'recording.wav',
  duration_seconds: 5.0,
  sample_rate: 44100,
  channels: 1,
  format: 'wav',
  file_size_bytes: 88200,
  audio_url: '/audio/clip-001.wav',
};

const mockClip2 = {
  file_id: 'clip-002',
  filename: 'clip-002.wav',
  original_filename: 'narration.wav',
  duration_seconds: 3.2,
  sample_rate: 22050,
  channels: 1,
  format: 'wav',
  file_size_bytes: 56448,
  audio_url: '/audio/clip-002.wav',
};

const defaultEffects = [
  { type: 'noise_reduction', enabled: false, strength: 0.5 },
  { type: 'normalize', enabled: false, target_db: -3 },
  { type: 'trim_silence', enabled: false, threshold_db: -40 },
  { type: 'gain', enabled: false, gain_db: 0 },
];

const mockFetchFiles = vi.fn().mockResolvedValue(undefined);
const mockFetchProviders = vi.fn().mockResolvedValue(undefined);
const mockRemoveClip = vi.fn().mockResolvedValue(undefined);
const mockSetSelectedClip = vi.fn();
const mockSetProcessingEngine = vi.fn();
const mockClearError = vi.fn();
const mockConcatClips = vi.fn().mockResolvedValue({});
const mockApplyEffects = vi.fn().mockResolvedValue({});
const mockAnalyzeClip = vi.fn().mockResolvedValue({});
const mockIsolateClip = vi.fn().mockResolvedValue({});
const mockExportClip = vi.fn().mockResolvedValue({ audio_url: '/export/out.wav', filename: 'out.wav' });
const mockUploadClip = vi.fn().mockResolvedValue({});
const mockTrimClip = vi.fn().mockResolvedValue({});
const mockUpdateEffect = vi.fn();
const mockSetExportFormat = vi.fn();
const mockSetExportSampleRate = vi.fn();

function makeStoreDefaults(overrides: Partial<ReturnType<typeof useAudioDesignStore>> = {}) {
  return {
    clips: [],
    selectedClipId: null,
    analysis: null,
    processingEngine: 'local' as const,
    effects: defaultEffects,
    exportFormat: 'wav',
    exportSampleRate: null,
    loading: false,
    processing: false,
    error: null,
    fetchFiles: mockFetchFiles,
    uploadClip: mockUploadClip,
    removeClip: mockRemoveClip,
    trimClip: mockTrimClip,
    concatClips: mockConcatClips,
    applyEffects: mockApplyEffects,
    analyzeClip: mockAnalyzeClip,
    isolateClip: mockIsolateClip,
    exportClip: mockExportClip,
    setSelectedClip: mockSetSelectedClip,
    setProcessingEngine: mockSetProcessingEngine,
    updateEffect: mockUpdateEffect,
    setExportFormat: mockSetExportFormat,
    setExportSampleRate: mockSetExportSampleRate,
    clearError: mockClearError,
    resetEffects: vi.fn(),
    ...overrides,
  };
}

function makeProviderDefaults(overrides: Partial<ReturnType<typeof useProviderStore>> = {}) {
  return {
    providers: [],
    fetchProviders: mockFetchProviders,
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();

  (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
    makeStoreDefaults(),
  );

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
    makeProviderDefaults(),
  );
});

// ── helpers ─────────────────────────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter>
      <AudioDesignPage />
    </MemoryRouter>,
  );
}

// ── tests ────────────────────────────────────────────────────────────────────

describe('AudioDesignPage', () => {
  it('renders heading "Audio Design Studio"', () => {
    renderPage();
    expect(screen.getByText('Audio Design Studio')).toBeInTheDocument();
  });

  it('shows drop zone when no clips exist', () => {
    renderPage();
    expect(screen.getByText('Drop audio files here')).toBeInTheDocument();
    expect(screen.getByText('WAV, MP3, OGG, FLAC, M4A supported')).toBeInTheDocument();
  });

  it('shows Import Audio button', () => {
    renderPage();
    expect(screen.getByText('Import Audio')).toBeInTheDocument();
  });

  it('shows clips list panel when clips exist', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip] }),
    );

    renderPage();

    expect(screen.getByText('Audio Clips (1)')).toBeInTheDocument();
    expect(screen.getByText('recording.wav')).toBeInTheDocument();
  });

  it('shows the effects chain panel', () => {
    renderPage();
    expect(screen.getByText('Effects Chain')).toBeInTheDocument();
  });

  it('shows ElevenLabs tools panel when engine is elevenlabs and provider is available', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ processingEngine: 'elevenlabs' }),
    );
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeProviderDefaults({
        providers: [
          {
            id: 'elevenlabs',
            enabled: true,
            health: { healthy: true },
          } as any,
        ],
      }),
    );

    renderPage();

    expect(screen.getByText('ElevenLabs Tools')).toBeInTheDocument();
    expect(screen.getByText('Audio Isolation')).toBeInTheDocument();
    expect(screen.getByText('Speech-to-Speech')).toBeInTheDocument();
    expect(screen.getByText('Voice Design')).toBeInTheDocument();
    expect(screen.getByText('Sound Effects')).toBeInTheDocument();
  });

  it('hides ElevenLabs tools panel when engine is local', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ processingEngine: 'local' }),
    );
    (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeProviderDefaults({
        providers: [
          {
            id: 'elevenlabs',
            enabled: true,
            health: { healthy: true },
          } as any,
        ],
      }),
    );

    renderPage();

    expect(screen.queryByText('ElevenLabs Tools')).not.toBeInTheDocument();
  });

  it('shows export panel with format options', () => {
    renderPage();

    expect(screen.getByText('Export')).toBeInTheDocument();
    expect(screen.getByText('Format')).toBeInTheDocument();
    expect(screen.getByText('WAV (lossless)')).toBeInTheDocument();
    expect(screen.getByText('MP3')).toBeInTheDocument();
    expect(screen.getByText('OGG Vorbis')).toBeInTheDocument();
    expect(screen.getByText('FLAC (lossless)')).toBeInTheDocument();
  });

  it('shows error alert when error state is set', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ error: 'Something went wrong' }),
    );

    renderPage();

    const alert = screen.getByRole('alert');
    expect(alert).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('calls clearError when the dismiss button is clicked', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ error: 'Upload failed' }),
    );

    renderPage();

    fireEvent.click(screen.getByLabelText('Dismiss error'));
    expect(mockClearError).toHaveBeenCalledTimes(1);
  });

  it('shows delete confirmation dialog when delete icon is clicked on a clip', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip] }),
    );

    renderPage();

    const deleteButton = screen.getByLabelText(`Delete ${mockClip.original_filename}`);
    fireEvent.click(deleteButton);

    expect(screen.getByLabelText('Confirm delete')).toBeInTheDocument();
    expect(screen.getByLabelText('Cancel delete')).toBeInTheDocument();
  });

  it('hides delete confirmation dialog when cancel is clicked', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip] }),
    );

    renderPage();

    fireEvent.click(screen.getByLabelText(`Delete ${mockClip.original_filename}`));
    expect(screen.getByLabelText('Confirm delete')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Cancel delete'));
    expect(screen.queryByLabelText('Confirm delete')).not.toBeInTheDocument();
  });

  it('Select All button selects all clips for joining', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip, mockClip2] }),
    );

    renderPage();

    const selectAllButton = screen.getByLabelText('Select all');
    fireEvent.click(selectAllButton);

    // After selecting all, the clip join checkboxes should be checked
    const joinCheckboxes = screen.getAllByLabelText(/Select .* for joining/);
    expect(joinCheckboxes).toHaveLength(2);
    joinCheckboxes.forEach((cb) => expect(cb).toBeChecked());
  });

  it('shows crossfade slider when 2 or more clips are selected for joining', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip, mockClip2] }),
    );

    renderPage();

    // Select both clips via their checkboxes
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    expect(screen.getByText('Crossfade')).toBeInTheDocument();
  });

  it('does not show crossfade slider when fewer than 2 clips are selected', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip, mockClip2] }),
    );

    renderPage();

    // Select only one clip
    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);

    expect(screen.queryByText('Crossfade')).not.toBeInTheDocument();
  });

  it('shows Join button with count when 2 or more clips are selected', () => {
    (useAudioDesignStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(
      makeStoreDefaults({ clips: [mockClip, mockClip2] }),
    );

    renderPage();

    const checkboxes = screen.getAllByRole('checkbox');
    fireEvent.click(checkboxes[0]);
    fireEvent.click(checkboxes[1]);

    expect(screen.getByText('Join (2)')).toBeInTheDocument();
  });

  it('shows the Processing Engine panel with local and ElevenLabs options', () => {
    renderPage();

    expect(screen.getByText('Processing Engine')).toBeInTheDocument();
    expect(screen.getByText('Local (Built-in)')).toBeInTheDocument();
    expect(screen.getByText('ElevenLabs')).toBeInTheDocument();
  });

  it('shows export sample rate selector', () => {
    renderPage();

    expect(screen.getByText('Sample Rate')).toBeInTheDocument();
    expect(screen.getByText('Original')).toBeInTheDocument();
    expect(screen.getByText('44.1 kHz (CD)')).toBeInTheDocument();
  });
});
