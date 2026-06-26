import React from 'react';
import { render, screen } from '@testing-library/react';
import PieChart from '../PieChart';

describe('PieChart', () => {
  test('renders a skeleton while loading', () => {
    render(<PieChart isLoading title="Distribution" subtitle="by center" data={[]} height={300} />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
    expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
  });

  test('renders no skeleton when not loading', () => {
    // An error short-circuits before the (heavy) chart renders.
    render(<PieChart isLoading={false} title="Distribution" data={[]} error="No data" height={300} />);

    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
