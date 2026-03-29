import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge } from '../../../components/ui/Badge';

describe('Badge', () => {
  it('renders the status text', () => {
    render(<Badge status="healthy" />);
    expect(screen.getByText('healthy')).toBeInTheDocument();
  });

  it('applies green classes for healthy status', () => {
    render(<Badge status="healthy" />);
    const badge = screen.getByText('healthy');
    expect(badge.className).toContain('bg-green-100');
    expect(badge.className).toContain('text-green-700');
  });

  it('applies red classes for error status', () => {
    render(<Badge status="error" />);
    const badge = screen.getByText('error');
    expect(badge.className).toContain('bg-red-100');
    expect(badge.className).toContain('text-red-700');
  });

  it('applies blue classes for training status', () => {
    render(<Badge status="training" />);
    const badge = screen.getByText('training');
    expect(badge.className).toContain('bg-blue-100');
    expect(badge.className).toContain('text-blue-700');
  });

  it('applies gray classes for pending status', () => {
    render(<Badge status="pending" />);
    const badge = screen.getByText('pending');
    expect(badge.className).toContain('bg-gray-100');
    expect(badge.className).toContain('text-gray-700');
  });

  it('applies default gray classes for unknown status', () => {
    render(<Badge status="unknown-status" />);
    const badge = screen.getByText('unknown-status');
    expect(badge.className).toContain('bg-gray-100');
  });

  it('capitalizes the status text via CSS', () => {
    render(<Badge status="ready" />);
    const badge = screen.getByText('ready');
    expect(badge.className).toContain('capitalize');
  });

  it('accepts custom className', () => {
    render(<Badge status="healthy" className="text-lg" />);
    const badge = screen.getByText('healthy');
    expect(badge.className).toContain('text-lg');
  });

  it('renders as a span element', () => {
    const { container } = render(<Badge status="healthy" />);
    expect(container.querySelector('span')).toBeInTheDocument();
  });
});
