import React from 'react';
import { render, screen } from '@testing-library/react';
import StatCard from '../StatCard';

describe('StatCard', () => {
  test('shows a skeleton in place of the value while loading', () => {
    render(<StatCard title="Datasets" value={0} isLoading />);

    expect(screen.getByTestId('skeleton')).toBeInTheDocument();
    // The label is a known prop, so it stays visible while the value loads.
    expect(screen.getByText('Datasets')).toBeInTheDocument();
  });

  test('shows the value and no skeleton once loaded', () => {
    render(<StatCard title="Datasets" value={42} />);

    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  test('renders no percent-change indicator — the dead %-change badge is gone (REQ-SH-DEAD-3)', () => {
    // previousValue was a prop no consumer ever passed, so its whole change-badge
    // block was unreachable. Even if a caller passes it, no badge is rendered.
    render(<StatCard title="Datasets" value={120} previousValue={100} />);

    expect(screen.getByText('120')).toBeInTheDocument();
    expect(screen.queryByText(/vs previous/i)).not.toBeInTheDocument();
    expect(screen.queryByText('20.0%')).not.toBeInTheDocument();
  });
});
