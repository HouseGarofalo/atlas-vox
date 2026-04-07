import { vi, describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import DocsPage from '../../pages/DocsPage';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

describe('DocsPage', () => {
  it('renders docs page heading', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Documentation')).toBeInTheDocument();
  });

  it('renders provider selector', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Select Provider')).toBeInTheDocument();
  });

  it('shows Kokoro guide by default', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    // Kokoro is the first provider guide
    expect(screen.getByText('No Setup Required')).toBeInTheDocument();
  });

  it('renders setup steps section', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Setup Steps')).toBeInTheDocument();
  });

  it('renders environment variables section', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Environment Variables')).toBeInTheDocument();
  });

  it('renders configuration checklist', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Configuration Checklist')).toBeInTheDocument();
  });

  it('renders tips section', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Tips & Best Practices')).toBeInTheDocument();
  });

  it('switching provider shows different content', () => {
    render(
      <MemoryRouter>
        <DocsPage />
      </MemoryRouter>,
    );
    // The Select component renders a native select element with label "Select Provider"
    const selectLabel = screen.getByText('Select Provider');
    const selectEl = selectLabel.closest('div')?.querySelector('select');
    expect(selectEl).toBeTruthy();
    fireEvent.change(selectEl!, { target: { value: 'elevenlabs' } });
    expect(screen.getByText('Create an ElevenLabs Account')).toBeInTheDocument();
  });
});
