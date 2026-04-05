import { vi, describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Sidebar from '../../../components/layout/Sidebar';

vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe('Sidebar', () => {
  it('renders the Atlas Vox brand name', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Atlas Vox')).toBeInTheDocument();
  });

  it('renders Dashboard navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
  });

  it('renders Voice Profiles navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Profiles')).toBeInTheDocument();
  });

  it('renders Voice Library navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Voice Library')).toBeInTheDocument();
  });

  it('renders Training Studio navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Training Studio')).toBeInTheDocument();
  });

  it('renders Synthesis Lab navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Synthesis Lab')).toBeInTheDocument();
  });

  it('renders Comparison navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Comparison')).toBeInTheDocument();
  });

  it('renders Providers navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Providers')).toBeInTheDocument();
  });

  it('renders API Keys navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('API Keys')).toBeInTheDocument();
  });

  it('renders Settings navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders Help navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Help')).toBeInTheDocument();
  });

  it('renders Audio Design navigation item', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByText('Audio Design')).toBeInTheDocument();
  });

  it('renders mobile menu toggle button', () => {
    render(
      <MemoryRouter>
        <Sidebar />
      </MemoryRouter>,
    );
    expect(screen.getByLabelText('Toggle menu')).toBeInTheDocument();
  });
});
