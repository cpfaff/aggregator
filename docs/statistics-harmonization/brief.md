---
title: Statistics-Collection Harmonization & Hardening — Brief
status: draft        # draft | final
created: 2026-06-26
updated: 2026-06-26
---

# Feature brief: Statistics-Collection Harmonization & Hardening

> Scope-level framing for one initiative within the Aggregator platform. Built on
> the evidence in [`discovery.md`](./discovery.md); the detailed requirements live
> in [`prd.md`](./prd.md). This brief fixes **why / what / who** and the go/no-go —
> not acceptance criteria or design.

## Summary

The Aggregator's statistics subsystem already has a **sound collection core** — an
append-only daily snapshot per archive, a functional unique index enforcing one
snapshot per archive per day, idempotent nightly collection, and a byte-budgeted,
fail-fast parser. What sits *around* that core has drifted: there is **no single
"when was this collected" concept** (two unrelated "timeline" notions keyed on two
different timestamps), the **same computations are re-implemented up to four times**
(twice beside a canonical helper that has *zero callers*), **dead fields and a dead
task route** ship as if live, and the **frontend re-derives number/date/error
handling per call site** while emitting **three incompatible timeline payload
shapes**. This initiative harmonizes the *language and arithmetic* around the
collection core — without touching the collection core's proven behaviour, the
public API contract, or the database schema unilaterally.

## The Problem

The collection core is trustworthy; the **semantics layered on top are not
self-consistent**, and that inconsistency is now a maintenance and correctness tax.

- **When** an engineer reads or changes a statistics path, **they want** one
  authoritative definition of each concept (collection time, "latest total units",
  "now"), **so they can** change it once instead of hunting 2–4 drifted copies and
  reconciling which is canonical.
- Concretely (from `discovery.md`): "as-of" timelines key on `recorded_at` while
  "growth" timelines key on `created_at` with nothing naming the difference (F-A);
  four "now" idioms coexist next to an **unused** canonical `utc_now()` (F-B); the
  latest-per-archive total is written four times (F-C) and two near-identical
  aggregates disagree on null-vs-zero (F-D); `abcd_compliance_rate` and
  `activity_score` are always `null` but documented as metrics (F-E); a
  `statistics.*` Celery route matches no task (F-F); the API ships three timeline
  shapes, two colliding on the `data_points` key (F-L); the frontend duplicates the
  K/M ladder across four charts beside an unused helper (F-H), formats dates five
  ways (F-I), and discards the typed error fields its own client computes (F-K).

How it's coped with today: each call site copies the nearest example and the copies
slowly diverge (the chart K/M formatter already has). The cost is silent: drifted
copies, dead surface area read as live, and timeline payloads the UI parses three
different ways through one formatter that assumes they agree.

## Who It's For — and Who It's Not

**For:** the engineers who maintain and extend the Aggregator statistics subsystem
(backend snapshot/stats services + the public landing page and admin dashboard),
and reviewers who need the subsystem to be legible. Secondarily, API consumers who
benefit from one coherent timeline/timestamp/error contract.

**Not for:** the data centers (no change is asked of them — see the fixed
constraint below); end-users of the search platform (no user-facing feature);
and the *broader* codebase's timestamp hygiene beyond statistics (noted as a
follow-up, not this initiative — Q4).

## The Solution

A focused harmonization, specified in `prd.md` and delivered test-first as a
separate follow-up, that:

1. **Names one canonical "collected-at" concept** (term fixed via
   `align-the-language` in the PRD) and makes the two timeline kinds explicitly
   distinct in naming and docs.
2. **Consolidates every duplicated computation** to one home each: one
   latest-snapshot-per-archive primitive, one "now" helper (the *existing*
   `core/utils.utc_now`), one compact-number formatter, one date formatter, one
   percent helper, one typed client error shape.
3. **Removes dead surface area** (dead route; dead/`None`-only fields and dead
   `%`-change paths — resolved per the PRD's public-API decision).
4. **Pins the nightly-snapshot reliability guarantees as testable obligations**
   (idempotency, one-per-archive-per-day uniqueness, byte budget) so the proven
   behaviour can't silently regress during the consolidation.

This is a *consolidate-and-name* effort at the level of internal seams and shared
helpers — not a rewrite of collection.

## Why Now

The resilience-hardening work (`DASS-3622`) just added the canonical helpers and
seams (`core/utils.utc_now`, `parseErrorResponse`, the unique index) but **left the
old call sites in place**, so the codebase now carries *both* the canonical and the
drifted forms side by side. That is the cheapest possible moment to converge: the
target helpers already exist and are tested — the work is routing call sites to
them and deleting the duplicates, before more code copies the drifted forms.

## Success Criteria

Measurable at the implementation PR (the follow-up to this spec); `[ASSUMPTION]`
dates track that PR, which is not yet scheduled.

- **One collected-at concept:** exactly **1** canonical term defined in the glossary
  and applied across both timeline kinds; **0** undocumented timeline-timestamp
  conflations. *(by implementation-PR merge [ASSUMPTION])*
- **DRY:** the latest-per-archive total computed in **1** place (down from **4**);
  the "now" value sourced from **1** helper (`utc_now`), with **0** bare
  `datetime.utcnow`/naive-local `datetime.now()` in the statistics subsystem (down
  from 4 idioms); the compact-number ladder in **1** place (down from **5**); dates
  formatted via **1** helper path. *(by implementation-PR merge [ASSUMPTION])*
- **No dead surface:** **0** always-`null` "metric" fields and **0** dead task
  routes remaining (each removed or explicitly marked deprecated per the API
  decision). *(by implementation-PR merge [ASSUMPTION])*
- **One timeline contract:** the frontend consumes **1** timeline payload shape
  (down from **3**); the multi-provider endpoint has a real typed `response_model`
  (not `dict[str, Any]`). *(by implementation-PR merge [ASSUMPTION])*
- **Reliability locked:** the nightly-collection guarantees (idempotency,
  per-archive-per-day uniqueness, byte budget) are covered by named tests that are
  **green**, with the pre-change baseline recorded first. *(baseline before the
  first change; green at PR merge)*
- **No regressions / no scope leakage:** public API response **shapes unchanged**
  except where the PRD's explicit Q3 decision applies; DB schema unchanged; data
  centers unaffected. *(continuous)*

## Scope & Non-Goals

**In scope:** the harmonization themes F-A…F-M from `discovery.md` (naming,
DRY consolidation, dead-surface removal, one timeline/timestamp/error contract) and
the reliability-as-tests obligations, confined to the **statistics-collection
subsystem** (backend snapshot/stats service, repository, tasks, schemas, the stats
endpoints; frontend stats components + shared formatting/error utils).

**Non-goals:**

- **No archive versioning at the data centers.** *(Fixed external constraint — the
  data centers do not version archives. We design around it by persisting daily
  counts to make in-place archive growth visible; we never assume it changes.)*
- **No unilateral public-API or DB-schema change.** The PRD may *propose* contract
  changes (e.g. removing dead fields, unifying timeline shapes); it does not enact
  them — each is gated behind an explicit decision (Q3/Q5).
- **No repo-wide "now"-idiom cleanup** beyond statistics (the `failed_task` /
  `validator_tasks` / `validation` / `manage_tasks` occurrences are recorded as a
  follow-up — Q4).
- **No new statistics features**, no re-architecture of the collection core, no
  re-introduction of the removed `abcd_compliance_rate` / `activity_score` metrics.

## What's Known / What's Unknown

**Known (verified in `discovery.md`):** the solid core (append-only + unique index
+ idempotency + byte budget + fail-fast + bounded aggregates); every drift finding
with a grep-verified `path:line`; the canonical helpers already exist and are
unused.

**Unknown / to decide in the PRD:** Q1 — whether growth timelines should adopt
as-of semantics or stay creation-based (genuinely open); Q2 — naive-UTC vs
aware-UTC serialization; Q3 — remove vs deprecate the dead public fields; Q5 —
whether the two backend timeline shapes agree at the element level or the shared
formatter is mis-mapping one. The **current test baseline** is unknown — the sweep
environment could not run the suites (jest transform / missing `abcd_validator` /
Docker); it must be captured via `make test` on a provisioned host before changes.

## Risks

- **Silent behaviour change during consolidation** (e.g. null-vs-zero, F-D; the
  `integerOnly` decimal variant folded into the shared K/M helper, F-H). *Mitigation:*
  test-first; pin the empty-case and formatting contracts before merging copies.
- **Touching the public contract by accident** while unifying timeline shapes or
  removing dead fields. *Mitigation:* the non-goal + the Q3/Q5 decision gates; treat
  any response-shape change as opt-in, with a contract test.
- **Unverified baseline** masks a pre-existing failure as "introduced by the
  refactor". *Mitigation:* record `make test` green counts before the first change.
- **Parallel in-flight work** on the same files (the resilience branch is active).
  *Mitigation:* this initiative is doc-only now; implementation sequences *after*
  the resilience work lands, against a known tip.

## Recommendation — Go / No-Go

**Go**, as a **doc-first** initiative: approve this brief and the PRD, then schedule
the implementation as a separate, test-first follow-up. The bet is low-risk and
high-legibility — the consolidation targets already exist and are tested, so the
work is convergence and deletion, not new design. **No-go conditions:** if the
public API or DB schema would have to change to achieve the core themes (it does
not — those are explicitly gated), or if the test baseline cannot be established
before implementation. The decision asked of the reader: *approve the harmonization
scope and its non-goals so the PRD's obligations can be built.*
