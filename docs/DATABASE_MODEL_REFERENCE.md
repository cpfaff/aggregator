# Database Model Reference

Conceptual guide for developers building modules that integrate with the Aggregator platform.

## Entity Relationship Overview

```
┌─────────────────┐
│   UserModel     │ ─── provider_roles JSON ───┐
└─────────────────┘                            │
                                               ▼
┌─────────────────┐    1:N    ┌─────────────────┐
│ DataProviderModel│─────────▶│   DatasetModel   │
└─────────────────┘           └─────────────────┘
                                     │
                        ┌────────────┼────────────┐
                        │ 1:N        │ 1:N        │ 1:N
                        ▼            ▼            ▼
              ┌──────────────┐ ┌──────────┐ ┌──────────────────┐
              │XmlArchiveModel│ │UsefulLink│ │ (Your Module)    │
              └──────────────┘ └──────────┘ └──────────────────┘
                     │
          ┌──────────┴──────────┐
          │ 1:N                 │ 1:N
          ▼                     ▼
   ┌────────────────┐  ┌─────────────────────┐
   │ValidationJobModel│  │ArchiveSnapshotModel│
   └────────────────┘  └─────────────────────┘
```

---

## Core Models

### UserModel
**Table:** `users`

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| username | String | Unique, indexed |
| hashed_password | String | bcrypt hash |
| provider_roles | JSON | `{"provider_id": "role"}` |
| is_global_admin | Boolean | System-wide access |
| last_login | DateTime | Nullable |

### DataProviderModel
**Table:** `data_providers`

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| datacenter | String | Organization identifier |
| shortName | String | Provider abbreviation |
| name | String | Full name |
| url | String | Nullable |
| biocaseUrl | String | Nullable, BioCASe endpoint |
| isDataCenter | Boolean | Flag for data centers |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

**Relationships:** `datasets` → DatasetModel (cascade delete)

### DatasetModel
**Table:** `datasets`

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| provider_id | Integer | FK → data_providers.id |
| source | String | Data source identifier |
| title | String | Dataset title |
| landingPageUrl | String | Nullable |
| created_at | DateTime | Auto |
| updated_at | DateTime | Auto |

**Relationships:**
- `provider` → DataProviderModel
- `xmlArchives` → XmlArchiveModel (cascade delete)
- `usefulLinks` → UsefulLinkModel (cascade delete)

### XmlArchiveModel
**Table:** `xml_archives`

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| dataset_id | Integer | FK → datasets.id |
| url | String | Archive URL |
| isLatest | Boolean | Current version flag |

### ArchiveSnapshotModel
**Table:** `archive_snapshots` (append-only)

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| archive_id | Integer | FK → xml_archives.id |
| recorded_at | DateTime | Snapshot timestamp |
| unit_count | Integer | Record count |
| http_etag | String | For change detection |
| http_last_modified | String | For change detection |

### ValidationJobModel
**Table:** `validation_jobs`

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| archive_id | Integer | FK → xml_archives.id |
| status | String | pending/running/completed/failed |
| task_id | String | Celery task ID |
| results | JSONB | Full validation details |
| total_files, valid_files, error_count | Integer | Summary metrics |

---

## Authentication & Authorization

### Authentication Flow

```
POST /api/v1/auth-token (username, password)
        │
        ▼
   bcrypt verify
        │
        ▼
   JWT tokens (access: 30min, refresh: 7days)
        │
        ▼
   Authorization: Bearer {access_token}
```

**JWT Claims:**
- `sub`: username
- `exp`: expiration
- `aud`: "dataset-api"
- `jti`: unique ID (for revocation)

### Two-Level Authorization

**Level 1: Global Admin**
- `is_global_admin = True` → full system access
- Required for: user management, provider creation/deletion

**Level 2: Provider Roles** (stored in `provider_roles` JSON)

| Role | Permissions |
|------|-------------|
| `admin` | Full provider control |
| `curator` | Read + write operations |
| `reader` | Read-only access |

### Key Auth Functions

```python
# Async dependency for protected endpoints
async def get_current_user(token, db) -> UserModel

# Check provider-level access
def check_provider_permission(provider_id, current_user, operation: "read"|"write")

# Require global admin
def require_admin(current_user) -> UserModel
```

---

## Integration Patterns

### Adding a New Data Module (e.g., DCAT)

**1. Create your model(s):**

```python
# backend/app/models/dcat.py
from app.models.base import Base, TimestampMixin

class DCATCatalogModel(Base, TimestampMixin):
    __tablename__ = "dcat_catalogs"

    id = Column(Integer, primary_key=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"))  # Link to existing
    # ... your DCAT fields

    dataset = relationship("DatasetModel", back_populates="dcat_catalogs")
```

**2. Add relationship to DatasetModel:**

```python
# In backend/app/models/dataset.py
class DatasetModel:
    # ... existing fields
    dcat_catalogs = relationship("DCATCatalogModel", back_populates="dataset",
                                  cascade="all, delete-orphan")
```

**3. Register in models/__init__.py:**

```python
from app.models.dcat import DCATCatalogModel
```

**4. Create migration:**

```bash
alembic revision --autogenerate -m "Add DCAT catalog model"
alembic upgrade head
```

### Protecting Your Endpoints

```python
# backend/app/api/v1/endpoints/dcat.py
from app.api.deps import get_current_user, get_db
from app.security.permissions import check_provider_permission

@router.get("/datasets/{dataset_id}/dcat")
async def get_dcat(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)  # Optional for public
):
    dataset = await get_dataset(db, dataset_id)
    check_provider_permission(dataset.provider_id, current_user, "read")
    # ... your logic

@router.post("/datasets/{dataset_id}/dcat")
async def create_dcat(
    dataset_id: int,
    data: DCATCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    dataset = await get_dataset(db, dataset_id)
    check_provider_permission(dataset.provider_id, current_user, "write")
    # ... your logic
```

### Associating with Providers

Option A: **Through Dataset** (recommended for dataset-specific data)
```python
dataset_id = Column(Integer, ForeignKey("datasets.id"))
# Access provider via: model.dataset.provider
```

Option B: **Direct to Provider** (for provider-level resources)
```python
provider_id = Column(Integer, ForeignKey("data_providers.id"))
provider = relationship("DataProviderModel")
```

---

## Database Session Patterns

**Async (FastAPI endpoints):**
```python
from app.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession

async def my_endpoint(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MyModel))
```

**Sync (Celery tasks):**
```python
from app.db.session import get_sync_db

def my_celery_task():
    db = next(get_sync_db())
    try:
        # ... work
        db.commit()
    finally:
        db.close()
```

---

## Conventions

- Use `TimestampMixin` for `created_at`/`updated_at`
- Cascade deletes flow: Provider → Dataset → Children
- Index foreign keys: `Index("idx_{table}_{fk}", "{fk}_id")`
- JSONB for flexible structured data
- Pydantic schemas in `backend/app/schemas/`
- CRUD operations in `backend/app/crud/`

---

## File Locations

| Component | Path |
|-----------|------|
| Models | `backend/app/models/` |
| Schemas | `backend/app/schemas/` |
| CRUD | `backend/app/crud/` |
| Endpoints | `backend/app/api/v1/endpoints/` |
| Auth/Permissions | `backend/app/security/` |
| Dependencies | `backend/app/api/deps.py` |
| Migrations | `backend/alembic/versions/` |
| Config | `backend/app/core/config.py` |
