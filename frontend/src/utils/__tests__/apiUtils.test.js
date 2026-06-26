import { apiRequest, parseErrorResponse } from '../apiUtils';

// Build a Response stub whose headers.get is keyed on the header NAME, with an
// optional header map merged in (used to exercise parseErrorResponse directly).
const mk = (status, body = {}, headers = {}) => ({
  ok: status < 400,
  status,
  headers: {
    get: (h) => {
      if (h === 'content-type') return 'application/json';
      return headers[h] ?? null;
    },
  },
  json: () => Promise.resolve(body),
});

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

      // Let execution reach the awaited fetch, then advance past the configured
      // REQUEST_TIMEOUT_MS (15000 ms) so the abort/timeout fires. A timeout is
      // retriable (FR-15), so advance repeatedly through the full retry budget
      // (each attempt times out, with a backoff between) until apiRequest finally
      // rejects with the TimeoutError.
      await flushMicrotasks();
      for (let i = 0; i < 10 && outcome.name === 'NEVER_SETTLED'; i++) {
        jest.advanceTimersByTime(20000);
        // eslint-disable-next-line no-await-in-loop
        await flushMicrotasks();
      }

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

  describe('FR-11 flatten 422 array detail (REQ-FE-DEG-4)', () => {
    test('parseErrorResponse flattens a 422 array detail into a readable string, not an array', async () => {
      const r = await parseErrorResponse(
        mk(422, { detail: [{ loc: ['body', 'password'], msg: 'too short', type: 'x' }] }),
      );

      // RED (pre-fix): line returns data.detail (the array) as message, so
      // typeof r.message is 'object' and the flattened text is absent.
      expect(typeof r.message).toBe('string');
      expect(r.message).toMatch(/password: too short/);
      expect(r.message).not.toContain('[object Object]');
    });
  });

  describe('FR-12 status classification + Retry-After (REQ-FE-DEG-3)', () => {
    test('parseErrorResponse classifies 429 as throttle and exposes Retry-After distinct from a 4xx client error', async () => {
      const throttled = await parseErrorResponse(mk(429, {}, { 'Retry-After': '30' }));
      // RED (pre-fix): the parser returns only { message, status, type } — no
      // class, never reads Retry-After.
      expect(throttled.class).toBe('throttle');
      expect(throttled.retryAfter).toBe(30);

      const client = await parseErrorResponse(mk(400, {}));
      expect(client.class).toBe('client');
      expect(client.retryAfter).toBeUndefined();
    });
  });

  describe('FR-14 CSRF fail-closed (REQ-FE-CLIENT-7)', () => {
    test('apiRequest does not send a state-changing request when the CSRF token cannot be obtained', async () => {
      // token is set in beforeEach; no csrfToken in localStorage.
      global.fetch = jest.fn((url) => {
        if (typeof url === 'string' && url.includes('/tokens/csrf')) {
          // CSRF token fetch fails.
          return Promise.resolve({ ok: false, status: 500, json: () => Promise.resolve({}) });
        }
        // Any mutating endpoint would succeed if (wrongly) reached.
        return Promise.resolve({
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({}),
        });
      });

      // RED (pre-fix): the catch only logs and falls through, so the POST to
      // /datasets/1 IS issued and apiRequest resolves; both assertions fail.
      await expect(apiRequest('/datasets/1', { method: 'POST' })).rejects.toMatchObject({
        name: 'CsrfUnavailableError',
      });

      // Assert on the mutating endpoint specifically (the CSRF probe is itself a fetch).
      expect(global.fetch).not.toHaveBeenCalledWith(
        expect.stringContaining('/datasets/1'),
        expect.objectContaining({ method: 'POST' }),
      );
    });
  });

  describe('FR-15 bounded retriable-only retry (REQ-FE-CLIENT-8)', () => {
    test('apiRequest retries a 503 once with backoff and then succeeds, but does NOT retry a 400', async () => {
      jest.useFakeTimers();
      const randomSpy = jest.spyOn(Math, 'random').mockReturnValue(0.5);
      try {
        const okResponse = {
          ok: true,
          status: 200,
          headers: { get: () => 'application/json' },
          json: () => Promise.resolve({ data: 'ok' }),
        };
        const serverError = {
          ok: false,
          status: 503,
          headers: { get: (h) => (h === 'content-type' ? 'application/json' : null) },
          json: () => Promise.resolve({ title: 'Service Unavailable' }),
        };
        global.fetch = jest
          .fn()
          .mockResolvedValueOnce(serverError)
          .mockResolvedValueOnce(okResponse);

        let resolved;
        let settled = false;
        apiRequest('/retry-me').then(
          (r) => {
            resolved = r;
            settled = true;
          },
          () => {
            settled = true;
          },
        );
        // Interleave microtask flushing with timer advancement until the call
        // settles: flush runs the pending attempt (scheduling the backoff sleep),
        // then advancing fires that sleep so the retry proceeds.
        for (let i = 0; i < 10 && !settled; i++) {
          // eslint-disable-next-line no-await-in-loop
          await flushMicrotasks();
          jest.advanceTimersByTime(5000);
        }
        await flushMicrotasks();

        expect(resolved).toBe(okResponse);
        expect(global.fetch).toHaveBeenCalledTimes(2);

        // 400 is a client error and must NOT be retried.
        const clientError = {
          ok: false,
          status: 400,
          headers: { get: (h) => (h === 'content-type' ? 'application/json' : null) },
          json: () => Promise.resolve({ detail: 'Bad request' }),
        };
        global.fetch = jest.fn().mockResolvedValue(clientError);

        let rejected;
        let settled2 = false;
        apiRequest('/no-retry').then(
          () => {
            settled2 = true;
          },
          (e) => {
            rejected = e;
            settled2 = true;
          },
        );
        for (let i = 0; i < 10 && !settled2; i++) {
          // eslint-disable-next-line no-await-in-loop
          await flushMicrotasks();
          jest.advanceTimersByTime(5000);
        }
        await flushMicrotasks();

        // RED (pre-fix): a 503 is returned as-is (fetch called once, no retry),
        // so toHaveBeenCalledTimes(2) fails.
        expect(rejected).toMatchObject({ status: 400 });
        expect(global.fetch).toHaveBeenCalledTimes(1);
      } finally {
        jest.useRealTimers();
        randomSpy.mockRestore();
      }
    });
  });
});
