import { vi, describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HelpPage from '../../pages/HelpPage';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe('HelpPage', () => {
  it('renders help center heading', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Help Center')).toBeInTheDocument();
  });

  it('renders all tabs', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Getting Started')).toBeInTheDocument();
    expect(screen.getByText('User Guide')).toBeInTheDocument();
    expect(screen.getByText('Troubleshooting')).toBeInTheDocument();
    expect(screen.getByText('API Reference')).toBeInTheDocument();
    expect(screen.getByText('About')).toBeInTheDocument();
  });

  it('shows Getting Started content by default', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Welcome to Atlas Vox')).toBeInTheDocument();
  });

  it('tab switching works - User Guide', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('User Guide'));
    expect(screen.getByText('Feature Guide')).toBeInTheDocument();
  });

  it('tab switching works - Troubleshooting', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Troubleshooting'));
    // Troubleshooting tab has a search input
    expect(screen.getByPlaceholderText('Search troubleshooting topics...')).toBeInTheDocument();
  });

  it('tab switching works - API Reference', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('API Reference'));
    expect(screen.getByText('Quick API Examples')).toBeInTheDocument();
  });

  it('tab switching works - About', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('About'));
    expect(screen.getByText('About Atlas Vox')).toBeInTheDocument();
  });

  it('getting started shows numbered steps', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Start Atlas Vox')).toBeInTheDocument();
    expect(screen.getByText('Open the Web UI')).toBeInTheDocument();
  });
});
