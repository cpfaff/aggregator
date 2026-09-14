---
title: Statistics-Collection Harmonization — Discovery
status: final    # draft | active | final
created: 2026-06-26
updated: 2026-06-26
last_reviewed: 2026-09-14
---

# Statistics-Collection Harmonization — Discovery

> **Status:** read-only discovery. No production code, migrations, or tests were
> changed. Every `path:line` below was grep-verified against the working tree
> described under *Code base* — citations are resolvable, not approximate.
>
> **Date:** 2026-06-26
> **Doc branch:** `statistics-harmonization-spec` (isolated git worktree under
> `.worktrees/statistics-harmonization`).
> **Code base specced:** the `DASS-3622-resilience-hardening` tip (`c8072a7`),
> *not* `master`. **Rationale (a vetoed assumption):** the goal proposed branching
> off `master`, but `master` is 39 commits behind and lacks the resilience-hardened
> form of this subsystem (the functional unique index, `core/utils.utc_now`, the
> typed-error client seam, the dashboard backoff/abort/bulkhead work). The seeds
> reference that hardened state (RH-/REQ- tags), and the harmonization is meaningful
> only against the subsystem **as it actually exists**. The worktree freezes a
> stable snapshot so citations stay resolvable while a parallel session edits the
> shared tree. Doc-only regardless.
>
> **Citation convention:** `path:line` relative to repo root; an anchor in «guillemets»
> is a verbatim substring present on that line.

---

## 0. Purpose & method

The statistics subsystem collects a daily **append-only** snapshot of each
archive's biological-unit count and renders counts, as-of/growth timelines, and
quality metrics through a public landing page and an authenticated admin
dashboard. The append-only core is sound (§1). What has drifted is the
*language and arithmetic around it*: there is no single "when was this
**collected**" concept, the same computations are re-implemented several times
(in two cases a canonical helper already exists but has **zero callers**), and
the frontend re-derives formatting and error handling per call site.

This document catalogues every semantic inconsistency, duplication, and dead
path. Each finding carries a **family**, a **severity**, **verified locations**,
the **evidence**, a **proposed resolution**, and — where the design is genuinely
open — a pointer to §4 (not silently decided). §5 seeds the PRD traceability.

**Discovery method:** the backend spine was read first-hand; a 6-agent read-only
sweep catalogued frontend drift, the API/endpoint contract, and additional
backend issues; then **every** citation (first-hand and agent-reported) was
re-grepped against the frozen worktree to pin true line numbers. Two seed
framings were found partly stale and are corrected in place (F-G, and the
"3×" K/M count is actually higher — F-H).

---

## 1. What is already solid (credit — preserve, do not "fix")

These are deliberate, tested strengths. Harmonization must **preserve** them.

- **Append-only model with an authoritative one-per-archive-per-day guard.**
  `ArchiveSnapshotModel` is a true append-only table
  (`backend/app/models/archive_snapshot.py:22` «TRUE append-only»). A **functional
  unique index** on `(archive_id, date(recorded_at))` is declared on the model
  (`archive_snapshot.py:57-70`, «uq_snapshot_archive_day» :67, «unique=True» :70)
  and created by migration `c4f1a2b9d7e3_add_unique_snapshot_per_archive_day.py:53`
  («CREATE UNIQUE INDEX uq_snapshot_archive_day»), which **de-duplicates legacy
  rows before building the index** (keep latest per archive/day, tie-broken by
  highest id — `c4f1a2b9d7e3:34-46`). The code, model, and migration agree.
- **Layered idempotency (RH-06).** Cheap app-level same-day short-circuit
  (`backend/app/tasks/snapshot_tasks.py:360-367`) plus the authoritative DB index
  with `IntegrityError → already_recorded` fallback on the single insert
  (`snapshot_tasks.py:411-424`) and a per-row retry on the batch commit
  (`snapshot_tasks.py:576-607`).
- **Byte-budget download bound (RH-04)** via an early `Content-Length` check and
  an authoritative running counter (`snapshot_tasks.py:179-208`), and **fail-fast
  on partial ZIPs (RH-10)** — any unparseable entry rejects the whole snapshot
  (`snapshot_tasks.py:228-248`, «ZIP entries failed to parse» :247).
- **Bounded SQL aggregates for the public surface (RH-03).** One shared
  `_SUCCESS_FILTER` predicate (`backend/app/repositories/snapshot_repository.py:71-75`)
  reused by both quality and success-rate aggregates so they never drift
  (`snapshot_repository.py:77-134`); no JSON-bearing rows are materialized.
- **`latest_total_units` is correct.** The management tool's total mirrors the
  authoritative latest-per-archive + `isLatest` restriction and uses
  `coalesce(sum, 0)` to avoid the append-only SUM-inflation trap it documents
  (`backend/app/utils/refresh_statistics.py:22-50`). (Its *duplication* is F-C; its
  *correctness* is sound.)
- **Frontend resilience seam.** `parseErrorResponse` is a well-built typed-error
  classifier (`frontend/src/utils/apiUtils.js:333-374`), `fetchWithTimeout` bounds
  every call and composes a caller abort signal (`apiUtils.js:29-58`), and
  `apiRequest` does bounded jittered retriable-only retry on idempotent calls and
  fails closed on a missing CSRF token. `PublicStatsDashboard` adds consecutive-
  failure backoff + an in-flight overlap guard + a per-batch abort, and
  `ProviderDetail` wraps each card in an `ErrorBoundary` bulkhead
  (`frontend/src/components/providers/ProviderDetail.js:886,909`).
- **Clean removal of the old `statistics` table/model** (migration
  `a1b2c3d4e5f6` drops it; no orphan imports remain).

The flaws below sit **next to** these strengths — they are naming/arithmetic
drift and dead surface area, not failures of the collection core.

---

## 2. Findings catalogue

### F-A — Two distinct "timeline" notions; no single *collected-at* concept · timeline-naming · **high**

Two semantically different timelines, keyed on two different timestamps, share no
vocabulary:

1. **As-of (snapshot) timelines** — "units **as of** date D" — forward-fill over
   `archive_snapshots.recorded_at` (the *collection/observation* time):
   `SnapshotService.get_biological_units_timeline`
   (`backend/app/services/snapshot_service.py:112-131`) →
   `repo.get_unit_count_for_date` (`backend/app/repositories/snapshot_repository.py:326-358`);
   dates come from `get_snapshot_dates`, grouped on `func.date(...recorded_at)`
   (`snapshot_repository.py:295-324`).
2. **Growth (creation) timelines** — "entities **created** by date D" — cumulative
   over `model.created_at` (row-insertion time, unrelated to snapshot collection):
   `get_growth_metrics` (`snapshot_service.py:412-451`) and
   `get_provider_datasets_timeline` (`snapshot_service.py:163-180`) →
   `repo.get_entity_timeline` (`snapshot_repository.py:364-403`), where
   `date_col = model.created_at` (`snapshot_repository.py:378`);
   `get_validation_timeline` likewise keys on `created_at`
   (`snapshot_repository.py:405-426`).

The model docstring even calls `recorded_at` "When this snapshot was taken"
(`archive_snapshot.py:28`) — an observation time — while the growth path silently
means creation time. Nothing names the unifying concept, so the two are easy to
conflate, and the API emits both (F-L).

**Proposed resolution:** adopt ONE canonical term for the collection/observation
timestamp and one explicit term for the entity-creation timeline; document both in
the glossary; keep the two timeline kinds explicitly distinct in naming.
**Open: §4-Q1** (whether growth timelines should adopt as-of semantics).

### F-B — Conflicting "now" idioms beside an unused canonical helper · now-idiom · **high**

A canonical naive-UTC factory already exists — `utc_now()` at
`backend/app/core/utils.py:11-17`, whose docstring states it "replaces the
deprecated datetime.utcnow()" (`core/utils.py:14`) — yet it has **zero callers**
in `backend/app`. Instead the subsystem stamps "now" several incompatible ways:

| Idiom | Location | Kind |
|---|---|---|
| `_utc_now()` = `datetime.now(UTC).replace(tzinfo=None)` | `backend/app/models/base.py:14-16`; used by `created_at`/`updated_at` at `base.py:22-23` | **byte-identical duplicate** of `core/utils.utc_now` |
| `default=datetime.utcnow` | `backend/app/models/archive_snapshot.py:38` | naive UTC, deprecated callable |
| `datetime.now(UTC)` (aware) | `backend/app/services/snapshot_service.py:45` | **aware** UTC, returned as `OverviewStats.last_updated` |
| `datetime.now()` (naive **local**) | `backend/app/utils/refresh_statistics.py:127` | naive local wall-clock |

So `recorded_at` and the `TimestampMixin` columns are both stored naive but seeded
by *two* different helpers, the service returns an *aware* datetime on the same
API surface that elsewhere serializes naive timestamps (F-L/#3), and the refresh
tool prints local time.

**Adjacent occurrences (broader codebase, same root cause — see §4 scope):** bare
`datetime.utcnow` at `backend/app/models/failed_task.py:47` and
`backend/app/tasks/validator_tasks.py:127,138,153,191`; naive-local
`datetime.now()` at `backend/app/utils/manage_tasks.py:61`; and a DB-side
`func.now()` default at `backend/app/models/validation.py:29` that mixes a third
clock source into rows whose `created_at`/`updated_at` come from `_utc_now()`.

**Proposed resolution:** route every default and every "now" read in the
statistics subsystem through the existing `core/utils.utc_now`; retire the
duplicate `base._utc_now` and the bare `datetime.utcnow`; ban naive-local
`datetime.now()`. **Open: §4-Q2** (naive-UTC vs aware-UTC serialization).

### F-C — "Latest-snapshot-per-archive SUM" re-implemented four times · duplication · **medium**

The "max(`recorded_at`) per `archive_id`, restrict to `isLatest`, `SUM(unit_count)`"
computation exists in four places:

- `_latest_snapshot_subquery` (`snapshot_repository.py:240-263`) feeding
  `get_unit_count` (`snapshot_repository.py:265-289`).
- `get_unit_count_for_date` builds the same `latest_per_archive` subquery inline
  (`snapshot_repository.py:326-358`).
- `latest_total_units` re-derives it in the management tool
  (`refresh_statistics.py:22-50`) — its docstring admits it "Mirror[s] the
  authoritative" repository method.
- The nightly task builds a fourth, unbounded-date `latest_snapshot_subq` for
  HTTP-metadata lookup (`snapshot_tasks.py:479-496`).

**Proposed resolution:** one repository primitive (`latest_snapshot_per_archive`)
that every caller — tool and task included — composes.

### F-D — Null-vs-zero mismatch between the two unit-count aggregates · duplication · **medium**

Two near-identical aggregates disagree on the empty case:
`get_unit_count` returns the raw `SUM`, i.e. **`None`** when no snapshot matches
(`snapshot_repository.py:289` «return result», deliberate so callers tell unknown
from zero — B4); `get_unit_count_for_date` returns **`0`** in the same case
(`snapshot_repository.py:358` «return query.scalar() or 0»). A consolidation (F-C)
must choose the empty-case contract deliberately rather than inherit both.

### F-E — Dead metric fields hardcoded `None`, still in the public schema · dead-path · **medium**

Two schema fields are always `None` yet advertised as live metrics:
`abcd_compliance_rate` (service `snapshot_service.py:72`; schema
`backend/app/schemas/statistics.py:77`; **public** `GET /quality`
`backend/app/api/v1/endpoints/snapshots.py:72`) and `activity_score` (service
`snapshot_service.py:274`; schema `statistics.py:55`; authenticated
`GET /providers/{id}` `snapshots.py:182`). Both carry "No longer tracked" comments.
**Open: §4-Q3** (remove vs mark deprecated — touches the public API).

### F-F — Stale Celery route glob matches no task · dead-path · **low**

`task_routes` routes `"statistics.*"` to `light_tasks`
(`backend/app/core/celery_app.py:39`), reinforced by a stale comment
(`celery_app.py:38` «Statistics tasks go to light_tasks»). No task uses a
`statistics.` namespace — the real tasks are `snapshots.collect_archive_snapshots`
(`snapshot_tasks.py:441`) and `snapshots.collect_single_archive_snapshot`
(`snapshot_tasks.py:321`), both already pinned to `light_tasks` at the decorator.
Dead config from the removed `statistics_tasks` module. **Resolution:** delete the
comment + route.

### F-G — Frontend: LandingPage bypasses the shared client (seed framing corrected) · frontend-fetch · **medium**

> **Seed correction:** the goal cited a "raw fetch" at `LandingPage.js:46`. The
> actual call is `fetchWithTimeout('/api/v1/statistics/overview')` at
> **`frontend/src/components/public/LandingPage.js:50`** (import at `:5`) — it is
> *not* a bare `window.fetch`; it already uses the resilient timeout + typed-error
> path. The real, narrower drift is:

1. it bypasses `publicStatsApi.getOverview()`, which hits the **identical** endpoint
   (`frontend/src/utils/statisticsApi.js:16`) and already encapsulates the
   ok/parse/json dance;
2. it **hardcodes** the path `/api/v1/statistics/overview`, ignoring `API_BASE`
   composition (environment-fragile, unlike the client);
3. it passes **no abort signal**, unlike `PublicStatsDashboard`'s unmount abort.

**Proposed resolution:** call `publicStatsApi.getOverview({ signal })` with an
effect-scoped `AbortController`; keep the stale-while-error behaviour.

### F-H — Frontend: K/M compact-number ladder copy-pasted; canonical helper unused · duplication · **medium**

> **Seed correction:** "copy-pasted 3×" undercounts. A canonical
> `statsUtils.formatLargeNumber` exists (`frontend/src/utils/statisticsApi.js:259-266`)
> with **zero callers**, while the identical `≥1e6→M / ≥1e3→K` ladder is inlined in
> chart tick formatters at **four** sites — `BarChart.js:241,243` **and** `285,287`
> (twice in one file), `TimeSeriesChart.js:337,339` (with an `integerOnly` precision
> variant), `MultiLineTimeSeriesChart.js:445,447`.

The copies have already **drifted** (TimeSeriesChart varies the decimal count; the
canonical helper does not). **Proposed resolution:** generalise `formatLargeNumber`
(add a `decimals`/`integerOnly` option), relocate it to a neutral
`utils/numberFormat` module, and point all four tick formatters at it.

### F-I — Frontend: ≥5 divergent date/time formatting styles; helpers bypassed · frontend-format · **medium**

12 date-format occurrences across 7 files group into 5 styles, while canonical
helpers in `frontend/src/utils/dateUtils.js` (`formatRelativeTime` :58,
`formatAbsoluteDateTime` :77) are bypassed by most call sites:
inline locale-default `toLocaleDateString(undefined, …)`
(`frontend/src/components/providers/ProviderCard.js:138`,
`frontend/src/components/datasets/DatasetCard.js:383`); inline **pinned** `'en-US'`
(`DatasetCard.js:798`, `frontend/src/components/statistics/ProviderStatistics.js:220`);
bare `toLocaleDateString()` (`frontend/src/components/statistics/PublicStatsDashboard.js:128`,
`statisticsApi.js:223,238`); and `toLocaleString(undefined, {…timeZoneName})`
(`frontend/src/components/datasets/ValidationResultsModal.js:274`). The `undefined`
-vs-`'en-US'` split makes some dates locale-variable (relevant given the de_DE
default thousands-separator gotcha). **Resolution:** route human-facing dates
through `dateUtils`; pick one locale policy for chart-axis dates.

### F-J — Frontend: percent-change math dead in two places · dead-path · **low**

> **Seed correction:** the goal framed this as live "StatCard vs statsUtils"
> duplication; both copies are **dead**. `StatCard`'s change badge
> (`frontend/src/components/ui/StatCard.js:120` «Math.abs(change).toFixed(1)»,
> `calculateChange` :19) reads a `previousValue` prop that **no consumer passes**
> (`previousValue` only at `StatCard.js:11,20,23`), so the whole block is
> unreachable. `statsUtils.calculatePercentageChange`
> (`statisticsApi.js:249-252`) likewise has **zero callers**.

**Resolution:** decide wire-or-delete; if wired, route the math through the single
`calculatePercentageChange` helper. Separately, `toFixed(1)` percent formatting is
hand-rolled at ~15 sites (e.g. `PieChart.js:116`, `ProviderDetail.js:591`,
`ValidationResultsModal.js:380`) with no shared `formatPercent` — a low-priority
DRY target.

### F-K — Frontend: two API-client error shapes; consumers discard the typed one · error-shape · **medium**

`publicStatsApi` throws the **typed** `parseErrorResponse` object
`{ message, status, class, retryAfter, fieldErrors }`
(`statisticsApi.js:18,35,47` → `apiUtils.js:333,345`), whereas `authStatsApi`
throws a **generic** `new Error(\`…: ${status}\`)` at eight sites
(`statisticsApi.js:65,79,93,117,143,156,181,206`). Worse, every consumer reads only
`err.message` and discards `class`/`status`/`retryAfter`
(`PublicStatsDashboard.js:162`, `AdminDashboard.js:109`, `ProviderStatistics.js:38`),
so the throttle/server/client distinction the client computed is thrown away at the UI.

> **Nuance:** `authStatsApi` calls flow through `apiRequest → fetchWithTokenExpiration`,
> which already rejects non-ok with the typed object (`apiUtils.js:233`), so the
> generic `if (!response.ok)` blocks are largely **dead guards** that only *downgrade*
> the contract on paper.

**Resolution:** delete the redundant generic `throw new Error` guards in
`authStatsApi` so one typed error shape reaches consumers, then have consumers
branch on `err.class`. **Open:** reconcile with the resilience spec (FR-02/FR-10).

### F-L — Contract: three timeline payload shapes, one collides on `data_points` · contract-drift · **high**

One statistics surface ships three structurally different timeline payloads:

1. **`GrowthMetrics`** — sibling arrays `datasets_timeline`/`providers_timeline`/
   `validation_timeline`, each `list[TimeSeriesPoint]` — `GET /timeline`
   (`snapshots.py:92` `response_model=GrowthMetrics`; schema
   `statistics.py:83-90`, `datasets_timeline` :86).
2. **`TimeSeriesResponse`** — series under a single **`data_points`** key with
   metadata — three endpoints (`snapshots.py:227,261,297`; schema
   `statistics.py:22-30`, `data_points` :29).
3. **Untyped wide rows** — `GET /multi-provider-biological-units`
   (`snapshots.py:332` `response_model=dict[str, Any]`) returns
   `get_multi_provider_timeline` (`snapshot_service.py:182-248`) whose **`data_points`**
   (`snapshot_service.py:244`) are **provider-keyed dicts**
   `{date, "<provider>": float, …}` (`:228,232`) — *not* `TimeSeriesPoint`. Same key
   name, incompatible element shape, and `dict[str, Any]` documents none of it in OpenAPI.

The frontend consumes both `datasets_timeline` (`PublicStatsDashboard.js:127`,
`AdminDashboard.js:120`) and `data_points` (`AdminDashboard.js:146,172`,
`ProviderStatistics.js:54,84`), funneling both through one formatter
`formatTimeSeriesForChart` (`statisticsApi.js:221`) that silently assumes a common
element shape. (`providers_timeline`/`validation_timeline` have **no** frontend
consumer.) **Resolution:** one timeline envelope, or rename the wide-row key and
give the multi-provider endpoint a real `response_model`. **Open:** do the two
backend shapes agree at the *element* level, or is the formatter mis-mapping one?

### F-M — Same-day idempotency check is order-undefined · contract-drift · **low**

The single-archive same-day existence check queries with **no `order_by`** and
takes `.first()` (`snapshot_tasks.py:360-367`, the `.first()` at `:366`), so under
multiple same-day rows the "existing" row is DB-arbitrary — while the
change-detection query immediately below orders `recorded_at.desc()`
(`snapshot_tasks.py:376-382`, `.first()` at `:381`) and the dedup migration's
keep-rule is "highest `recorded_at`, tie-broken by highest id"
(`c4f1a2b9d7e3:37,40-46`). Post-unique-index at most one same-day row can exist, so
this is moot going forward and harmless for correctness; it is an internal
inconsistency worth aligning (`order_by(recorded_at.desc(), id.desc())`).

---

## 3. Test baseline

The collection subsystem's tests exist but **could not be executed in the
discovery-sweep environment**; this is an environment limitation, not a red
suite:

| Suite | Seam | Result in sweep env |
|---|---|---|
| Frontend stats (`components/statistics/__tests__/*`, `ui/__tests__/StatCard.test.js`, `public/__tests__/LandingPage.test.js`) | jest | 0 collected — `npx jest` bypassed the project Babel/JSX transform ("experimental syntax 'jsx' isn't enabled"). Needs the project runner (`make`/`npm test`). |
| `backend/tests/test_refresh_statistics.py`, `test_snapshot_endpoints.py` | pytest | 0 collected — `ModuleNotFoundError: No module named 'abcd_validator'` at import (`app.services → validation_service → validator_tasks → validator/service.py:13`). |
| `backend/tests/services/test_snapshot_service.py` | pytest + testcontainers | Not reached — same import error; also requires Docker-in-Docker (`make test` from host, per CLAUDE.md). |

**Baseline to record before implementation:** run `make test` on a provisioned host
(Docker available) and capture green counts. The existing suites already encode the
idempotency, byte-budget, and endpoint guarantees credited in §1; the PRD (§5) makes
the reliability obligations testable against these seams.

---

## 4. Open questions for the PRD (not decided here)

- **Q1 — Should growth timelines adopt as-of/snapshot semantics?** Growth keys on
  `created_at`, unit timelines on `recorded_at`. Unify under one *collected-at*
  concept, or keep two explicitly-named timeline kinds? (F-A) — genuinely open.
- **Q2 — Serialization convention:** naive-UTC everywhere vs aware-UTC everywhere
  for API timestamps (F-B/F-K-adjacent/F-L#3). The smaller change matches the
  documented "`_utc_now` strips tzinfo for DB compatibility" convention.
- **Q3 — Dead fields:** remove `abcd_compliance_rate`/`activity_score` from the
  schema vs mark them deprecated/always-null (F-E) — touches the **public API**,
  which this initiative does not change unilaterally.
- **Q4 — Now-idiom scope:** confine the canonical-`utc_now` cleanup to the
  statistics subsystem, or extend to the adjacent `failed_task`/`validator_tasks`/
  `validation`/`manage_tasks` occurrences listed in F-B? (Recommended: spec the
  statistics scope; note the rest as a follow-up.)
- **Q5 — `data_points` element shape:** do `GrowthMetrics` and `TimeSeriesResponse`
  guarantee identical `{date, value, extra_data}` elements, or is
  `formatTimeSeriesForChart` mis-mapping one? (F-L)

---

## 5. Traceability seed (finding → proposed obligation theme)

| Finding | Severity | Proposed PRD obligation (theme) |
|---|---|---|
| F-A | high | ONE canonical *collected-at* term; two timeline kinds explicitly named |
| F-B | high | Route the subsystem through the existing `core/utils.utc_now`; one serialization convention |
| F-C | medium | ONE latest-snapshot-per-archive primitive; all callers compose it |
| F-D | medium | Explicit empty-case (unknown vs zero) contract for unit-count reads |
| F-E | medium | Resolve dead metric fields (remove or mark deprecated) |
| F-F | low | Remove the stale `statistics.*` Celery route + comment |
| F-G | medium | LandingPage uses `publicStatsApi.getOverview({signal})` — no hardcoded path |
| F-H | medium | ONE compact-number formatter consumed by all charts |
| F-I | medium | ONE date formatter (route through `dateUtils`); one locale policy |
| F-J | low | Wire-or-delete the dead %-change paths; one `formatPercent` |
| F-K | medium | ONE typed client error shape; consumers branch on `err.class` |
| F-L | high | ONE timeline payload contract (or explicitly-named, typed distinct shapes) |
| F-M | low | Deterministic same-day idempotency ordering |
| §1 | — | Nightly-snapshot reliability guarantees (idempotency, uniqueness, byte-budget) made testable |
