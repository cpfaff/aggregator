# GFBio Aggregator Frontend Resilience Hardening — A Specification

> Status: **draft for human approval** (discovery + spec; no production code changed).
> Scope: `aggregator/frontend/src/` (CRA, React 18, plain JS).
> Companion: `roadmap.md` sequences the work that makes this
> specification true. The backend counterpart is `../resilience-backend/spec.md`
> (already hardened on this branch); this document is its frontend mirror and
> reuses its structure, keyword convention, and traceability discipline.

**Keyword convention:** BCP 14 (RFC 2119 / RFC 8174). The UPPERCASE words MUST,
MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY are normative obligations;
the same words in lower case are prose.

**Normative references:**
- BCP 14 — RFC 2119 / RFC 8174 (keyword interpretation). *(undated — latest)*
- RFC 9110 §15 (HTTP status semantics: 4xx client / 5xx server / 429 + Retry-After). *(undated — latest)*
- RFC 7807 / RFC 9457 (Problem Details for HTTP APIs — `type`/`title`/`detail`). *(undated — latest)*
- WHATWG Fetch — `AbortController` / `AbortSignal`. *(living standard)*
- React 18 — error boundaries (`getDerivedStateFromError` / `componentDidCatch`). *(undated — latest)*

---

## 1. Overview (informative)

### 1.1 Motivation

The aggregator frontend is the single human entry point to the platform. It
crosses exactly one trust/process boundary that matters for resilience: the
network call to the FastAPI backend. The backend half of that boundary has been
hardened on this branch (timeouts, typed failures, idempotency, dead-letter).
The frontend half has not: it assumes the backend always answers, answers fast,
and answers well-formed. None of those hold under load, partial outage, or
deploy.

The lever is the same as the backend's: `Availability = MTBF / (MTBF + MTTR)`.
A frontend cannot raise the backend's MTBF, but it controls its own MTTR and its
own blast radius — whether a slow dependency hangs a spinner forever, whether a
single malformed payload blanks the whole app, and whether a transient blip is
shown to the user as a permanent dead end. Today, each of those degrades to the
worst outcome.

### 1.2 The canonical pattern (the conformance target)

The backend established one resilient seam — `EsGateway` — through which every
Elasticsearch call passes, so a timeout, a typed failure, and an honest
`unknown` are guaranteed in *one* place rather than re-implemented per caller.

The frontend has the inverse problem: **three independent transport idioms**
already exist and drift apart —
1. `apiUtils.apiRequest` → `fetchWithTokenExpiration` (raw `fetch`, authenticated),
2. `statisticsApi.publicStatsApi` (bare `fetch`, unauthenticated),
3. `DatasetCard` (raw `axios`), plus `Login` (raw `fetch`) —
and **none** of them is resilient (no timeout, no abort, no typed error, no
bounded retry).

This specification's conformance target is therefore a pattern the frontend does
**not yet** have: a single resilient client formed by **deepening `apiRequest`**
into the place that owns timeout + abort, bounded jittered retry, and a typed,
status-bearing error (via the currently-dead `parseErrorResponse`), with the
scattered callers routed through it. The deepened `apiRequest` is to the
frontend what `EsGateway` is to the backend. The requirements in §3 are written
so that they can be satisfied at that one seam.

A partial exemplar already exists at the **consumption** layer and MUST be
preserved, not churned (see §1.4 Strengths and Appendix A): the three-state
loading skeleton, the stale-while-error banner, and the honest `unknown` badge
are textbook honest-degradation and are credited throughout.

### 1.3 Method and findings

Method: the `resilience-review` checklist (`reference/checklist.md`, 14 practice
fields) was run against each of the four frontend boundaries below; the diff was
pattern-matched against the 22-item antipattern catalogue; each candidate defect
was then **adversarially refute-verified** by an independent reviewer that
re-read the cited lines and tried to refute it (default verdict *uncertain*; kept
only *confirmed*).

The four audited boundaries:
1. **Transport / data layer** — `apiUtils.js`, `statisticsApi.js`, and the
   scattered raw `fetch`/`axios` in `DatasetCard.js`, `Login.js`, `LandingPage.js`.
2. **Whole-app render containment** — React error boundaries (`index.js`, `App.js`).
3. **Polling / backpressure** — `DatasetCard` (3 s) and `PublicStatsDashboard` (60 s).
4. **Degradation consumption** — 429/5xx-vs-4xx handling; FastAPI 422 `detail`
   arrays consumed by forms.

Result: **18 distinct confirmed defects** (9 MUST-class, 9 SHOULD-class) and
**0 refuted**. The unusually clean refute rate reflects the nature of these
defects — they are *structural absences of a mechanism* (no timeout, no
`AbortController`, no error boundary, no idempotency key), each verifiable by
direct inspection or grep, not speculative behavioural bugs. The verification
pass nonetheless re-read every cited line; where a line citation was imprecise it
was corrected before this spec.

Baseline (the conformance gate's starting point) was recorded green **first**, on
this branch at commit `231c82c`: `CI=true npm test -- --watchAll=false` →
16 suites / 73 tests passing; `npx eslint src/` → clean (exit 0). (Three
pre-existing `testing-library/*` lint errors in test files, present on `master`
and unrelated to this work, were fixed in that commit to make the gate honestly
green.)

### 1.4 Terms (glossary — each defined once)

- **Resilient client (the seam):** the target deepened `apiUtils.apiRequest`
  through which every backend call passes, owning timeout+abort, bounded retry,
  and typed errors. Does not yet exist; §3.2 specifies it.
- **Typed error:** an error object exposing at least `{ status, message }` (and,
  per REQ-FE-DEG-3, `class` ∈ {client, throttle, server} and `retryAfter`),
  produced by `parseErrorResponse`, as opposed to a generic `Error` whose only
  signal is interpolated text.
- **`REQUEST_TIMEOUT_MS`:** the single named constant (to be introduced in
  `apiUtils.js`) that fixes the request timeout the resilient client enforces; the
  requirements that reference "a configured request timeout" mean this constant.
- **Liberal acceptance:** parsing/rendering a response body as valid domain data
  without first checking the response is ok (antipattern #20).
- **Stale-while-error:** on a failed refresh, retaining the last successful data
  on screen and surfacing a non-blocking warning, rather than blanking. A
  credited strength (`PublicStatsDashboard`, `LandingPage`).
- **Honest `unknown`:** mapping a fetch error or an explicit `unknown` payload to
  a distinct "Status unavailable" affordance rather than guessing a state. A
  credited strength (`DatasetCard` harvest badge).
- **Blast radius:** the portion of the rendered UI that a single fault destroys.
  Today an uncontained render throw has whole-app blast radius (§3.3).
- **Strengths (credited, preserve — do not churn):**
  three-state loading skeleton (`Skeleton.js`, `StatCard.js`); stale-while-error
  banner (`PublicStatsDashboard.js:299-303`); honest `unknown` badge
  (`DatasetCard.js:54-58, 797-803`); security-fails-closed on a missing access
  token (`apiUtils.js:176-180`); idempotency-conscious SWR null-keying
  (`DatasetCard.js:45-51`).

---

## 2. Conformance (normative)

### 2.1 Conformance target

The single conformance target is **the aggregator frontend** (`frontend/src/`). A
boundary (§1.3) is **conformant** when every MUST-class requirement scoped to it
in §3 is satisfied and verified by that requirement's named **Verification**.

### 2.2 Statement levels

- A **MUST / MUST NOT / SHALL / SHALL NOT** requirement is mandatory. An
  unsatisfied MUST means the boundary is *malformed* and MUST NOT be released as
  hardened.
- A **SHOULD / SHOULD NOT** requirement is a strong default. It MAY be left
  unsatisfied only with a recorded justification and a tracked follow-up item.
- A **MAY** provision is optional and carries no conformance weight.

### 2.3 Claiming conformance

Conformance is claimed per requirement by demonstrating that requirement's
**Verification** — for a testable requirement, a named automated Jest/RTL test
(listed in §3 and in the roadmap item) that was observed **failing against
pre-hardening code** and passing after the fix. A conformance claim for a
boundary lists each of its requirements with the verifying test and its status.

### 2.4 Precedence

Where this specification conflicts with incidental code comments or prior
informal notes, this specification prevails for the aggregator frontend.
Unresolved conflicts MUST be settled before the affected requirement is claimed
conformant. This spec does not govern the backend (`backend/app/`), the harvester,
the index, or the Angular search UI.

---

## 3. Requirements (normative)

### 3.0 How to read traceability

Each leaf requirement (§3.2–§3.5) has a stable ID, a single testable obligation in
EARS form, an informative rationale, a named verification test, and two-way
traceability: `↑` to the checklist Field and the cross-cutting `REQ-FE-CORE-*` it
specialises, and `↓` to the roadmap item (`FR-NN`) that implements it. The
cross-cutting `REQ-FE-CORE-*` requirements (§3.1) are **roll-ups**: each enumerates
an obligation discharged by its leaf requirements and is verified *by analysis*
(its leaves carry the per-obligation tests), not by a single test of its own.
Finding IDs (`FE-*`) reference the discovery record summarised in Appendix A.

### 3.1 Cross-cutting canonical requirements (REQ-FE-CORE-*)

**[REQ-FE-CORE-1] (MUST).** While the frontend has a request in flight across the
network boundary to the backend API, the frontend SHALL bound that request with a
configured request timeout (`REQUEST_TIMEOUT_MS`) enforced by an `AbortController`,
such that the request's promise always settles.
- *Rationale:* a backend that accepts the connection but never responds otherwise
  leaves the promise unsettled forever; loading flags set before the call never
  clear and no `finally`/cleanup runs.
- *Verification:* analysis — established by REQ-FE-CLIENT-1 and inherited by
  REQ-FE-CLIENT-2, -3, -5 and REQ-FE-POLL-2, -4.
- *Trace:* ↑ Field 9 (Timeouts). ↓ REQ-FE-CLIENT-1, -2, -3, -5; REQ-FE-POLL-2, -4.

**[REQ-FE-CORE-2a] (MUST).** When a backend request completes with a non-ok HTTP
status or fails at the transport, the frontend SHALL represent the failure as a
single typed error carrying the HTTP status, and SHALL NOT discard the status into
free text.
- *Rationale:* without a typed, status-bearing error the UI cannot tell 429 from
  503 from 400, cannot drive retry-only-on-5xx, and cannot show a real message.
- *Verification:* analysis — established by REQ-FE-CLIENT-6 and verified through
  REQ-FE-CLIENT-2 and REQ-FE-DEG-1, -2, -3, -4.
- *Trace:* ↑ Field 5 (fail-fast), Field 1 (boundary validation).
  ↓ REQ-FE-CLIENT-2, -6; REQ-FE-DEG-1, -2, -3, -4.

**[REQ-FE-CORE-2b] (MUST).** When a backend request fails, the frontend SHALL NOT
swallow the failure silently, and SHALL NOT parse or render a non-ok response body
as valid data.
- *Rationale:* a silent catch hides the fault from user and logs alike; rendering a
  non-ok body as data (liberal acceptance) lets a 500 error page become "stats".
- *Verification:* analysis — verified through REQ-FE-CLIENT-5.
- *Trace:* ↑ Field 5 (no silent catch), Field 1 (no liberal acceptance).
  ↓ REQ-FE-CLIENT-5.

**[REQ-FE-CORE-3] (MUST).** The frontend SHALL contain a render-time exception
thrown by any component within a bounded blast radius via a React error boundary,
and SHALL NOT allow a single descendant's render-time throw to unmount the entire
application.
- *Rationale:* React 18 `createRoot` unmounts the whole tree on any uncaught
  render error; with no boundary, one malformed payload blanks every route,
  including `/login`, with no recovery affordance.
- *Verification:* analysis — verified via REQ-FE-EB-1 and REQ-FE-EB-2.
- *Trace:* ↑ Field 11 (blast-radius containment). ↓ REQ-FE-EB-1, -2.

**[REQ-FE-CORE-4] (MUST).** Where the frontend issues a side-effecting request
that may be retried or re-submitted, the frontend SHALL attach a client-supplied
idempotency key so the server can deduplicate replays.
- *Rationale:* a timeout never reveals whether the effect happened; a retry or a
  double-click without a key enqueues duplicate work (here, duplicate validation
  jobs). Idempotency MUST exist before any transport retry is enabled.
- *Verification:* analysis — verified via REQ-FE-CLIENT-4.
- *Trace:* ↑ Field 10 (Idempotency). ↓ REQ-FE-CLIENT-4.

**[REQ-FE-CORE-5] (MUST).** If a security control required for a request cannot be
satisfied — no access token, or no CSRF token for a state-changing method — then
the frontend SHALL fail closed by not issuing the request.
- *Rationale:* a security control must initialise to deny; an exception in
  obtaining it MUST NOT downgrade to a permissive send. (The access-token path
  already fails closed — `apiUtils.js:176-180`, credited; the CSRF path is the gap.)
- *Verification:* analysis — verified via REQ-FE-CLIENT-7.
- *Trace:* ↑ Field 5; Composition (security fails closed). ↓ REQ-FE-CLIENT-7.

**[REQ-FE-CORE-6] (SHOULD).** Where the frontend retries transient failures or
polls a backend endpoint, it should bound and jitter retries at a single layer,
and should reduce its request rate — back off, or open a breaker — after
consecutive failures, rather than firing at a fixed cadence against a dependency
that is already failing.
- *Rationale:* a fixed-cadence poller and an un-jittered retry both amplify load
  on a struggling backend (Retry Storm); recovery should be automatic for
  transient faults and self-throttling for sustained ones.
- *Verification:* analysis — verified via REQ-FE-CLIENT-8 and REQ-FE-POLL-1, -3, -4.
- *Trace:* ↑ Fields 8 (bounded consumption), 9 (backoff+jitter), 11 (breaker),
  12 (backpressure). ↓ REQ-FE-CLIENT-8; REQ-FE-POLL-1, -3, -4.

### 3.2 Transport — the resilient client (REQ-FE-CLIENT-*)

**[REQ-FE-CLIENT-1] (MUST).** While `fetchWithTokenExpiration` awaits a `fetch`,
the frontend SHALL pass an `AbortController` signal to that `fetch` and SHALL
abort the request after `REQUEST_TIMEOUT_MS` — on both the initial call
(`apiUtils.js:140`) and the post-401 retry (`apiUtils.js:153`).
- *Rationale:* `apiRequest` is the seam for every authenticated call; a hung
  backend otherwise pins every such call (Slow Responses + Blocked Threads).
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "apiRequest
  rejects with a TimeoutError when the backend never responds within the timeout"`:
  with `localStorage.token` set (auth precondition met), fake timers and a
  never-resolving `fetch`, advancing past `REQUEST_TIMEOUT_MS` makes the returned
  promise reject with a typed `TimeoutError`.
- *Trace:* ↑ REQ-FE-CORE-1; Field 9. Finding FE-T-01. ↓ FR-01.

**[REQ-FE-CLIENT-2] (MUST).** When a `publicStatsApi` call
(`statisticsApi.js:16,33,45`) receives a non-ok response, the frontend SHALL
reject with a typed error exposing the HTTP `status`.
- *Rationale:* the unauthenticated stats path bypasses `apiRequest` entirely and
  throws `Error('Failed to fetch …: ' + status)`, discarding the status as data and
  the RFC 7807 body. (Its request timeout is inherited from REQ-FE-CORE-1 once the
  call is routed through the resilient client.)
- *Verification:* test — `src/utils/__tests__/statisticsApi.test.js >
  "publicStatsApi.getOverview rejects with a typed error carrying the HTTP status,
  not a generic string"`: a 503 response yields a rejection matching `{ status: 503 }`.
- *Trace:* ↑ REQ-FE-CORE-1, -2a; Fields 9, 5. Finding FE-T-02. ↓ FR-02.

**[REQ-FE-CLIENT-3] (MUST).** While `DatasetCard` issues its validation-status,
harvest-status, and `validate` requests (`DatasetCard.js:14-16, 91-98, 177-185`),
each request SHALL carry a request timeout — a `timeout`/`signal` on the call or
by routing through the resilient client.
- *Rationale:* `axios` defaults to no timeout and no `axios.create`/`defaults.timeout`
  exists repo-wide; combined with the 3 s poll (§3.4) a hung endpoint stacks
  requests without bound.
- *Verification:* test — `src/components/datasets/__tests__/DatasetCard.test.js >
  "validation-status request is issued with a request timeout"`: `axios.get` is
  called with a config containing a numeric `timeout`.
- *Trace:* ↑ REQ-FE-CORE-1; Field 9. Finding FE-T-03. ↓ FR-03.

**[REQ-FE-CLIENT-4] (MUST).** When `DatasetCard` issues the side-effecting
`POST …/validate` (`DatasetCard.js:177-185`), the frontend SHALL include a
client-supplied `Idempotency-Key` so a retry or double-submit cannot enqueue
duplicate validation jobs.
- *Rationale:* `force: true` with no key lets one user action spawn multiple
  concurrent validation jobs once transport retry (REQ-FE-CLIENT-8) exists; the
  key MUST precede retry (Non-Idempotent Retry, #17).
- *Verification:* test — `src/components/datasets/__tests__/DatasetCard.test.js >
  "triggerValidation sends an Idempotency-Key header on the validate POST"`.
- *Trace:* ↑ REQ-FE-CORE-4; Field 10. Finding FE-T-04. ↓ FR-09.

**[REQ-FE-CLIENT-5] (SHOULD).** When the `LandingPage` public-overview request
(`LandingPage.js:46-49`) returns a non-ok response, the frontend should not set
the response body as stats data.
- *Rationale:* the request calls `res.json()` without checking `res.ok` and the
  `.catch` is a silent no-op; a 500 body is rendered as stats, and a hung backend
  leaves the skeleton forever. The accompanying fix also adds a timeout and an error
  log; the stale-retain fallback is a credited strength and is preserved.
- *Verification:* test — `src/components/public/__tests__/LandingPage.test.js >
  "does not render a stat taken from a non-ok overview response"`: a numeric value
  from a 500 body is not rendered (asserted with a separator-agnostic, digit-only
  matcher, since `StatCard` renders numbers via locale-dependent `toLocaleString()`).
- *Trace:* ↑ REQ-FE-CORE-2b; Fields 1, 5, 9. Finding FE-T-05. ↓ FR-13.

**[REQ-FE-CLIENT-6] (SHOULD).** When the resilient client receives a non-ok
response, it should obtain the typed error by calling `parseErrorResponse`
(`apiUtils.js:233-250`), which should thereby have at least one live call site.
- *Rationale:* `parseErrorResponse` is a correct RFC 7807 parser but is dead
  (zero call sites); it is the keystone that makes a typed error model possible
  for every caller. Reviving and consuming it removes the duplicated string-error
  idioms.
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "apiRequest
  rejects with the RFC-7807 detail/title and status on a 4xx problem+json
  response"`: a 409 `problem+json` yields a rejection matching `{ status: 409,
  message: 'Already validating' }`.
- *Trace:* ↑ REQ-FE-CORE-2a; Field 5. Finding FE-T-06. ↓ FR-10.

**[REQ-FE-CLIENT-7] (SHOULD).** If `getCsrfToken` throws while preparing a
state-changing request (`apiUtils.js:191-197`), then `apiRequest` should reject
and should not issue the mutating request without the `X-CSRF-Token` header.
- *Rationale:* the current `catch` only logs and continues, sending an
  unprotected mutating request — a security control degrading open. A deliberate
  degrade, if ever wanted, must be a recorded justification, not the default.
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "apiRequest does
  not send a state-changing request when the CSRF token cannot be obtained"`: no
  `fetch` is made to the mutating endpoint and `apiRequest` rejects.
- *Trace:* ↑ REQ-FE-CORE-5; Field 5, Composition. Finding FE-T-07. ↓ FR-14.

**[REQ-FE-CLIENT-8] (SHOULD).** Where the resilient client retries a failed
request, it should not retry a 4xx response, and should otherwise retry only on
timeout/network-error/5xx, with a bounded attempt count, capped exponential backoff
with jitter, applied at this one layer (not double-stacked with SWR).
- *Rationale:* the only retry today is the single un-jittered post-401 refresh;
  there is no transient-error recovery, and any retry added without these bounds
  becomes a Retry Storm.
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "apiRequest
  retries a 503 once with backoff and then succeeds, but does NOT retry a 400"`:
  `fetch` is called twice for 503, exactly once for 400.
- *Trace:* ↑ REQ-FE-CORE-6; Fields 9, 11. Finding FE-T-08. ↓ FR-15.

### 3.3 Whole-app render containment (REQ-FE-EB-*)

**[REQ-FE-EB-1] (MUST).** The frontend SHALL contain a render-time throw from any
descendant of `<App/>` by rendering a static fallback in its place, instead of
unmounting the application root.
- *Mechanism (informative):* a React error boundary (class component with
  `getDerivedStateFromError` + `componentDidCatch`) wrapping `<App/>` inside
  `<BrowserRouter>` in `src/index.js`, whose fallback offers a reload affordance and
  makes no new network calls (failover, not cold fallback).
- *Rationale:* the root tree (`index.js:9-17`) is `StrictMode > BrowserRouter >
  AuthProvider > App` with zero boundaries; one throw blanks the entire app.
- *Verification:* test — `src/components/ui/__tests__/ErrorBoundary.test.js >
  "renders a fallback UI when a child throws during render instead of unmounting
  the whole tree"`.
- *Trace:* ↑ REQ-FE-CORE-3; Field 11. Finding FE-EB-01. ↓ FR-04.

**[REQ-FE-EB-2] (SHOULD).** The frontend should wrap each heavy route element or
widget (e.g. `AdminDashboard`, `PublicStatsDashboard`, `ProviderDetail`,
`DatasetCard`) in an error boundary so that a throw is contained to that panel
while the header, footer, navigation, and sibling routes keep rendering.
- *Rationale:* a top-level-only boundary still replaces the entire app when one
  widget faults; finer boundaries are bulkheads that preserve the credited
  degradation strengths for the rest of the page.
- *Verification:* test — `src/components/ui/__tests__/ErrorBoundary.test.js >
  "contains a throwing child to its own boundary while a sibling subtree keeps
  rendering"`.
- *Trace:* ↑ REQ-FE-CORE-3; Field 11 (bulkheads). Finding FE-EB-02. ↓ FR-18.

### 3.4 Polling / backpressure (REQ-FE-POLL-*)

**[REQ-FE-POLL-1] (MUST).** While the `DatasetCard` validation poller is active
(`DatasetCard.js:198`), the frontend SHALL NOT dispatch a new validation-status
request while the previous one is still in flight.
- *Rationale:* `setInterval(fetchValidationStatus, 3000)` fires unconditionally;
  on a hung backend, in-flight requests pile up without bound (no backpressure).
- *Verification:* test — `src/components/datasets/__tests__/DatasetCard.test.js >
  "validation poll does not stack a second request while the first is still
  pending"`: with a never-resolving fetch, advancing 9 s issues at most one
  in-flight request.
- *Trace:* ↑ REQ-FE-CORE-6; Fields 8, 12. Finding FE-P-01. ↓ FR-05.

**[REQ-FE-POLL-2] (MUST).** When `DatasetCard` unmounts while a validation request
is in flight, the frontend SHALL abort that request (via an `AbortController`
signal) so that no `setState` runs after unmount.
- *Rationale:* the unmount cleanup clears only the interval
  (`DatasetCard.js:68-72`), not the in-flight request; the resolve path then sets
  state on an unmounted component. (The per-request timeout is required separately by
  REQ-FE-CLIENT-3.)
- *Verification:* test — `src/components/datasets/__tests__/DatasetCard.test.js >
  "unmounting mid-validation-fetch passes an abort signal and aborts the in-flight
  request"`: `axios.get` is called with an options object carrying a `signal`, and
  unmount triggers `abort()`. (React 18 emits no unmount warning, so the assertion is
  on the signal, not on `console.error`.)
- *Trace:* ↑ REQ-FE-CORE-1; Field 8. Finding FE-P-02. ↓ FR-06.

**[REQ-FE-POLL-3] (SHOULD).** Where the `PublicStatsDashboard` auto-refresh
(`PublicStatsDashboard.js:153-157`) observes consecutive failures, it should widen
its effective interval (capped backoff) or pause and offer a manual retry,
resetting to the 60 s cadence on the first success.
- *Rationale:* on failure the dashboard logs "will retry on next interval" and
  keeps firing every 60 s at a backend that is already down, from every open tab,
  with no breaker.
- *Verification:* test — `src/components/statistics/__tests__/PublicStatsDashboard.test.js >
  "auto-refresh backs off after repeated failures instead of firing every 60s"`.
- *Trace:* ↑ REQ-FE-CORE-6; Fields 11, 9. Finding FE-P-03. ↓ FR-16.

**[REQ-FE-POLL-4] (SHOULD).** While a `PublicStatsDashboard` refresh batch is in
flight, the frontend should skip the next refresh tick rather than overlap
batches, and should abort the in-flight batch on unmount via an `AbortController`
signal passed to each request.
- *Rationale:* `fetchAllStats` fires `Promise.all` of three un-timed bare fetches;
  a refresh slower than 60 s overlaps, and unmount does not abort. (The per-request
  timeout is required by REQ-FE-CORE-1 / REQ-FE-CLIENT-2.)
- *Verification:* test — `src/components/statistics/__tests__/PublicStatsDashboard.test.js >
  "passes an abort signal to the stats requests and aborts them on unmount"`: each
  `publicStatsApi` call receives an options object carrying a `signal`, and unmount
  triggers `abort()` (asserted on the signal, not on a removed React-18 warning).
- *Trace:* ↑ REQ-FE-CORE-1, -6; Fields 9, 8. Finding FE-P-04. ↓ FR-17.

### 3.5 Degradation consumption (REQ-FE-DEG-*)

**[REQ-FE-DEG-1] (MUST).** When a user-management request returns HTTP 422 with an
array `detail` (`UserManagement.js:281-282`), the frontend SHALL render a
per-field validation message rather than passing the raw `detail` array to the
error `Alert`.
- *Rationale:* FastAPI 422 `detail` is an array of `{loc,msg,type}`; `errorData.detail
  || errorMessage` keeps the truthy array, and passing an array of objects as a React
  child throws "Objects are not valid as a React child", so the form errors out on
  every validation error instead of showing the field message.
- *Verification:* test — `src/components/users/__tests__/UserManagement.test.js >
  "shows the per-field message when create returns a 422 array detail"`.
- *Trace:* ↑ REQ-FE-CORE-2a; Fields 1, 5. Finding FE-D-01. ↓ FR-07.

**[REQ-FE-DEG-2] (MUST).** When a dataset create/update request returns HTTP 422
with an array `detail` (`DatasetForm.js:119-120`), the frontend SHALL render a
per-field validation message rather than passing the raw `detail` array to the
error `Alert`.
- *Rationale:* identical defect to REQ-FE-DEG-1 on the dataset path; the curator
  cannot tell which field the backend rejected (and the form errors out on the
  array child).
- *Verification:* test — `src/components/datasets/__tests__/DatasetForm.test.js >
  "surfaces the field message on a 422 array detail"`.
- *Trace:* ↑ REQ-FE-CORE-2a; Fields 1, 5. Finding FE-D-02. ↓ FR-08.

**[REQ-FE-DEG-3] (SHOULD).** When a backend response carries HTTP 429, the typed
error should carry a `throttle` class (distinct from a 4xx `client` and a 5xx
`server` class) and should expose the `Retry-After` value.
- *Rationale:* every status ≥ 400 is currently collapsed to one generic banner;
  the frontend has zero references to 429 or `Retry-After`, so overload looks like
  a permanent client error and a transient 5xx like a user-fixable 4xx.
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "parseErrorResponse
  classifies 429 as throttle and exposes Retry-After distinct from a 4xx client
  error"`.
- *Trace:* ↑ REQ-FE-CORE-2a, -6; Fields 12, 5. Finding FE-D-03. ↓ FR-12.

**[REQ-FE-DEG-4] (SHOULD).** When `parseErrorResponse` receives a body whose
`detail` is an array, it should return `message` as a readable string (e.g.
`loc: msg` per entry), not the array.
- *Rationale:* the parser is the intended single seam for REQ-FE-DEG-1/-2, but as
  written (`apiUtils.js:240-242`) it returns the array unchanged for a 422,
  reproducing the array-child failure at every future call site.
- *Verification:* test — `src/utils/__tests__/apiUtils.test.js > "parseErrorResponse
  flattens a 422 array detail into a readable string, not an array"`.
- *Trace:* ↑ REQ-FE-CORE-2a; Fields 1, 5. Finding FE-D-04. ↓ FR-11.

---

## 4. Requirements traceability matrix (normative index)

| Requirement | Level | Checklist Field | ↑ Core | Finding | Roadmap | Verification (test) |
|---|---|---|---|---|---|---|
| REQ-FE-CORE-1 | MUST | 9 | — | — | (FR-01,02,03,06,13,17) | analysis |
| REQ-FE-CORE-2a | MUST | 5,1 | — | — | (FR-02,07,08,10,11,12) | analysis |
| REQ-FE-CORE-2b | MUST | 5,1 | — | — | (FR-13) | analysis |
| REQ-FE-CORE-3 | MUST | 11 | — | — | (FR-04,18) | analysis |
| REQ-FE-CORE-4 | MUST | 10 | — | — | (FR-09) | analysis |
| REQ-FE-CORE-5 | MUST | 5,Comp | — | — | (FR-14) | analysis |
| REQ-FE-CORE-6 | SHOULD | 8,9,11,12 | — | — | (FR-05,15,16,17) | analysis |
| REQ-FE-CLIENT-1 | MUST | 9 | CORE-1 | FE-T-01 | FR-01 | apiUtils.test.js (timeout→TimeoutError) |
| REQ-FE-CLIENT-2 | MUST | 9,5 | CORE-1,2a | FE-T-02 | FR-02 | statisticsApi.test.js (typed status) |
| REQ-FE-CLIENT-3 | MUST | 9 | CORE-1 | FE-T-03 | FR-03 | DatasetCard.test.js (axios timeout) |
| REQ-FE-CLIENT-4 | MUST | 10 | CORE-4 | FE-T-04 | FR-09 | DatasetCard.test.js (Idempotency-Key) |
| REQ-FE-CLIENT-5 | SHOULD | 1,5,9 | CORE-2b | FE-T-05 | FR-13 | LandingPage.test.js (no liberal accept) |
| REQ-FE-CLIENT-6 | SHOULD | 5 | CORE-2a | FE-T-06 | FR-10 | apiUtils.test.js (typed reject) |
| REQ-FE-CLIENT-7 | SHOULD | 5,Comp | CORE-5 | FE-T-07 | FR-14 | apiUtils.test.js (CSRF fail-closed) |
| REQ-FE-CLIENT-8 | SHOULD | 9,11 | CORE-6 | FE-T-08 | FR-15 | apiUtils.test.js (retry 503 not 400) |
| REQ-FE-EB-1 | MUST | 11 | CORE-3 | FE-EB-01 | FR-04 | ErrorBoundary.test.js (fallback) |
| REQ-FE-EB-2 | SHOULD | 11 | CORE-3 | FE-EB-02 | FR-18 | ErrorBoundary.test.js (sibling survives) |
| REQ-FE-POLL-1 | MUST | 8,12 | CORE-6 | FE-P-01 | FR-05 | DatasetCard.test.js (no stacking) |
| REQ-FE-POLL-2 | MUST | 8 | CORE-1 | FE-P-02 | FR-06 | DatasetCard.test.js (abort signal on unmount) |
| REQ-FE-POLL-3 | SHOULD | 11,9 | CORE-6 | FE-P-03 | FR-16 | PublicStatsDashboard.test.js (backoff) |
| REQ-FE-POLL-4 | SHOULD | 9,8 | CORE-1,6 | FE-P-04 | FR-17 | PublicStatsDashboard.test.js (abort signal) |
| REQ-FE-DEG-1 | MUST | 1,5 | CORE-2a | FE-D-01 | FR-07 | UserManagement.test.js (422 field msg) |
| REQ-FE-DEG-2 | MUST | 1,5 | CORE-2a | FE-D-02 | FR-08 | DatasetForm.test.js (422 field msg) |
| REQ-FE-DEG-3 | SHOULD | 12,5 | CORE-2a,6 | FE-D-03 | FR-12 | apiUtils.test.js (429 throttle class) |
| REQ-FE-DEG-4 | SHOULD | 1,5 | CORE-2a | FE-D-04 | FR-11 | apiUtils.test.js (flatten 422) |

Coverage: every leaf requirement traces to exactly one confirmed finding and one
roadmap item; every confirmed finding (18) has a leaf requirement. Counting **leaf
requirements/findings**: MUST-class 9 (REQ-FE-CLIENT-1..4, -EB-1, -POLL-1..2,
-DEG-1..2); SHOULD-class 9. (The seven §3.1 CORE roll-ups — six MUST, one SHOULD —
are verified by analysis through these leaves and are not separately counted.)

---

## 5. Examples (informative)

**Canonical seam sketch (target, not yet built).** The shape REQ-FE-CLIENT-1/-6/-8
generalise — one place owns timeout, abort, typed error, and bounded retry:

```js
// target: apiUtils.fetchWithTokenExpiration, deepened
const controller = new AbortController();
const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
try {
  const res = await fetch(url, { ...options, signal: controller.signal });
  if (!res.ok) throw await parseErrorResponse(res); // typed {status, message, class, retryAfter}
  return res;
} finally {
  clearTimeout(timer); // always runs — the promise always settles
}
```

**EARS forms used in §3.** State-driven ("While … the frontend SHALL …" —
REQ-FE-CLIENT-1), event-driven ("When … the frontend SHALL …" — REQ-FE-DEG-1),
unwanted-behaviour ("If … then the frontend SHALL …" — REQ-FE-CLIENT-7),
ubiquitous ("The frontend SHALL …" — REQ-FE-EB-1).

---

## Appendix A — Per-boundary resilience blueprints (as-audited 2026-06-26)

Each boundary below carries a filled blueprint and a rubric verdict
(`reference/rubric.md`, 0–2 per dimension, max 24; **malformed** if total < 16 or
any starred dimension = 0). Starred dimensions are 1, 3, 4, 5, 7. Findings are
summarised; full per-finding detail (defect, minimal fix, RED test) lives in the
roadmap.

### A.1 Transport / data layer — rubric 6/24 (malformed: dims 4, 5, 7 = 0)

```yaml
component: frontend transport (apiUtils.apiRequest + fetchWithTokenExpiration;
           statisticsApi.publicStatsApi; DatasetCard axios; Login fetch; LandingPage fetch)
trust_boundaries:
  - source: peer-service (FastAPI backend over HTTP)
    validation: none at the seam — JSON consumed raw via res.json()/res.data; status
      checked only as the res.ok boolean (and not at all in LandingPage.js:46-49)
    on_invalid: inconsistent — statisticsApi throws a stringly-typed Error discarding
      body/type; LandingPage swallows; parseErrorResponse exists but is DEAD (0 call sites)
contracts:
  preconditions: [apiRequest requires a non-null access token (apiUtils.js:176-180)]
  postconditions: [SHOULD resolve to a typed result OR reject with a typed status-bearing
    error — NOT honoured today; callers get a bare Response or a generic Error]
  invariants: [every caller's loading-flag reset must run — VIOLATED: a hung fetch never
    settles, so the reset never runs]
error_model:
  expected_errors: [network failure, timeout, 4xx (esp. 401/403/429), 5xx]
  failure_stance: mixed — statisticsApi fail-fast but lossy; LandingPage fail-soft but SILENT;
    no 429-vs-5xx-vs-4xx distinction anywhere
  security_failure: PARTIAL fail-closed — token-absent throws (good, apiUtils.js:176-180),
    but CSRF-token failure is swallowed and the mutating request proceeds (apiUtils.js:194-197)
resources:
  acquired: [outbound HTTP request — NO release/abort path; no AbortController in src/]
  bounds: {retries: 1 post-401 only (NOT for 5xx/timeout), result_set: server-paginated}
  shared_mutable_state: token/csrfToken in localStorage (read per-call)
remote_calls:
  - dependency: backend API (all idioms)
    timeout: {connect: NONE, request: NONE}
    retry: {max: 1 (401 only), backoff: none, jitter: none, retriable_errors: [401]}
    idempotency: n/a-readonly for GETs; MISSING for POST /validate (DatasetCard.js:177-185)
    breaker: none
    bulkhead: none (SWR + axios + fetch share the browser pool)
    fallback: LandingPage stale-retain (acceptable, but masks the error)
overload:
  shed: n/a (client); 429/Retry-After NOT honoured
  degradation: LandingPage → last-known stats; DatasetCard → honest 'unknown'
  backpressure: none
observability:
  sli: [none — only scattered console.error/console.log]
  key_metrics: [none — no retry rate, breaker state, latency]
  traces: no correlation id propagated
verification:
  fault_injection_tests: [PARTIAL — LandingPage has a never-resolving-fetch skeleton test;
    NO hung-backend/timeout test for apiRequest, statisticsApi, Login, DatasetCard]
  idempotency_test: none for POST /validate
```
Findings: FE-T-01..08 (4 MUST, 4 SHOULD). Starred zeros: dim 4 (resource bounds —
un-abortable request), dim 5 (timeouts — none), dim 7 (idempotency — POST /validate).
**Verdict: malformed.**

### A.2 Whole-app render containment — rubric n/a (not a data/IO boundary)

```yaml
component: whole-app render tree (index.js root; App.js Routes)
trust_boundaries:
  - source: own render (malformed API payload reaching JSX, e.g. .map over null,
    undefined deref, useAuth() throwing outside its provider — AuthContext.js)
    validation: none — no error boundary anywhere (grep: zero componentDidCatch /
      getDerivedStateFromError / ErrorBoundary / class-extends-Component across src/)
    on_invalid: React 18 createRoot unmounts the WHOLE tree → blank page, no recovery
error_model:
  failure_stance: data-failures handled well (three-state loading/error/empty, credited);
    render-time throws UNCONTAINED → whole-app loss
  blast_radius: whole app (header, nav, every route incl. /login)
resources:
  bounds: {error_boundaries: 0}
lifecycle:
  crash_only: n/a (browser); recovery today = manual full-page reload
observability:
  key_metrics: [none — componentDidCatch reporting absent]
verification:
  fault_injection_tests: [none — no throwing-child render test]
```
Findings: FE-EB-01 (MUST — no top-level boundary), FE-EB-02 (SHOULD — no
route/widget bulkhead). The full 12-dimension rubric does not apply cleanly to a
render-containment (non-IO) boundary; the dominant gap is checklist Field 11 /
rubric dim 8 (Isolation, **unstarred**) scoring 0 — no render-fault containment.
The malformed verdict therefore rests on the unmet MUST-class finding, **not** on a
starred-zero (dim 8 is not a starred dimension).
**Verdict: malformed (FE-EB-01, a MUST-class finding, unmet).**

### A.3 Polling / backpressure — rubric 9/24 (malformed: dim 5 = 0)

```yaml
component: pollers (DatasetCard 3s validation; PublicStatsDashboard 60s refresh)
trust_boundaries:
  - source: peer-service (backend) on a repeating timer
    validation: res.ok checked; payload consumed raw
error_model:
  failure_stance: stale-while-error (credited) BUT pollers keep firing on failure
    and setState-after-unmount on a hung backend
resources:
  acquired: [setInterval timers — RELEASED on resolve/unmount (credited strength);
    in-flight requests — NOT released/aborted]
  bounds: {interval: cleared on terminal/unmount (good);
    in-flight requests: UNBOUNDED on a hung backend (FE-P-01); request timeout: NONE}
remote_calls:
  - dependency: validation-status (3s) / overview+providers+timeline (60s)
    timeout: {request: NONE}
    retry: {cadence: fixed; backoff: none; breaker: none}
    overlap_guard: none (a new tick fires before the previous settles)
overload:
  degradation: stale-while-error warning banner (credited)
  backpressure: none (no in-flight guard, no breaker)
lifecycle:
  shutdown: interval cleared on unmount; in-flight request NOT aborted → setState-after-unmount
verification:
  fault_injection_tests: [none for hung-poll stacking or unmount-abort]
```
Findings: FE-P-01..04 (2 MUST, 2 SHOULD). Strengths credited: interval cleanup on
resolve/unmount; clear-then-set guard; stale-while-error. Starred zero: dim 5
(timeouts). **Verdict: malformed.**

### A.4 Degradation consumption — rubric 11/24 (malformed: total < 16; FE-D-01/-02 MUST unmet)

```yaml
component: error-to-UI consumption (statisticsApi throws; UserManagement / DatasetForm
           banners; parseErrorResponse)
trust_boundaries:
  - source: backend error responses (RFC 7807 problem+json; FastAPI 422 array detail)
    validation: NOT parsed — errorData.detail used as-is; an array detail passed as a
      React child throws "Objects are not valid as a React child"
      (UserManagement.js:281-282; DatasetForm.js:119-120)
    on_invalid: generic banner; status discarded
error_model:
  expected_errors: [422 (array detail), 429 (throttle), 4xx (client), 5xx (server)]
  failure_stance: three-state + stale-while-error (credited) BUT typed-error consumption
    broken: 422 array child throws; no 429/5xx/4xx distinction; Retry-After never read
  typed_error_seam: parseErrorResponse exists but DEAD and itself returns the array unchanged
overload:
  shed: n/a; 429 + Retry-After discarded
  degradation: stale-while-error banner (credited); honest 'unknown' badge (credited)
observability:
  key_metrics: [none]
verification:
  fault_injection_tests: [none for 422-array rendering or 429 classification]
```
Findings: FE-D-01..04 (2 MUST, 2 SHOULD). Strengths credited: three-state loading
(`UserManagement.js:536-564`), stale-while-error banner, honest `unknown` badge.
**Verdict: malformed (total < 16; FE-D-01/-02 MUST unmet).**

---

## Appendix B — Change log

| Date | Author | Change |
|---|---|---|
| 2026-06-26 | DASS-3622 frontend discovery | Initial spec — 18 confirmed findings (9 MUST, 9 SHOULD, 0 refuted) across 4 boundaries; baseline green at `231c82c`. Reviewed for well-formedness (`craft-the-spec`) and execution-readiness (`refine-the-tasks`); split REQ-FE-CORE-2 into 2a/2b and aligned RED-test obligations. Draft for human approval; no production code changed. |

---

## Appendix C — Refuted / dropped candidates (informative)

The adversarial verification pass refuted **0** of the 18 candidates; all were
confirmed. Two candidates raised during recon were resolved rather than refuted:
- **`LandingPage.js` raw transport** — the orientation flagged it as "confirm or
  drop"; the reviewer confirmed a real raw `fetch` at `LandingPage.js:46-49` (not
  a hook consumption), so it stands as FE-T-05.
- **`DatasetCard` 45 s "safety timeout"** (`DatasetCard.js:140-149`) — confirmed
  to reset React state only; it does **not** abort the in-flight request, so it
  does not satisfy REQ-FE-POLL-2 and is not credited as a timeout.

No requirement in §3 rests on an unconfirmed finding.
