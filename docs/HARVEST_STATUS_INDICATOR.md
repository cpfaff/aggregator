# Harvest-success indicator

Per-dataset, provider-facing confirmation of whether a registered dataset was **harvested
successfully into the public Elasticsearch search index** — the confirmation-loop sibling to the
harvest-**ready** flag (DASS-3610). Where harvest-ready controls *which* datasets the feed offers,
this feature reports whether a dataset actually *arrived* in the index, and how completely.

## What a provider sees

A status badge on each dataset card (beside the Validation badge), one of:

| State | Meaning |
|---|---|
| **In index** | The dataset's current-version records are present (`M units`, or `M of N` when the expected count is known), with a *last seen* date. |
| **Partially in index** | Present but `M < N` — fewer records than expected. |
| **Not yet in index** | Harvest-ready, but no current-version records found (awaiting the next nightly harvest, or panFMP reprocessing lag). |
| **Staged** | Not harvest-ready — deliberately excluded from the feed; **no index query is made**. |
| **Status unavailable** | The index could not be reached / returned `unknown` — non-blocking. |

The signal is at most one harvest cycle (~24h) old. Harvest runs nightly; the aggregator reads the
index **live**, mirroring the existing live validation-status badge.

## Backend architecture

The aggregator **pulls** from the index — there are **no harvester changes**, no new DB column, no
Alembic migration, and no Celery task. The index itself is the source of truth, read on request.

- **`EsGateway`** (`app/services/es_gateway.py`) — the single home for all Elasticsearch
  wire-details (base URL `http://index:9200`, index `portals_v1`, doc type `pansimple`, the term/sort
  field names, the URN scheme, optional env-configurable auth, a bounded timeout). Built on the
  existing `httpx` dependency (not `elasticsearch-py`). Two operations: a term `_count` and a 1-hit
  `_search` for the last-seen datestamp. Any transport failure / non-2xx / unparseable body becomes a
  typed `EsUnavailable` — **never** a guessed presence. This is the one interface every consumer
  mocks; no live ES in the unit suite.
- **`HarvestStatusService`** (`app/services/harvest_status_service.py`) — derives the dataset's
  index identity, queries the gateway, and assembles the status. Takes an injected
  `unit_count_provider` so the (sync-session) snapshot count never executes inside the async session
  (avoids `MissingGreenlet`).
- **Endpoint** `GET /api/v1/datasets/{dataset_id}/harvest-status` (`app/api/v1/endpoints/harvest_status.py`)
  — authenticated (`get_current_user`), returns the response model. It fetches the expected count N
  off the event loop via `run_in_threadpool(SnapshotService(sync_db).get_dataset_unit_count, …)` and
  hands the result to the service as a constant closure.

### Response contract

```
dataset_id:            int
is_harvest_ready:      bool           # echoed so the UI renders "staged" without a 2nd call
harvest_status:        str-enum       # staged | not_in_index | partial | in_index | unknown
units_in_index:        int | null     # M (units present; dataset-level doc excluded)
units_expected:        int | null     # N (snapshot unit_count; null when no snapshot yet)
last_seen_in_index_at: datetime|null  # ISO-8601
index_checked_at:      datetime       # ISO-8601, tz-aware
```

### The dataset → index join (proven, not assumed)

The aggregator derives the dataset-level URN entirely from data it already holds:

```
urn:gfbio.org:abcd:<provider_id>_<dataset_id>_<latest_archive_id>
```

`latest_archive_id` = the `xmlArchives` row with `isLatest` true (deterministic `max(id)` tie-break
for the zero/multiple-flagged anomaly). The harvester writes this same string as the
`abcdDatasetIdentifier` keyword on every `pansimple` doc (dataset doc + one per `<Unit>`), so:

- **presence** = term `_count` on `abcdDatasetIdentifier` ≥ 1;
- **M (units present)** = `count − 1` (the dataset-level doc is excluded);
- **field path** = the **plain** `abcdDatasetIdentifier` (the `.keyword` sub-field does **not** exist).

This was verified against a real harvested document on the localhost stack (T-5 spike): composed URN
`urn:gfbio.org:abcd:1_5_1` → `_count` 281 (1 dataset doc + 280 unit docs ⇒ M = 280, matching 280
`<Unit>`s in the source XML); a non-existent archive id → 0. `gfbio-abcd-push` and `portals` are
filtered aliases over the same physical index `portals_v1`.

### Expected count N

N (expected units) comes from the existing **snapshot** subsystem — `ArchiveSnapshotModel.unit_count`
(it counts `<Unit>` elements, the same definition the harvester emits docs from), **not** the
validator's file count. When no snapshot exists yet, N is `null` and the badge degrades to "M units"
(still per-dataset). State mapping: `present & M<N → partial`; `present & (M≥N or N null) → in_index`;
`harvest-ready & M=0 → not_in_index`; gateway `EsUnavailable → unknown`; `not harvest-ready → staged`
(no query).

## Frontend

`DatasetCard.js` renders the badge via **SWR** (keyed by dataset id) — per-key cache, request
de-duplication, background revalidation, no polling. A `null` SWR key (when `isHarvestReady === false`,
strictly, or no id) makes the **staged** path genuinely fetch-free. `unknown`/error renders
"Status unavailable" without breaking the card. The existing Validation fetch is untouched.

## Deliberate boundaries

- **No degrade fallback of any kind.** Per-dataset accuracy is a hard requirement: if the join could
  not be proven, the run was to hard-stop for a rethink rather than fall back to provider-level
  presence. (It was proven — see above.)
- **No harvester / panFMP / feed / public-search changes.**
- **Non-ABCD harvest paths** (GBIF, ENA, PANGAEA) use different id schemes and are **out of scope**.
- **Provider-page scale:** SWR covers in-session churn; the first-load fan-out (~100 distinct cards →
  ~100 requests) is left to a future **backend batch endpoint**, built only if the page proves slow.

## Tests

- `tests/test_es_gateway.py` — gateway parse + every failure→`EsUnavailable` path (httpx mocked).
- `tests/test_harvest_status_service.py` — every state, the `isLatest` tie-break, the staged
  short-circuit (gateway not called), N-null degrade, against the real async `db_session` with a
  mocked gateway.
- `tests/test_harvest_status_endpoint.py` — thin HTTP contract (service mocked), route + auth + 422.
- `frontend/.../__tests__/DatasetCard.test.js` — every badge state + the no-fetch staged path, inside
  an isolated `SWRConfig`.
