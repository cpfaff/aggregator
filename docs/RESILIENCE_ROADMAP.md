# GFBio Aggregator Backend Resilience Hardening — Roadmap

This roadmap sequences the work that makes `RESILIENCE_HARDENING_SPEC.md` true.
Each item closes exactly one confirmed defect, is independently committable, and
is driven test-first: **write the named RED test, watch it fail for the stated
reason, then make the minimal fix turn it green.** No item changes behaviour
beyond what its requirement demands.

## How to run an item (the gate every item must pass)

Every item passes the project's standard gate — test suite, ruff check and ruff
format. `CLAUDE.md` ("Running Tests" and "Linting/Formatting") is the single
source for those commands and the current green baselines; it is not repeated
here, because the copy that used to live in this section rotted while the
original stayed correct.

Use one atomic conventional commit per item, e.g.
`fix(resilience): bound request body size (RH-02, REQ-ROUTE-1)`. Land the RED
test and its fix in the **same** commit — the test is the regression lock.

## Definition of Done (per item)

1. The named RED test exists and was observed FAILING against pre-fix code (paste
   the failing output in the commit/PR body).
2. The minimal fix makes that test pass.
3. The full suite stays green; `ruff check` and `ruff format --check` are clean.
4. No unrelated behaviour changed; no test weakened, skipped, or xfail'd.
5. The item's Success criteria all hold.

## Dependencies & Ordering

- **Priority = severity.** RH-01…RH-07 are MUST-class (the spec is *malformed*
  until they land); RH-08…RH-12 are SHOULD-class. Do MUST first.
- **All twelve items are independently committable** — none blocks another in
  code. The recommended order below is by blast-radius then cost.
- **Two items add an Alembic migration** (RH-06 unique index; RH-07 dead-letter
  table). Follow `docs/DATABASE_MIGRATION_GUIDE.md`; these two are independent of
  each other and of the rest. Generate the migration *before* the code that
  relies on the new schema.
- RH-05 (a one-line broker setting) SHOULD precede RH-06/RH-07 only because it is
  the cheapest Celery fix; there is no code dependency.
- Recommended sequence: **RH-01 → RH-02 → RH-03 → RH-04 → RH-05 → RH-06 → RH-07**
  (MUST), then **RH-08 → RH-09 → RH-10 → RH-11 → RH-12** (SHOULD).

---

## RH-01 (MUST) — Bound every DB query with a statement timeout

- **Boundary:** PostgreSQL · **Requirement:** REQ-PG-1 · **Finding:** F-DB-01 ·
  **Field:** 9 (timeouts) · **Effort:** ~4h

**Goal:** A slow or lock-blocked query is aborted by a server-side deadline
instead of pinning a pooled connection until the pool is exhausted.

**Confirmed defect:** `app/db/base.py:15-21` builds the async engine and
`app/db/session.py:17` the sync engine, both with no `connect_args`; no
`statement_timeout`/`lock_timeout`/`command_timeout` is set anywhere.

**Minimal fix:** Add timeout settings to `app/core/config.py` (e.g.
`DB_STATEMENT_TIMEOUT_MS: int = 5000`, `DB_LOCK_TIMEOUT_MS: int = 3000`) and pass
them via `connect_args` on **both** engines, mirroring the single-bounded-timeout
discipline of `es_gateway`:
- async (asyncpg): `connect_args={"server_settings": {"statement_timeout":
  str(settings.DB_STATEMENT_TIMEOUT_MS), "lock_timeout":
  str(settings.DB_LOCK_TIMEOUT_MS)}}`
- sync (psycopg2): `connect_args={"options": f"-c statement_timeout=
  {settings.DB_STATEMENT_TIMEOUT_MS} -c lock_timeout={settings.DB_LOCK_TIMEOUT_MS}"}`

**RED test** — `tests/services/test_db_statement_timeout.py::test_slow_query_aborts_within_timeout`
(testcontainers, sync engine): with `statement_timeout` set to 2000 ms, execute
`SELECT pg_sleep(10)` through a session and assert it raises a DB error in under 5s
(the 10s sleep is aborted, never run to completion — e.g.
`pytest.raises((OperationalError, DBAPIError))` under a wall-clock assertion).
**Fails today** because the query runs the full 10s unbounded. (A factory-kwargs
spy is unreliable — `connect_args` live in a driver closure — so the test is
behavioural.)

**Implementation checklist:**
- [ ] Add `DB_STATEMENT_TIMEOUT_MS` and `DB_LOCK_TIMEOUT_MS` to `app/core/config.py` `Settings`.
- [ ] Pass `connect_args` on the async engine in `app/db/base.py:15-21`.
- [ ] Pass `connect_args` on the sync engine in `app/db/session.py:17`.
- [ ] Write the RED test; observe it fail; apply the fix; observe it pass.

**Success criteria:**
- [ ] `test_slow_query_aborts_within_timeout` passes; was shown failing first.
- [ ] Both engines carry the timeout (assert via the behavioural test on the sync
  engine and an async variant, or one test per engine).
- [ ] Full suite green; `ruff check app/ tests/` and `ruff format --check` clean.
- [ ] No existing query that legitimately runs <5s regresses (run the service
  test subset).

**Key considerations (SRE review):**
- *Edge — long legitimate work:* the nightly snapshot/validation run in Celery
  tasks, not request handlers; confirm no legitimate **single query** exceeds 5s
  before tightening (raise the default if one does, with a comment).
- *Edge — migrations:* Alembic uses its own engine; do not let a short
  `statement_timeout` abort a long migration — scope the setting to the app
  engines only (it already is — Alembic builds its engine in `alembic/env.py`).
- *Dependency failure:* a timeout surfaces as a 5xx; that is the intended
  fail-fast, superior to a stalled worker.
- *Reference:* `es_gateway.py:144-148` (one explicit bounded timeout).

**Anti-patterns:**
- ❌ Setting the timeout on only one engine (the sync engine feeds every Celery task).
- ❌ A unit test that asserts on `engine.url`/kwargs instead of behaviour (tautological — connect_args are not on the URL).
- ❌ Swallowing the resulting `OperationalError` with a bare `except`.

---

## RH-02 (MUST) — Reject oversized request bodies at the edge

- **Boundary:** inbound routes · **Requirement:** REQ-ROUTE-1 ·
  **Finding:** F-BODY-01 · **Field:** 8 (bounded consumption) · **Effort:** ~4h

**Goal:** A request body larger than a small cap is rejected with HTTP 413 before
it is buffered into memory and parsed — closing a memory-exhaustion DoS on every
JSON route, including the public unauthenticated `POST /validation-stats`.

**Confirmed defect:** `main.py:71-94` registers CORS, `SecurityHeadersMiddleware`,
and request-logging middleware — no body-size guard — and there is no infra cap.

**Minimal fix:** Add a small ASGI/Starlette middleware that, before the handler,
rejects requests whose `Content-Length` exceeds `settings.MAX_REQUEST_BODY_BYTES`
(default `256 * 1024`) with 413, and — because `Content-Length` can be absent on
chunked uploads — also counts streamed bytes and rejects once the cap is exceeded.
Register it in `main.py` alongside `SecurityHeadersMiddleware`. Belt-and-suspenders:
bound each `ValidationStatsRequest` identifier with
`Annotated[str, StringConstraints(max_length=512)]`.

**RED test** — `tests/test_request_body_limit.py::test_oversized_body_rejected_with_413`:
with `TestClient(app)`, send `POST /api/v1/validation-stats` with an explicit
`Content-Length` header set above the 256 KiB cap and a matching-size body of
otherwise-valid JSON; assert status 413 and that the handler did not run. **Fails
today** (no guard → the body is buffered and parsed, yielding 200/422, never 413).
Driving the rejection through the `Content-Length` header keeps the test
deterministic and free of per-item byte tuning; add a second case with a chunked
body (no `Content-Length`) over the cap to exercise the streamed-byte counter.

**Implementation checklist:**
- [ ] Add `MAX_REQUEST_BODY_BYTES: int = 256 * 1024` to `app/core/config.py`.
- [ ] Add a `BodySizeLimitMiddleware` (Content-Length pre-check + streamed-byte
  counter) in `main.py`; register it via `app.add_middleware(...)`.
- [ ] Add `max_length=512` to the identifier item type in the
  `ValidationStatsRequest` schema.
- [ ] Write the RED test (count-valid, size-invalid payload); fail → fix → pass.

**Success criteria:**
- [ ] `test_oversized_body_rejected_with_413` passes; shown failing first.
- [ ] A normal small body (e.g. 2 KiB) still returns its usual 2xx/422 — add
  `test_normal_body_passes` to prove the guard is not over-eager.
- [ ] Full suite green; ruff check + format clean.
- [ ] The 413 path does not read the whole oversized body (assert via the
  Content-Length branch returning before handler logic).

**Key considerations (SRE review):**
- *Edge — missing Content-Length (chunked):* the streamed-byte counter must still
  enforce the cap; test both a header-present and a header-absent oversized case.
- *Edge — multipart/large legit uploads:* confirm no current endpoint legitimately
  accepts >256 KiB (validators submit IDs/URLs, not file bodies); if one does,
  scope the cap per-route rather than globally.
- *Concurrency:* the middleware is per-request and stateless — no shared state.
- *Reference:* `SecurityHeadersMiddleware` (`main.py:82-94`) is the in-repo
  middleware shape to copy.

**Anti-patterns:**
- ❌ Trusting `Content-Length` alone (a chunked body omits it).
- ❌ A test that overshoots the 500-item limit (then 422 masks the missing 413 —
  tautological for this requirement).
- ❌ Reading `await request.body()` in the middleware (defeats the purpose).

---

## RH-03 (MUST) — Compute public quality metrics with bounded SQL aggregates

- **Boundary:** PostgreSQL · **Requirement:** REQ-PG-2 · **Finding:** F-DB-02 ·
  **Field:** 8 · **Effort:** ~5h

**Goal:** The public, unauthenticated statistics surface computes its quality
metrics with SQL aggregates instead of materializing every validation-job row
(each with a JSON `results` blob) into memory.

**Confirmed defect:** `app/repositories/snapshot_repository.py:79-83`
(`get_validation_jobs_since`) issues `.all()` with no LIMIT; it is consumed by
`SnapshotService.get_quality_metrics` (`snapshot_service.py:52`), reached from the
public `GET /api/v1/statistics/quality`. Its sibling `get_completed_validation_jobs`
(`:59-77`) is the same unbounded `.all()` pattern on the related success-rate path
and should be converted in the same change.

**Minimal fix:** Replace the Python-side counting in `get_quality_metrics` with
scalar SQL aggregates on the repository — `COUNT(*)`,
`COUNT(*) FILTER (WHERE status='completed' AND valid_files=total_files AND
total_files>0)`, `AVG(validation_time) FILTER (...)` — following the existing
`count_recent_validations` pattern (`snapshot_repository.py:85-92`). Add the
aggregate method(s) to `SnapshotRepository`; have `get_quality_metrics` call them.

**RED test** — `tests/services/test_snapshot_service.py::test_quality_metrics_does_not_materialize_all_jobs`
(testcontainers, reuses the `sync_db_session` fixture): seed several completed/
failed `ValidationJobModel` rows; monkeypatch `get_validation_jobs_since` to raise
`AssertionError`; call `get_quality_metrics` and assert it (a) returns the correct
counts and (b) does **not** raise — proving it no longer routes through the
unbounded method. **Fails today** because `get_quality_metrics` calls
`get_validation_jobs_since`.

**Implementation checklist:**
- [ ] Add aggregate method(s) to `SnapshotRepository` (mirror `count_recent_validations`).
- [ ] Rewrite `SnapshotService.get_quality_metrics` to use them; stop calling the
  unbounded `get_validation_jobs_since` (and convert the success-rate path's
  `get_completed_validation_jobs` likewise).
- [ ] Keep the existing correctness tests
  (`test_snapshot_service.py:191-291`) green (same numbers, new path).
- [ ] Write the RED test (monkeypatch-to-raise); fail → fix → pass.

**Success criteria:**
- [ ] `test_quality_metrics_does_not_materialize_all_jobs` passes; shown failing first.
- [ ] The existing quality-metric correctness tests still pass unchanged (numbers
  identical).
- [ ] Full suite green; ruff check + format clean.
- [ ] `grep -n "\.all()" app/repositories/snapshot_repository.py` shows no
  validation-job `.all()` remains on the public quality path.

**Key considerations (SRE review):**
- *Edge — zero rows:* `AVG(...)` over zero rows is NULL → coerce to 0/None as the
  existing code does (`scalar() or 0`); test the empty-window case.
- *Edge — division:* percentage math must guard `total_files==0` (already a
  documented case — preserve it).
- *Large input:* the whole point — seed e.g. 1000 rows and confirm constant memory
  (no row list built).
- *Reference:* `count_recent_validations` (`snapshot_repository.py:85-92`).

**Anti-patterns:**
- ❌ Leaving the unbounded `.all()` methods on the public path "for now".
- ❌ Adding a `LIMIT` instead of an aggregate (a capped fetch still returns wrong
  counts — the requirement is *aggregate in SQL*).
- ❌ A test that only checks numbers (does not prove boundedness).

---

## RH-04 (MUST) — Bound the streamed archive download

- **Boundary:** outbound HTTP · **Requirement:** REQ-OUT-1 · **Finding:** F-SNAP-01
  · **Field:** 8 · **Effort:** ~5h

**Goal:** A provider archive download aborts with a typed error once it exceeds a
byte budget, so a huge/hostile archive cannot exhaust the worker's disk/memory.

**Confirmed defect:** `app/tasks/snapshot_tasks.py:160-212` streams into
`SpooledTemporaryFile(max_size=10 MiB)` — a memory→disk rollover threshold, not a
cap — then reads the whole buffer for `ET.fromstring`.

**Minimal fix:** Introduce `MAX_ARCHIVE_BYTES` (config, e.g. 200 MiB). In the
`iter_content` loop keep a `written` counter and
`if written > MAX_ARCHIVE_BYTES: raise XMLParsingError("archive exceeds N bytes")`
before each write (authoritative — `Content-Length` may be absent or lie). As an
early-out, also reject up-front if `response.headers.get("Content-Length")`
exceeds the budget. (Optional follow-on, not required for green: switch the
full-DOM `ET.fromstring` to `ET.iterparse` to bound parse memory too.)

**RED test** — `tests/test_snapshot_archive_bound.py::test_oversized_archive_stream_aborts`
: monkeypatch `requests.get` to return a streamed response yielding well-formed
single-root XML chunks totaling more than the budget, with **no** `Content-Length`;
spy on `tempfile.SpooledTemporaryFile.write` (or the temp file) and assert total
bytes written stays at/under the cap (and/or `XMLParsingError` is raised). **Fails
today** (no cap → all bytes written). Use single-root well-formed XML so the only
abort cause is the byte cap (a multi-root padding would raise `ParseError` for the
wrong reason — tautological).

**Implementation checklist:**
- [ ] Add `MAX_ARCHIVE_BYTES: int` to `app/core/config.py`.
- [ ] Add the `written` counter + raise in the `iter_content` loop
  (`snapshot_tasks.py:173-175`).
- [ ] Add the early `Content-Length` reject after `raise_for_status`.
- [ ] Write the RED test (no-Content-Length, byte-spy); fail → fix → pass.

**Success criteria:**
- [ ] `test_oversized_archive_stream_aborts` passes; shown failing first.
- [ ] A normal small archive still parses correctly — add/keep
  `test_normal_archive_parses` (single-root and ZIP).
- [ ] The cap fires by **byte count**, not by Content-Length alone (test the
  header-absent path).
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — Content-Length lies/absent:* the running counter is authoritative; the
  header check is an optimization only.
- *Edge — ZIP bomb:* a small ZIP can inflate hugely on `zip_file.open().read()`;
  note this as a known residual (cap per-entry read in the optional iterparse
  follow-on) — do not silently claim full coverage.
- *Concurrency:* runs in the stats worker (prefork); per-task local — no shared state.
- *Reference:* `es_gateway` bounded-resource discipline (`es_gateway.py`).

**Anti-patterns:**
- ❌ Trusting `SpooledTemporaryFile(max_size=...)` as a size cap (it is a rollover threshold).
- ❌ A RED test whose payload is malformed XML (then `ParseError` passes the test for the wrong reason).
- ❌ Catching the new `XMLParsingError` and reporting a clean snapshot anyway.

---

## RH-05 (MUST) — Make broker visibility timeout exceed the longest task limit

- **Boundary:** Celery/Redis · **Requirement:** REQ-CEL-1 · **Finding:** F-CELERY-01
  · **Field:** 14 · **Effort:** ~2h

**Goal:** A long-running task is never redelivered and re-executed while it is
still running.

**Confirmed defect:** `app/core/celery_app.py:45-68` does not set
`broker_transport_options`, so the Redis default visibility timeout (3600s)
applies, while `validate_archive` runs up to `task_time_limit=7500s`
(`validator_tasks.py:31`); with `task_acks_late=True` (`celery_app.py:53`) a >1h
task is redelivered.

**Minimal fix:** In the `celery_app.conf.update(...)` block, set
`broker_transport_options={"visibility_timeout": 8100}` (> the 7500s longest hard
limit, with margin). Derive the value from the longest configured task limit in a
comment so the two never silently drift.

**RED test** — `tests/test_celery_config.py::test_visibility_timeout_exceeds_longest_task_limit`:
`assert celery_app.conf.broker_transport_options.get("visibility_timeout", 3600) > 7500`.
**Fails today** (`{}` → `.get(...,3600) == 3600`, and `3600 > 7500` is false).

**Implementation checklist:**
- [ ] Add `broker_transport_options={"visibility_timeout": 8100}` to
  `celery_app.conf.update(...)` (`celery_app.py:45-68`).
- [ ] Add a comment tying 8100 to `validate_archive`'s 7500s hard limit.
- [ ] Write the RED test; fail → fix → pass.

**Success criteria:**
- [ ] `test_visibility_timeout_exceeds_longest_task_limit` passes; shown failing first.
- [ ] The existing `test_celery_config.py` assertions still pass.
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — future task limits:* if a task later raises its hard limit above 8100s,
  this setting must rise too; the comment + a test asserting `> longest limit`
  guards it (consider asserting against the actual max of the configured limits).
- *Dependency failure:* purely a config value; no runtime dependency.
- *Reference:* the existing `conf.update` block.

**Anti-patterns:**
- ❌ Hardcoding 8100 with no link to the task limit it must exceed.
- ❌ Asserting the literal 8100 in the test instead of the `> 7500` relationship.

---

## RH-06 (MUST) — Make snapshot insertion idempotent under redelivery

- **Boundary:** Celery/Redis · **Requirement:** REQ-CEL-3 ·
  **Findings:** F-CELERY-03 / F-SNAP-03 · **Field:** 10 · **Effort:** ~8h
  (includes a migration)

**Goal:** A redelivered `collect_single_archive_snapshot` (acks_late crash/lost or
visibility-timeout redelivery) does not create a duplicate snapshot row for the
same archive on the same calendar day.

**Confirmed defect:** `app/tasks/snapshot_tasks.py:326-333` unconditionally
`db.add`/`commit`s an `ArchiveSnapshotModel`; the model has indexes but **no**
uniqueness constraint (`app/models/archive_snapshot.py:52-57`). Under
`task_acks_late` + `task_reject_on_worker_lost` a redelivery double-inserts. (The
bulk task `collect_archive_snapshots` shares the insert pattern.)

**Minimal fix:** Add a deterministic uniqueness guard on `(archive_id, day)` and
make the insert tolerate a conflict:
- **DB-enforced (preferred):** an Alembic migration adding a **functional unique
  index** `UNIQUE (archive_id, date(recorded_at))` — note a plain column-tuple
  `UniqueConstraint` cannot express `date(recorded_at)`; use
  `op.create_index(..., postgresql_*)` with the `func.date` expression per
  `docs/DATABASE_MIGRATION_GUIDE.md`.
- In `collect_single_archive_snapshot`, before inserting, check for today's
  snapshot for this `archive_id` (mirror the change-detection short-circuit that
  already exists), and/or catch `IntegrityError` → treat as "already recorded"
  (return status unchanged). Apply the same guard to the bulk task.

**RED test** — `tests/test_snapshot_idempotency.py::test_single_snapshot_redelivery_inserts_once`
(testcontainers): seed one `isLatest` `XmlArchiveModel`; monkeypatch
`parse_archive_xml` to return `ArchiveParseResult(unit_count=5,
http_metadata=HttpMetadata(etag=None, last_modified=None))` (so change-detection
reports "changed" on the second run — `etag=None` triggers the no-previous-metadata
path); call `collect_single_archive_snapshot(archive_id)` twice; assert exactly
**one** `ArchiveSnapshotModel` row. **Fails today** (two rows). The stub MUST use
`etag=None` — a stable ETag would hit the "unchanged" short-circuit and pass
tautologically.

**Implementation checklist:**
- [ ] Alembic migration: functional unique index on `(archive_id, date(recorded_at))`
  (`docs/DATABASE_MIGRATION_GUIDE.md`).
- [ ] Add `__table_args__` index/constraint to `ArchiveSnapshotModel` to match.
- [ ] Add check-before-insert and/or `IntegrityError` handling in
  `collect_single_archive_snapshot` and `collect_archive_snapshots`.
- [ ] Write the RED test (no-ETag stub, run twice); fail → fix → pass.

**Success criteria:**
- [ ] `test_single_snapshot_redelivery_inserts_once` passes; shown failing first.
- [ ] A genuinely changed archive on a **different day** still inserts a new row —
  add `test_snapshot_new_day_inserts_again`.
- [ ] The migration applies and reverts cleanly (`alembic upgrade head` /
  `downgrade -1` in a testcontainer or the dev DB).
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — two runs same day, changed content:* business decision — one snapshot
  per archive per day (the unique index encodes this); if intra-day change history
  is wanted, key on a coarser idempotency token instead and record the decision.
- *Edge — existing duplicate rows:* the migration may fail if duplicates already
  exist; the migration MUST de-duplicate (keep latest per `archive_id, day`) before
  creating the unique index, or the upgrade aborts.
- *Concurrency:* two workers racing the same archive/day — the DB unique index is
  the authoritative guard; the Python check is an optimization (catch
  `IntegrityError`).
- *Reference:* `validate_archive`'s `task_id`-based retry dedup
  (`validator_tasks.py:82-95`) is the in-repo idempotency pattern.

**Anti-patterns:**
- ❌ A plain `UniqueConstraint("archive_id", "recorded_at")` (the timestamp differs
  by milliseconds — never collides; useless).
- ❌ A check-before-insert with no DB constraint (loses the race under concurrency).
- ❌ A RED test with a stable ETag (passes via the unchanged short-circuit — tautological).
- ❌ Creating the unique index without de-duplicating existing rows (migration aborts in prod).

---

## RH-07 (MUST) — Replace the phantom DLQ config with a real dead-letter sink

- **Boundary:** Celery/Redis · **Requirement:** REQ-CEL-2 · **Finding:** F-CELERY-02
  · **Field:** 14 · **Effort:** ~8h (includes a migration)

**Goal:** A task that exhausts retries or is rejected has its payload persisted to
a durable, redrivable store — not merely logged then acked and dropped — and the
config carries no setting that silently does nothing.

**Confirmed defect:** `app/core/celery_app.py:62-67` sets
`task_dead_letter_queue_config={...}`, which is **not** a real Celery setting (no
such key in Celery's defaults); it is stored inertly. The only "DLQ" behaviour is
a `logger.critical` in the task base class.

**Minimal fix (two parts):**
1. Remove the phantom `task_dead_letter_queue_config` key.
2. Implement a real give-up sink: in the task base class `on_failure` (final
   failure / give-up path), persist `{task_id, task_name, args, kwargs, last
   exception, timestamp}` to a durable store — a new `failed_tasks` DB table
   (Alembic migration) is preferred over a Redis list for redrivability. Expose a
   minimal redrive entry point (a function that re-submits a stored payload).

**RED test** — two tests in `tests/test_dead_letter.py`:
- `test_no_phantom_dead_letter_setting`: `assert
  "task_dead_letter_queue_config" not in celery_app.conf.table()` — **fails today**
  (the unknown key IS present in `conf.table()`).
- `test_failed_task_payload_is_persisted`: invoke the base-class `on_failure`
  (or drive a task to final failure with a stubbed store) and assert one
  `failed_tasks` record with the task name + args + exception. **Fails today**
  (no store exists).

**Implementation checklist:**
- [ ] Delete `task_dead_letter_queue_config` from `celery_app.py:62-67`.
- [ ] Alembic migration: `failed_tasks` table.
- [ ] Persist the failed payload in the task base class final-failure path
  (`app/core/task_base.py`).
- [ ] Add a `redrive(task_id)` helper.
- [ ] Write both RED tests; fail → fix → pass.

**Success criteria:**
- [ ] Both RED tests pass; both shown failing first.
- [ ] A successful task writes **no** `failed_tasks` row — add
  `test_successful_task_not_dead_lettered`.
- [ ] The migration applies/reverts cleanly.
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — store unavailable:* if persisting the failure itself fails, log
  loudly (do not crash the worker on the failure path); the original failure must
  still propagate.
- *Edge — huge args:* truncate/serialize args safely (a validation payload may be
  large); store a bounded JSON.
- *Concurrency:* many failures at once — the table insert must be cheap and not
  block; no global lock.
- *Reference:* the existing `LoggingTask` base (`app/core/task_base.py`) is where
  the hook lives.

**Anti-patterns:**
- ❌ Leaving the phantom key "because it's harmless" (it misleads the next reader).
- ❌ A Redis-list sink with no redrive path (not redrivable = not a real DLQ).
- ❌ Letting a dead-letter write failure mask or replace the original exception.

---

## RH-08 (SHOULD) — Rate-limit the public statistics endpoints

- **Boundary:** inbound routes · **Requirement:** REQ-ROUTE-2 ·
  **Finding:** F-RATELIMIT-01 · **Field:** 12 · **Effort:** ~3h

**Goal:** Public, unauthenticated endpoints that run non-trivial DB reads shed
excess load with 429 instead of letting the DB pool saturate.

**Confirmed defect:** `app/api/v1/endpoints/validation_stats.py:77-80`
(`POST /validation-stats`, a batched read of ≤500 summaries) and the public
`GET /api/v1/statistics/*` reads in `snapshots.py` carry no `@limiter.limit`,
while `login`/`csrf`/`harvest` do. The slowapi limiter + 429 handler are wired
(`main.py:68-69`).

**Minimal fix:** Add `request: Request` to each public handler and decorate with a
new `settings.PUBLIC_STATS_RATE_LIMIT` (e.g. `"60/minute"` per IP). The existing
`RateLimitExceeded` handler returns 429.

**RED test** — `tests/test_public_rate_limit.py::test_public_validation_stats_is_rate_limited`:
with `TestClient(app)` from one client host, issue N+1 `POST /api/v1/validation-stats`
beyond the configured limit; assert at least one response is 429. **Fails today**
(no limit → all succeed). Note: the existing harvest test rotates client hosts
*specifically to avoid* tripping its limit — proof slowapi is live in tests and not
disabled by a flag.

**Implementation checklist:**
- [ ] Add `PUBLIC_STATS_RATE_LIMIT: str = "60/minute"` to `app/core/config.py`.
- [ ] Decorate `POST /validation-stats` and the six public `/statistics/*` reads
  with `@limiter.limit(settings.PUBLIC_STATS_RATE_LIMIT)`, adding `request: Request`.
- [ ] Write the RED test (N+1 from one host); fail → fix → pass.

**Success criteria:**
- [ ] `test_public_validation_stats_is_rate_limited` passes; shown failing first.
- [ ] A single call still returns its normal 2xx — `test_public_stats_single_call_ok`.
- [ ] Full suite green; ruff check + format clean (the existing harvest rate-limit
  test still passes — confirm no cross-test limiter-state bleed; reset limiter
  storage in the fixture if needed).

**Key considerations (SRE review):**
- *Edge — shared limiter state across tests:* slowapi keeps per-IP counters; tests
  must rotate client host or reset storage to stay independent (follow the harvest
  test's approach).
- *Edge — legit burst:* 60/min/IP is generous for a dashboard; make it a setting
  so ops can tune.
- *Reference:* the `@limiter.limit` usage on the harvest endpoint
  (`app/api/v1/endpoints/harvest.py`).

**Anti-patterns:**
- ❌ Applying the limit only to `/validation-stats` and forgetting the
  `/statistics/*` reads (same defect class).
- ❌ A flaky test that depends on wall-clock windows (use a tight burst within one window).

---

## RH-09 (SHOULD) — Retry only transient task failures

- **Boundary:** Celery/Redis · **Requirement:** REQ-CEL-4 · **Finding:** F-CELERY-04
  · **Field:** 9 · **Effort:** ~3h

**Goal:** A deterministic failure (e.g. archive-not-found) is not retried; the
retry budget and backoff window are spent only on transient errors.

**Confirmed defect:** `app/tasks/validator_tasks.py:30` declares
`autoretry_for=(Exception,)`, but `:69-70` raises
`ValueError("Archive with ID … not found")` for a missing archive — missing on
every retry. (Backoff/jitter are already capped — `retry_backoff_max=120`,
`retry_jitter=True` — so this is purely about *which* errors retry.)

**Minimal fix:** Narrow `autoretry_for` to transient classes (e.g.
`(OperationalError, ConnectionError, TimeoutError)`) and raise a non-retriable
error for deterministic failures — either a dedicated `PermanentTaskError`
excluded from autoretry, or use Celery's `dont_autoretry_for`, or raise
`Reject(requeue=False)`/`Ignore()` for the not-found case.

**RED test** — `tests/test_validator_retry.py::test_archive_not_found_is_not_retried`:
with no archive row seeded and `SessionLocal` patched to the test session factory,
spy on `validate_archive.retry` (`with patch.object(validate_archive, "retry") as
retry_spy`) and call the task expecting the not-found error; assert
`retry_spy.call_count == 0`. **Fails today** (Celery's autoretry invokes
`retry`, so `call_count > 0`).

**Implementation checklist:**
- [ ] Replace `autoretry_for=(Exception,)` with a transient-only tuple in the
  `@shared_task` decorator (`validator_tasks.py:20-32`).
- [ ] Make the archive-not-found path raise a non-retriable error
  (`validator_tasks.py:69-70`).
- [ ] Write the RED test (retry spy); fail → fix → pass.

**Success criteria:**
- [ ] `test_archive_not_found_is_not_retried` passes; shown failing first.
- [ ] A transient error still retries — `test_transient_error_is_retried` (raise a
  patched `OperationalError`, assert `retry` invoked).
- [ ] The existing `validate_archive` tests stay green (retry-dedup behaviour at
  `:82-95` unaffected).
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — SoftTimeLimitExceeded:* Celery has no `SoftTimeLimitExceeded`-exclusion
  syntax inside `autoretry_for`; use a typed permanent-error or `dont_autoretry_for`
  — do not write an exclusion that Celery ignores.
- *Edge — validator-internal parse error:* a malformed archive is deterministic
  too; classify it non-retriable as well (note it).
- *Reference:* the decorator at `validator_tasks.py:20-32`.

**Anti-patterns:**
- ❌ A `SoftTimeLimitExceeded` "exclusion" string that Celery silently ignores.
- ❌ Catching the not-found error and returning success (hides a real problem).
- ❌ A test that asserts on retry *count number* rather than `== 0` (brittle).

---

## RH-10 (SHOULD) — Don't report a clean snapshot when a ZIP entry fails to parse

- **Boundary:** outbound HTTP · **Requirement:** REQ-OUT-2 · **Finding:** F-SNAP-04
  · **Field:** 5 · **Effort:** ~3h

**Goal:** A multi-entry archive where some XML entries fail to parse is not
silently reported as a clean, complete snapshot.

**Confirmed defect:** `app/tasks/snapshot_tasks.py:194-202` catches `ET.ParseError`
per ZIP entry, logs, and `continue`s, then returns the partial `total_unit_count`
as a successful `ArchiveParseResult` (`:214-217`).

**Minimal fix (choose one, document it):** Prefer **fail-fast** — collect failed
entry names and, if any, `raise XMLParsingError("entries failed to parse: …")`,
symmetric with the already-correct whole-file path (`:221-222`). (Alternative:
surface an explicit `parse_errors`/`incomplete` indicator on `ArchiveParseResult`
and persist it; only if partial counts are a product requirement.)

**RED test** — `tests/test_snapshot_zip_partial.py::test_zip_with_unparseable_entry_not_clean`:
monkeypatch `requests.get` to stream an in-memory ZIP (first bytes `PK`) with two
entries — `good.xml` = `<root><Unit/><Unit/></root>` and `bad.xml` =
`<root><Unit></root>` (mismatched tag); call `parse_archive_xml(url)` and assert it
**either** raises `XMLParsingError` **or** returns a result whose incompleteness
indicator is truthy. **Fails today** (returns a clean partial count, no error/flag).

**Implementation checklist:**
- [ ] Collect failed entry names in the ZIP loop (`snapshot_tasks.py:194-202`).
- [ ] After the loop, raise `XMLParsingError` listing them (or set the indicator).
- [ ] If using the indicator route, add the field to `ArchiveParseResult` and
  persist it on the snapshot.
- [ ] Write the RED test (good+bad ZIP); fail → fix → pass.

**Success criteria:**
- [ ] `test_zip_with_unparseable_entry_not_clean` passes; shown failing first.
- [ ] A ZIP whose entries **all** parse still returns the correct count —
  `test_zip_all_entries_parse_ok`.
- [ ] Full suite green; ruff check + format clean.
- [ ] The chosen stance (fail-fast vs flag) is documented in the function docstring.

**Key considerations (SRE review):**
- *Edge — all entries fail:* already raises `XMLParsingError("No XML files…")` only
  when none exist; ensure the all-fail case also raises, not returns 0.
- *Edge — `__MACOSX/` noise:* already filtered (`:188`); keep that filter.
- *Reference:* the whole-file path (`snapshot_tasks.py:221-222`) is the symmetric
  fail-fast model.

**Anti-patterns:**
- ❌ Keeping the `continue` and returning a partial count as success.
- ❌ A RED test asserting only `raises` when the multi-root padding itself throws
  for the wrong reason (use well-formed `good.xml` + cleanly-malformed `bad.xml`).

---

## RH-11 (SHOULD) — Run subprocesses without a shell

- **Boundary:** subprocess · **Requirement:** REQ-SUB-1 · **Finding:** F-MTASKS-01
  · **Field:** 1 · **Effort:** ~3h

**Goal:** Operator-supplied `task_id` can never be re-interpreted by a shell —
removing the command-injection bug class.

**Confirmed defect:** `app/utils/manage_tasks.py:18-23` runs
`subprocess.run(cmd, shell=True, …)` where `cmd` is an f-string; `cancel_task`/
`cancel_all_tasks` interpolate `task_id` (`:207, :213, :259, :264`).

**Minimal fix:** Change `run_celery_command` to accept the celery args as a **list**
and call `subprocess.run([...], shell=False, …)`:
`base = ["celery", "-A", "app.core.celery_app", *args]` (append `"--json"` when
`json_output`). Callers pass argument lists, e.g.
`run_celery_command(["control", "terminate", task_id])`, so `task_id` is one argv
element, never parsed by a shell. Preserve the existing return contract
(`{"output", "error"}` / parsed JSON / `None`) so `tests/test_manage_tasks.py`
(which patches `manage_tasks.subprocess.run`) stays valid.

**RED test** — `tests/test_manage_tasks.py::test_cancel_task_uses_argv_not_shell`:
patch `manage_tasks.subprocess.run` with a spy returning a stub proc; call
`cancel_task("$(touch /tmp/pwn)", force_terminate=False)`; assert
`spy.call_args.kwargs.get("shell") is not True` **and** `spy.call_args.args[0]` is
a list/tuple containing the literal element `"$(touch /tmp/pwn)"` unsplit. **Fails
today** (`shell=True`, `args[0]` is a single interpolated string).

**Implementation checklist:**
- [ ] Refactor `run_celery_command(command, json_output)` →
  `run_celery_command(args: list[str], json_output=True)` with `shell=False`.
- [ ] Update all call sites (`:84, :157, :181, :207, :213, :227, :240, :259, :264,
  :282, :297`) to pass lists.
- [ ] Keep the static `docker logs …` call (`:131-137`) as-is or convert too (it is
  static, lower priority; note the decision).
- [ ] Write the RED test (injection string spy); fail → fix → pass.

**Success criteria:**
- [ ] `test_cancel_task_uses_argv_not_shell` passes; shown failing first.
- [ ] The existing `test_manage_tasks.py` cases still pass (return contract intact).
- [ ] `grep -n "shell=True" app/utils/manage_tasks.py` shows the celery-control
  path no longer uses it.
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — `--json` flag placement:* append it as its own list element, not string-concatenated.
- *Edge — empty/whitespace task_id:* with list-argv it is a harmless single arg;
  celery rejects it — fine.
- *Reference:* `es_gateway` parses inputs into safe typed values at the boundary.

**Anti-patterns:**
- ❌ Keeping `shell=True` and trying to "escape" `task_id` (use list-argv instead).
- ❌ Breaking the `{"output","error"}`/`None` return contract the tests depend on.

---

## RH-12 (SHOULD) — Treat a non-zero subprocess exit as failure

- **Boundary:** subprocess · **Requirement:** REQ-SUB-2 · **Finding:** F-MTASKS-02
  · **Field:** 5 · **Effort:** ~2h

**Goal:** A failed celery control command is reported to the operator as a failure,
not a success.

**Confirmed defect:** `app/utils/manage_tasks.py:33` returns
`{"output": result.stdout, "error": result.stderr}` for the non-JSON path without
checking `result.returncode`; the dict is always truthy, so `cancel_task`'s
`if result:` prints "✅ … revoked" even on a non-zero celery exit.

**Minimal fix:** In `run_celery_command`, after `subprocess.run`, add
`if result.returncode != 0: return None` (so callers' `if not result:` failure path
fires "❌ Failed to cancel task"). Gate the JSON branch on `returncode` too before
`json.loads`. This mirrors the JSON path that already returns `None` on empty
stdout (`:30-31`) and the `es_gateway` discipline of turning a down-path into a
typed/None signal.

**RED test** — `tests/test_manage_tasks.py::test_cancel_task_reports_failure_on_nonzero_exit`:
patch `manage_tasks.subprocess.run` to return
`SimpleNamespace(stdout="", stderr="Error: task not found", returncode=1)`; call
`cancel_task("abc")`; capture stdout and assert it contains "❌ Failed to cancel
task" and **not** "✅". **Fails today** (the always-truthy dict makes the success
branch fire — confirmed by direct execution).

**Implementation checklist:**
- [ ] Add `if result.returncode != 0: return None` in `run_celery_command` (after
  `subprocess.run`, before the non-JSON return at `:33`).
- [ ] Gate the JSON branch on `returncode` before `json.loads` (`:30-32`).
- [ ] Write the RED test (`returncode=1`, capsys); fail → fix → pass.

**Success criteria:**
- [ ] `test_cancel_task_reports_failure_on_nonzero_exit` passes; shown failing first.
- [ ] A zero-exit command still reports success — `test_cancel_task_success_on_zero_exit`.
- [ ] The existing `test_manage_tasks.py` cases (which assume the current contract)
  are updated to the corrected contract and pass.
- [ ] Full suite green; ruff check + format clean.

**Key considerations (SRE review):**
- *Edge — zero exit, stderr-only warnings:* returncode 0 with stderr text is still
  success; key off `returncode`, not stderr presence.
- *Edge — interaction with RH-11:* if RH-11 lands first, this change applies to the
  list-argv version; both touch `run_celery_command` — sequence RH-11 then RH-12 to
  avoid a conflict, or fold the returncode check in during RH-11 (note in PR).
- *Reference:* the JSON path's existing `None`-on-empty-stdout degrade (`:30-31`).

**Anti-patterns:**
- ❌ Keying success off stdout/stderr presence instead of `returncode`.
- ❌ Printing success and *also* the error (mixed signal to the operator).

---

## Summary

| ID | Lvl | Boundary | Defect (one line) | Req | RED test |
|----|-----|----------|-------------------|-----|----------|
| RH-01 | MUST | postgres | no statement/lock timeout on either engine | REQ-PG-1 | test_slow_query_aborts_within_timeout |
| RH-02 | MUST | routes | no request body-size limit | REQ-ROUTE-1 | test_oversized_body_rejected_with_413 |
| RH-03 | MUST | postgres | unbounded `.all()` over validation jobs on public path | REQ-PG-2 | test_quality_metrics_does_not_materialize_all_jobs |
| RH-04 | MUST | outbound_http | streamed archive body unbounded | REQ-OUT-1 | test_oversized_archive_stream_aborts |
| RH-05 | MUST | celery_redis | visibility_timeout (3600s) < longest task (7500s) | REQ-CEL-1 | test_visibility_timeout_exceeds_longest_task_limit |
| RH-06 | MUST | celery_redis | snapshot insert not idempotent under acks_late | REQ-CEL-3 | test_single_snapshot_redelivery_inserts_once |
| RH-07 | MUST | celery_redis | phantom DLQ config; no real dead-letter | REQ-CEL-2 | test_no_phantom_dead_letter_setting |
| RH-08 | SHOULD | routes | public stats endpoints unthrottled | REQ-ROUTE-2 | test_public_validation_stats_is_rate_limited |
| RH-09 | SHOULD | celery_redis | autoretry retries non-retriable errors | REQ-CEL-4 | test_archive_not_found_is_not_retried |
| RH-10 | SHOULD | outbound_http | ZIP partial-parse reported as clean success | REQ-OUT-2 | test_zip_with_unparseable_entry_not_clean |
| RH-11 | SHOULD | subprocess | shell=True with interpolated task_id | REQ-SUB-1 | test_cancel_task_uses_argv_not_shell |
| RH-12 | SHOULD | subprocess | non-zero child exit reported as success | REQ-SUB-2 | test_cancel_task_reports_failure_on_nonzero_exit |

Baseline at branch point (commit `6976091`): `make test` 574 passed (with
`PYTHONPATH=validator/src`), `ruff check app/` clean. Every item above must keep
that suite green while adding its own RED→green regression lock.
