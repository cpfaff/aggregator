# Database Migration Guide

## Overview

The project uses [Alembic](https://alembic.sqlalchemy.org/) for database schema migrations. Alembic tracks schema changes as versioned Python scripts and applies them in sequence to bring the database to the desired state.

**Key files:**
- `backend/alembic.ini` — Alembic configuration
- `backend/alembic/env.py` — Migration environment (loads DB URL, imports models)
- `backend/alembic/versions/` — Migration scripts

## Database Connection

Alembic uses the **synchronous** database URL (`SYNC_DATABASE_URL`) because migrations run as blocking operations:

```
SYNC_DATABASE_URL=postgresql://user:password@postgres:5432/dbname
```

This is separate from the async URL used by the FastAPI application (`DATABASE_URL=postgresql+asyncpg://...`).

The connection URL is loaded in `alembic/env.py`:
```python
config.set_main_option("sqlalchemy.url", os.getenv("SYNC_DATABASE_URL"))
```

In Docker, environment variables are injected directly. For local development, `env.py` falls back to loading from `.env` files.

## Running Migrations

### Apply All Pending Migrations

```bash
# Via Makefile (inside Docker)
make migrate

# Directly
docker exec <backend_container> alembic upgrade head
```

### Check Current Version

```bash
docker exec <backend_container> alembic current
```

### View Migration History

```bash
docker exec <backend_container> alembic history --verbose
```

### Apply Migrations Up To a Specific Revision

```bash
docker exec <backend_container> alembic upgrade <revision_id>
```

## Creating New Migrations

### Auto-Generate from Model Changes

After modifying SQLAlchemy models in `app/models/`:

```bash
docker exec <backend_container> alembic revision --autogenerate -m "description of change"
```

This compares the current database schema against the model metadata and generates a migration script with the detected differences.

### Create an Empty Migration

For manual schema changes that autogenerate cannot detect:

```bash
docker exec <backend_container> alembic revision -m "description of change"
```

### Migration File Structure

Generated files are placed in `backend/alembic/versions/` and follow this pattern:

```python
"""description of change"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'abc123def456'
down_revision = 'previous_rev_id'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Schema changes to apply
    op.add_column('table_name', sa.Column('new_col', sa.String(), nullable=True))

def downgrade() -> None:
    # Reverse the changes
    op.drop_column('table_name', 'new_col')
```

### Review Before Applying

Always review auto-generated migrations before applying:

1. Check that `upgrade()` does what you expect
2. Verify `downgrade()` correctly reverses the changes
3. Look for data migrations that autogenerate cannot handle (e.g., populating new non-nullable columns)

## Rolling Back Migrations

### Downgrade One Step

```bash
docker exec <backend_container> alembic downgrade -1
```

### Downgrade to a Specific Revision

```bash
docker exec <backend_container> alembic downgrade <revision_id>
```

### Downgrade to Base (empty database)

```bash
docker exec <backend_container> alembic downgrade base
```

**Warning:** Downgrades may cause data loss. Always create a backup first.

## Migration History

The project has 12 migrations tracking the schema evolution:

| # | Revision | Description |
|---|----------|-------------|
| 1 | `ee08ccb0785a` | Initial migration (users, providers, datasets, xml_archives, useful_links) |
| 2 | `ed0dd59f436b` | Add statistics table |
| 3 | `84a53b5a2b87` | Add timestamp fields (created_at, updated_at) |
| 4 | `679a3c003046` | Add last_login timestamp to users table |
| 5 | `5170fba784be` | Add provider biological units metric |
| 6 | `92bd2a56238f` | Add provider unit_count and system unit count |
| 7 | `6af81fd1122b` | Remove deprecated statistics metrics |
| 8 | `eeee34d2629a` | Add unique constraint for statistics |
| 9 | `f8716259908d` | Add validation job model |
| 10 | `d3a5a08b3c0a` | Add HTTP change detection fields (etag, last_modified) |
| 11 | `d03846f7cbdf` | Add isDataCenter boolean flag to providers |
| 12 | `a1b2c3d4e5f6` | Replace Statistics table with ArchiveSnapshotModel |

## Best Practices

### Before Creating a Migration

1. Make sure your models in `app/models/` are correct
2. Run the test suite to verify nothing is broken
3. Check `alembic current` to confirm your starting point

### Writing Migrations

- **Always include both `upgrade()` and `downgrade()`**
- **Use batch operations** for SQLite compatibility in tests (though production uses PostgreSQL)
- **Handle data migrations separately** from schema migrations when possible
- **Add indexes** for columns used in WHERE clauses or JOINs
- **Set `nullable=True`** for new columns on existing tables, then backfill and alter if needed

### Testing Migrations

```bash
# Apply migration
docker exec <backend_container> alembic upgrade head

# Run tests to verify
make test

# If something is wrong, rollback
docker exec <backend_container> alembic downgrade -1
```

### Production Safety

1. **Always back up before migrating** — `make backup-db`
2. **The CI/CD pipeline does this automatically** — creates a timestamped backup before `alembic upgrade head`
3. **Test migrations locally first** — run against your dev database before pushing
4. **Keep migrations small** — one logical change per migration file
5. **Never edit a migration that has been applied to production** — create a new migration instead

### Connection Pooling Note

Alembic uses `NullPool` (one direct connection) for migrations, separate from the application's connection pool. This prevents interference with running application connections during migration execution.
