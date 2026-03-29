import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../services/api', () => ({
  api: {
    listApiKeys: vi.fn().mockResolvedValue({ api_keys: [] }),
    createApiKey: vi.fn(),
    revokeApiKey: vi.fn(),
  },
}));

import { api } from '../../services/api';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ApiKeysPage from '../../pages/ApiKeysPage';

beforeEach(() => {
  vi.clearAllMocks();
  (api.listApiKeys as ReturnType<typeof vi.fn>).mockResolvedValue({ api_keys: [] });
});

describe('ApiKeysPage', () => {
  it('renders the API Keys heading', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('API Keys')).toBeInTheDocument();
  });

  it('shows create button', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('New Key')).toBeInTheDocument();
  });

  it('shows empty state when no keys', async () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    // Initially there are no keys so it shows the empty state
    expect(await screen.findByText('No API keys yet.')).toBeInTheDocument();
  });

  it('clicking new key opens create modal', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('New Key'));
    expect(screen.getByText('Create API Key')).toBeInTheDocument();
  });

  it('create modal shows key name input', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('New Key'));
    expect(screen.getByPlaceholderText('My API Key')).toBeInTheDocument();
  });

  it('create modal shows scope buttons', () => {
    render(
      <MemoryRouter>
        <ApiKeysPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('New Key'));
    expect(screen.getByText('read')).toBeInTheDocument();
    expect(screen.getByText('write')).toBeInTheDocument();
    expect(screen.getByText('synthesize')).toBeInTheDocument();
    expect(screen.getByText('train')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
  });
});
