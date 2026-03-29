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

vi.mock('../../stores/providerStore', () => ({
  useProviderStore: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  api: {
    listProfiles: vi.fn(),
    createProfile: vi.fn(),
    deleteProfile: vi.fn(),
  },
}));

import { useProfileStore } from '../../stores/profileStore';
import { useProviderStore } from '../../stores/providerStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ProfilesPage from '../../pages/ProfilesPage';

const mockFetchProfiles = vi.fn().mockResolvedValue(undefined);
const mockFetchProviders = vi.fn().mockResolvedValue(undefined);
const mockCreateProfile = vi.fn().mockResolvedValue(undefined);
const mockDeleteProfile = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    profiles: [],
    loading: false,
    fetchProfiles: mockFetchProfiles,
    createProfile: mockCreateProfile,
    deleteProfile: mockDeleteProfile,
  });

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    providers: [],
    fetchProviders: mockFetchProviders,
  });
});

describe('ProfilesPage', () => {
  it('renders the profiles heading', () => {
    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Profiles')).toBeInTheDocument();
  });

  it('shows empty state when no profiles', () => {
    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('No profiles yet. Create your first voice profile.')).toBeInTheDocument();
  });

  it('renders profile list when profiles exist', () => {
    (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      profiles: [
        {
          id: '1',
          name: 'My Voice',
          description: 'Test voice',
          language: 'en',
          provider_name: 'kokoro',
          voice_id: null,
          status: 'ready',
          sample_count: 5,
          version_count: 2,
        },
      ],
      loading: false,
      fetchProfiles: mockFetchProfiles,
      createProfile: mockCreateProfile,
      deleteProfile: mockDeleteProfile,
    });

    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('My Voice')).toBeInTheDocument();
  });

  it('new profile button is present', () => {
    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('New Profile')).toBeInTheDocument();
  });

  it('clicking new profile button opens modal', () => {
    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('New Profile'));
    expect(screen.getByText('Create Voice Profile')).toBeInTheDocument();
  });

  it('shows loading state when loading and no profiles', () => {
    (useProfileStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      profiles: [],
      loading: true,
      fetchProfiles: mockFetchProfiles,
      createProfile: mockCreateProfile,
      deleteProfile: mockDeleteProfile,
    });

    render(
      <MemoryRouter>
        <ProfilesPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });
});
