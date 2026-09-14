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

Feature specs live here once they are worth keeping. **In-flight** run artifacts
(`brief.md` / `discovery.md` / `prd.md`) live in `.omc/runs/<run-id>/`, which is excluded
from git via `.git/info/exclude` — they are local-only until deliberately promoted here.

| Initiative | Status |
|---|---|
| [statistics-harmonization/](./statistics-harmonization/) — language, arithmetic and dead-surface cleanup of the statistics core | **Shipped** 2026-06-26 (`6846e92`) |
| [resilience-backend/](./resilience-backend/) — `spec.md` (target) · `roadmap.md` (sequenced work) | Backend resilience |
| [resilience-frontend/](./resilience-frontend/) — `spec.md` (target) · `roadmap.md` (sequenced work) | Frontend resilience |
| [DCAT_V3_IMPLEMENTATION_PRD.md](./DCAT_V3_IMPLEMENTATION_PRD.md) | Superseded — see its status note |
| `statistics-reliability` — provable curves, self-healing snapshots, honest charts | In flight, in `.omc/runs/statistics-reliability/` |

## Conventions

- A doc answers **one** reader question. If it drifts between "how do I" and "why is it",
  split it rather than letting it grow.
- Mark a spec whose work has landed with a `> **Status — shipped <date>.**` banner at the
  top and `status: final` in its frontmatter; keep it for the design rationale rather than
  deleting it.
- There is currently no `docs/adr/` and no `CONTEXT.md`. When a decision needs to outlive
  the spec that made it, start `docs/adr/0001-<slug>.md`.
