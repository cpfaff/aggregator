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
});
