import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../stores/settingsStore', () => ({
  useSettingsStore: vi.fn(),
}));

vi.mock('../../stores/providerStore', () => ({
  useProviderStore: vi.fn(),
}));

import { useSettingsStore } from '../../stores/settingsStore';
import { useProviderStore } from '../../stores/providerStore';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SettingsPage from '../../pages/SettingsPage';

const mockToggleTheme = vi.fn();
const mockSetDefaultProvider = vi.fn();
const mockSetAudioFormat = vi.fn();
const mockFetchProviders = vi.fn().mockResolvedValue(undefined);

beforeEach(() => {
  vi.clearAllMocks();

  (useSettingsStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    theme: 'light',
    defaultProvider: 'kokoro',
    audioFormat: 'wav',
    toggleTheme: mockToggleTheme,
    setDefaultProvider: mockSetDefaultProvider,
    setAudioFormat: mockSetAudioFormat,
  });

  (useProviderStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    providers: [
      { name: 'kokoro', display_name: 'Kokoro' },
      { name: 'piper', display_name: 'Piper' },
    ],
    fetchProviders: mockFetchProviders,
  });
});

describe('SettingsPage', () => {
  it('renders settings heading', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders appearance section', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Appearance')).toBeInTheDocument();
  });

  it('shows theme toggle button', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Switch to Dark')).toBeInTheDocument();
  });

  it('renders default provider selector', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Default Provider')).toBeInTheDocument();
  });

  it('renders defaults section', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Defaults')).toBeInTheDocument();
  });

  it('renders about section', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('About')).toBeInTheDocument();
    expect(screen.getByText('Atlas Vox v0.1.0')).toBeInTheDocument();
  });

  it('shows audio format selector', () => {
    render(
      <MemoryRouter>
        <SettingsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Default Audio Format')).toBeInTheDocument();
  });
});
