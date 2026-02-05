# Deployment Guide

## Prerequisites

- Docker and Docker Compose
- Access to the GitLab container registry (`docker.gitlab-pe.gwdg.de/gfbio/aggregator/`)
- PostgreSQL 16, Redis 7 (provided via Docker)

## Environment Configuration

### Required Environment Variables

Create a `.env` file at the project root:

```env
# Database
DB_USER=user
DB_PASSWORD=<secure_password>
DB_NAME=dbname

# Backend
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
SYNC_DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
SECRET_KEY=<cryptographically_secure_random_string>
ACCESS_TOKEN_EXPIRE_MINUTES=30
LOG_LEVEL=INFO
ALLOWED_ORIGINS=https://your-domain.example.com
LOGIN_RATE_LIMIT=5/minute
HARVEST_RATE_LIMIT=30/hour
VALIDATOR_CPU_PERCENT=75
STATS_WORKER_CONCURRENCY=auto

# Frontend
REACT_APP_API_URL=   # Leave empty when using Traefik (routes /api to backend)

# General
ENVIRONMENT=production
```

### Backend-Specific Environment

The backend also reads from `backend/.env`. In Docker, environment variables are passed directly via the compose file, so the `.env` file is only needed for local development outside Docker.

## Development Setup

### Start Development Environment

```bash
make up
```

This starts all services using `docker-compose.merged.yml`:
- Backend: http://localhost:8000/api/v1
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Run Migrations

```bash
make migrate
```

### Create Admin User

```bash
make create-admin
# Or non-interactively:
make create-admin USERNAME=admin PASSWORD=<password>
```

### Run Tests

```bash
make test
```

### View Logs

```bash
make logs           # All services
make logs-backend   # Backend only
make logs-worker    # Celery worker
```

## Production Deployment

### Docker Compose Files

| File | Purpose |
|------|---------|
| `docker-compose.merged.yml` | Development (local build) |
| `docker-compose.prod.registry.yml` | Production (pulls from registry) |

### Start Production

```bash
make prod-up
```

### Stop Production

```bash
make prod-down
```

### Restart Production

```bash
make prod-restart
```

## CI/CD Pipeline

The GitLab CI pipeline (`.gitlab-ci.yml`) runs these stages:

1. **create_merge_request** — Auto-creates MR for feature branches
2. **tag_release_check / tag_release** — Semantic versioning on main
3. **test** — Runs pytest with testcontainers, ruff lint, ruff format check
4. **build** — Builds and pushes Docker images to GitLab registry
5. **deploy** — Automated production deployment (main branch only)

### Automated Deployment Steps

The deploy job performs these steps in order:

1. Enable maintenance mode (swap Traefik routing to maintenance page)
2. Start database and Redis, wait for health checks
3. Create timestamped database backup to `/home/gitlab-runner/db-backups/`
4. Run Alembic migrations (`alembic upgrade head`)
5. Start Traefik, wait for health
6. Start all application services with timeout waits
7. Verify all services are healthy
8. Disable maintenance mode, restore traffic
9. Final health verification

Deployment timeout: 15 minutes.

### Container Registry

Images are pushed to:
- `docker.gitlab-pe.gwdg.de/gfbio/aggregator/backend:latest`
- `docker.gitlab-pe.gwdg.de/gfbio/aggregator/frontend:latest`

## Traefik Routing

Traefik routes requests based on Docker labels:

| Path Pattern | Service | Port |
|-------------|---------|------|
| `/api/*` | Backend (FastAPI) | 8000 |
| `/` (not `/api`) | Frontend (React) | 3000 |
| `/` (maintenance mode) | Maintenance (nginx) | 80 (priority 100) |

Configuration is in `traefik/traefik.yml`. Service routing is defined via Docker labels in the compose files.

## Maintenance Mode

Enable maintenance mode to show a static page while performing updates:

```bash
make maintenance-on    # Enables maintenance page, disables backend/frontend
make maintenance-off   # Restores normal routing
```

During maintenance mode, Traefik routes all traffic to an nginx container serving a static maintenance page.

## Health Checks

All services include Docker health checks:

| Service | Health Check Command |
|---------|---------------------|
| Traefik | `traefik healthcheck --ping` |
| PostgreSQL | `pg_isready` |
| Redis | `redis-cli ping` |
| Backend | `curl http://localhost:8000/api/v1/health` |
| Celery Workers | `celery -A app.core.celery_app inspect ping` |

### Application Health Endpoints

- `GET /api/v1/health` — Basic health with database status (always responds if backend is running)
- `GET /api/v1/health/live` — Liveness probe (simple alive check)
- `GET /api/v1/health/ready` — Readiness probe (checks DB and Redis connectivity, returns 503 if dependencies are down)

## Database Backup and Restore

### Manual Backup

```bash
make backup-db
# Creates: backups/db_backup_<YYYYMMDD_HHMMSS>.sql
```

### Restore from Backup

```bash
make restore-db
# Interactive: lists available backups, prompts for selection
```

### Production Backups

The CI/CD pipeline automatically creates a backup before every deployment:
- Location: `/home/gitlab-runner/db-backups/aggregator_backup_<YYYYMMDD_HHMMSS>.sql`

## Celery Workers

### Worker Configuration

| Worker | Queue | Pool | Memory Limit | Concurrency |
|--------|-------|------|-------------|-------------|
| celery_worker_validation | heavy_validation | solo | 2GB | 1 |
| celery_worker_stats | light_tasks | prefork | 1GB | auto (remaining CPUs) |
| celery_beat | — | — | — | — (scheduler only) |

### Worker Management

```bash
make tasks            # List running background tasks
make tasks-health     # Check worker health
make workers-restart  # Restart all Celery workers
make tasks-cancel ID=<task_id>  # Cancel a specific task
```

## Statistics Collection

Daily statistics are collected automatically at 2:00 AM UTC via Celery Beat.

### Manual Collection

```bash
make stats-collect     # Full collection with gap filling
make stats-status      # Check current status
make stats-xml         # Process XML archives only
make stats-daily       # Daily statistics only
make stats-biological  # Biological units only
```

### Monitor Collection

```bash
make watch-stats       # Real-time log monitoring
```
