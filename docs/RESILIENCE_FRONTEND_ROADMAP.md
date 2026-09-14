# GFBio Aggregator Frontend Resilience Hardening — Roadmap

This roadmap sequences the work that makes `RESILIENCE_FRONTEND_SPEC.md` true.
Each item closes exactly one confirmed defect, is independently committable, and
is driven test-first: **write the named RED test, watch it fail for the stated
reason, then make the minimal fix turn it green.** No item changes behaviour
beyond what its requirement demands, and every item preserves the credited
strengths (three-state loading skeleton, stale-while-error banner, honest
`unknown` badge — see spec §1.4).

All 18 items map 1:1 to a refute-verified finding (`FE-*`, 0 refuted) and a spec
requirement (`REQ-FE-*`). Baseline at the start of this work was green on branch
`DASS-3622-resilience-hardening`, commit `231c82c`: 16 suites / 73 tests passing,
`eslint src/` clean. (Re-confirm the 16/73 count before starting an item — this is
a frontend-only baseline and the branch also carries backend commits.)

## How to run an item (the gate every item must pass)

Every item passes the project's standard gate — the frontend suite plus
`npx eslint src/`. `CLAUDE.md` ("Running Tests") is the single source for those
commands and the current green baselines; it is not repeated here, because the
copy that used to live in this section had drifted to a stale baseline while the
original stayed correct.

Use one atomic conventional commit per item, landing the RED test and its fix in
the **same** commit — the test is the regression lock — e.g.
`fix(resilience): bound the api client with a request timeout (FR-01, REQ-FE-CLIENT-1)`.

## Definition of Done (per item)

1. The named RED test exists and was observed **FAILING** against pre-fix code,
   for the stated reason (record the failure).
2. The minimal fix makes that test pass; the **full suite stays green** (≥ 73
   passing) and `eslint src/` stays clean (exit 0).
3. No behaviour changes beyond the requirement; the credited strengths are
   preserved (not churned).
4. One atomic conventional commit (RED test + fix together) referencing `FR-NN`
   and `REQ-FE-*`.
5. The requirement's **Verification** in the spec §3 is thereby satisfied.

## Dependencies & Ordering

- **Priority = severity.** FR-01…FR-09 are MUST-class (the spec is *malformed*
  until they land); FR-10…FR-18 are SHOULD-class. Do MUST first.
- **The canonical seam.** FR-01 (timeout + abort in `apiRequest`) is the
  foundation that FR-02, FR-03, and the pollers inherit; FR-10 (revive
  `parseErrorResponse`) is the typed-error foundation that FR-11, FR-12, and FR-15
  build on. Each MUST item is nonetheless **independently committable** with a
  local fix — e.g. FR-07/FR-08 flatten the 422 array inline and do **not** block
  on the SHOULD seam (FR-10/FR-11); the SHOULD seam later consolidates those
  inline fixes into the one place.
- **Shared apiUtils test setup.** Every test that calls `apiRequest`
  (FR-01, FR-10, FR-14, FR-15) MUST first satisfy its auth precondition:
  `apiUtils.js:178` throws `'No authentication token found'` synchronously before
  any fetch. In `beforeEach`, `localStorage.setItem('token', 't')` and set
  `tokenExpiry` to a future value (so the proactive-refresh branch at
  `apiUtils.js:121-122` is also skipped). Without this, those tests "pass"
  trivially for the wrong reason and lock nothing.
- **New files.** FR-04 and FR-18 add `src/components/ui/ErrorBoundary.js`
  (FR-04 creates it; FR-18 reuses it). New test files: `apiUtils.test.js`,
  `statisticsApi.test.js`, `DatasetForm.test.js`, `ErrorBoundary.test.js`. Existing
  test files extended: `UserManagement.test.js`, `DatasetCard.test.js`,
  `LandingPage.test.js`, `PublicStatsDashboard.test.js` — **add** to their existing
  `describe` blocks; do not overwrite (they hold passing baseline tests).
- **Within the SHOULD block:** FR-10 (revive parser) precedes FR-11/FR-12 (parser
  behaviours) and FR-15 (retry branches on the typed status class).
- **Recommended sequence:** FR-01 → FR-02 → FR-03 → FR-04 → FR-05 → FR-06 →
  FR-07 → FR-08 → FR-09 (MUST), then FR-10 → FR-11 → FR-12 → FR-13 → FR-14 →
  FR-15 → FR-16 → FR-17 → FR-18 (SHOULD).

---

## FR-01 (MUST) — Bound the API client with a request timeout + AbortController

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-1 · **Finding:** FE-T-01 ·
  **Field:** 9 (timeouts) · **Effort:** ~4h

**Goal:** A backend that accepts the connection but never responds causes the
request to reject promptly with a typed `TimeoutError` instead of pinning every
authenticated call forever.

**Confirmed defect:** `apiUtils.js:140` (`const response = await fetch(url, options)`)
and the post-401 retry at `apiUtils.js:153` await `fetch` with no timeout and no
`AbortController`. `apiRequest` → `fetchWithTokenExpiration` is the seam for every
authenticated call, so loading flags set before the call (e.g. `setIsValidating(true)`)
never clear.

**Minimal fix:** Introduce a named `REQUEST_TIMEOUT_MS` (e.g. 15000) in `apiUtils.js`.
In `fetchWithTokenExpiration` create an `AbortController`, merge `signal` into
`options`, start `setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)` cleared
in a `finally`, and on abort reject with a typed `TimeoutError` (e.g. an `Error`
whose `name === 'TimeoutError'`). Apply to both the line-140 call and the line-153
retry.

**RED test** — `src/utils/__tests__/apiUtils.test.js > "apiRequest rejects with a TimeoutError when the backend never responds within the timeout"` (new file, Jest):
in `beforeEach` set `localStorage.token` and a future `tokenExpiry` (see "Shared
apiUtils test setup"). With `jest.useFakeTimers()` and
`global.fetch = jest.fn(() => new Promise(() => {}))`, advance timers past
`REQUEST_TIMEOUT_MS` and assert
`await expect(apiRequest('/statistics/overview')).rejects.toMatchObject({ name: 'TimeoutError' })`.
- *Fails RED because:* today `fetch` is awaited with no controller and no timer, so
  the promise never settles and no `TimeoutError` is ever produced; advancing fake
  timers changes nothing. Asserting the **typed `TimeoutError`** (not a bare
  `rejects`) prevents the no-token precondition from satisfying the test for the
  wrong reason.

- [ ] Write the RED test; observe it hang/fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-02 (MUST) — Route public stats through a timeout-bounded, typed-error path

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-2 · **Finding:** FE-T-02 ·
  **Field:** 9, 5 · **Effort:** ~3h

**Goal:** A failed public-stats call rejects with a typed, status-bearing error
(not a generic string) and its request is timeout-bounded.

**Confirmed defect:** `statisticsApi.js:16-20` (and identically `33-37`, `45-49`)
issue a bare `fetch` with no timeout, then on `!response.ok` throw
`new Error('Failed to fetch public overview: ' + response.status)` — discarding the
status as data and the RFC 7807 body. This is the unauthenticated path that
bypasses `apiRequest` entirely.

**Minimal fix:** Route the three `publicStatsApi` calls through a shared
timeout-bounded fetch (the FR-01 seam, or a small `fetchJson` helper that adds the
`AbortController` + timeout) and replace the generic throw with
`throw await parseErrorResponse(response)` (revived per FR-10) so a typed
`{ status, message }` propagates.

**RED test** — `src/utils/__tests__/statisticsApi.test.js > "publicStatsApi.getOverview rejects with a typed error carrying the HTTP status, not a generic string"` (new file, Jest):
`fetch` resolves `{ ok:false, status:503, headers:{ get:(h)=> h==='content-type' ? 'application/problem+json' : null }, json:()=>({title:'Service Unavailable'}) }`
(key the `headers.get` mock on the header **name** so the revived `parseErrorResponse`
reads `content-type`); `await expect(publicStatsApi.getOverview()).rejects.toMatchObject({ status: 503 })`.
- *Fails RED because:* today it throws `new Error('Failed to fetch public overview: 503')`
  — a plain `Error` with no `.status` property, so the matcher fails.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-03 (MUST) — Give DatasetCard's axios calls a request timeout

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-3 · **Finding:** FE-T-03 ·
  **Field:** 9 · **Effort:** ~3h

**Goal:** A hung validation/harvest/validate endpoint no longer leaves a
`DatasetCard` request pending forever.

**Confirmed defect:** `DatasetCard.js:91-98` (`axios.get(... , { headers: { Authorization } })`),
the SWR fetcher at `14-16`, and the `axios.post` at `177-185` set no `timeout`;
a repo-wide grep confirms no `axios.defaults.timeout` and no `axios.create`.

**Minimal fix:** Route these through the FR-01 resilient seam, or — as a smaller
interim step — pass `{ timeout: REQUEST_TIMEOUT_MS, signal }` on each `axios.get`/`axios.post`.

**RED test** — `src/components/datasets/__tests__/DatasetCard.test.js > "validation-status request is issued with a request timeout"` (existing file — extend, RTL/Jest):
with `jest.mock('axios')`, render `DatasetCard` and assert
`expect(axios.get).toHaveBeenCalledWith(expect.stringContaining('validation-status'), expect.objectContaining({ timeout: expect.any(Number) }))`.
- *Fails RED because:* today the config is `{ headers: { Authorization } }` with no
  `timeout` key, so the matcher fails.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-04 (MUST) — Add a top-level error boundary so one throw can't blank the app

- **Boundary:** render containment · **Requirement:** REQ-FE-EB-1 · **Finding:** FE-EB-01 ·
  **Field:** 11 (blast-radius containment) · **Effort:** ~3h

**Goal:** A render-time throw anywhere in the tree shows a recoverable fallback
panel instead of unmounting the whole app to a blank page.

**Confirmed defect:** `index.js:9-17` renders `StrictMode > BrowserRouter >
AuthProvider > App` with **no** error boundary (grep across all `src/*.js`:
zero `componentDidCatch` / `getDerivedStateFromError` / `ErrorBoundary` /
class-extends-Component). React 18 `createRoot` unmounts the entire tree on any
uncaught render error.

**Minimal fix:** New `src/components/ui/ErrorBoundary.js` — a class component with
`getDerivedStateFromError` (set `hasError`), `componentDidCatch(error, info)` (log
to console/reporter), and a `render` that returns a static fallback with a Reload
button when `hasError`, else `this.props.children`. The fallback makes **no** new
network calls. Wrap `<App/>` with it just inside `<BrowserRouter>` in `index.js`.

**RED test** — `src/components/ui/__tests__/ErrorBoundary.test.js > "renders a fallback UI when a child throws during render instead of unmounting the whole tree"` (new file, RTL):
render `<ErrorBoundary><Boom/></ErrorBoundary>` where `Boom` throws on render;
assert `screen.getByText(/something went wrong|reload/i)` is present. **Setup:**
silence the expected error log for throwing-child tests
(`jest.spyOn(console, 'error').mockImplementation(() => {})`, restored in `afterEach`),
matching the pattern at `DatasetCard.test.js:62`, so React's boundary-error log does
not redden the suite under `--ci`.
- *Fails RED because:* no `ErrorBoundary` component/file exists, so the import
  target is missing and a child throw propagates uncaught.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-05 (MUST) — Add an overlap guard to the 3 s validation poller

- **Boundary:** polling · **Requirement:** REQ-FE-POLL-1 · **Finding:** FE-P-01 ·
  **Field:** 8, 12 (backpressure) · **Effort:** ~3h

**Goal:** A slow/hung validation backend no longer accumulates overlapping
in-flight requests every 3 s.

**Confirmed defect:** `DatasetCard.js:198` installs
`setInterval(fetchValidationStatus, 3000)` with no guard against a still-pending
fetch; the interval is cleared only inside the resolve/reject handlers
(`104-110`, `115-119`), so a never-resolving backend clears nothing and requests
stack without bound.

**Minimal fix:** Add an in-flight guard with a `useRef`:
`if (inFlightRef.current) return; inFlightRef.current = true; try {…} finally { inFlightRef.current = false; }`
around the fetch body. (Pairs with FR-06's timeout/abort so a hung poll cannot
stay in flight across ticks.)

**RED test** — `src/components/datasets/__tests__/DatasetCard.test.js > "validation poll does not stack a second request while the first is still pending"` (existing file — extend, RTL):
**Setup:** scope `jest.useFakeTimers()` to this test (the existing suite uses real
timers — restore after); mock the mount `axios.get` for `validation-status` to
resolve `{ has_latest_archive: true, validation_status: 'completed', is_valid: true }`
so the "Re-validate" button renders (it is gated on `validationStatus.has_latest_archive`
at `DatasetCard.js:513`); click it to start the poller, with `axios.get` then
returning a never-resolving promise. Advancing fake timers by 9000 ms issues **at
most one** in-flight validation-status GET (count `axios.get` calls to that URL).
- *Fails RED because:* today each 3 s tick calls `axios.get` again regardless of the
  outstanding request, so the call count grows by one every 3 s.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-06 (MUST) — Time out and abort the validation poll on unmount

- **Boundary:** polling · **Requirement:** REQ-FE-POLL-2 · **Finding:** FE-P-02 ·
  **Field:** 9, 8 · **Effort:** ~3h

**Goal:** Unmounting the card mid-fetch aborts the request so no `setState` runs
after unmount; a hung backend cannot keep the closure alive.

**Confirmed defect:** `DatasetCard.js:88-121` calls `axios.get` with no timeout and
no `signal`; the unmount cleanup (`68-72`) clears only the interval, so the resolve
path runs `setValidationStatus`/`setIsValidating` after unmount.

**Minimal fix:** Create an `AbortController` in the mount effect, pass
`controller.signal` into `axios.get` (with a `timeout`), `abort()` in the cleanup
return, and guard each `setState` with `if (!controller.signal.aborted)` (or a
`mountedRef`).

**RED test** — `src/components/datasets/__tests__/DatasetCard.test.js > "unmounting mid-validation-fetch passes an abort signal and aborts the in-flight request"` (existing file — extend, RTL):
**Setup:** mock the mount `axios.get` for `validation-status` to resolve
`{ has_latest_archive: true, ... }` so the Re-validate button renders; click it to
start the poller with `axios.get` then returning a never-resolving promise; render
then unmount. Assert **(primary)** that `axios.get` was called with an options
object carrying a `signal`, and that unmount aborts it.
- *Fails RED because:* today `axios.get` is called with only `{ headers: { Authorization } }`
  — no `signal` — so the signal matcher fails, and the unmount cleanup
  (`DatasetCard.js:68-72`) clears only the interval, never aborting the request.
  (React 18 emits **no** "state update on an unmounted component" warning, so the
  assertion is on the signal, not on `console.error`.)

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-07 (MUST) — Render per-field 422 messages in UserManagement

- **Boundary:** degradation · **Requirement:** REQ-FE-DEG-1 · **Finding:** FE-D-01 ·
  **Field:** 1, 5 · **Effort:** ~2h

**Goal:** A FastAPI 422 on the Add/Edit User form shows the offending field's
message instead of failing on the raw array.

**Confirmed defect:** `UserManagement.js:281-282` —
`const errorData = await res.json(); errorMessage = errorData.detail || errorMessage;`
FastAPI 422 `detail` is an array of `{loc,msg,type}`; a non-empty array is truthy,
so `errorMessage` becomes the array and is passed as a React child to
`<Alert type="error">` (`UserManagement.js:812`).

**Minimal fix:** Before assigning, flatten an array `detail`:
`Array.isArray(errorData.detail) ? errorData.detail.map(d => \`${d.loc.at(-1)}: ${d.msg}\`).join('; ') : (errorData.detail || errorMessage)`.
(Later consolidated onto the FR-11 parser seam.)

**RED test** — `src/components/users/__tests__/UserManagement.test.js > "shows the per-field message when create returns a 422 array detail"` (existing file — add to the existing `describe`, reusing its `jest.mock('../../../utils/apiUtils')`):
submit Add User with `apiRequest` resolving
`{ ok:false, status:422, json:()=>({ detail:[{loc:['body','password'],msg:'String should have at least 8 characters',type:'string_too_short'}] }) }`;
assert `await screen.findByText(/at least 8 characters/i)` is present.
- *Fails RED because:* today the truthy 422 array is assigned to `errorMessage` and
  passed as a React child to `<Alert>`; React 18 throws "Objects are not valid as a
  React child" rendering an array of `{loc,msg,type}` objects, so the form errors out
  and the field message never appears (the `findByText` fails).

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-08 (MUST) — Render per-field 422 messages in DatasetForm

- **Boundary:** degradation · **Requirement:** REQ-FE-DEG-2 · **Finding:** FE-D-02 ·
  **Field:** 1, 5 · **Effort:** ~2h

**Goal:** A FastAPI 422 on dataset create/update shows which field the backend
rejected instead of failing on the raw array.

**Confirmed defect:** `DatasetForm.js:119-120` —
`const errorData = await res.json(); errorMessage = errorData.detail || errorMessage;`
then `setError(errorMessage)` → `<Alert type="error">{error}</Alert>` (line 330).
Same array-detail mangling as FR-07.

**Minimal fix:** Same flatten-array-`detail` helper as FR-07 applied before
`setError` at line 120.

**RED test** — `src/components/datasets/__tests__/DatasetForm.test.js > "surfaces the field message on a 422 array detail"` (new file, RTL):
submit with `apiRequest` resolving
`{ ok:false, status:422, json:()=>({ detail:[{loc:['body','title'],msg:'Title must be less than 300 characters',type:'string_too_long'}] }) }`;
assert `await screen.findByText(/Title must be less than 300 characters/i)` is present.
- *Fails RED because:* today `setError` stores the truthy 422 array and it is passed
  as a React child to `<Alert>`; React 18 throws "Objects are not valid as a React
  child" rendering an array of `{loc,msg,type}` objects, so the field message never
  appears.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-09 (MUST) — Make the validate POST idempotent with a client key

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-4 · **Finding:** FE-T-04 ·
  **Field:** 10 (idempotency) · **Effort:** ~2h (frontend) + backend dedupe (coordinate)

**Goal:** A retry or double-click on "Re-validate" cannot enqueue duplicate
validation jobs.

**Confirmed defect:** `DatasetCard.js:177-185` issues
`axios.post(.../validate, { force: true }, { headers: { Authorization } })` — a
side-effecting call with no idempotency key. The moment FR-15 adds transport
retry, a timeout-then-retry double-submits (Non-Idempotent Retry, #17).

**Minimal fix:** Capture a key once per validation intent (e.g.
`crypto.randomUUID()` per click, or `${dataset.id}:${force}`) and send it as an
`Idempotency-Key` header; ensure the resilient client only enables retry for calls
carrying such a key. (Backend must dedupe on the key — coordinate; the frontend
item is the header.)

**RED test** — `src/components/datasets/__tests__/DatasetCard.test.js > "triggerValidation sends an Idempotency-Key header on the validate POST"` (existing file — extend, RTL):
mock the mount `axios.get` for `validation-status` to resolve
`{ has_latest_archive: true, ... }` so the Re-validate button renders; click it;
assert
`expect(axios.post).toHaveBeenCalledWith(expect.stringContaining('/validate'), expect.anything(), expect.objectContaining({ headers: expect.objectContaining({ 'Idempotency-Key': expect.any(String) }) }))`.
- *Fails RED because:* today the post headers are only `{ Authorization }`.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

---

## FR-10 (SHOULD) — Revive parseErrorResponse as the consumed typed-error seam

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-6 · **Finding:** FE-T-06 ·
  **Field:** 5 · **Effort:** ~3h

**Goal:** `apiRequest` produces a typed, status-bearing error on a non-ok response
by calling the (currently dead) RFC 7807 parser, giving every caller one error shape.

**Confirmed defect:** `apiUtils.js:233-250` defines a correct `parseErrorResponse`
but a repo-wide grep finds **zero** call sites; `apiRequest` returns the raw
`Response`, leaving status interpretation scattered (statisticsApi strings; Login
maps every non-ok to "Invalid username or password" at `Login.js:47-51`).

**Minimal fix:** In the deepened `apiRequest`, on a non-ok response call
`parseErrorResponse(response)` and reject with the typed result; export/consume it
so it has ≥ 1 live call site.

**RED test** — `src/utils/__tests__/apiUtils.test.js > "apiRequest rejects with the RFC-7807 detail/title and status on a 4xx problem+json response"` (Jest):
with `localStorage.token` set in `beforeEach` (shared apiUtils setup, see FR-01),
`fetch` resolves `{ ok:false, status:409, headers:{ get:(h)=> h==='content-type' ? 'application/problem+json' : null }, json:()=>({title:'Conflict',detail:'Already validating'}) }`;
`await expect(apiRequest('/x')).rejects.toMatchObject({ status: 409, message: 'Already validating' })`.
- *Fails RED because:* today `apiRequest` resolves to the raw `Response` on a non-ok
  status (it never calls the parser and never rejects), so `.rejects` fails.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-11 (SHOULD) — Flatten 422 array detail inside parseErrorResponse

- **Boundary:** degradation · **Requirement:** REQ-FE-DEG-4 · **Finding:** FE-D-04 ·
  **Field:** 1, 5 · **Effort:** ~2h

**Goal:** The typed-error seam itself returns a readable `message` for a 422 array
detail, so FR-07/FR-08's inline flattening can consolidate here.

**Confirmed defect:** `apiUtils.js:240-242` —
`const message = data.detail || data.title || data.message || 'An error occurred'`
returns the **array** unchanged when `data.detail` is a FastAPI 422 array, so any
consumer rendering it hits the array-child failure.

**Minimal fix:** When `Array.isArray(data.detail)`, set `message` to a joined
`loc: msg` string and also expose a `fieldErrors` map; else keep the existing
precedence.

**RED test** — `src/utils/__tests__/apiUtils.test.js > "parseErrorResponse flattens a 422 array detail into a readable string, not an array"` (Jest):
`const r = await parseErrorResponse(mk(422, { detail:[{loc:['body','password'],msg:'too short',type:'x'}] }));`
where `mk` builds a Response stub with `headers.get` keyed on name; assert
`typeof r.message === 'string'`, `r.message` matches `/password: too short/`, and does
not contain `[object Object]`.
- *Fails RED because:* today line 241 returns `data.detail` (the array) as `message`,
  so `typeof r.message` is `'object'` and the flattened text is absent.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-12 (SHOULD) — Classify status (client/throttle/server) and read Retry-After

- **Boundary:** degradation · **Requirement:** REQ-FE-DEG-3 · **Finding:** FE-D-03 ·
  **Field:** 12, 5 · **Effort:** ~3h

**Goal:** The UI can distinguish 429 (back off / Retry-After), 5xx (transient,
keep stale), and 4xx (user-fixable) instead of one undifferentiated banner.

**Confirmed defect:** Every status ≥ 400 collapses to one generic string;
`statisticsApi.js:16-21` (and 9 siblings) discard the status; a grep finds **zero**
references to 429 or `Retry-After` frontend-wide.

**Minimal fix:** In `parseErrorResponse`, return `class` (`'client' | 'throttle' |
'server'`) derived from `Math.floor(status/100)` and `status === 429`, and
`retryAfter` from `response.headers.get('Retry-After')`. Consumers branch:
429/5xx → "temporary, try again" (keep stale data on dashboards); 4xx → surface message.

**RED test** — `src/utils/__tests__/apiUtils.test.js > "parseErrorResponse classifies 429 as throttle and exposes Retry-After distinct from a 4xx client error"` (Jest):
`parseErrorResponse(mk(429, {'Retry-After':'30'}))` resolves `class === 'throttle'`
and `retryAfter === 30`; `parseErrorResponse(mk(400))` resolves `class === 'client'`
and `retryAfter` undefined (the `mk` header stub returns the value for the requested
header name).
- *Fails RED because:* today the parser returns only `{ message, status, type }` — no
  `class`, never reads `Retry-After`.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-13 (SHOULD) — Harden LandingPage: timeout, res.ok guard, no silent swallow

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-5 · **Finding:** FE-T-05 ·
  **Field:** 1, 5, 9 · **Effort:** ~2h

**Goal:** A non-ok or hung public-overview response no longer feeds garbage into
the landing stats or stalls the skeleton silently — while keeping the credited
stale-retain fallback.

**Confirmed defect:** `LandingPage.js:46-55` issues a raw `fetch` with no timeout,
calls `res.json()` without checking `res.ok` (a 500 body is set as stats), and the
`.catch(() => setIsLoadingStats(false))` is a silent no-op.

**Minimal fix:** Route through the FR-01 seam (or add an `AbortController` timeout),
guard with `if (!res.ok) throw await parseErrorResponse(res)` before `res.json()`,
and in the catch keep the stale-retain fallback **but** `console.error` and set an
error flag so an honest "live stats unavailable" affordance can render. Do not
churn the stale-retain strength.

**RED test** — `src/components/public/__tests__/LandingPage.test.js > "does not render a stat taken from a non-ok overview response"` (existing file — extend, RTL):
`global.fetch` resolves `{ ok:false, status:500, json:()=>({ total_datasets: 999999 }) }`.
`StatCard` (`StatCard.js:73`) renders the value via `value.toLocaleString()` with **no
locale arg**, so the thousands separator is **locale-dependent** (`de_DE` → `999.999`,
`en-US` → `999,999`, `LANG=C` may differ) — never hardcode a separator. Assert with a
digit-only, separator-agnostic matcher:
```js
await waitFor(() =>
  expect(
    screen.queryByText((content) => content.replace(/\D/g, '').includes('999999'))
  ).not.toBeInTheDocument()
);
```
- *Fails RED because:* today `res.json()` runs unconditionally and `setStats(data)`
  regardless of `res.ok`, so the 500 body's value is rendered (in whatever locale
  grouping) and the digit-stripped matcher finds `999999`. (A hardcoded `'999999'`
  never matches a grouped render and `'999,999'` never matches a `de_DE` `.`-grouped
  render — either is a tautology in some environment.)

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-14 (SHOULD) — Fail closed when the CSRF token cannot be obtained

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-7 · **Finding:** FE-T-07 ·
  **Field:** 5, Composition (security fails closed) · **Effort:** ~2h

**Goal:** A state-changing request is not sent without its CSRF header when the
token fetch fails — the security control fails closed.

**Confirmed defect:** `apiUtils.js:191-197` — for non-GET/HEAD methods the CSRF
fetch is wrapped in a `catch` that only `console.error`s and comments "Continue
with the request even if CSRF token retrieval fails", so the mutating request is
sent without `X-CSRF-Token`.

**Minimal fix:** If `getCsrfToken()` throws for a state-changing method, reject with
a typed `CsrfUnavailableError` instead of proceeding. (The token-absent path
already fails closed and is credited — preserve it.)

**RED test** — `src/utils/__tests__/apiUtils.test.js > "apiRequest does not send a state-changing request when the CSRF token cannot be obtained"` (Jest):
`localStorage` has a `token` (set in `beforeEach`, see FR-01) but no `csrfToken`;
mock the CSRF token fetch (the `fetch` to `/tokens/csrf`) to reject / return `!ok`;
call `apiRequest('/datasets/1', { method:'POST' })` and assert it **rejects** with a
typed `CsrfUnavailableError` **and** that no `fetch` was made to the mutating
endpoint:
`expect(global.fetch).not.toHaveBeenCalledWith(expect.stringContaining('/datasets/1'), expect.objectContaining({ method:'POST' }))`.
- *Fails RED because:* today the `catch` only logs and falls through, so the POST to
  `/datasets/1` IS issued and `apiRequest` resolves; both assertions fail. (Assert on
  the **mutating endpoint specifically** — not a total `fetch` count — because the
  CSRF probe is itself a `fetch`.)

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-15 (SHOULD) — Bounded, jittered, retriable-only transient retry

- **Boundary:** transport · **Requirement:** REQ-FE-CLIENT-8 · **Finding:** FE-T-08 ·
  **Field:** 9, 11 · **Effort:** ~4h

**Goal:** A transient network error or 5xx is recovered by a small, jittered,
capped retry at one layer; a 4xx is never retried; a chronically-down dependency
fast-fails.

**Confirmed defect:** `apiUtils.js:143-160` — the only retry is the single
un-jittered post-401 refresh (`145` refresh, `153` retry fetch, itself un-timed);
there is no transient-error retry, no backoff/jitter, and no breaker.

**Minimal fix:** In the deepened `apiRequest`, add a bounded retry (e.g. max 2) that
fires **only** on timeout/network-error/5xx (branch on the FR-12 typed `class`),
with `sleep = random(0, min(cap, base * 2^attempt))`; retry at this one layer only
(no double-stacking with SWR). Keep the 401→refresh retry distinct. **Retry MUST be
gated on idempotency:** only idempotent methods (GET/HEAD), or side-effecting calls
carrying an `Idempotency-Key` (from FR-09), are retried. Optionally add a lightweight
per-endpoint breaker.

**RED test** — `src/utils/__tests__/apiUtils.test.js > "apiRequest retries a 503 once with backoff and then succeeds, but does NOT retry a 400"` (Jest, fake timers):
with `localStorage.token` set (`beforeEach`, see FR-01), `jest.useFakeTimers()`, and
`Math.random` mocked to a fixed value (e.g. 0.5) so the jittered backoff is a known
duration: `fetch` returns `{ok:false,status:503}` then `{ok:true,…}` → after
`jest.advanceTimersByTime(cap)` `apiRequest` resolves with `fetch` called twice; a
second case returns `{ok:false,status:400}` → `apiRequest` rejects with `fetch`
called exactly once.
- *Fails RED because:* today a 503 is returned as-is (fetch called once, no retry),
  so `toHaveBeenCalledTimes(2)` fails.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-16 (SHOULD) — Back off the dashboard auto-refresh after repeated failures

- **Boundary:** polling · **Requirement:** REQ-FE-POLL-3 · **Finding:** FE-P-03 ·
  **Field:** 11, 9 · **Effort:** ~3h

**Goal:** A backend that is down stops being polled every 60 s from every open
dashboard tab; the cadence widens or pauses and resets on recovery.

**Confirmed defect:** `PublicStatsDashboard.js:153-157` calls `fetchAllStats(true)`
every `REFRESH_INTERVAL = 60000` ms unconditionally; on failure the catch only logs
"will retry on next interval" (`127`) — no failure counter, no backoff, no breaker.

**Minimal fix:** Track consecutive failures in a ref; after N (e.g. 3) rejections
widen the effective interval (the interval keeps firing but the callback
early-returns while in backoff — count consecutive failures in a ref and
`if (failures >= 3 && !dueForRetry()) return;`), or pause with a manual-retry control,
resetting to 60 s on the first success. (The guard-skip design makes the assertion
below deterministic; do not rely on clearing/recreating the interval.)

**RED test** — `src/components/statistics/__tests__/PublicStatsDashboard.test.js > "auto-refresh backs off after repeated failures instead of firing every 60s"` (existing file — extend, RTL + fake timers):
with `jest.useFakeTimers()` and `publicStatsApi.getOverview` rejecting on every call,
after the initial load advance time by 60 s three times, **flushing microtasks
between ticks** (`await act(async () => { jest.advanceTimersByTime(60000); })`) so the
failure counter — incremented in the async `.catch` — settles before the next tick;
then advance a further 60 s. Assert **no** new `getOverview` call fires on the fourth
60 s tick.
- *Fails RED because:* today the interval callback calls `fetchAllStats(true)` every
  60 s regardless of prior failures, so `getOverview` IS invoked on the fourth tick.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-17 (SHOULD) — Guard and abort the dashboard refresh batch

- **Boundary:** polling · **Requirement:** REQ-FE-POLL-4 · **Finding:** FE-P-04 ·
  **Field:** 9, 8 · **Effort:** ~3h

**Goal:** A refresh slower than 60 s does not overlap a second batch, and unmount
aborts the in-flight batch.

**Confirmed defect:** `PublicStatsDashboard.js:35-48,129-133,153-157` —
`fetchAllStats` fires `Promise.all` of three bare un-timed fetches; the 60 s
interval does not check whether the previous batch is still pending; `stopAutoRefresh`
(`160-169`) clears timers but does not abort, so the resolve path setStates after
unmount.

**Minimal fix:** Add an `isFetchingRef` guard so a tick is skipped while a batch is
in flight; thread an `AbortController.signal` into the `publicStatsApi` calls (the
FR-01/FR-02 seam, which must accept a `signal`/options arg) and abort it in
`stopAutoRefresh`/the unmount cleanup; guard the setStates behind a `mountedRef` or
`!signal.aborted`.

**RED test** — `src/components/statistics/__tests__/PublicStatsDashboard.test.js > "passes an abort signal to the stats requests and aborts them on unmount"` (existing file — extend, RTL):
spy on `publicStatsApi.getOverview/getProviders/getTimeline`; render then unmount the
dashboard. Assert each call received an options object carrying an `AbortSignal`
(`expect(publicStatsApi.getOverview).toHaveBeenCalledWith(expect.objectContaining({ signal: expect.any(AbortSignal) }))`)
and that unmount triggered `abort()` on that controller.
- *Fails RED because:* today the three `publicStatsApi` calls take no `signal`
  argument and `stopAutoRefresh` (`PublicStatsDashboard.js:160-169`) only clears the
  timers, so the signal matcher fails. (React 18 emits no "state update on an
  unmounted component" warning, so a `console.error` assertion would be a tautology —
  assert on the signal instead.)

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

## FR-18 (SHOULD) — Add route/widget error boundaries as bulkheads

- **Boundary:** render containment · **Requirement:** REQ-FE-EB-2 · **Finding:** FE-EB-02 ·
  **Field:** 11 (bulkheads) · **Effort:** ~3h

**Goal:** A throw in one heavy widget is contained to that panel while the header,
footer, nav, and sibling routes keep rendering.

**Confirmed defect:** `App.js:140-236` renders every `<Route>` element bare with no
per-route/per-widget boundary; with FR-04's top-level-only boundary, one widget
fault still replaces the entire app with the fallback.

**Minimal fix:** Reuse the FR-04 `ErrorBoundary` (add an optional `fallback` prop)
as a finer bulkhead around the heavy dashboards/cards (`AdminDashboard`,
`PublicStatsDashboard`, `ProviderDetail`, `DatasetCard`).

**RED test** — `src/components/ui/__tests__/ErrorBoundary.test.js > "contains a throwing child to its own boundary while a sibling subtree keeps rendering"` (existing file from FR-04, RTL):
render `<><ErrorBoundary><Boom/></ErrorBoundary><div>sibling-ok</div></>`; assert the
boundary fallback shows **and** `screen.getByText('sibling-ok')` is still present.
Reuse FR-04's `console.error` silencing for the throwing-child render.
- *Fails RED because:* without a wrapping boundary at the sibling level, a throw
  propagates past the sibling and unmounts the whole render, so `sibling-ok` is absent.

- [ ] Write the RED test; observe it fail; apply the fix; observe it pass; full suite green + eslint clean.

---

## Summary

| Block | Items | Findings | Spec requirements |
|---|---|---|---|
| MUST | FR-01…FR-09 (9) | FE-T-01,02,03,04; FE-EB-01; FE-P-01,02; FE-D-01,02 | REQ-FE-CLIENT-1..4, -EB-1, -POLL-1..2, -DEG-1..2 |
| SHOULD | FR-10…FR-18 (9) | FE-T-05,06,07,08; FE-P-03,04; FE-D-03,04; FE-EB-02 | REQ-FE-CLIENT-5..8, -POLL-3..4, -DEG-3..4, -EB-2 |

The spec is **malformed** (all four boundaries) until the MUST block lands; the
SHOULD block clears the degraded items and completes the canonical resilient-client
seam. Each item is test-locked and independently committable; nothing here changes
behaviour beyond its requirement, and the credited strengths are preserved
throughout.
