import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import PublicStatsDashboard from '../PublicStatsDashboard';

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ isMobile: false, isTablet: false, getGridColumns: () => 'repeat(3, 1fr)' }),
}));

jest.mock('../../../utils/statisticsApi', () => ({
  publicStatsApi: {
    getOverview: jest.fn(),
    getProviders: jest.fn(),
    getTimeline: jest.fn(),
  },
}));

// Charts are heavy and irrelevant to the loading state.
jest.mock('../../ui/TimeSeriesChart', () => () => <div data-testid="timeseries-chart" />);
jest.mock('../../ui/PieChart', () => () => <div data-testid="pie-chart" />);

const { publicStatsApi } = require('../../../utils/statisticsApi');

beforeEach(() => {
  jest.clearAllMocks();
});

describe('PublicStatsDashboard', () => {
  test('shows a dashboard skeleton while statistics load', () => {
    publicStatsApi.getOverview.mockReturnValue(new Promise(() => {}));
    publicStatsApi.getProviders.mockReturnValue(new Promise(() => {}));
    publicStatsApi.getTimeline.mockReturnValue(new Promise(() => {}));

    render(<PublicStatsDashboard />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the skeleton once statistics load', async () => {
    publicStatsApi.getOverview.mockResolvedValue({
      total_providers: 5,
      total_datacenters: 3,
      total_datasets: 42,
    });
    publicStatsApi.getProviders.mockResolvedValue({ datacenters: [] });
    publicStatsApi.getTimeline.mockResolvedValue({ datasets_timeline: [] });

    render(<PublicStatsDashboard />);

    await waitFor(() => {
      expect(screen.getByText('GFBio Registry Statistics')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
