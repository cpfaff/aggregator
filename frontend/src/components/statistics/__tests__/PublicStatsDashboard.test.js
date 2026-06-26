import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import PublicStatsDashboard from '../PublicStatsDashboard';

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ isMobile: false, isTablet: false, getGridColumns: () => 'repeat(3, 1fr)' }),
}));

jest.mock('../../../utils/statisticsApi', () => ({
  // Keep the real pure helpers (e.g. statisticsErrorMessage) used in the catch path.
  ...jest.requireActual('../../../utils/statisticsApi'),
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

  // FR-17 (REQ-FE-POLL-4): the stats requests must carry an AbortSignal and be
  // aborted on unmount. (React 18 emits no unmount warning, so assert on the
  // signal, not on console.error.)
  test('passes an abort signal to the stats requests and aborts them on unmount', async () => {
    publicStatsApi.getOverview.mockResolvedValue({
      total_providers: 1,
      total_datacenters: 1,
      total_datasets: 1,
    });
    publicStatsApi.getProviders.mockResolvedValue({ datacenters: [] });
    publicStatsApi.getTimeline.mockResolvedValue({ datasets_timeline: [] });

    const { unmount } = render(<PublicStatsDashboard />);

    await waitFor(() => expect(publicStatsApi.getOverview).toHaveBeenCalled());

    // RED (pre-fix): the three calls take no signal argument, so these matchers fail.
    expect(publicStatsApi.getOverview).toHaveBeenCalledWith(
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(publicStatsApi.getProviders).toHaveBeenCalledWith(
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );
    expect(publicStatsApi.getTimeline).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    );

    const { signal } = publicStatsApi.getOverview.mock.calls[0][0];
    expect(signal.aborted).toBe(false);

    unmount();

    // RED (pre-fix): stopAutoRefresh only clears timers, never aborting.
    expect(signal.aborted).toBe(true);
  });

  // Regression: the FR-17 abort handling surfaced "signal is aborted without
  // reason" on the public stats page under React StrictMode's dev double-mount.
  // The discarded first mount's request is aborted, but the catch checked the
  // CURRENT controller ref (the surviving mount's, not aborted) and the overlap
  // guard persisted across the remount, so the page errored instead of loading.
  test('loads under StrictMode remount and does not surface the discarded mount abort as an error', async () => {
    // Abort-aware mocks: reject with an AbortError when their signal aborts, else
    // resolve — mirroring real fetch/AbortController behaviour (the plain
    // mockResolvedValue mocks cannot reproduce the abort path).
    const abortAware = (value) =>
      jest.fn(
        (options = {}) =>
          new Promise((resolve, reject) => {
            const { signal } = options;
            const fail = () => {
              const e = new Error('signal is aborted without reason');
              e.name = 'AbortError';
              reject(e);
            };
            if (signal?.aborted) {
              fail();
              return;
            }
            if (signal) {
              signal.addEventListener('abort', fail, { once: true });
            }
            Promise.resolve().then(() => {
              if (!signal?.aborted) {
                resolve(value);
              }
            });
          })
      );

    publicStatsApi.getOverview.mockImplementation(
      abortAware({ total_providers: 5, total_datacenters: 3, total_datasets: 42 })
    );
    publicStatsApi.getProviders.mockImplementation(abortAware({ datacenters: [] }));
    publicStatsApi.getTimeline.mockImplementation(abortAware({ datasets_timeline: [] }));

    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    try {
      render(
        <React.StrictMode>
          <PublicStatsDashboard />
        </React.StrictMode>
      );

      // The surviving (second) mount loads stats: the skeleton clears.
      await waitFor(() => expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument());

      // RED (pre-fix): the discarded mount's abort is mis-attributed to the live
      // controller and shown as a banner.
      expect(screen.queryByText(/Failed to load statistics/i)).not.toBeInTheDocument();
    } finally {
      errorSpy.mockRestore();
    }
  });
});
