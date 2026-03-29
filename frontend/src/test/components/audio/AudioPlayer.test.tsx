import { vi, describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AudioPlayer } from '../../../components/audio/AudioPlayer';

vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe('AudioPlayer', () => {
  it('renders without crashing', () => {
    const { container } = render(<AudioPlayer src="/audio/test.wav" />);
    expect(container.firstElementChild).toBeInTheDocument();
  });

  it('renders play button with correct aria-label', () => {
    render(<AudioPlayer src="/audio/test.wav" />);
    const playBtn = screen.getByLabelText('Play');
    expect(playBtn).toBeInTheDocument();
  });

  it('renders mute button', () => {
    render(<AudioPlayer src="/audio/test.wav" />);
    const buttons = screen.getAllByRole('button');
    // At least play and mute buttons
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it('renders volume icon', () => {
    const { container } = render(<AudioPlayer src="/audio/test.wav" />);
    // Volume icon is rendered as an SVG
    expect(container.querySelector('svg')).toBeInTheDocument();
  });
});
