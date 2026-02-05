# Architecture Overview

## System Overview

The GFBio Aggregator is a full-stack scientific dataset management platform that catalogs datasets, manages data providers, and provides a REST API for integration with external systems. It collects and validates ABCD XML archives from data providers, tracks biological unit counts via daily snapshots, and serves statistics through a dashboard.

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Backend API | FastAPI (async) | 0.109+ |
| ORM | SQLAlchemy 2.0+ | async via asyncpg |
| Database | PostgreSQL | 16 |
| Migrations | Alembic | 1.13+ |
| Task Queue | Celery | 5.3+ |
| Message Broker / Cache | Redis 7 | alpine |
| Frontend | React | 18.2 |
| Reverse Proxy | Traefik | v2.10 (dev) / v3.3 (prod) |
| Python Tooling | Poetry, Ruff | |
| CI/CD | GitLab CI | |

## Service Architecture

```
                    ┌─────────────┐
                    │   Traefik   │ :80/:443
                    │ (reverse    │
                    │  proxy)     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        /api/* path   / path      /maintenance
              │            │            │
     ┌────────▼──────┐ ┌───▼──────┐ ┌──▼───────────┐
     │   Backend     │ │ Frontend │ │ Maintenance   │
     │   (FastAPI)   │ │ (React)  │ │ (nginx)       │
     │   :8000       │ │ :3000    │ │ (disabled by  │
     └───┬───────┬───┘ └──────────┘ │  default)     │
         │       │                   └───────────────┘
         │       │
    ┌────▼───┐ ┌─▼──────────┐
    │ Redis  │ │ PostgreSQL │
    │ :6379  │ │ :5432      │
    └──┬─────┘ └────────────┘
       │
  ┌────▼────────────────────────────┐
  │        Celery Workers           │
  │  ┌──────────┐ ┌──────────────┐  │
  │  │ Validation│ │ Stats Worker │  │
  │  │ Worker    │ │ (light_tasks)│  │
  │  │ (heavy_   │ │ prefork pool │  │
  │  │ validation│ │ dynamic      │  │
  │  │ solo pool)│ │ concurrency) │  │
  │  └──────────┘ └──────────────┘  │
  │  ┌──────────┐                   │
  │  │  Beat    │ (scheduler)       │
  │  │  2 AM    │                   │
  │  └──────────┘                   │
  └─────────────────────────────────┘
```

## Backend Architecture

### Layered Structure

```
HTTP Request
    │
    ▼
┌─────────────────────┐
│   API Routers       │  app/api/v1/endpoints/
│   (thin handlers)   │  Route definitions, request/response mapping
└──────────┬──────────┘
           │
    ┌──────▼──────────┐
    │   Services      │  app/services/
    │   (business     │  Business logic, orchestration, validation
    │    logic)       │
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │  Repositories   │  app/repositories/
    │  (data access)  │  SQLAlchemy queries, CRUD operations
    └──────┬──────────┘
           │
    ┌──────▼──────────┐
    │   Models        │  app/models/
    │   (ORM)         │  SQLAlchemy table definitions
    └─────────────────┘
```

### Directory Layout

```
backend/
├── main.py                    # Legacy monolith (being migrated)
├── alembic/                   # Database migrations
│   ├── env.py
│   └── versions/              # Migration files
├── app/
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/     # Route handlers
│   │           ├── auth.py
│   │           ├── health.py
│   │           ├── snapshots.py
│   │           ├── tasks.py
│   │           ├── users.py
│   │           └── validators.py
│   ├── core/
│   │   ├── cache.py           # Redis cache decorators
│   │   ├── celery_app.py      # Celery configuration
│   │   ├── config.py          # Settings (env vars)
│   │   ├── logging_config.py  # Structured JSON logging
│   │   └── resource_allocation.py
│   ├── models/
│   │   ├── base.py            # TimestampMixin
│   │   ├── user.py            # UserModel
│   │   ├── provider.py        # DataProviderModel
│   │   ├── dataset.py         # DatasetModel
│   │   ├── validation.py      # ValidationJobModel
│   │   └── archive_snapshot.py # ArchiveSnapshotModel
│   ├── repositories/
│   │   ├── base.py            # BaseRepository[T] (generic CRUD)
│   │   ├── user_repository.py
│   │   ├── validation_repository.py
│   │   ├── dataset_repository.py
│   │   └── snapshot_repository.py
│   ├── schemas/               # Pydantic request/response models
│   ├── security/
│   │   ├── token.py           # JWT creation/verification
│   │   ├── password.py        # Bcrypt hashing
│   │   └── permissions.py     # RBAC
│   ├── services/
│   │   ├── user_service.py
│   │   ├── validation_service.py
│   │   ├── snapshot_service.py
│   │   └── dataset_deletion.py
│   ├── tasks/                 # Celery task definitions
│   └── utils/                 # CLI utilities
└── tests/                     # pytest test suite
```

### Key Design Decisions

**Async vs Sync Sessions**: The API uses `AsyncSession` (via asyncpg) for non-blocking request handling. The `SnapshotRepository` uses synchronous `Session` because it is consumed by both async endpoints and synchronous Celery tasks.

**Repository Pattern**: `BaseRepository[T]` provides generic CRUD using `flush()` (not `commit()`) so that services control transaction boundaries. Repositories are concrete classes, not abstract interfaces.

**Legacy Monolith**: `main.py` (1759+ lines) still houses ~30 CRUD endpoints. These are being progressively migrated to `app/api/v1/endpoints/`. Deprecated code is tagged with `TODO-REMOVE` comments linked to bd cleanup tasks.

## Data Model

```
UserModel
    username, hashed_password, provider_roles (JSON), is_global_admin, last_login

DataProviderModel ──(1:N)──▶ DatasetModel ──(1:N)──▶ XmlArchiveModel
    name, shortName,            title, source,          xml_data, isLatest,
    datacenter, url,            landing_page_url        etag, last_modified
    isDataCenter                    │
                                    ├──(1:N)──▶ UsefulLinkModel
                                    │               url, title
                                    │
                              XmlArchiveModel ──(1:N)──▶ ArchiveSnapshotModel
                                                            unit_count, recorded_at
                                                │
                                          ──(1:N)──▶ ValidationJobModel
                                                        status, valid_files,
                                                        total_files, validation_time
```

## Background Tasks

### Celery Configuration

| Queue | Worker | Pool | Purpose |
|-------|--------|------|---------|
| `heavy_validation` | celery_worker_validation | solo | XML archive validation (CPU-intensive) |
| `light_tasks` | celery_worker_stats | prefork | Statistics collection, snapshots |

### Scheduled Tasks (Celery Beat)

| Task | Schedule | Description |
|------|----------|-------------|
| `snapshots.collect_archive_snapshots` | Daily at 2:00 AM UTC | Collects unit counts from all latest archives |

### Resource Allocation

- Validation worker gets a configurable percentage of CPUs (`VALIDATOR_CPU_PERCENT`, default 75%)
- Stats worker gets remaining CPUs (`STATS_WORKER_CONCURRENCY=auto`)
- Memory limits: validation 2GB, stats 1GB

## Security

- **Authentication**: JWT tokens (HS256) with configurable expiration
- **CSRF Protection**: fastapi-csrf-protect for state-changing requests
- **Rate Limiting**: slowapi with per-endpoint limits (login: 5/min, harvest: 30/hr)
- **RBAC**: Role-based access via `provider_roles` JSON field and `is_global_admin` flag
- **Password Hashing**: bcrypt

## Observability

- **Structured Logging**: JSON format via python-json-logger with request ID correlation
- **Health Checks**: `/api/v1/health` (basic), `/api/v1/health/live` (liveness), `/api/v1/health/ready` (readiness with DB + Redis checks)
- **Cache**: Redis-backed with configurable TTL (default 300s)

## API

All endpoints are under `/api/v1/`. OpenAPI/Swagger documentation is available at `/docs` (development only).

Key endpoint groups:
- `/api/v1/auth/` — Login, token refresh, CSRF
- `/api/v1/users/` — User management (admin only)
- `/api/v1/providers/` — Data provider CRUD
- `/api/v1/datasets/` — Dataset CRUD
- `/api/v1/validators/` — Validation job submission and results
- `/api/v1/snapshots/` — Statistics and timeline data
- `/api/v1/health`, `/api/v1/health/live`, `/api/v1/health/ready` — Health endpoints
