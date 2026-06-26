import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import ProviderStatistics from '../ProviderStatistics';

jest.mock('../../auth/AuthContext', () => ({
  useAuth: () => ({ handleTokenExpiration: jest.fn() }),
}));

jest.mock('../../../utils/statisticsApi', () => ({
  authStatsApi: {
    getProviderStats: jest.fn(),
    getProviderDatasetsTimeline: jest.fn(),
    getProviderBiologicalUnitsTimeline: jest.fn(),
  },
  statsUtils: {
    formatTimeSeriesForChart: jest.fn(() => []),
    toChartSeries: jest.fn(() => []),
  },
}));

jest.mock('../../ui/TimeSeriesChart', () => () => <div data-testid="timeseries-chart" />);

const { authStatsApi, statsUtils } = require('../../../utils/statisticsApi');

beforeEach(() => {
  jest.clearAllMocks();
});

describe('ProviderStatistics', () => {
  test('shows a skeleton while provider trends load', () => {
    authStatsApi.getProviderStats.mockReturnValue(new Promise(() => {})); // never resolves

    render(<ProviderStatistics providerId={1} providerName="Prov X" />);

    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the skeleton once provider trends load', async () => {
    // CRA's jest sets resetMocks:true, so factory-default impls are wiped —
    // set the canonical reader's return inside the test (REQ-SH-TL-3).
    statsUtils.toChartSeries.mockReturnValue([]);
    authStatsApi.getProviderStats.mockResolvedValue({ last_activity: null });
    authStatsApi.getProviderDatasetsTimeline.mockResolvedValue({ data_points: [] });
    authStatsApi.getProviderBiologicalUnitsTimeline.mockResolvedValue({ data_points: [] });

    render(<ProviderStatistics providerId={1} providerName="Prov X" />);

    await waitFor(() => {
      expect(screen.getByText('Prov X')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });
});
