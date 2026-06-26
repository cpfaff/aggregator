import { publicStatsApi, statsUtils } from '../statisticsApi';

describe('statsUtils dead-surface removal (REQ-SH-DEAD-3)', () => {
  test('the unreachable calculatePercentageChange helper is removed', () => {
    // It had zero callers and was a dead percent-change computation (F-J).
    expect(statsUtils.calculatePercentageChange).toBeUndefined();
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
