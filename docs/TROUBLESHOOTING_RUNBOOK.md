# Troubleshooting Runbook

## Quick Diagnostics

### Check System Health

```bash
# Application health (basic)
curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

# Readiness probe (checks DB + Redis)
curl -s http://localhost:8000/api/v1/health/ready | python3 -m json.tool

# Docker service status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Worker health
make tasks-health
```

### Check Logs

```bash
make logs-backend     # Backend API logs
make logs-worker      # Celery worker logs
make logs-db          # PostgreSQL logs
make logs             # All services
```

---

## Common Issues

### Backend Won't Start

**Symptoms:** Backend container exits immediately or restarts in a loop.

**Diagnostic steps:**
```bash
docker logs <backend_container> --tail 50
```

**Possible causes:**

1. **Database not ready**
   - Check: `docker exec <db_container> pg_isready`
   - Fix: Wait for PostgreSQL to finish starting, or restart: `docker restart <db_container>`

2. **Missing environment variables**
   - Check: `docker exec <backend_container> env | grep DATABASE_URL`
   - Fix: Verify `.env` file exists and contains `DATABASE_URL` and `SYNC_DATABASE_URL`

3. **Migration not applied**
   - Check: `docker logs <backend_container> | grep -i "alembic\|migration\|error"`
   - Fix: `make migrate`

4. **Port conflict**
   - Check: `lsof -i :8000`
   - Fix: Stop the conflicting process or change the port

### Database Connection Failures

**Symptoms:** `/api/v1/health/ready` returns 503, logs show connection errors.

**Diagnostic steps:**
```bash
# Check PostgreSQL is running
docker exec <db_container> pg_isready -U ${DB_USER:-user}

# Check connection from backend
docker exec <backend_container> python -c "
from sqlalchemy import create_engine, text
import os
e = create_engine(os.environ['SYNC_DATABASE_URL'])
with e.connect() as c:
    print(c.execute(text('SELECT 1')).scalar())
"
```

**Possible causes:**

1. **PostgreSQL not running** — `docker restart <db_container>`
2. **Wrong credentials** — Verify `DB_USER`, `DB_PASSWORD`, `DB_NAME` match between `.env` and compose file
3. **Connection pool exhausted** — Check `DB_POOL_SIZE` (default 10) and `DB_MAX_OVERFLOW` (default 20). If backend is under heavy load, increase these values.

### Redis Connection Failures

**Symptoms:** Cache not working, Celery tasks not dispatching.

```bash
# Check Redis is running
docker exec <redis_container> redis-cli ping
# Expected: PONG

# Check from backend
docker exec <backend_container> python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"
```

**Fix:** `docker restart <redis_container>`

### Celery Workers Not Processing Tasks

**Symptoms:** Validation jobs or statistics collection stuck in pending state.

**Diagnostic steps:**
```bash
# Check worker health
make tasks-health

# Check running tasks
make tasks

# Check worker logs
docker logs <celery_worker_validation> --tail 50
docker logs <celery_worker_stats> --tail 50
```

**Possible causes:**

1. **Worker crashed** — `make workers-restart`
2. **Redis down** — Check Redis (see above)
3. **Task stuck** — `make tasks-cancel ID=<task_id>`
4. **All tasks stuck** — `make tasks-cancel-all` (requires confirmation)
5. **Worker unresponsive** — `make tasks-force-kill` then `make workers-restart`

### Validation Worker High Memory

**Symptoms:** Validation worker killed by OOM, container restarts.

```bash
docker stats celery_worker_validation --no-stream
```

The validation worker has a 2GB memory limit. Large XML archives can cause high memory usage.

**Mitigation:**
- The worker uses `solo` pool (single task at a time) to prevent pile-up
- If consistently hitting limits, increase `mem_limit` in docker-compose
- Consider splitting large archives

### Statistics Collection Issues

**Symptoms:** Dashboard shows stale data, snapshot timeline has gaps.

```bash
# Check status
make stats-status

# Check Celery Beat is running (scheduler)
docker logs <celery_beat_container> --tail 20
```

**Possible causes:**

1. **Celery Beat not running** — `docker restart <celery_beat_container>`
2. **Stats worker down** — `make workers-restart`
3. **Gaps in historical data** — `make stats-collect` (runs gap-filling)
4. **Today's data incomplete** — `make refresh-stats-today`

### Migration Failures

**Symptoms:** `make migrate` fails, backend won't start after code update.

```bash
# Check current migration state
docker exec <backend_container> alembic current

# Check migration history
docker exec <backend_container> alembic history --verbose
```

**Possible causes:**

1. **Database out of sync** — Run `alembic upgrade head`
2. **Conflicting migration** — Check for duplicate `down_revision` values in `alembic/versions/`
3. **Schema mismatch** — The migration expects a column/table that doesn't exist. Restore from backup: `make restore-db`, then re-apply migrations

**Recovery:**
```bash
# Restore from most recent backup
make restore-db

# Re-apply all migrations
make migrate
```

### Authentication Issues

**Symptoms:** Users cannot log in, 401 errors on API calls.

**Diagnostic steps:**
```bash
# Test login
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=<password>"
```

**Possible causes:**

1. **Wrong credentials** — Verify with `make create-admin` to reset
2. **SECRET_KEY changed** — All existing tokens are invalidated when SECRET_KEY changes. Users must re-login.
3. **Token expired** — Check `ACCESS_TOKEN_EXPIRE_MINUTES` setting
4. **CSRF token missing** — Frontend must fetch CSRF token before POST requests
5. **Rate limited** — Login is limited to 5 attempts per minute per IP

### Frontend Not Loading

**Symptoms:** Blank page, API errors in browser console.

**Diagnostic steps:**
```bash
docker logs <frontend_container> --tail 20
```

**Possible causes:**

1. **Traefik routing issue** — Check `docker logs <traefik_container>`
2. **Backend unreachable** — Frontend gets 502/503 from API calls. Check backend health.
3. **CORS misconfiguration** — Verify `ALLOWED_ORIGINS` includes the frontend URL
4. **API URL mismatch** — When using Traefik, `REACT_APP_API_URL` should be empty (Traefik routes `/api` to backend). When connecting directly, set it to `http://localhost:8000`.

---

## Maintenance Procedures

### Enable Maintenance Mode

```bash
make maintenance-on
```

This swaps Traefik routing to serve a static maintenance page while keeping database and Redis running for background tasks.

### Disable Maintenance Mode

```bash
make maintenance-off
```

### Database Backup

```bash
make backup-db
# Output: backups/db_backup_<YYYYMMDD_HHMMSS>.sql
```

### Database Restore

```bash
make restore-db
# Interactive: select from available backups
```

---

## Log Format

Backend logs are structured JSON:

```json
{
  "timestamp": "2026-02-04T10:30:00Z",
  "level": "INFO",
  "name": "app.services.validation_service",
  "message": "Validation job completed",
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Filter logs by level:
```bash
docker logs <backend_container> 2>&1 | python3 -c "
import sys, json
for line in sys.stdin:
    try:
        log = json.loads(line)
        if log.get('level') == 'ERROR':
            print(line.strip())
    except: pass
"
```

Or use `jq` if available:
```bash
docker logs <backend_container> 2>&1 | jq 'select(.level == "ERROR")'
```

---

## Escalation

If the above steps do not resolve the issue:

1. Collect relevant logs: `make logs > /tmp/aggregator-logs.txt 2>&1`
2. Check Docker resource usage: `docker stats --no-stream`
3. Check disk space: `df -h`
4. Check database size: `docker exec <db_container> psql -U user -d dbname -c "SELECT pg_size_pretty(pg_database_size('dbname'));"`
