import { apiRequest } from '../apiUtils';

// Flush a generous number of microtask ticks so a rejection that propagates
// through several awaited promises (Promise.race -> fetchWithTimeout ->
// fetchWithTokenExpiration -> apiRequest) settles before we assert.
const flushMicrotasks = async () => {
  for (let i = 0; i < 5; i++) {
    // eslint-disable-next-line no-await-in-loop
    await Promise.resolve();
  }
};

describe('apiUtils resilient client', () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    localStorage.clear();
    // Shared apiUtils auth precondition: apiRequest throws synchronously with no
    // token (apiUtils.js:178). Set a token and a far-future expiry so the
    // proactive-refresh branch (apiUtils.js:121-122) is also skipped.
    localStorage.setItem('token', 't');
    localStorage.setItem('tokenExpiry', String(Date.now() + 60 * 60 * 1000));
  });

  afterEach(() => {
    global.fetch = originalFetch;
    jest.useRealTimers();
    localStorage.clear();
  });

  describe('FR-01 request timeout (REQ-FE-CLIENT-1)', () => {
    test('apiRequest rejects with a TimeoutError when the backend never responds within the timeout', async () => {
      jest.useFakeTimers();
      // A backend that accepts the connection but never responds.
      global.fetch = jest.fn(() => new Promise(() => {}));

      let outcome = { name: 'NEVER_SETTLED' };
      apiRequest('/statistics/overview').then(
        () => {
          outcome = { name: 'RESOLVED' };
        },
        (err) => {
          outcome = err;
        },
      );

      // Let execution reach the awaited fetch, then advance comfortably past the
      // configured REQUEST_TIMEOUT_MS (15000 ms) so the abort/timeout fires.
      await flushMicrotasks();
      jest.advanceTimersByTime(20000);
      await flushMicrotasks();

      // RED (pre-fix): no controller/timer is installed, the promise never
      // settles and no TimeoutError is produced, so outcome stays NEVER_SETTLED.
      expect(outcome).toMatchObject({ name: 'TimeoutError' });
    });
  });

  describe('FR-10 typed-error seam (REQ-FE-CLIENT-6)', () => {
    test('apiRequest rejects with the RFC-7807 detail/title and status on a 4xx problem+json response', async () => {
      global.fetch = jest.fn(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          headers: {
            get: (h) => (h === 'content-type' ? 'application/problem+json' : null),
          },
          json: () => Promise.resolve({ title: 'Conflict', detail: 'Already validating' }),
        }),
      );

      // RED (pre-fix): apiRequest resolves to the raw Response on a non-ok
      // status (it never calls the parser and never rejects), so .rejects fails.
      await expect(apiRequest('/x')).rejects.toMatchObject({
        status: 409,
        message: 'Already validating',
      });
    });
  });
});
