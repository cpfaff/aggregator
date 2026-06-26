import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import LandingPage from '../LandingPage';
import { publicStatsApi } from '../../../utils/statisticsApi';

jest.mock('../../../hooks/useMediaQuery', () => ({
  useResponsiveGrid: () => ({ getGridColumns: () => 'repeat(3, 1fr)' }),
}));

afterEach(() => {
  delete global.fetch;
  jest.restoreAllMocks();
});

describe('LandingPage', () => {
  test('shows stat skeletons while overview statistics load', () => {
    global.fetch = jest.fn(() => new Promise(() => {})); // never resolves

    render(<LandingPage />);

    // The three StatCards render skeletons in place of their values.
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0);
  });

  test('removes the stat skeletons once statistics load', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({ total_providers: 5, total_datacenters: 3, total_datasets: 42 }),
      })
    );

    render(<LandingPage />);

    await waitFor(() => {
      expect(screen.getByText('42')).toBeInTheDocument();
    });
    expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument();
  });

  // FR-13 (REQ-FE-CLIENT-5): a non-ok overview response must not be rendered as
  // stats (liberal acceptance). StatCard renders numbers via locale-dependent
  // toLocaleString() (no locale arg), so assert with a separator-agnostic,
  // digit-only matcher — never a hardcoded thousands separator.
  test('does not render a stat taken from a non-ok overview response', async () => {
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        headers: { get: (h) => (h === 'content-type' ? 'application/json' : null) },
        json: () => Promise.resolve({ total_datasets: 999999 }),
      })
    );

    render(<LandingPage />);

    // Wait for a POSITIVE signal that the overview round-trip settled: the stat
    // skeletons clear in BOTH the success and error paths (setIsLoadingStats(false)).
    // Without this wait the negative assertion below is a tautology — it passes at
    // t=0 before the fetch resolves.
    await waitFor(() => expect(screen.queryByTestId('skeleton')).not.toBeInTheDocument());

    // RED (pre-fix): res.json() runs unconditionally and setStats(data) regardless
    // of res.ok, so the 500 body's value is rendered (in whatever locale grouping)
    // and the digit-stripped matcher finds 999999.
    expect(
      screen.queryByText((content) => content.replace(/\D/g, '').includes('999999'))
    ).not.toBeInTheDocument();
  });

  test('fetches overview through the shared public client with an abort signal (REQ-SH-FE-1/2)', () => {
    // REQ-SH-FE-1: the landing page consumes publicStatsApi.getOverview rather than
    // a hardcoded endpoint path; REQ-SH-FE-2: it passes an effect-scoped abort signal.
    const spy = jest
      .spyOn(publicStatsApi, 'getOverview')
      .mockReturnValue(new Promise(() => {})); // never resolves

    render(<LandingPage />);

    expect(spy).toHaveBeenCalledTimes(1);
    const options = spy.mock.calls[0][0];
    expect(options).toBeTruthy();
    expect(options.signal).toBeInstanceOf(AbortSignal);
  });

  test('aborts the in-flight overview request when the landing page unmounts (REQ-SH-FE-2)', () => {
    let capturedSignal;
    jest.spyOn(publicStatsApi, 'getOverview').mockImplementation((options) => {
      capturedSignal = options.signal;
      return new Promise(() => {}); // stays in flight
    });

    const { unmount } = render(<LandingPage />);
    expect(capturedSignal.aborted).toBe(false);

    unmount();
    expect(capturedSignal.aborted).toBe(true);
  });
});
