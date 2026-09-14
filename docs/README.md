# Aggregator documentation

Router index for `docs/`. Every document has one home; find it by the question you're
asking. `CLAUDE.md` in the repo root stays a thin router into this folder.

## Start here

| I want to… | Read |
|---|---|
| Understand how the system is put together | [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) |
| Deploy it | [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) |
| Fix something that's broken | [TROUBLESHOOTING_RUNBOOK.md](./TROUBLESHOOTING_RUNBOOK.md) |
| Change the database schema | [DATABASE_MIGRATION_GUIDE.md](./DATABASE_MIGRATION_GUIDE.md) |
| Look up a table or column | [DATABASE_MODEL_REFERENCE.md](./DATABASE_MODEL_REFERENCE.md) |

## Reference — facts to look up while working

- [DATABASE_MODEL_REFERENCE.md](./DATABASE_MODEL_REFERENCE.md) — tables, columns, relationships
- [API_DOCUMENTATION_STANDARDS.md](./API_DOCUMENTATION_STANDARDS.md) — how endpoints are documented
- [API_BEST_PRACTICES_STANDARDS.md](./API_BEST_PRACTICES_STANDARDS.md) — pagination, filtering, sorting, error shape
- [DESIGN_SYSTEM_DOCUMENTATION.md](./DESIGN_SYSTEM_DOCUMENTATION.md) — frontend design tokens and components

## How-to — steps toward a goal

- [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- [DATABASE_MIGRATION_GUIDE.md](./DATABASE_MIGRATION_GUIDE.md)
- [TROUBLESHOOTING_RUNBOOK.md](./TROUBLESHOOTING_RUNBOOK.md)

## Explanation — why things are the way they are

- [ARCHITECTURE_OVERVIEW.md](./ARCHITECTURE_OVERVIEW.md) — services, boundaries, data flow
- [HARVEST_STATUS_INDICATOR.md](./HARVEST_STATUS_INDICATOR.md) — what the harvest-status badge means
- [SKELETON_LOADING.md](./SKELETON_LOADING.md) — the reserve-space + skeleton pattern used to keep
  layout shift at zero

## Specs and initiatives

| Initiative | Status |
|---|---|
| [statistics-harmonization/](./statistics-harmonization/) — language, arithmetic and dead-surface cleanup of the statistics core | **Shipped** 2026-06-26 (`6846e92`) |
| [resilience-backend/](./resilience-backend/) — bounding queries, uploads, tasks and the DLQ · `spec.md` (target) · `roadmap.md` (RH-01…) | **Active** — roadmap checkboxes are not maintained; read the code, not the ticks |
| [resilience-frontend/](./resilience-frontend/) — timeouts, abort handling and typed errors in the client · `spec.md` (target) · `roadmap.md` (FR-01…) | **Active** — same caveat |
| [archive/DCAT_V3_IMPLEMENTATION_PRD.md](./archive/DCAT_V3_IMPLEMENTATION_PRD.md) | Superseded 2026-06-24 — archived, direction moved to the external `nexus` catalog |
| `statistics-reliability` — provable curves, self-healing snapshots, honest charts | **Status unknown** — no spec in this folder, no commits on `master`, and the `.omc/runs/` working area it was drafted in is no longer present. Promote a spec here or drop this row. |

## Conventions

- A doc answers **one** reader question. If it drifts between "how do I" and "why is it",
  split it rather than letting it grow.
- **An initiative is a folder**, not a prefix: `<initiative>/` holding `spec.md`,
  `roadmap.md`, `brief.md`, `discovery.md`, `prd.md` as the work needs. Sibling
  references inside it are bare (`spec.md`), so the folder can be renamed freely.
- Mark a spec whose work has landed with a `> **Status — shipped <date>.**` banner at the
  top and `status: final` in its frontmatter; keep it for the design rationale rather than
  deleting it.
- Specs and roadmaps carry frontmatter: `title`, `status` (`draft | active | final`),
  `created`, `updated`, `last_reviewed`. `last_reviewed` is what the staleness
  scanner reads — bump it when you have actually re-read the doc, not when you edit it.
- **Never delete a doc.** When it is superseded or abandoned, leave a stub at its
  path and move the body to [archive/](./archive/) — links this repo cannot see
  (CLAUDE.md, code comments, the wiki) must keep resolving. Merely out of date is
  not a reason to archive; refresh `last_reviewed` instead.
- **Commands live in one place.** `CLAUDE.md` owns test, lint and format commands and
  their baselines. Docs point at it rather than restating it — the copies that used to
  sit in the resilience roadmaps both rotted while the original stayed right.
- There is currently no `docs/adr/` and no `CONTEXT.md`. When a decision needs to outlive
  the spec that made it, start `docs/adr/0001-<slug>.md`.
