---
title: Statistics-Collection Harmonization & Hardening — PRD
status: draft        # draft | final
created: 2026-06-26
updated: 2026-06-26
---

# Statistics-Collection Harmonization & Hardening

> Feature-level spec built on [`brief.md`](./brief.md) and the evidence in
> [`discovery.md`](./discovery.md). Requirements are **normative** and traceable up
> to a discovery finding (`F-A`…`F-M`, or §1) and down to a test seam. This PRD
> *specifies* the target state for a separate, test-first implementation; it does
> **not** change production code, the public API, or the DB schema.

## Problem Statement

The Aggregator statistics subsystem has a sound collection core (append-only daily
snapshots, a functional unique index, idempotent nightly collection, a
byte-budgeted fail-fast parser) but the semantics layered on top have drifted.
Engineers who read or change a statistics path face: two unrelated "timeline"
notions with no shared name (`F-A`), four "now" idioms beside an unused canonical
helper (`F-B`), the same total computed four ways (`F-C`) with a null-vs-zero
disagreement (`F-D`), always-null fields and a dead task route shipped as live
(`F-E`, `F-F`), three incompatible timeline payload shapes (`F-L`), and a frontend
that re-derives number/date/error handling per call site (`F-G`…`F-K`). The cost is
silent drift, dead surface read as live, and timeline payloads parsed three ways
through one formatter that assumes they agree.

## Solution

Converge the *language and arithmetic* around the collection core onto a single
canonical form for each concept, remove dead surface area, and pin the proven
nightly-collection guarantees as named tests so they cannot regress during the
consolidation — while leaving collection behaviour, the public API contract, and
the DB schema unchanged except where an explicit decision (Q3/Q5) applies.

## Ubiquitous Language

The canonical terms below are settled for this initiative and used verbatim
throughout. They sharpen the overloaded word "timeline" (`F-A`); they introduce no
new identifier that would require a DB rename.

| Term | Definition |
|---|---|
| **Snapshot** | An append-only, point-in-time record of one archive's `unit_count`, stamped at its `recorded_at` instant; at most one per archive per calendar day. |
| **`recorded_at`** | The canonical **collected-at** timestamp — the instant a snapshot's count was recorded (collected). The existing column name is retained; "collected-at" is its prose gloss, not a new field. |
| **Collection timeline** | THE canonical term for the as-of series of biological-unit counts, forward-filled over `recorded_at`. Retired synonyms: "as-of timeline", "biological-units timeline", "snapshot timeline". |
| **Registration timeline** | The cumulative series of entity (dataset / provider / validation) counts keyed on `created_at` (entity registration). Distinct from a collection timeline; retired loose synonym: "growth timeline" used as if interchangeable. |
| **`created_at`** | Entity registration timestamp (row insertion). Drives the registration timeline only; never a collection timestamp. |
| **Canonical now** | The single naive-UTC current-time helper `utc_now()` already present in the codebase, documented as the replacement for the deprecated `datetime.utcnow()`. |

## User Stories

1. **As a** statistics maintainer, **I want** one canonical name and timestamp per
   concept, **so that** I change a definition once instead of reconciling 2–4
   drifted copies. *(Acceptance: REQ-SH-LANG-\*, REQ-SH-NOW-\*, REQ-SH-AGG-\*.)*
2. **As a** statistics maintainer, **I want** dead fields, routes, and unreachable
   UI code removed, **so that** what ships reads as live. *(Acceptance:
   REQ-SH-DEAD-\*.)*
3. **As an** API consumer, **I want** one coherent timeline payload and one error
   shape, **so that** I parse responses one way. *(Acceptance: REQ-SH-TL-\*,
   REQ-SH-ERR-\*.)*
4. **As a** frontend maintainer, **I want** shared formatting and fetch helpers,
   **so that** number/date/error rendering does not drift per call site.
   *(Acceptance: REQ-SH-FE-\*, REQ-SH-ERR-\*.)*
5. **As an** operator, **I want** the nightly-collection guarantees covered by named
   tests, **so that** the consolidation cannot silently regress idempotency,
   uniqueness, or the byte budget. *(Acceptance: REQ-SH-REL-\*.)*

## Requirements (normative)

The keywords **MUST**, **MUST NOT**, **SHALL**, **SHALL NOT**, **SHOULD**, and
**MAY** are to be interpreted as described in BCP 14 (RFC 2119 / RFC 8174). Each
requirement states one testable obligation. `↑` cites the originating discovery
finding; `↓` names the lowest existing test seam that verifies it.

### Terminology (F-A)

- **REQ-SH-LANG-1** — The statistics-collection subsystem and its documentation
  SHALL name the as-of unit-count series the "collection timeline". `↑F-A ↓inspection (glossary grep)`
- **REQ-SH-LANG-2** — The statistics-collection subsystem and its documentation
  SHALL name the cumulative entity-count series the "registration timeline". `↑F-A ↓inspection (glossary grep)`
- **REQ-SH-LANG-3** — A symbol or API field that denotes a timeline SHOULD indicate
  which kind it is (collection or registration). `↑F-A ↓inspection`

### Single time idiom (F-B)

- **REQ-SH-NOW-1** — Every current-time value in the statistics-collection
  subsystem SHALL be obtained from the canonical now helper. `↑F-B ↓model unit test`
- **REQ-SH-NOW-2** — The statistics-collection subsystem SHALL NOT call
  `datetime.utcnow()`, `datetime.now()`, or `func.now()` directly. `↑F-B ↓static grep test`
- **REQ-SH-NOW-3** — The statistics-collection subsystem SHALL NOT define a now
  helper that duplicates the canonical one. `↑F-B ↓static grep test`
- **REQ-SH-NOW-4** — WHERE a statistics API response contains datetime fields, the
  system SHALL serialize every such field of that response under one timezone
  convention (all offset-bearing or all offset-less). `↑F-B,F-L ↓statistics API contract test`

### DRY aggregate consolidation (F-C, F-D)

- **REQ-SH-AGG-1** — The "latest-snapshot-per-archive" selection SHALL be defined in
  exactly one shared primitive. `↑F-C ↓snapshot repository unit test`
- **REQ-SH-AGG-2** — For identical snapshot data at any scope (dataset, provider,
  system), the point total and the latest-date collection-timeline total SHALL
  return equal values. `↑F-C ↓snapshot repository unit test`
- **REQ-SH-AGG-3** — Each unit-count read SHALL specify whether its empty result
  denotes "unknown" or "zero". `↑F-D ↓snapshot repository unit test`

### Dead-surface removal (F-E, F-F, F-J)

- **REQ-SH-DEAD-1** — The Celery routing configuration SHALL NOT contain a route
  pattern that matches no registered task. `↑F-F ↓Celery config unit test`
- **REQ-SH-DEAD-2** — The statistics API SHALL NOT present an unconditionally-null
  field as a live metric. `↑F-E ↓statistics API contract test`
- **REQ-SH-DEAD-3** — The statistics frontend SHALL NOT ship an unreachable
  percent-change computation. `↑F-J ↓stats-component RTL test`

> *Resolution latitude (informative):* REQ-SH-DEAD-2 is satisfied by removing the
> field or marking its schema description deprecated (direction gated by Q3);
> REQ-SH-DEAD-3 by removing the indicator or wiring a real previous value (direction
> gated by Q-FE). The obligation (no dead surface presented as live) holds either way.

### One timeline contract (F-L)

- **REQ-SH-TL-1** — Every statistics timeline endpoint SHALL declare a typed
  response model other than `dict[str, Any]`. `↑F-L ↓OpenAPI schema test`
- **REQ-SH-TL-2** — Across all statistics endpoints, a response key named
  `data_points` SHALL carry elements of one declared element type. `↑F-L ↓statistics API contract test`
- **REQ-SH-TL-3** — The statistics frontend SHALL read each timeline series through
  one canonical shape rather than branching on per-endpoint keys. `↑F-L ↓stats-component RTL test`

### Frontend DRY (F-G, F-H, F-I)

- **REQ-SH-FE-1** — The public landing page SHALL fetch overview statistics through
  the shared public statistics client, not a hardcoded endpoint path. `↑F-G ↓LandingPage RTL test`
- **REQ-SH-FE-2** — WHEN a landing-page statistics request is in flight and the
  component unmounts, the system SHALL abort that request. `↑F-G ↓LandingPage RTL unmount test`
- **REQ-SH-FE-3** — Compact-number (K/M) axis formatting SHALL be produced by one
  shared helper that every chart tick formatter reuses. `↑F-H ↓formatter unit test + static grep test`
- **REQ-SH-FE-4** — Human-facing dates in the statistics UI SHALL be rendered
  through one shared date helper. `↑F-I ↓formatter unit test`
- **REQ-SH-FE-5** — The shared statistics date helper SHOULD pin an explicit locale
  rather than rely on the runtime default. `↑F-I ↓formatter unit test`

### One error shape (F-K)

- **REQ-SH-ERR-1** — Both the public and the authenticated statistics clients SHALL
  reject a failed request with the same typed error shape (`message`, `status`,
  `class`, `retryAfter`). `↑F-K ↓statistics client unit test`
- **REQ-SH-ERR-2** — WHEN a statistics request fails with a throttle (429) or
  server (5xx) class, the consuming component SHALL surface a message derived from
  the error's `class`. `↑F-K ↓stats-component RTL test`

### Nightly-collection reliability, locked as tests (§1, F-M)

- **REQ-SH-REL-1** — WHEN snapshot collection runs more than once for the same
  archive on the same calendar day, the system SHALL persist at most one snapshot
  for that archive and day. `↑§1 ↓snapshot task service test`
- **REQ-SH-REL-2** — IF an archive download exceeds the configured byte budget,
  THEN the system SHALL abort that archive's snapshot and persist no partial count.
  `↑§1 ↓snapshot parser unit test`
- **REQ-SH-REL-3** — IF any XML entry in a multi-entry archive fails to parse, THEN
  the system SHALL reject the whole snapshot for that archive. `↑§1 ↓snapshot parser unit test`
- **REQ-SH-REL-4** — IF two workers insert the same archive-and-day snapshot
  concurrently, THEN the system SHALL treat the unique-index conflict as
  already-recorded. `↑§1,F-M ↓snapshot task service test`
- **REQ-SH-REL-5** — IF a duplicate snapshot is rejected during batch collection,
  THEN the system SHALL persist the batch's remaining non-conflicting snapshots.
  `↑§1 ↓snapshot task service test`
- **REQ-SH-REL-6** — The same-day snapshot existence check SHALL select its row
  ordered by `recorded_at` descending, then `id` descending. `↑F-M ↓snapshot task service test`

### Invariants (brief non-goals, enforced)

- **REQ-SH-INV-1** — The harmonization SHALL NOT alter the statistics database
  schema. `↑brief ↓alembic review (no new migration touching statistics tables)`
- **REQ-SH-INV-2** — The harmonization SHALL NOT change a public statistics API
  response shape, except a change authorized under REQ-SH-DEAD-2 or REQ-SH-TL-1/2.
  `↑brief ↓statistics API contract test`
- **REQ-SH-INV-3** — The harmonization SHALL NOT introduce any dependency on the
  data centers versioning their archives. `↑brief ↓design review`

## Implementation Decisions

- **One latest-per-archive primitive.** Promote the repository's
  latest-snapshot-per-archive selection to a single named method; the point total,
  the as-of collection-timeline total, the management-tool total, and the nightly
  task's metadata lookup all compose it (REQ-SH-AGG-1). The four current copies are
  deleted. Rejected: leaving the management tool's copy as an intentional mirror —
  its own docstring already concedes it duplicates the authoritative method, so the
  mirror is debt, not isolation.
- **Canonical now.** The subsystem routes every default and now-read through the
  existing canonical `utc_now()`; the duplicate model-local helper is removed and
  its references repointed (REQ-SH-NOW-1/3). The bare `datetime.utcnow()` /
  naive-local `datetime.now()` call sites in the subsystem are replaced
  (REQ-SH-NOW-2). Serialization consistency (REQ-SH-NOW-4) is satisfied by emitting
  every response datetime under one convention; the specific convention is Q2.
- **Empty-case contract.** Each unit-count read declares whether its empty result is
  "unknown" (None) or "zero", documented at the method and pinned by a test
  (REQ-SH-AGG-3); the consolidation in REQ-SH-AGG-1 preserves the existing
  unknown-vs-zero split deliberately rather than collapsing it.
- **Timeline contract.** The multi-provider endpoint gains a real typed response
  model (REQ-SH-TL-1); the provider-keyed wide-row payload either adopts the shared
  `TimeSeriesPoint` element type or is renamed off the `data_points` key so the key
  denotes one element type everywhere (REQ-SH-TL-2). The exact direction is Q5. The
  frontend reads one normalized shape (REQ-SH-TL-3).
- **Dead surface.** The `statistics.*` Celery route and its stale comment are
  deleted (REQ-SH-DEAD-1, queue assignment already lives on the task decorators);
  the always-null `abcd_compliance_rate` / `activity_score` fields are resolved per
  Q3 (REQ-SH-DEAD-2); the unreachable `previousValue` percent-change path is
  resolved per Q-FE (REQ-SH-DEAD-3).
- **Frontend seams.** The landing page consumes the shared public client with an
  unmount-abort controller (REQ-SH-FE-1/2); the existing-but-unused compact-number
  and percent helpers, plus the date helpers, become the single source each chart /
  card reuses (REQ-SH-FE-3/4); the authenticated client's redundant generic-error
  guards are removed so one typed error shape reaches consumers (REQ-SH-ERR-1),
  which then branch on `class` (REQ-SH-ERR-2).
- **Reliability lock.** The idempotency, byte-budget, fail-fast, and race-fallback
  guarantees gain (or retain) named tests (REQ-SH-REL-1…4); the same-day existence
  check is made order-deterministic (REQ-SH-REL-5).

## Testing Decisions

- **Behaviour through public seams, prefer the highest existing seam.** Backend
  obligations are verified at the **snapshot repository** seam (totals, empty-case,
  latest-per-archive equivalence), the **snapshot task service** seam (idempotency,
  race fallback, ordering — testcontainers/Docker per project convention), the
  **snapshot parser** seam (byte budget, fail-fast ZIP), the **statistics API
  contract / OpenAPI** seam (response models, `data_points` element type, dead
  fields, serialization consistency), and a **Celery config** seam (no orphan
  route). Prior art exists for each (the subsystem already ships idempotency,
  byte-budget, and endpoint tests).
- **Frontend** obligations are verified with React Testing Library at the
  component seam (landing-page client use + unmount abort, error-class messaging,
  one timeline shape) and with unit tests at the shared-helper seam (compact-number,
  date, percent). Tests assert observable behaviour and thrown error shape, not
  implementation detail.
- **Static seams.** REQ-SH-NOW-2/3 and REQ-SH-FE-3 are additionally enforced by a
  grep/lint assertion (no naive-now call, single helper definition, no inline K/M
  ladder) so regressions fail loudly.
- **Baseline first.** The current green counts of the statistics suites are recorded
  via `make test` on a Docker-provisioned host (the discovery sweep could not run
  them — jest transform / missing `abcd_validator` / Docker) **before** the first
  consolidation commit, so a pre-existing failure is never mis-attributed to the
  refactor.

## Out of Scope / Anti-Goals

- Archive versioning at the data centers (fixed external constraint; the daily
  snapshot exists precisely to make in-place growth visible without it).
- Any DB-schema change (REQ-SH-INV-1) and any unilateral public-API shape change
  beyond the Q3/Q5-gated REQ-SH-DEAD-2 / REQ-SH-TL-\* (REQ-SH-INV-2).
- Repo-wide "now"-idiom cleanup outside the statistics subsystem (the
  `failed_task` / `validator_tasks` / `validation` / `manage_tasks` occurrences in
  `discovery.md` F-B are a follow-up — Q4).
- New statistics features, re-architecture of the collection core, or
  re-introducing the removed `abcd_compliance_rate` / `activity_score` metrics.
- Deciding Q1 (whether the registration timeline should adopt collection/as-of
  semantics) — recorded as open; this PRD only names the two kinds distinctly.

## Open Questions

- **Q1 (semantics) — `↑F-A`** — Should the registration timeline be re-expressed in
  collection/as-of semantics, or remain creation-based? Genuinely open; **not
  decided here**. The terminology requirements are neutral to the outcome.
- **Q2 (serialization) — `↑F-B,F-L`** — Naive-UTC vs aware-UTC as the single
  convention for REQ-SH-NOW-4. Recommendation: naive-UTC, matching the documented
  "`utc_now` strips tzinfo for DB compatibility" convention (smaller change).
- **Q3 (dead fields) — `↑F-E`** — Remove `abcd_compliance_rate` / `activity_score`
  vs mark them deprecated/always-null. Touches the public API; gates REQ-SH-DEAD-2.
- **Q4 (now-idiom scope) — `↑F-B`** — Confine the canonical-now cleanup to
  statistics (recommended), or extend to the adjacent subsystems.
- **Q5 (`data_points` element shape) — `↑F-L`** — Do `GrowthMetrics` and
  `TimeSeriesResponse` agree at the element level, or is the shared formatter
  mis-mapping one? Resolution direction for REQ-SH-TL-2 depends on the answer.
- **Q-FE (percent-change) — `↑F-J`** — Remove the dead change indicator vs wire a
  real previous value; gates REQ-SH-DEAD-3.

## Conformance

An implementation is **conformant** with this PRD when:

1. **Every** requirement whose ID is prefixed `REQ-SH-` and stated with **SHALL** /
   **SHALL NOT** / **MUST** / **MUST NOT** is satisfied and has a passing test at the
   seam named in its `↓` trace (or, for the review/static seams, a recorded
   check). Requirements stated with **SHOULD** are satisfied or carry a recorded
   waiver; **MAY** items are optional.
2. **Decision gates are closed before the gated requirement is judged.** REQ-SH-DEAD-2
   (Q3), REQ-SH-TL-2 (Q5), REQ-SH-NOW-4 (Q2), and REQ-SH-DEAD-3 (Q-FE) are evaluated
   only after their open question is answered and recorded; until then they are
   *pending*, not *failing*.
3. **No invariant is violated:** REQ-SH-INV-1…3 hold across the whole change set
   (no statistics-schema migration; no unauthorized public-API shape change; no new
   data-center dependency).
4. **The baseline precedes the change:** the pre-change statistics test baseline is
   recorded before the first consolidation commit (per Testing Decisions).

**Traceability obligation.** Every `REQ-SH-` requirement traces **up** to a
discovery finding (`F-A`…`F-M`) or §1 via its `↑` tag and **down** to a test seam
via its `↓` tag; a requirement without both traces is non-conformant *as a spec*
and MUST be corrected before implementation begins.

**Normative references & version.** This PRD is **v0.1.0** (`status: draft`, see
frontmatter). Normative references: BCP 14 (RFC 2119, RFC 8174), undated. Requirement
IDs are stable under the `REQ-SH-<group>-<n>` scheme; a ratified requirement's ID is
never reused for a different obligation. Term definitions are fixed once in
*Ubiquitous Language* and used identically throughout.
