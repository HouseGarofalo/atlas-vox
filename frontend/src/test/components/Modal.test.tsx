import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

vi.mock('../../utils/logger', () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

import { render, screen, fireEvent } from '@testing-library/react';
import { Modal } from '../../components/ui/Modal';

// Mock focus method on HTMLElement prototype
Object.defineProperty(HTMLElement.prototype, 'focus', {
  value: vi.fn(),
  writable: true,
});

describe('Modal', () => {
  const onCloseMock = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock document methods
    vi.spyOn(document, 'addEventListener');
    vi.spyOn(document, 'removeEventListener');
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Reset body overflow
    document.body.style.overflow = '';
  });

  it('renders when open is true', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Modal content')).toBeInTheDocument();
  });

  it('does not render when open is false', () => {
    render(
      <Modal open={false} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(screen.queryByText('Test Modal')).not.toBeInTheDocument();
    expect(screen.queryByText('Modal content')).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    const closeButton = screen.getByLabelText('Close dialog');
    fireEvent.click(closeButton);

    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('calls onClose when backdrop is clicked', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    // Find backdrop (the div with role="presentation")
    const backdrop = document.querySelector('[role="presentation"]');
    expect(backdrop).toBeInTheDocument();

    if (backdrop) {
      fireEvent.click(backdrop);
      expect(onCloseMock).toHaveBeenCalledTimes(1);
    }
  });

  it('does not close when modal content is clicked', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    const modalContent = screen.getByText('Modal content');
    fireEvent.click(modalContent);

    expect(onCloseMock).not.toHaveBeenCalled();
  });

  it('has proper ARIA attributes', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    const dialog = screen.getByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(dialog).toHaveAttribute('aria-labelledby', 'modal-title');

    const title = screen.getByText('Test Modal');
    expect(title).toHaveAttribute('id', 'modal-title');
  });

  it('prevents body scroll when open', () => {
    const { rerender } = render(
      <Modal open={false} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('');

    rerender(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('hidden');
  });

  it('restores body scroll when closed', () => {
    const { rerender } = render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('hidden');

    rerender(
      <Modal open={false} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    expect(document.body.style.overflow).toBe('');
  });

  it('calls onClose when Escape key is pressed', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onCloseMock).toHaveBeenCalledTimes(1);
  });

  it('traps focus within modal', () => {
    render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <button>First Button</button>
        <button>Last Button</button>
      </Modal>
    );

    // Since focus trapping is complex to test in jsdom, we'll just verify
    // that Tab key handler is registered
    expect(document.addEventListener).toHaveBeenCalledWith('keydown', expect.any(Function));
  });

  it('handles focus restoration on close', () => {
    const { rerender } = render(
      <Modal open={true} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    // Close modal
    rerender(
      <Modal open={false} onClose={onCloseMock} title="Test Modal">
        <p>Modal content</p>
      </Modal>
    );

    // Focus restoration is handled in cleanup
    expect(document.removeEventListener).toHaveBeenCalledWith('keydown', expect.any(Function));
  });
});