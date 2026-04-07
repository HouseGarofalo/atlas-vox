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

vi.mock('../../components/providers/ProviderLogo', () => ({
  default: ({ name }: { name: string }) => <span data-testid="provider-logo">{name}</span>,
}));

describe('HelpPage', () => {
  it('renders help page heading', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Help & Documentation')).toBeInTheDocument();
  });

  it('renders group buttons', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Guide')).toBeInTheDocument();
    expect(screen.getByText('Reference')).toBeInTheDocument();
    expect(screen.getByText('Technical')).toBeInTheDocument();
    expect(screen.getByText('Support')).toBeInTheDocument();
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

  it('tab switching works - Support group shows Troubleshooting', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    // Switch to Support group
    fireEvent.click(screen.getByText('Support'));
    // The Troubleshooting tab should be visible within the Support group
    expect(screen.getByText('Troubleshooting')).toBeInTheDocument();
    // Click it to load the troubleshooting content with its search input
    fireEvent.click(screen.getByText('Troubleshooting'));
    expect(screen.getByPlaceholderText('Search troubleshooting topics...')).toBeInTheDocument();
  });

  it('tab switching works - Reference group shows API tab', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    // Switch to Reference group
    fireEvent.click(screen.getByText('Reference'));
    // Click the API tab
    fireEvent.click(screen.getByText('API'));
    expect(screen.getByText('Interactive API Documentation')).toBeInTheDocument();
  });

  it('tab switching works - Support group shows About', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    // Switch to Support group
    fireEvent.click(screen.getByText('Support'));
    // Click the About tab
    fireEvent.click(screen.getByText('About'));
    expect(screen.getByText('About Atlas Vox')).toBeInTheDocument();
  });

  it('getting started shows numbered steps', () => {
    render(
      <MemoryRouter>
        <HelpPage />
      </MemoryRouter>,
    );
    expect(screen.getByText('Install Prerequisites')).toBeInTheDocument();
    expect(screen.getByText('Clone and Configure')).toBeInTheDocument();
  });
});
