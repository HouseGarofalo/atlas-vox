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

vi.mock('../../hooks/useWebSocket', () => ({
  useTrainingProgress: vi.fn().mockReturnValue({ progress: null, connected: false }),
}));

vi.mock('../../services/api', () => ({
  api: {
    listSamples: vi.fn().mockResolvedValue({ samples: [] }),
    uploadSamples: vi.fn(),
    preprocessSamples: vi.fn(),
  },
}));

vi.mock('../../components/audio/AudioRecorder', () => ({
  AudioRecorder: () => <div data-testid="audio-recorder">Recorder</div>,
  FileUploader: () => <div data-testid="file-uploader">Upload Area</div>,
}));

import { useProfileStore } from '../../stores/profileStore';
import { useTrainingStore } from '../../stores/trainingStore';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import TrainingStudioPage from '../../pages/TrainingStudioPage';

const mockFetchProfiles = vi.fn().mockResolvedValue(undefined);
const mockFetchJobs = vi.fn().mockResolvedValue(undefined);
const mockStartTraining = vi.fn().mockResolvedValue({ id: 'job1' });
const mockCancelJob = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    profiles: [
      { id: 'p1', name: 'Test Voice', provider_name: 'coqui_xtts' },
    ],
    fetchProfiles: mockFetchProfiles,
  });

  (useTrainingStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    jobs: [],
    fetchJobs: mockFetchJobs,
    startTraining: mockStartTraining,
    cancelJob: mockCancelJob,
  });
});

describe('TrainingStudioPage', () => {
  it('renders the training studio heading', () => {
    render(
      <MemoryRouter>
        <TrainingStudioPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Training Studio')).toBeInTheDocument();
  });

  it('renders profile selector', () => {
    render(
      <MemoryRouter>
        <TrainingStudioPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Profile')).toBeInTheDocument();
  });

  it('shows select a profile placeholder', () => {
    render(
      <MemoryRouter>
        <TrainingStudioPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Select a profile...')).toBeInTheDocument();
  });

  it('calls fetchProfiles and fetchJobs on mount', () => {
    render(
      <MemoryRouter>
        <TrainingStudioPage />
      </MemoryRouter>,
    );
    expect(mockFetchProfiles).toHaveBeenCalled();
    expect(mockFetchJobs).toHaveBeenCalled();
  });
});
