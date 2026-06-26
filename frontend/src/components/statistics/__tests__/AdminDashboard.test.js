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
    toChartSeries: jest.fn(() => []),
  },
}));

// Charts are heavy and irrelevant to the loading state.
jest.mock('../../ui/TimeSeriesChart', () => () => <div data-testid="timeseries-chart" />);
jest.mock('../../ui/MultiLineTimeSeriesChart', () => () => <div data-testid="multiline-chart" />);
jest.mock('../../ui/PieChart', () => () => <div data-testid="pie-chart" />);
jest.mock('../../ui/Breadcrumbs', () => () => <nav data-testid="breadcrumbs" />);

const { authStatsApi, publicStatsApi, statsUtils } = require('../../../utils/statisticsApi');

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
    statsUtils.toChartSeries.mockReturnValue([]);
    authStatsApi.getOverview.mockResolvedValue({
      total_providers: 5,
      total_datacenters: 3,
      total_datasets: 42,
      total_xml_archives: 10,
      validation_success_rate: null,
    });
    authStatsApi.getQualityMetrics.mockResolvedValue({ total_validations: 7 });
    authStatsApi.getBiologicalUnitsTimeline.mockResolvedValue({ data_points: [] });
    authStatsApi.getMultiProviderBiologicalUnits.mockResolvedValue({ series: [], providers: [] });
    publicStatsApi.getProviders.mockResolvedValue({ datacenters: [] });
    publicStatsApi.getTimeline.mockResolvedValue({ datasets_timeline: [] });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Statistics')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });

  test('reads the multi-provider timeline through the renamed `series` key (REQ-SH-TL-3)', async () => {
    statsUtils.toChartSeries.mockReturnValue([]);
    authStatsApi.getOverview.mockResolvedValue({
      total_providers: 1,
      total_datacenters: 1,
      total_datasets: 1,
      total_xml_archives: 1,
      validation_success_rate: null,
    });
    authStatsApi.getQualityMetrics.mockResolvedValue({ total_validations: 0 });
    authStatsApi.getBiologicalUnitsTimeline.mockResolvedValue({ data_points: [] });
    const multiProvider = {
      series: [{ date: '2024-01-01', ProvA: 5 }],
      providers: [{ key: 'ProvA' }],
    };
    authStatsApi.getMultiProviderBiologicalUnits.mockResolvedValue(multiProvider);
    publicStatsApi.getProviders.mockResolvedValue({ datacenters: [] });
    publicStatsApi.getTimeline.mockResolvedValue({ datasets_timeline: [] });

    render(<AdminDashboard />);

    await waitFor(() => {
      expect(screen.getByText('Statistics')).toBeInTheDocument();
    });
    // The dashboard hands the whole multi-provider response to the one canonical
    // reader (which resolves the `series` key) instead of poking data_points itself.
    expect(statsUtils.toChartSeries).toHaveBeenCalledWith(multiProvider);
  });
});
