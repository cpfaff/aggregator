import { publicStatsApi, statsUtils } from '../statisticsApi';

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
