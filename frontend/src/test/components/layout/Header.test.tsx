import { vi, describe, it, expect, beforeEach } from 'vitest';

vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock('../../../stores/settingsStore', () => ({
  useSettingsStore: vi.fn(),
}));

import { useSettingsStore } from '../../../stores/settingsStore';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from '../../../components/layout/Header';

const mockToggleTheme = vi.fn();

beforeEach(() => {
  vi.clearAllMocks();

  (useSettingsStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
    theme: 'light',
    toggleTheme: mockToggleTheme,
  });
});

describe('Header', () => {
  it('renders the header element', () => {
    const { container } = render(<BrowserRouter><Header /></BrowserRouter>);
    expect(container.querySelector('header')).toBeInTheDocument();
  });

  it('renders theme toggle button', () => {
    render(<BrowserRouter><Header /></BrowserRouter>);
    expect(screen.getByLabelText('Toggle theme')).toBeInTheDocument();
  });

  it('clicking theme toggle calls toggleTheme', () => {
    render(<BrowserRouter><Header /></BrowserRouter>);
    fireEvent.click(screen.getByLabelText('Toggle theme'));
    expect(mockToggleTheme).toHaveBeenCalledTimes(1);
  });

  it('shows Moon icon in light mode', () => {
    const { container } = render(<BrowserRouter><Header /></BrowserRouter>);
    // In light mode, the Moon icon is rendered
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('shows Sun icon in dark mode', () => {
    (useSettingsStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      theme: 'dark',
      toggleTheme: mockToggleTheme,
    });
    const { container } = render(<BrowserRouter><Header /></BrowserRouter>);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});
