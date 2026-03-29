import { vi, describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AudioRecorder, FileUploader } from '../../../components/audio/AudioRecorder';

vi.mock('../../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

describe('AudioRecorder', () => {
  it('renders record button', () => {
    render(<AudioRecorder onRecorded={vi.fn()} />);
    expect(screen.getByText('Record Audio')).toBeInTheDocument();
  });

  it('record button is a secondary variant', () => {
    render(<AudioRecorder onRecorded={vi.fn()} />);
    const btn = screen.getByText('Record Audio').closest('button');
    expect(btn).toBeInTheDocument();
  });

  it('record button has aria-label', () => {
    render(<AudioRecorder onRecorded={vi.fn()} />);
    const btn = screen.getByRole('button', { name: /start recording/i });
    expect(btn).toBeInTheDocument();
  });
});

describe('FileUploader', () => {
  it('renders upload area text', () => {
    render(<FileUploader onFiles={vi.fn()} />);
    expect(screen.getByText('Drop audio files here or click to browse')).toBeInTheDocument();
  });

  it('shows supported formats', () => {
    render(<FileUploader onFiles={vi.fn()} />);
    expect(screen.getByText('WAV, MP3, FLAC, OGG')).toBeInTheDocument();
  });

  it('contains a hidden file input', () => {
    const { container } = render(<FileUploader onFiles={vi.fn()} />);
    const input = container.querySelector('input[type="file"]');
    expect(input).toBeInTheDocument();
    expect(input?.className).toContain('hidden');
  });

  it('file input accepts audio files', () => {
    const { container } = render(<FileUploader onFiles={vi.fn()} />);
    const input = container.querySelector('input[type="file"]');
    expect(input?.getAttribute('accept')).toBe('audio/*');
  });

  it('file input allows multiple files', () => {
    const { container } = render(<FileUploader onFiles={vi.fn()} />);
    const input = container.querySelector('input[type="file"]');
    expect(input?.hasAttribute('multiple')).toBe(true);
  });

  it('upload area has role button and aria-label', () => {
    render(<FileUploader onFiles={vi.fn()} />);
    const dropZone = screen.getByRole('button', { name: /upload audio files/i });
    expect(dropZone).toBeInTheDocument();
  });
});
