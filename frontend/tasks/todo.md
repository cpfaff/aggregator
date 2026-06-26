# DASS-3622 Frontend Resilience Hardening — Execution Tracker

Branch: `DASS-3622-resilience-hardening`. Source of truth:
`docs/RESILIENCE_FRONTEND_ROADMAP.md` (work list) + `docs/RESILIENCE_FRONTEND_SPEC.md` (target).

Method per item: write named RED test → observe FAIL for stated reason → minimal fix →
observe GREEN → full suite green (≥73) + `npx eslint src/` exit 0 → ONE atomic conventional commit.

Gate commands (from `frontend/`):
- single: `CI=true npx react-scripts test --watchAll=false <path>`
- full:   `CI=true npm test -- --watchAll=false`
- lint:   `npx eslint src/`
- before commit: `export PATH="$PWD/../backend/.venv/bin:$PATH"`

Baseline (231c82c head be51e5e): 16 suites / 73 tests pass; eslint exit 0. CONFIRMED green at session start.

## MUST block (FR-01..FR-09) — clears the spec's malformed verdict

- [x] FR-01 timeout+AbortController in apiRequest (REQ-FE-CLIENT-1) — apiUtils.test.js [SEAM] ✓ 74 tests
- [x] FR-02 publicStatsApi typed status error (REQ-FE-CLIENT-2) — statisticsApi.test.js ✓ 75 tests
- [x] FR-03 DatasetCard axios timeout (REQ-FE-CLIENT-3) — DatasetCard.test.js ✓ 76 tests
- [x] FR-04 top-level ErrorBoundary (REQ-FE-EB-1) — ErrorBoundary.test.js [NEW FILE] ✓ 77 tests
- [x] FR-05 validation poller overlap guard (REQ-FE-POLL-1) — DatasetCard.test.js ✓ 78 tests
- [x] FR-06 validation poll abort on unmount (REQ-FE-POLL-2) — DatasetCard.test.js ✓ 79 tests
- [x] FR-07 UserManagement 422 per-field message (REQ-FE-DEG-1) — UserManagement.test.js ✓ 80 tests
- [x] FR-08 DatasetForm 422 per-field message (REQ-FE-DEG-2) — DatasetForm.test.js [NEW FILE] ✓ 81 tests
- [x] FR-09 validate POST Idempotency-Key (REQ-FE-CLIENT-4) — DatasetCard.test.js ✓ 82 tests

### >>> CONFORMANCE GATE: after FR-09, report MUST milestone before SHOULD block <<<

## SHOULD block (FR-10..FR-18) — completes the resilient-client seam

- [x] FR-10 revive parseErrorResponse as live seam (REQ-FE-CLIENT-6) — apiUtils.test.js [SEAM] ✓ 83 tests
- [x] FR-11 flatten 422 array in parseErrorResponse (REQ-FE-DEG-4) — apiUtils.test.js ✓ 84 tests
- [x] FR-12 classify status + Retry-After (REQ-FE-DEG-3) — apiUtils.test.js ✓ 85 tests
- [x] FR-13 LandingPage timeout/res.ok/no silent swallow (REQ-FE-CLIENT-5) — LandingPage.test.js ✓ 86 tests (corrected roadmap's tautological waitFor-not to a positive-wait-then-assert)
- [x] FR-14 fail closed on CSRF token failure (REQ-FE-CLIENT-7) — apiUtils.test.js ✓ 87 tests
- [x] FR-15 bounded jittered retriable-only retry (REQ-FE-CLIENT-8) — apiUtils.test.js ✓ 88 tests (also updated FR-01 timeout test to advance through the retry budget)
- [x] FR-16 dashboard auto-refresh backoff (REQ-FE-POLL-3) — PublicStatsDashboard.test.js ✓ 89 tests
- [x] FR-17 dashboard refresh guard+abort (REQ-FE-POLL-4) — PublicStatsDashboard.test.js ✓ 90 tests (fetchWithTimeout now composes a caller signal; publicStatsApi accepts options)
- [x] FR-18 route/widget error boundaries (REQ-FE-EB-2) — ErrorBoundary.test.js ✓ 92 tests (roadmap's sibling-survives test is a tautology vs the FR-04 boundary; kept it as the spec's named conformance check and added a genuine RED test for the new fallback prop)

## Notes / gotchas carried forward
- apiRequest throws synchronously without a token → set `localStorage.token` + future `tokenExpiry` in beforeEach.
- React 18 emits NO unmounted-component warning → assert on AbortSignal, never console.error.
- `toLocaleString()` separator is locale-dependent → assert digits-only, never a hardcoded separator.
- Do NOT push or open MR — human stop-gate precedes any remote action.

## Resume pointer
ALL ITEMS COMPLETE: FR-01..FR-18 landed as atomic commits. Full suite 92 tests green; eslint src/ exit 0.

MILESTONE 1: MUST block FR-01..FR-09 — spec's MUST set satisfied (malformed verdict cleared).
MILESTONE 2: SHOULD block FR-10..FR-18 — resilient-client seam completed; degradation items cleared.

NEXT: human stop-gate before any remote action (no push/MR performed). Awaiting review.
