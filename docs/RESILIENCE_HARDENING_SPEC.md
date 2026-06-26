# GFBio Aggregator Backend Resilience Hardening — A Specification

**Status:** Draft · **Owner:** Claas-Thido Pfaff (GFBio SAHIS)
**Scope:** The aggregator backend (`backend/app/`, ~85 files) and the bundled
`validator/`, specifically the six trust/process boundaries enumerated in §1.3.
**NOT covered:** the React `frontend/`; the harvester, Elasticsearch `index`, and
`search` siblings; and any production-code change (deferred to the gated
hardening sub-goals that consume this spec — see `RESILIENCE_ROADMAP.md`).
**Audience:** aggregator maintainers and reviewers; the engineers executing the
roadmap; the resilience gate that verifies conformance.
**Keyword convention:** BCP 14 (RFC 2119 / RFC 8174). The UPPERCASE words MUST,
MUST NOT, SHALL, SHALL NOT, SHOULD, SHOULD NOT, MAY are normative obligations;
the same words in lowercase carry no normative weight.
**Normative references:**
- BCP 14 — RFC 2119 / RFC 8174 (keyword interpretation). *(undated — latest)*
- `resilience-review` checklist, the 14 Definition-of-Done practice fields, as
  applied on 2026-06-26. *(dated — the audit baseline)*
- `backend/app/services/es_gateway.py` — the in-repo **canonical pattern** and
  conformance exemplar this spec generalises. *(dated — commit `6976091`)*

---

## 1. Overview (informative)

### 1.1 Motivation

The aggregator catalogs ABCD datasets, runs CPU-heavy XML validation, and serves
public statistics. Every request, query, download, broker message, and
subprocess crosses a trust or process boundary where a *fault* in a dependency
(a slow query, a hostile upload, a redelivered task, a down broker) can become a
*failure* of the service. One boundary — the Elasticsearch gateway — already
demonstrates the discipline this spec requires; the others do not yet. This
specification fixes the **target behaviour** for all six boundaries so the
roadmap can drive each gap closed under test, one independently-committable
change at a time.

### 1.2 The canonical pattern (the conformance exemplar)

`EsGateway` (`backend/app/services/es_gateway.py`) is the reference all boundaries
are measured against. Its properties, generalised in §3.1 as REQ-CORE-\*:

- a per-call `httpx.AsyncClient` opened inside `async with`, so the socket is
  always released, even on the exception path;
- a single **explicit bounded** `httpx.Timeout` covering connect+read+write+pool;
- every down-path (timeout, transport error, non-2xx, garbled body) collapses to
  one **typed** `EsUnavailable`, raised `from err`;
- the caller **degrades to a declared safe value** (`harvest_status = unknown`) —
  never a silent guess, never a swallowed exception, never a fabricated success.

### 1.3 Method and findings

The six boundaries were audited with the `resilience-review` checklist by six
independent reviewers; every candidate defect was then put through an adversarial
*refute* pass and dropped unless confirmed against the code. The audit confirmed
**12 distinct defects** (7 MUST-class, 5 SHOULD-class) and refuted 8 candidates.
The Elasticsearch gateway produced **zero** confirmed defects (rubric 19/24,
acceptable) and stands as the conformance exemplar. Each confirmed defect maps to
exactly one requirement in §3 and one roadmap item in `RESILIENCE_ROADMAP.md`.
The per-boundary filled blueprints are in **Appendix A**.

### 1.4 Terms (glossary — each defined once)

- **Boundary** — a point where data or control crosses from a less-trusted or
  separate process zone (network/user/file/broker/DB/child process) into the
  backend.
- **Fail-fast** — reject loudly and close to the fault. **Fail-soft** — degrade
  to a declared reduced behaviour with the failure made visible.
- **Degrade-to-safe-value** — return a pre-declared placeholder (e.g. `unknown`)
  on dependency failure rather than guessing or fabricating a result.
- **Bounded** — having an explicit finite cap (bytes, rows, seconds, retries)
  enforced in code or config, not left to a library default.
- **Idempotency key** — a deterministic value on which a side-effecting
  operation is deduplicated, so a retry/redelivery produces one effect.
- **Statement timeout** — a server-side per-query deadline (PostgreSQL
  `statement_timeout`) after which the query is aborted.
- **Visibility timeout** — the broker interval after which an un-acked message is
  redelivered to another worker.
- **Dead-letter sink** — a durable, redrivable store for a message that has
  exhausted its retries, so it is neither lost nor infinitely redelivered.
- **Public endpoint** — a route reachable without authentication
  (`get_current_user_optional` or no auth dependency).

---

## 2. Conformance (normative)

### 2.1 Conformance target

The single conformance target is **the aggregator backend** (`backend/app/`). A
boundary (§1.3) is **conformant** when every MUST-class requirement scoped to it
in §3 is satisfied and verified by that requirement's named verification
artifact, and its Appendix-A blueprint is filled.

### 2.2 Statement levels

- A **MUST / MUST NOT / SHALL / SHALL NOT** requirement is mandatory. An
  implementation that violates one is **non-conformant** for that boundary; the
  artifact is *malformed* and MUST NOT be released as hardened.
- A **SHOULD / SHOULD NOT** requirement is a strong default. It MAY be left
  unmet only with a recorded justification and a tracked follow-up; such a
  boundary is *degraded but acceptable*.
- A **MAY** provision is optional and carries no conformance weight.

### 2.3 Claiming conformance

Conformance is claimed per requirement by demonstrating that requirement's
**Verification** (an automated test, named in §3 and implemented by the
corresponding roadmap item) passes, and — per the roadmap's red-green
discipline — that the same test was first observed to FAIL against the
pre-hardening code. A conformance claim for a boundary lists each of its
requirements with its verifying test and the test's pass result.

### 2.4 Precedence

Where this spec and the `resilience-review` checklist appear to conflict, this
spec prevails for the aggregator backend; unresolved conflicts MUST be settled
before a requirement is marked verified.

---

## 3. Requirements (normative)

Each requirement is `[ID] (LEVEL)` followed by one EARS-structured obligation,
its informative rationale, its verification method, and two-way traceability.
IDs are stable and never reused (composition rule R1). A requirement appears
normatively once (R2); other sections reference it by ID.

### 3.0 How to read traceability

`Trace: ↑ <source need>` is the checklist field or canonical property the
requirement derives from; `↓ <artifact>` is the roadmap item (RH-\*\*) and the
named test that verifies it. Every requirement traces up to a need and down to at
least one verification artifact (R7).

### 3.1 Cross-cutting canonical requirements (REQ-CORE-\*)

These generalise the §1.2 pattern. Per-boundary requirements in §3.2–§3.7
specialise them; `EsGateway` is their satisfied reference implementation.

**[REQ-CORE-1] (MUST).** While the backend issues a call across a process
boundary (HTTP, database, broker, or child process), the backend SHALL bound
that call with an explicit, finite timeout rather than rely on a library default.
- *Rationale (informative):* an unbounded call ties up a worker/connection
  indefinitely when the dependency hangs (Nygard: Blocked Threads).
- *Verification:* analysis — the database and broker timeout requirements
  (REQ-PG-1, REQ-CEL-1) are verified; the HTTP-boundary timeouts are already
  satisfied (`EsGateway` — inspection of `es_gateway.py:144-148`; the snapshot
  `requests` calls — `snapshot_tasks.py:99,160`), as are the subprocess child
  timeouts (Appendix A.6).
- *Trace:* ↑ Checklist Field 9 (Timeouts). ↓ REQ-PG-1, REQ-CEL-1; reference
  `es_gateway.py`, `tests/test_es_gateway.py`.

**[REQ-CORE-2a] (MUST).** When a remote dependency is unreachable or returns an
unusable response, the boundary SHALL surface a single typed failure to its
caller.
- *Rationale (informative):* a typed failure lets every caller branch on
  dependency-down explicitly instead of guessing.
- *Verification:* inspection — `EsGateway.count_for_urn` /
  `latest_datestamp_for_urn` raise `EsUnavailable` for every down-path
  (reference, satisfied).
- *Trace:* ↑ Field 5 (fail-fast/no-silent-catch) + canonical §1.2. ↓ REQ-OUT-2,
  REQ-SUB-2; reference `es_gateway.py:150-215`.

**[REQ-CORE-2b] (MUST).** When a boundary surfaces a typed dependency failure,
the caller SHALL degrade to a pre-declared safe value and SHALL NOT fabricate a
successful result.
- *Rationale (informative):* a guessed/fabricated success on dependency failure
  corrupts downstream state silently.
- *Verification:* inspection — `HarvestStatusService` maps `EsUnavailable` to
  `unknown` (reference, satisfied).
- *Trace:* ↑ Field 5 + canonical §1.2. ↓ REQ-OUT-2, REQ-SUB-2; reference
  `HarvestStatusService`.

**[REQ-CORE-3] (MUST).** If a boundary operation fails partway, then the backend
SHALL NOT continue and report success with partial or corrupt state.
- *Rationale (informative):* a silent "log-and-continue" that commits partial
  results is worse than a clean failure.
- *Verification:* analysis — verified via REQ-OUT-2 and REQ-SUB-2.
- *Trace:* ↑ Field 5. ↓ REQ-OUT-2, REQ-SUB-2.

**[REQ-CORE-4] (MUST).** The backend SHALL enforce an explicit finite bound on
every request body, streamed download, and result set that crosses a boundary
under external influence.
- *Rationale (informative):* an unbounded body/stream/result set is a
  memory-exhaustion (DoS) vector (Nygard: Unbounded Result Set).
- *Verification:* analysis — verified via REQ-ROUTE-1, REQ-OUT-1, REQ-PG-2.
- *Trace:* ↑ Field 8 (bounded consumption). ↓ REQ-ROUTE-1, REQ-OUT-1, REQ-PG-2.

**[REQ-CORE-5] (MUST).** Where a side-effecting operation may be retried or
redelivered, the backend SHALL make it idempotent on a deterministic key so that
repeated execution yields a single effect.
- *Rationale (informative):* `task_acks_late` redelivery re-runs a task body;
  without a key it double-writes.
- *Verification:* analysis — verified via REQ-CEL-3.
- *Trace:* ↑ Field 10 (idempotency). ↓ REQ-CEL-3.

**[REQ-CORE-6] (MUST).** The backend SHALL fail closed on every
authentication/authorization decision, denying access on any ambiguity or error.
- *Rationale (informative):* an authz check that throws must never leave access
  granted.
- *Verification:* inspection — `app/security/permissions.py` denies by default;
  `get_current_user` maps all decode errors to 401 (reference, satisfied at
  audit).
- *Trace:* ↑ Field 1 + Composition R5. ↓ reference `app/security/permissions.py`.

### 3.2 Inbound HTTP routes (REQ-ROUTE-\*)

**[REQ-ROUTE-1] (MUST).** If a client submits a request whose body exceeds the
configured maximum (default 256 KiB), then the API SHALL reject it with HTTP 413
before the body is parsed into a model, and SHALL NOT buffer the whole body into
memory first.
- *Rationale (informative):* the app registers CORS, security-headers, and
  request-logging middleware but no body-size guard (`main.py:71-94`), and there
  is no infrastructure cap; every JSON route — including the public,
  unauthenticated `POST /api/v1/validation-stats` — reads the full body into
  memory before any handler logic.
- *Verification:* test — `test_oversized_body_rejected_with_413`: send a body
  that passes the per-field item-count limit yet exceeds 256 KiB; assert status
  413 and that no handler-side effect occurred. Fails today (no guard → 422/200).
- *Trace:* ↑ Field 8; REQ-CORE-4. ↓ RH-02.

**[REQ-ROUTE-2] (SHOULD).** While a public (unauthenticated) endpoint that
performs a batched or aggregate database read is serving requests, the API SHOULD
apply a per-client rate limit and shed excess load with HTTP 429 and a
`Retry-After` header.
- *Rationale (informative):* `login` (5/min), `csrf` (20/min), and `harvest`
  (30/hour) carry `@limiter.limit`, but the public `POST /validation-stats`
  (a batched read of up to 500 dataset summaries) and the public
  `GET /api/v1/statistics/*` aggregations have none; the slowapi limiter and its
  429 handler are already wired (`main.py:68-69`).
- *Verification:* test — `test_public_validation_stats_is_rate_limited`: from one
  client host, issue N+1 `POST /api/v1/validation-stats` beyond the configured
  limit; assert at least one 429. Fails today (no limit → all 200).
- *Trace:* ↑ Field 12 (load shedding). ↓ RH-08.

### 3.3 Elasticsearch gateway (REQ-ESGW-\*) — conformance exemplar

These requirements are **satisfied** by the current code and define the bar the
other boundaries must reach. The audit confirmed zero defects here.

**[REQ-ESGW-1] (MUST).** While the backend queries Elasticsearch, every request
SHALL be bounded by an explicit `httpx.Timeout` and SHALL release its socket on
all paths.
- *Rationale (informative):* the harvest-status feature must not hang on a slow
  ES cluster.
- *Verification:* inspection of `es_gateway.py:144-148, 159-173`;
  `tests/test_es_gateway.py` exercises the timeout path. *(satisfied)*
- *Trace:* ↑ REQ-CORE-1; Field 9. ↓ `tests/test_es_gateway.py` (existing).

**[REQ-ESGW-2a] (MUST).** When Elasticsearch is unreachable or returns an
unusable body, the gateway SHALL raise `EsUnavailable`.
- *Rationale (informative):* per-dataset accuracy is non-negotiable; absence is
  not ES-down.
- *Verification:* inspection of `es_gateway.py:164-173, 201-210`; covered by
  `tests/test_es_gateway.py`. *(satisfied)*
- *Trace:* ↑ REQ-CORE-2a; Field 5. ↓ `tests/test_es_gateway.py` (existing).

**[REQ-ESGW-2b] (MUST).** When the gateway raises `EsUnavailable`, the caller
SHALL map it to `harvest_status = unknown` and SHALL NOT report a guessed
presence.
- *Rationale (informative):* the degraded value must be safe and explicit, never
  a fabricated presence.
- *Verification:* inspection of `HarvestStatusService`; covered by
  `tests/test_es_gateway.py`. *(satisfied)*
- *Trace:* ↑ REQ-CORE-2b; Field 5. ↓ `tests/test_es_gateway.py` (existing).

### 3.4 Outbound HTTP — snapshot tasks (REQ-OUT-\*)

**[REQ-OUT-1] (MUST).** While downloading a provider-controlled remote archive,
the snapshot task SHALL abort with a typed error once the cumulative streamed
body exceeds a configured byte budget (`MAX_ARCHIVE_BYTES`), and SHALL NOT load
the entire archive into memory in one read.
- *Rationale (informative):* `parse_archive_xml`
  (`snapshot_tasks.py:160-212`) streams into
  `SpooledTemporaryFile(max_size=10 MiB)` — a memory→disk *rollover* threshold,
  not a size cap — then reads the whole buffer for `ET.fromstring`; a huge or
  hostile archive exhausts the worker's disk/memory.
- *Verification:* test —
  `test_oversized_archive_stream_aborts_before_cap`: stub a well-formed
  single-root XML stream larger than the budget with no `Content-Length`; spy on
  `temp_file.write` (or assert `XMLParsingError`) and assert total bytes written
  stays under the cap. Fails today (no cap; all bytes written).
- *Trace:* ↑ Field 8; REQ-CORE-4. ↓ RH-04.

**[REQ-OUT-2] (SHOULD).** If any XML entry inside a multi-entry archive fails to
parse, then the snapshot task SHALL NOT report a clean successful snapshot — it
SHALL either fail the whole archive with a typed error listing the failed
entries, or persist an explicit incompleteness indicator alongside the count.
- *Rationale (informative):* the ZIP branch
  (`snapshot_tasks.py:194-202`) catches `ET.ParseError` per entry, logs, and
  `continue`s, then returns a partial `unit_count` as a successful snapshot; the
  timeline cannot distinguish a complete count from a partial one.
- *Verification:* test —
  `test_zip_with_unparseable_entry_not_reported_clean`: stub a ZIP with one
  well-formed and one malformed XML entry; assert `parse_archive_xml` either
  raises `XMLParsingError` or returns a result whose incompleteness indicator is
  truthy. Fails today (returns clean partial count).
- *Trace:* ↑ Field 5; REQ-CORE-3. ↓ RH-10.

### 3.5 PostgreSQL (REQ-PG-\*)

**[REQ-PG-1] (MUST).** While the backend executes any database query (on either
the async or the sync engine), a bounded server-side statement timeout SHALL be
in force so that a slow or lock-blocked query is aborted rather than pinning a
pooled connection indefinitely.
- *Rationale (informative):* `create_async_engine` (`app/db/base.py:15-21`) and
  `create_engine` (`app/db/session.py:17`) are built with no `connect_args`; no
  `statement_timeout`/`lock_timeout`/`command_timeout` exists anywhere, so one
  slow query crossing the boundary can exhaust the pool.
- *Verification:* test (testcontainers) —
  `test_slow_query_aborts_within_timeout`: with `statement_timeout` set to
  2000 ms, run `SELECT pg_sleep(10)` through the engine and assert it raises in
  under 5 s (the 10 s sleep is aborted, never run to completion). Fails today
  (the query runs the full 10 s, unbounded).
- *Trace:* ↑ Field 9; REQ-CORE-1. ↓ RH-01.

**[REQ-PG-2] (MUST).** When the public statistics surface computes quality
metrics, it SHALL derive its counts via bounded SQL aggregates and SHALL NOT
materialize an unbounded result set of validation-job rows into application
memory.
- *Rationale (informative):* `get_validation_jobs_since`
  (`snapshot_repository.py:79-83`) issues `.all()` with no LIMIT — each row
  carrying a JSON `results` blob — and is reached from the public,
  unauthenticated `GET /api/v1/statistics/quality` via
  `SnapshotService.get_quality_metrics` (`snapshot_service.py:52`). Its sibling
  `get_completed_validation_jobs` (`:59-77`) is the same unbounded `.all()`
  pattern on the related success-rate path. The bounded aggregate pattern already
  exists at `count_recent_validations` (`:85-92`).
- *Verification:* test —
  `test_quality_metrics_does_not_materialize_all_jobs`: monkeypatch
  `get_validation_jobs_since` to raise, then assert `get_quality_metrics` still
  returns correct counts (proving it now uses aggregates). Fails today (it calls
  that unbounded method).
- *Trace:* ↑ Field 8; REQ-CORE-4. ↓ RH-03.

### 3.6 Celery / Redis (REQ-CEL-\*)

**[REQ-CEL-1] (MUST).** The broker visibility timeout SHALL exceed the longest
configured task time limit, so that a long-running task is never redelivered and
re-executed while it is still running.
- *Rationale (informative):* `broker_transport_options` is unset
  (`celery_app.py:45-68`), so the Redis default visibility timeout (3600 s)
  applies, while `validate_archive` runs up to `task_time_limit=7500 s`
  (`validator_tasks.py:31`); with `task_acks_late=True` a >1 h validation is
  redelivered and re-run.
- *Verification:* test —
  `test_visibility_timeout_exceeds_longest_task_limit`: assert
  `celery_app.conf.broker_transport_options.get('visibility_timeout', 3600) >
  7500`. Fails today (`{}` → 3600 > 7500 is false).
- *Trace:* ↑ Field 14. ↓ RH-05.

**[REQ-CEL-2] (MUST).** When a task exhausts its retries or is rejected, the
backend SHALL persist the failed payload to a durable, redrivable dead-letter
sink.
- *Rationale (informative):* the only current give-up behaviour is a
  `logger.critical`, after which the message is acked and dropped — the payload is
  lost and cannot be redriven.
- *Verification:* test — `test_failed_task_is_persisted_to_dead_letter`: drive a
  task to give-up and assert its payload is persisted in the new sink. Fails today
  (no durable sink exists).
- *Trace:* ↑ Field 14. ↓ RH-07.

**[REQ-CEL-2b] (MUST).** The backend SHALL NOT configure broker or task settings
that have no effect.
- *Rationale (informative):* `task_dead_letter_queue_config`
  (`celery_app.py:62-67`) is not a real Celery setting — it is stored inertly and
  misleads the reader into believing a dead-letter queue exists.
- *Verification:* test — `test_no_phantom_dead_letter_setting`: assert
  `'task_dead_letter_queue_config' not in celery_app.conf.table()`. Fails today
  (the unknown key IS stored).
- *Trace:* ↑ Field 14 + Composition R2 (single source of truth). ↓ RH-07.

**[REQ-CEL-3] (MUST).** When the snapshot-collection task is redelivered for an
archive that already has a snapshot for the same calendar day, the task SHALL
NOT insert a duplicate snapshot row.
- *Rationale (informative):* `collect_single_archive_snapshot`
  (`snapshot_tasks.py:326-333`) unconditionally `db.add`/`commit`s an
  `ArchiveSnapshotModel`, which has indexes but no uniqueness constraint
  (`archive_snapshot.py:52-57`); under `task_acks_late` + `reject_on_worker_lost`
  a redelivery double-inserts. (The validation task is already retry-safe via its
  `task_id`-based dedup — `validator_tasks.py:82-95`.)
- *Verification:* test —
  `test_single_snapshot_redelivery_inserts_once`: seed one `isLatest`
  archive; stub `parse_archive_xml` to return metadata with `etag=None`
  (so change-detection reports "changed" on the second run); invoke the task
  twice and assert exactly one `ArchiveSnapshotModel` row. Fails today
  (two rows).
- *Trace:* ↑ Field 10; REQ-CORE-5. ↓ RH-06.

**[REQ-CEL-4] (SHOULD).** When a task fails with a deterministic, non-transient
error (e.g. archive-not-found), the backend SHOULD NOT auto-retry it; retries
SHOULD fire only for transient error classes.
- *Rationale (informative):* `validate_archive` declares
  `autoretry_for=(Exception,)` (`validator_tasks.py:30`) yet raises
  `ValueError("Archive with ID … not found")` (`:70`) for a missing archive,
  which is missing on every retry — burning the retry budget and backoff window.
- *Verification:* test —
  `test_archive_not_found_is_not_retried`: with no archive row seeded, spy on
  `validate_archive.retry` and assert `retry.call_count == 0` while the
  `ValueError` propagates. Fails today (autoretry invokes retry).
- *Trace:* ↑ Field 9 (retries fire only on retriable errors). ↓ RH-09.

### 3.7 Subprocess (REQ-SUB-\*)

**[REQ-SUB-1] (SHOULD).** While invoking a Celery control command, the
task-management utility SHOULD execute the child process without a shell,
passing the command and its arguments as a list, so that no argument is
re-interpreted by a shell.
- *Rationale (informative):* `run_celery_command`
  (`manage_tasks.py:18-23`) calls `subprocess.run(cmd, shell=True, …)` where
  `cmd` is an f-string; `cancel_task`/`cancel_all_tasks` interpolate an
  operator-supplied `task_id` (`:207, :213, :259, :264`), a latent
  command-injection class.
- *Verification:* test —
  `test_cancel_task_uses_argv_not_shell`: call
  `cancel_task("$(touch /tmp/pwn)")` with `subprocess.run` spied; assert the
  call's `shell` is not `True` and that `argv[0]` is a list containing the
  literal `"$(touch /tmp/pwn)"` unsplit. Fails today (`shell=True`, string cmd).
- *Trace:* ↑ Field 1 (input validation at the boundary). ↓ RH-11.

**[REQ-SUB-2] (SHOULD).** If a managed subprocess exits with a non-zero status,
then the utility SHOULD report the command as failed, and SHOULD NOT present a
non-zero exit as success.
- *Rationale (informative):* `run_celery_command` (`manage_tasks.py:33`) returns
  `{"output": …, "error": …}` for the non-JSON path without inspecting
  `returncode`; the dict is always truthy, so `cancel_task` prints
  "✅ … revoked" even when the celery child exited non-zero.
- *Verification:* test —
  `test_cancel_task_reports_failure_on_nonzero_exit`: stub `subprocess.run` to
  return `returncode=1` with stderr set; call `cancel_task` and assert the
  failure branch ("❌ Failed to cancel task") fires, not the success branch.
  Fails today (success branch fires).
- *Trace:* ↑ Field 5; REQ-CORE-3. ↓ RH-12.

---

## 4. Requirements traceability matrix (normative index)

| Req | Level | Boundary | Field | Finding | Roadmap | Status |
|-----|-------|----------|-------|---------|---------|--------|
| REQ-CORE-1 | MUST | cross-cut | 9 | — | RH-01, RH-05 | partial |
| REQ-CORE-2a | MUST | cross-cut | 5 | — | RH-10, RH-12 | partial |
| REQ-CORE-2b | MUST | cross-cut | 5 | — | RH-10, RH-12 | partial |
| REQ-CORE-3 | MUST | cross-cut | 5 | — | RH-10, RH-12 | partial |
| REQ-CORE-4 | MUST | cross-cut | 8 | — | RH-02, RH-03, RH-04 | partial |
| REQ-CORE-5 | MUST | cross-cut | 10 | — | RH-06 | unmet |
| REQ-CORE-6 | MUST | cross-cut | 1 | — | (reference) | satisfied |
| REQ-ROUTE-1 | MUST | routes | 8 | F-BODY-01 | RH-02 | unmet |
| REQ-ROUTE-2 | SHOULD | routes | 12 | F-RATELIMIT-01 | RH-08 | unmet |
| REQ-ESGW-1 | MUST | es_gateway | 9 | — | (reference) | satisfied |
| REQ-ESGW-2a | MUST | es_gateway | 5 | — | (reference) | satisfied |
| REQ-ESGW-2b | MUST | es_gateway | 5 | — | (reference) | satisfied |
| REQ-OUT-1 | MUST | outbound_http | 8 | F-SNAP-01 | RH-04 | unmet |
| REQ-OUT-2 | SHOULD | outbound_http | 5 | F-SNAP-04 | RH-10 | unmet |
| REQ-PG-1 | MUST | postgres | 9 | F-DB-01 | RH-01 | unmet |
| REQ-PG-2 | MUST | postgres | 8 | F-DB-02 | RH-03 | unmet |
| REQ-CEL-1 | MUST | celery_redis | 14 | F-CELERY-01 | RH-05 | unmet |
| REQ-CEL-2 | MUST | celery_redis | 14 | F-CELERY-02 | RH-07 | unmet |
| REQ-CEL-2b | MUST | celery_redis | 14 | F-CELERY-02 | RH-07 | unmet |
| REQ-CEL-3 | MUST | celery_redis | 10 | F-CELERY-03 | RH-06 | unmet |
| REQ-CEL-4 | SHOULD | celery_redis | 9 | F-CELERY-04 | RH-09 | unmet |
| REQ-SUB-1 | SHOULD | subprocess | 1 | F-MTASKS-01 | RH-11 | unmet |
| REQ-SUB-2 | SHOULD | subprocess | 5 | F-MTASKS-02 | RH-12 | unmet |

"Status" is as-audited on 2026-06-26; the roadmap moves every *unmet* row to
*satisfied* under test.

---

## 5. Examples (informative)

- **Happy path (REQ-ROUTE-1):** a 2 KiB `POST /validation-stats` body is parsed
  and served normally; the 256 KiB guard is transparent.
- **Edge (REQ-CEL-3):** the beat job and an ad-hoc `collect_single_archive_snapshot`
  race on the same archive on the same day → exactly one snapshot row, the second
  insert a no-op via the uniqueness guard.
- **Failure (REQ-PG-1):** a pathological join exceeds `statement_timeout` → the
  query is aborted, the connection returns to the pool, the request gets a 5xx
  instead of the whole worker stalling.

---

## Appendix A — Per-boundary resilience blueprints (as-audited 2026-06-26)

Each blueprint is the filled `resilience-review` schema for the boundary,
condensed to the fields with non-trivial content. **GAP** marks an unmet
property addressed by the cited requirement.

### A.1 Inbound HTTP routes — rubric 14/24 (malformed: Field 8 = 0)
- **trust_boundaries:** path/query params coerced by FastAPI + `Query(ge/le)`
  bounds; filter/sort allowlisted (`filtering.py`, `sorting.py`), values
  LIKE-escaped (`query_utils.py:111-112`); JSON bodies parsed to Pydantic
  models. **GAP:** no request body-size limit (REQ-ROUTE-1).
- **error_model:** fail-fast on validation/auth; global handler → generic 500,
  no stacktrace leak. **security_failure:** fail-closed (deny by default, role
  `None` → 403).
- **resources/bounds:** list endpoints paginate (≤101/page); validation-stats
  identifiers ≤500. **GAP:** request body unbounded (REQ-ROUTE-1).
- **remote_calls:** Postgres pool 10+20; **GAP:** no per-request statement
  timeout (REQ-PG-1). Redis readiness probe bounded at 5 s.
- **overload:** slowapi on login/csrf/harvest. **GAP:** public `/validation-stats`
  and `/statistics/*` unthrottled (REQ-ROUTE-2).
- **lifecycle:** liveness (`/health/live`, no deps) ≠ readiness (`/health/ready`,
  DB+Redis → 503) — distinct. Minor: no SIGTERM drain hook (SHOULD).
- **observability:** structured logs + correlation id; no latency/saturation
  metrics (SHOULD).

### A.2 Elasticsearch gateway — rubric 19/24 (acceptable: conformance exemplar)
- **trust_boundaries:** identifiers parsed to typed ids (`parse_dataset_urn`);
  URN ASCII by construction (no injection).
- **error_model:** every down-path → typed `EsUnavailable from err`; caller
  degrades to `unknown`; nothing silent. **security_failure:** n/a (read-only),
  optional basic auth.
- **resources/bounds:** `_count` and size-1 `_search` bounded; per-call client in
  `async with` → socket always released.
- **remote_calls:** `httpx.Timeout(ES_TIMEOUT_SECONDS=5 s)` bounds
  connect+read+write+pool; no retry (read-only, acceptable); no breaker
  (acceptable at scale). **No GAP** — reference posture.

### A.3 Outbound HTTP (snapshot tasks) — rubric 14/24 (malformed: Fields 8,10 = 0)
- **trust_boundaries:** provider-controlled remote archive (HTTP) + provider XML.
- **remote_calls:** `requests.head` t=10 s, `requests.get` t=30 s present (Field 9
  PASS). **GAP:** streamed body unbounded (REQ-OUT-1).
- **resources/bounds:** **GAP:** `SpooledTemporaryFile(max_size)` is a rollover,
  not a cap; full-buffer read into `ET.fromstring` (REQ-OUT-1).
- **error_model:** download/parse errors → typed `XMLParsingError`. **GAP:** ZIP
  per-entry parse failure silently skipped → partial count reported clean
  (REQ-OUT-2).
- **idempotency:** **GAP:** snapshot insert not keyed; redelivery double-inserts
  (REQ-CEL-3 / RH-06).

### A.4 PostgreSQL — rubric 12/24 (malformed)
- **trust_boundaries:** parameterized queries (no SQL injection); sessions
  released via `get_db`/`get_sync_db` `finally`.
- **remote_calls:** async (`asyncpg`) + sync (`psycopg2`) engines; pool 10+20,
  `pool_recycle=1800`. **GAP:** no `statement_timeout`/`lock_timeout`/
  `command_timeout` on either engine (REQ-PG-1).
- **resources/bounds:** most reads bounded/aggregated. **GAP:** unbounded
  `.all()` over validation jobs reachable from public stats (REQ-PG-2).
- **error_model:** write path rolls back cleanly; read path broad-catch (minor,
  refuted as a separate defect — driver errors do not corrupt state here).

### A.5 Celery / Redis — rubric 14/24 (malformed: Field 10 = 0)
- **config:** `task_acks_late=True`, `reject_on_worker_lost=True`,
  `prefetch=1`, `result_expires=3600 s` (bounded ✓), global limits
  7200/7000 s; `validate_archive` 7500/7200 s with capped backoff+jitter
  (`retry_backoff_max=120`, `retry_jitter=True`).
- **GAP (REQ-CEL-1):** `broker_transport_options={}` → default visibility 3600 s
  < 7500 s longest hard limit.
- **GAP (REQ-CEL-2):** `task_dead_letter_queue_config` is a phantom (inert) key;
  no real dead-letter sink.
- **GAP (REQ-CEL-3):** snapshot tasks append-only, no idempotency key under
  acks_late.
- **GAP (REQ-CEL-4):** `autoretry_for=(Exception,)` retries deterministic errors.
- broker reconnect, Redis socket timeout: audited and **acceptable** (refuted as
  defects).

### A.6 Subprocess — rubric 17/24 (acceptable, two SHOULD gaps)
- **trust_boundaries:** `manage_tasks.py` is an operator CLI (not
  network-reachable); both `subprocess.run` calls have a timeout (10 s / 2 s).
- **GAP (REQ-SUB-1):** `shell=True` with f-string-interpolated `task_id` — latent
  injection class; switch to list-argv + `shell=False`.
- **GAP (REQ-SUB-2):** child `returncode` never checked on the non-JSON path →
  non-zero exit reported as success.
- **resources:** `capture_output` buffers child output in memory (bounded in
  practice by the trusted child; noted, not a confirmed defect).

---

## Appendix B — Change log

| Version | Date | Change |
|---------|------|--------|
| Draft   | 2026-06-26 | Initial specification from the resilience audit of commit `6976091`; 6 boundaries, 12 confirmed defects, 23 requirements. |

## Appendix C — Refuted candidates (informative)

Dropped by the adversarial refute pass; recorded so they are not re-raised:
F-HARVEST-01 (`/legacy-data-sets` "unbounded" — bounded in practice / not a
public-reachable hot path as claimed), F-SNAP-01-routes (broad-except 500 —
acceptable masking, no leak), F-ESCFG-01 (ES timeout default — satisfied),
F-ESCFG-02 (ES fail-fast config — fail-soft is correct), F-SNAP-02 (scalar
read-timeout — impact claim false), F-DB-03 (untyped DB error — no state
corruption), F-CELERY-05 (Redis socket timeout — config already safe),
F-CELERY-06 (broker reconnect — already enabled).
