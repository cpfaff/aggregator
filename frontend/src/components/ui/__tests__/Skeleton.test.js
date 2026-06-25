import React from 'react';
import { render, screen } from '@testing-library/react';
import Skeleton from '../Skeleton';

describe('Skeleton', () => {
  test('exposes a stable test hook for surfaces to assert on', () => {
    render(<Skeleton />);
    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
  });

  test('is announced to assistive tech as a busy status region', () => {
    render(<Skeleton />);
    const region = screen.getByTestId('skeleton');
    expect(region).toHaveAttribute('role', 'status');
    expect(region).toHaveAttribute('aria-busy', 'true');
    // Default accessible name communicates the loading state.
    expect(region).toHaveAccessibleName(/loading/i);
  });

  test('accepts a custom accessible label', () => {
    render(<Skeleton ariaLabel="Loading providers" />);
    expect(screen.getByTestId('skeleton')).toHaveAccessibleName('Loading providers');
  });

  test('renders a single bar by default', () => {
    render(<Skeleton />);
    expect(screen.getAllByTestId('skeleton-bar')).toHaveLength(1);
  });

  test('renders one bar per count for multi-line silhouettes', () => {
    render(<Skeleton variant="text" count={4} />);
    expect(screen.getAllByTestId('skeleton-bar')).toHaveLength(4);
  });

  test('visual bars are hidden from assistive tech (avoid double announce)', () => {
    render(<Skeleton count={3} />);
    screen.getAllByTestId('skeleton-bar').forEach((bar) => {
      expect(bar).toHaveAttribute('aria-hidden', 'true');
    });
  });

  test('bars carry the shimmer class so reduced-motion CSS can override them', () => {
    render(<Skeleton />);
    expect(screen.getByTestId('skeleton-bar')).toHaveClass('skeleton-shimmer');
  });

  test('circle variant renders a fully-rounded bar', () => {
    render(<Skeleton variant="circle" width={48} />);
    const bar = screen.getByTestId('skeleton-bar');
    expect(bar).toHaveStyle({ borderRadius: '50%' });
  });

  test('applies numeric width and height as pixels', () => {
    render(<Skeleton width={120} height={16} />);
    const bar = screen.getByTestId('skeleton-bar');
    expect(bar).toHaveStyle({ width: '120px', height: '16px' });
  });

  test('passes through string dimensions verbatim', () => {
    render(<Skeleton width="80%" height="2rem" />);
    const bar = screen.getByTestId('skeleton-bar');
    expect(bar).toHaveStyle({ width: '80%', height: '2rem' });
  });

  test('merges caller style and className onto the region', () => {
    render(<Skeleton className="grid-slot" style={{ marginTop: '1rem' }} />);
    const region = screen.getByTestId('skeleton');
    expect(region).toHaveClass('grid-slot');
    expect(region).toHaveStyle({ marginTop: '1rem' });
  });
});
