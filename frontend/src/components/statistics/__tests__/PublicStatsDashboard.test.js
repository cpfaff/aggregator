import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
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

describe('PublicStatsDashboard auto-refresh backoff', () => {
  // Flush the async catch (failure counter) within act so it settles before the
  // next tick.
  const settle = async () => {
    await act(async () => {
      for (let i = 0; i < 5; i++) {
        // eslint-disable-next-line no-await-in-loop
        await Promise.resolve();
      }
    });
  };

  // FR-16 (REQ-FE-POLL-3): a backend that is down must stop being polled every
  // 60s; after repeated failures the cadence widens.
  test('auto-refresh backs off after repeated failures instead of firing every 60s', async () => {
    jest.useFakeTimers();
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    try {
      publicStatsApi.getOverview.mockRejectedValue(new Error('down'));
      publicStatsApi.getProviders.mockRejectedValue(new Error('down'));
      publicStatsApi.getTimeline.mockRejectedValue(new Error('down'));

      render(<PublicStatsDashboard />);
      await settle(); // initial load fails -> failures = 1

      // Three 60s ticks, settling the async catch between each.
      for (let i = 0; i < 3; i++) {
        // eslint-disable-next-line no-await-in-loop
        await act(async () => {
          jest.advanceTimersByTime(60000);
        });
        // eslint-disable-next-line no-await-in-loop
        await settle();
      }
      const callsBeforeFourth = publicStatsApi.getOverview.mock.calls.length;

      // Fourth 60s tick.
      await act(async () => {
        jest.advanceTimersByTime(60000);
      });
      await settle();

      // RED (pre-fix): the interval calls fetchAllStats(true) every 60s regardless
      // of prior failures, so getOverview IS invoked on the fourth tick.
      expect(publicStatsApi.getOverview.mock.calls.length).toBe(callsBeforeFourth);
    } finally {
      jest.useRealTimers();
      errorSpy.mockRestore();
      warnSpy.mockRestore();
    }
  });
});
