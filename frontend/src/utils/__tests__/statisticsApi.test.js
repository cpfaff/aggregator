import fs from 'fs';
import path from 'path';
import { publicStatsApi, authStatsApi, statsUtils } from '../statisticsApi';

describe('ERR-1 both statistics clients reject with one typed error shape (REQ-SH-ERR-1)', () => {
  afterEach(() => {
    localStorage.removeItem('token');
    delete global.fetch;
  });

  test('authStatsApi.getOverview rejects with the typed { status, class } shape, not a generic Error', async () => {
    localStorage.setItem('token', 'test-token');
    global.fetch = jest.fn(() =>
      Promise.resolve({
        ok: false,
        status: 404,
        headers: { get: (h) => (h === 'content-type' ? 'application/problem+json' : null) },
        json: () => Promise.resolve({ title: 'Not Found' }),
      }),
    );

    // The shared apiRequest layer already rejects non-ok with parseErrorResponse,
    // so the typed shape must reach the caller (not a downgraded generic Error).
    await expect(authStatsApi.getOverview()).rejects.toMatchObject({ status: 404, class: 'client' });
  });

  test('the authenticated client defines no generic Error downgrade for non-ok responses', () => {
    const src = fs.readFileSync(path.join(__dirname, '..', 'statisticsApi.js'), 'utf8');
    expect(src).not.toMatch(/throw new Error/);
  });
});

describe('statsUtils dead-surface removal (REQ-SH-DEAD-3)', () => {
  test('the unreachable calculatePercentageChange helper is removed', () => {
    // It had zero callers and was a dead percent-change computation (F-J).
    expect(statsUtils.calculatePercentageChange).toBeUndefined();
  });
});

describe('statsUtils.toChartSeries reads any timeline through one shape (REQ-SH-TL-3)', () => {
  test('reads a narrow TimeSeriesResponse via its data_points key', () => {
    const out = statsUtils.toChartSeries({ data_points: [{ date: '2024-01-01', value: 5 }] });
    expect(out).toHaveLength(1);
    expect(out[0].value).toBe(5);
  });

  test('reads the renamed multi-provider wide rows via its series key (not data_points)', () => {
    const out = statsUtils.toChartSeries({
      series: [{ date: '2024-01-01', ProvA: 5 }],
      providers: [{ key: 'ProvA' }],
    });
    expect(out).toHaveLength(1);
    expect(out[0].ProvA).toBe(5);
  });

  test('reads a bare points array (a GrowthMetrics sub-timeline) as a narrow series', () => {
    const out = statsUtils.toChartSeries([{ date: '2024-02-01', value: 9 }]);
    expect(out).toHaveLength(1);
    expect(out[0].value).toBe(9);
  });

  test('returns [] when no recognised series key is present', () => {
    expect(statsUtils.toChartSeries({ providers: [] })).toEqual([]);
    expect(statsUtils.toChartSeries(null)).toEqual([]);
  });
});

describe('publicStatsApi resilient transport', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  describe('FR-02 typed status error (REQ-FE-CLIENT-2)', () => {
    test('publicStatsApi.getOverview rejects with a typed error carrying the HTTP status, not a generic string', async () => {
      // Key headers.get on the header NAME so the revived parseErrorResponse
      // reads content-type and parses the RFC 7807 body.
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          status: 503,
          headers: {
            get: (h) => (h === 'content-type' ? 'application/problem+json' : null),
          },
          json: () => Promise.resolve({ title: 'Service Unavailable' }),
        }),
      );

      // RED (pre-fix): getOverview throws new Error('Failed to fetch public
      // overview: 503') — a plain Error with no .status property, so the matcher
      // fails. GREEN: a typed { status, message } propagates.
      await expect(publicStatsApi.getOverview()).rejects.toMatchObject({ status: 503 });
    });
  });
});
