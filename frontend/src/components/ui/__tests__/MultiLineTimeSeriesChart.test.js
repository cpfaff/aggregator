import React from 'react';
import { render, screen } from '@testing-library/react';
import MultiLineTimeSeriesChart from '../MultiLineTimeSeriesChart';

describe('MultiLineTimeSeriesChart', () => {
  test('renders a skeleton while loading', () => {
    render(
      <MultiLineTimeSeriesChart isLoading title="Trends" subtitle="over time" data={[]} height={350} />
    );

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
    expect(screen.queryByText('Loading chart...')).not.toBeInTheDocument();
  });

  test('renders no skeleton when not loading', () => {
    // An error short-circuits before the (heavy) chart renders.
    render(
      <MultiLineTimeSeriesChart isLoading={false} title="Trends" data={[]} error="No data" height={350} />
    );

    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
