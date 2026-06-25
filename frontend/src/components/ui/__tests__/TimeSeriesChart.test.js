import React from 'react';
import { render, screen } from '@testing-library/react';
import TimeSeriesChart from '../TimeSeriesChart';

describe('TimeSeriesChart', () => {
  test('renders a skeleton in the chart area while loading', () => {
    render(<TimeSeriesChart isLoading title="Growth" subtitle="over time" data={[]} height={300} />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
    // The old spinner copy must be gone.
    expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
  });

  test('does not render a skeleton when not loading', () => {
    // An error short-circuits before the (heavy) chart renders.
    render(<TimeSeriesChart isLoading={false} title="Growth" data={[]} error="No data" height={300} />);

    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
