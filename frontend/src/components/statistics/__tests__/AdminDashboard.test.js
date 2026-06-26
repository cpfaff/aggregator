import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import AdminDashboard from '../AdminDashboard';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ handleTokenExpiration: jest.fn() }),
}));

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ isMobile: false, isTablet: false, getGridColumns: () => 'repeat(4, 1fr)' }),
}));

jest.mock('../../../utils/statisticsApi', () => ({
  authStatsApi: {
    getOverview: jest.fn(),
    getQualityMetrics: jest.fn(),
    getBiologicalUnitsTimeline: jest.fn(),
    getMultiProviderBiologicalUnits: jest.fn(),
  },
  publicStatsApi: {
    getProviders: jest.fn(),
    getTimeline: jest.fn(),
  },
  statsUtils: {
    formatTimeSeriesForChart: jest.fn(() => []),
    formatMultiProviderTimeSeriesForChart: jest.fn(() => ({ data: [], providers: [] })),
  },
}));

// Charts are heavy and irrelevant to the loading state.
jest.mock('../../ui/TimeSeriesChart', () => () => <div data-testid="timeseries-chart" />);
jest.mock('../../ui/MultiLineTimeSeriesChart', () => () => <div data-testid="multiline-chart" />);
jest.mock('../../ui/PieChart', () => () => <div data-testid="pie-chart" />);
jest.mock('../../ui/Breadcrumbs', () => () => <nav data-testid="breadcrumbs" />);

const { authStatsApi, publicStatsApi } = require('../../../utils/statisticsApi');

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AdminDashboard', () => {
  test('shows a dashboard skeleton while statistics load', () => {
    authStatsApi.getOverview.mockReturnValue(new Promise(() => {})); // never resolves

    render(<AdminDashboard />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the skeleton once statistics load', async () => {
    authStatsApi.getOverview.mockResolvedValue({
      total_providers: 5,
      total_datacenters: 3,
      total_datasets: 42,
      total_xml_archives: 10,
      validation_success_rate: null,
    });
    authStatsApi.getQualityMetrics.mockResolvedValue({ total_validations: 7 });
    authStatsApi.getBiologicalUnitsTimeline.mockResolvedValue([]);
    authStatsApi.getMultiProviderBiologicalUnits.mockResolvedValue({ data: [], providers: [] });
    publicStatsApi.getProviders.mockResolvedValue({ datacenters: [] });
    publicStatsApi.getTimeline.mockResolvedValue({ datasets_timeline: [] });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Statistics')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
