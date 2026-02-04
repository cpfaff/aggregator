# REST API Best Practices Standards

> Comprehensive analysis and uniform standards for API implementation best practices

**Document Version:** 1.0.0
**Last Updated:** 2025-01-08
**Applies To:** GFBio Aggregator Backend API

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
3. [Best Practices Standards](#best-practices-standards)
   - [Standard 1: Error Handling](#standard-1-error-handling)
   - [Standard 2: Pagination](#standard-2-pagination)
   - [Standard 3: Filtering](#standard-3-filtering)
   - [Standard 4: Sorting](#standard-4-sorting)
   - [Standard 5: Input Validation](#standard-5-input-validation)
   - [Standard 6: Response Consistency](#standard-6-response-consistency)
   - [Standard 7: HTTP Semantics](#standard-7-http-semantics)
   - [Standard 8: Idempotency](#standard-8-idempotency)
   - [Standard 9: Security](#standard-9-security)
   - [Standard 10: Caching](#standard-10-caching)
   - [Standard 11: Partial Updates (PATCH)](#standard-11-partial-updates-patch)
   - [Standard 12: Bulk Operations](#standard-12-bulk-operations)
4. [Implementation Checklist](#implementation-checklist)
5. [Critical Bugs Found](#critical-bugs-found)
6. [Priority Fixes](#priority-fixes)

---

## Executive Summary

After comprehensive analysis of **~50+ endpoints** across 4 API modules, the current implementation scores approximately **45%** on REST API best practices adherence. While the API has solid foundations in authentication, basic CRUD operations, and security middleware, significant gaps exist in pagination, sorting, error consistency, and HTTP semantics.

### Overall Scorecard

| Category | Current Score | Target Score | Status |
|----------|---------------|--------------|--------|
| Error Handling | 65% | 95% | Needs Work |
| Pagination | 40% | 95% | Critical Gap |
| Filtering | 50% | 90% | Needs Work |
| Sorting | 0% | 90% | **Missing** |
| Input Validation | 70% | 95% | Good Foundation |
| Response Consistency | 55% | 95% | Needs Work |
| HTTP Semantics | 60% | 95% | Needs Work |
| Idempotency | 50% | 95% | Inconsistent |
| Security | 75% | 95% | Good Foundation |
| Caching | 60% | 90% | Partial |
| Partial Updates | 0% | 80% | **Missing** |
| Bulk Operations | 0% | 70% | **Missing** |
| **Overall** | **45%** | **90%+** | **Significant Work Needed** |

---

## Current State Assessment

### What's Working Well

| Aspect | Implementation | Location |
|--------|----------------|----------|
| JWT Authentication | OAuth2 with refresh tokens | `main.py:403-501` |
| CSRF Protection | State-changing endpoints protected | `main.py:558, 603, etc.` |
| Rate Limiting | IP-based via slowapi | `main.py:212-214` |
| Security Headers | Comprehensive middleware | `main.py:241-258` |
| Request Logging | UUID tracking, JSON format | `main.py:262-307` |
| Global Exception Handler | Catches unhandled errors | `main.py:362-382` |
| Basic Validation | Pydantic models with validators | All schema files |
| Caching | Decorator-based with invalidation | `main.py:780, 836, etc.` |

### Critical Issues Found

#### Issue 1: Pagination Without Total Counts

**Current Implementation:**
```python
# main.py:523-539
@v1_router.get("/users", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    ...
):
    result = await db.execute(select(UserModel).offset(skip).limit(limit))
    return result.scalars().all()  # Returns bare list!
```

**Problems:**
- Returns `List[User]` instead of paginated response
- No `total` count for clients to know total records
- No pagination metadata (current page, total pages, has_next)
- `PaginatedResponse` schema exists in `common.py:13-28` but is **never used**!

---

#### Issue 2: Zero Sorting Support

**Current State:**
- **No endpoint supports user-defined sorting**
- All list endpoints use hardcoded ordering:
  - `/data-providers`: `order_by(DataProviderModel.id)` (line 824)
  - `/validators/`: `order_by(desc(ValidationJobModel.created_at))` (line 187)
  - Others: Default database order (undefined)

**Missing Parameters:**
- No `sort_by` parameter
- No `sort_order` (asc/desc) parameter
- No multi-field sorting

---

#### Issue 3: Inconsistent Error Codes

**Exception Handler (good):**
```python
# main.py:336-345
return JSONResponse(
    content={
        "detail": "Validation error",
        "code": "validation_error",  # Has code
        "path": str(request.url.path),
        "timestamp": datetime.utcnow().isoformat(),
        "errors": errors,
    },
)
```

**Endpoint-Level (inconsistent):**
```python
# main.py:554
raise HTTPException(status_code=404, detail="User not found")  # No code!

# main.py:848
raise HTTPException(status_code=400, detail="Provider ID must be...")  # No code!
```

The exception handler wraps these with `code: "http_exception"` but specific codes would be more useful.

---

#### Issue 4: DELETE Returns Body with 204

**Bug in `main.py:1390-1462`:**
```python
@v1_router.delete(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    status_code=204,  # Says 204 No Content
    ...
)
async def delete_dataset(...):
    ...
    return {  # But returns a body!
        "message": "Dataset and all associated data deleted successfully",
        "deletion_summary": deletion_summary
    }
```

**HTTP Specification Violation:** 204 No Content MUST NOT include a response body.

---

#### Issue 5: Inconsistent DELETE Idempotency

| Endpoint | Behavior When Not Found | Idempotent? |
|----------|------------------------|-------------|
| `DELETE /users/{username}` | Returns 404 | No |
| `DELETE /data-providers/{id}` | Silent success | Yes |
| `DELETE /data-sets/{id}` | Returns 404 | No |

DELETE should be idempotent - calling it multiple times should have the same effect.

---

#### Issue 6: Manual Path Parameter Validation

**Current (Anti-pattern):**
```python
# main.py:846-849
async def get_provider(provider_id: int, ...):
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be...")
```

**Should Be:**
```python
async def get_provider(
    provider_id: int = Path(..., ge=1, description="Provider ID"),
    ...
):
    # FastAPI auto-validates, returns 422 if invalid
```

---

#### Issue 7: Inconsistent Pagination Parameter Names

| Endpoint | Skip Parameter | Limit Parameter |
|----------|---------------|-----------------|
| `/users` | `skip` | `limit` |
| `/data-providers` | `skip` | `limit` |
| `/validators/` | `offset` | `limit` |

Should use consistent naming across all endpoints.

---

#### Issue 8: Missing CSRF on Some Endpoints

**Protected (correct):**
```python
@csrf_protect.validate_csrf
@v1_router.post("/users", ...)
```

**Not Protected:**
```python
# tasks.py:32
@router.post("/", ...)  # No CSRF!

# tasks.py:85
@router.post("/statistics/collect", ...)  # No CSRF!

# validators.py:78
@router.post("/", ...)  # No CSRF!
```

---

#### Issue 9: Mixed Field Naming Conventions

| Schema | Field | Convention |
|--------|-------|------------|
| DataProvider | `shortName`, `biocaseUrl`, `isDataCenter` | camelCase |
| TokenResponse | `access_token`, `refresh_token`, `token_type` | snake_case |
| LegacyDataset | `provider_datacenter`, `is_data_center` | snake_case |

While supporting both via `populate_by_name=True`, the inconsistency is confusing.

---

## Best Practices Standards

### Standard 1: Error Handling

#### 1.1 Standard Error Response Schema

**All errors MUST use this response format:**

```python
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    # Client errors (4xx)
    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"

    # Server errors (5xx)
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"
    DATABASE_ERROR = "database_error"


class FieldError(BaseModel):
    """Individual field validation error."""
    field: str = Field(..., description="Field name that caused the error")
    message: str = Field(..., description="Human-readable error message")
    code: str = Field(..., description="Machine-readable error code")


class ErrorResponse(BaseModel):
    """Standard error response for all API errors."""
    detail: str = Field(..., description="Human-readable error summary")
    code: ErrorCode = Field(..., description="Machine-readable error code")
    path: str = Field(..., description="Request path that caused the error")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    errors: Optional[List[FieldError]] = Field(
        None,
        description="Field-level errors for validation failures"
    )
    context: Optional[dict] = Field(
        None,
        description="Additional context (non-sensitive)"
    )
```

#### 1.2 Error Response Examples

```json
// 400 Bad Request
{
    "detail": "Provider ID must be a positive integer",
    "code": "bad_request",
    "path": "/api/v1/data-providers/0",
    "timestamp": "2024-01-08T12:00:00Z",
    "request_id": "req_abc123"
}

// 401 Unauthorized
{
    "detail": "Authentication required",
    "code": "unauthorized",
    "path": "/api/v1/users",
    "timestamp": "2024-01-08T12:00:00Z",
    "request_id": "req_abc123"
}

// 404 Not Found
{
    "detail": "User not found",
    "code": "not_found",
    "path": "/api/v1/users/unknown",
    "timestamp": "2024-01-08T12:00:00Z",
    "request_id": "req_abc123",
    "context": {
        "resource_type": "user",
        "identifier": "unknown"
    }
}

// 422 Validation Error
{
    "detail": "Validation failed for 2 fields",
    "code": "validation_error",
    "path": "/api/v1/users",
    "timestamp": "2024-01-08T12:00:00Z",
    "request_id": "req_abc123",
    "errors": [
        {"field": "username", "message": "Field is required", "code": "required"},
        {"field": "password", "message": "Must be at least 8 characters", "code": "min_length"}
    ]
}
```

#### 1.3 Exception Helper Functions

```python
from fastapi import HTTPException, Request
from typing import Optional, Dict, Any


def raise_bad_request(
    detail: str,
    context: Optional[Dict[str, Any]] = None
) -> None:
    """Raise a 400 Bad Request error."""
    raise HTTPException(
        status_code=400,
        detail={
            "detail": detail,
            "code": "bad_request",
            "context": context
        }
    )


def raise_not_found(
    resource_type: str,
    identifier: Any
) -> None:
    """Raise a 404 Not Found error."""
    raise HTTPException(
        status_code=404,
        detail={
            "detail": f"{resource_type.title()} not found",
            "code": "not_found",
            "context": {
                "resource_type": resource_type,
                "identifier": str(identifier)
            }
        }
    )


def raise_forbidden(
    detail: str = "Insufficient permissions",
    required_permission: Optional[str] = None
) -> None:
    """Raise a 403 Forbidden error."""
    context = {}
    if required_permission:
        context["required_permission"] = required_permission

    raise HTTPException(
        status_code=403,
        detail={
            "detail": detail,
            "code": "forbidden",
            "context": context or None
        }
    )


# Usage in endpoints:
async def get_user(username: str):
    user = await get_user_by_username(username)
    if not user:
        raise_not_found("user", username)
    return user
```

#### 1.4 HTTP Status Code Guidelines

| Status Code | When to Use | Error Code |
|-------------|-------------|------------|
| 200 OK | Successful GET, PUT, PATCH | N/A |
| 201 Created | Successful POST creating resource | N/A |
| 204 No Content | Successful DELETE (no body!) | N/A |
| 400 Bad Request | Invalid request syntax or parameters | `bad_request` |
| 401 Unauthorized | Missing or invalid authentication | `unauthorized` |
| 403 Forbidden | Valid auth but insufficient permissions | `forbidden` |
| 404 Not Found | Resource does not exist | `not_found` |
| 409 Conflict | Resource state conflict (duplicate, etc.) | `conflict` |
| 422 Unprocessable Entity | Validation errors | `validation_error` |
| 429 Too Many Requests | Rate limit exceeded | `rate_limited` |
| 500 Internal Server Error | Unexpected server error | `internal_error` |
| 503 Service Unavailable | Temporary service issue | `service_unavailable` |

---

### Standard 2: Pagination

#### 2.1 Pagination Response Schema

**All list endpoints MUST return paginated responses:**

```python
from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, Field
from pydantic.generics import GenericModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    total: int = Field(..., description="Total number of records", ge=0)
    page: int = Field(..., description="Current page number (1-based)", ge=1)
    page_size: int = Field(..., description="Number of records per page", ge=1)
    total_pages: int = Field(..., description="Total number of pages", ge=0)
    has_next: bool = Field(..., description="Whether there are more pages")
    has_previous: bool = Field(..., description="Whether there are previous pages")


class PaginatedResponse(GenericModel, Generic[T]):
    """Standard paginated response wrapper."""
    items: List[T] = Field(..., description="List of items for current page")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse[T]":
        """Factory method to create paginated response."""
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

        return cls(
            items=items,
            pagination=PaginationMeta(
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_previous=page > 1
            )
        )
```

#### 2.2 Pagination Query Parameters

**Standard parameters for all list endpoints:**

```python
from fastapi import Query
from typing import Annotated


# Define reusable pagination parameters
PageParam = Annotated[
    int,
    Query(
        default=1,
        ge=1,
        le=10000,
        description="Page number (1-based)",
        examples=[1, 2, 10]
    )
]

PageSizeParam = Annotated[
    int,
    Query(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page",
        examples=[10, 20, 50, 100]
    )
]


# Usage in endpoint:
@router.get("/users", response_model=PaginatedResponse[User])
async def list_users(
    page: PageParam = 1,
    page_size: PageSizeParam = 20,
    db: AsyncSession = Depends(get_db),
):
    # Calculate offset
    offset = (page - 1) * page_size

    # Get total count
    total = await db.scalar(select(func.count(UserModel.id)))

    # Get paginated items
    result = await db.execute(
        select(UserModel)
        .offset(offset)
        .limit(page_size)
    )
    items = result.scalars().all()

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
```

#### 2.3 Pagination Response Example

```json
{
    "items": [
        {"id": 1, "username": "admin", "is_global_admin": true},
        {"id": 2, "username": "curator1", "is_global_admin": false}
    ],
    "pagination": {
        "total": 150,
        "page": 1,
        "page_size": 20,
        "total_pages": 8,
        "has_next": true,
        "has_previous": false
    }
}
```

#### 2.4 Alternative: Offset-Based (Legacy Compatibility)

If maintaining backwards compatibility with `skip`/`limit`:

```python
@router.get("/users", response_model=PaginatedResponse[User])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    db: AsyncSession = Depends(get_db),
):
    total = await db.scalar(select(func.count(UserModel.id)))

    result = await db.execute(
        select(UserModel).offset(skip).limit(limit)
    )
    items = result.scalars().all()

    # Convert skip/limit to page/page_size for response
    page = (skip // limit) + 1 if limit > 0 else 1

    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=limit
    )
```

---

### Standard 3: Filtering

#### 3.1 Filter Parameter Schema

**Define filter parameters with clear documentation:**

```python
from fastapi import Query
from typing import Optional, List
from datetime import date


class FilterParams:
    """Reusable filter parameter definitions."""

    @staticmethod
    def text_search(
        field_name: str,
        description: str
    ):
        """Create a text search filter parameter."""
        return Query(
            None,
            description=f"{description}. Case-insensitive partial match.",
            min_length=1,
            max_length=200,
            examples=["example", "search term"]
        )

    @staticmethod
    def exact_match(
        field_name: str,
        description: str,
        examples: List[str]
    ):
        """Create an exact match filter parameter."""
        return Query(
            None,
            description=f"{description}. Exact match.",
            examples=examples
        )

    @staticmethod
    def date_range_start(field_name: str):
        """Create a date range start parameter."""
        return Query(
            None,
            description=f"Filter {field_name} on or after this date (inclusive)",
            examples=["2024-01-01"]
        )

    @staticmethod
    def date_range_end(field_name: str):
        """Create a date range end parameter."""
        return Query(
            None,
            description=f"Filter {field_name} on or before this date (inclusive)",
            examples=["2024-12-31"]
        )


# Usage:
@router.get("/data-providers")
async def list_providers(
    name: Optional[str] = FilterParams.text_search(
        "name", "Filter by provider name"
    ),
    datacenter: Optional[str] = FilterParams.text_search(
        "datacenter", "Filter by datacenter name"
    ),
    is_data_center: Optional[bool] = Query(
        None, description="Filter by data center status"
    ),
    created_after: Optional[date] = FilterParams.date_range_start("created_at"),
    created_before: Optional[date] = FilterParams.date_range_end("created_at"),
    ...
):
```

#### 3.2 Filter Implementation Pattern

```python
from sqlalchemy import select, and_, or_
from typing import Optional


async def apply_filters(
    query,
    model,
    filters: dict
) -> select:
    """Apply filters to a SQLAlchemy query."""
    conditions = []

    for field_name, filter_value in filters.items():
        if filter_value is None:
            continue

        # Get the model attribute
        if not hasattr(model, field_name):
            continue

        column = getattr(model, field_name)

        # Handle different filter types
        if isinstance(filter_value, str):
            # Text search - case-insensitive partial match
            conditions.append(column.ilike(f"%{filter_value}%"))
        elif isinstance(filter_value, bool):
            # Boolean exact match
            conditions.append(column == filter_value)
        elif isinstance(filter_value, (int, float)):
            # Numeric exact match
            conditions.append(column == filter_value)
        elif isinstance(filter_value, date):
            # Date comparison (handled separately for start/end)
            pass

    if conditions:
        query = query.where(and_(*conditions))

    return query


# Usage in endpoint:
@router.get("/data-providers")
async def list_providers(
    name: Optional[str] = None,
    datacenter: Optional[str] = None,
    is_data_center: Optional[bool] = None,
    ...
):
    query = select(DataProviderModel)

    query = await apply_filters(
        query,
        DataProviderModel,
        {
            "name": name,
            "datacenter": datacenter,
            "isDataCenter": is_data_center,
        }
    )

    # Continue with pagination, sorting, etc.
```

#### 3.3 Multi-Value Filters

**Support filtering by multiple values:**

```python
from typing import List


@router.get("/validation-jobs")
async def list_validation_jobs(
    status: Optional[List[str]] = Query(
        None,
        description="Filter by status(es). Multiple values allowed.",
        examples=[["pending", "running"], ["completed"]]
    ),
    ...
):
    query = select(ValidationJobModel)

    if status:
        query = query.where(ValidationJobModel.status.in_(status))

    ...
```

---

### Standard 4: Sorting

#### 4.1 Sort Parameter Schema

**All list endpoints MUST support sorting:**

```python
from fastapi import Query
from typing import Optional, List
from enum import Enum


class SortOrder(str, Enum):
    """Sort order options."""
    ASC = "asc"
    DESC = "desc"


def create_sort_params(allowed_fields: List[str], default_field: str):
    """Create sort parameter definitions for an endpoint."""

    sort_by = Query(
        default_field,
        description=f"Field to sort by. Allowed: {', '.join(allowed_fields)}",
        examples=allowed_fields[:3]
    )

    sort_order = Query(
        SortOrder.ASC,
        description="Sort direction"
    )

    return sort_by, sort_order


# Usage:
PROVIDER_SORT_FIELDS = ["id", "name", "datacenter", "created_at", "updated_at"]

@router.get("/data-providers")
async def list_providers(
    sort_by: str = Query(
        "id",
        description=f"Sort by field. Allowed: {', '.join(PROVIDER_SORT_FIELDS)}"
    ),
    sort_order: SortOrder = Query(SortOrder.ASC, description="Sort direction"),
    ...
):
    # Validate sort field
    if sort_by not in PROVIDER_SORT_FIELDS:
        raise_bad_request(
            f"Invalid sort field. Allowed: {', '.join(PROVIDER_SORT_FIELDS)}"
        )

    # Apply sorting
    order_column = getattr(DataProviderModel, sort_by)
    if sort_order == SortOrder.DESC:
        order_column = order_column.desc()

    query = query.order_by(order_column)
```

#### 4.2 Multi-Field Sorting

**Support sorting by multiple fields:**

```python
@router.get("/datasets")
async def list_datasets(
    sort: Optional[str] = Query(
        None,
        description="Sort specification. Format: 'field1:asc,field2:desc'. "
                    "Allowed fields: id, title, source, created_at",
        examples=["created_at:desc", "title:asc,created_at:desc"]
    ),
    ...
):
    if sort:
        sort_specs = parse_sort_string(sort)
        for field, direction in sort_specs:
            if field not in ALLOWED_SORT_FIELDS:
                raise_bad_request(f"Invalid sort field: {field}")

            column = getattr(DatasetModel, field)
            if direction == "desc":
                column = column.desc()
            query = query.order_by(column)
    else:
        # Default sort
        query = query.order_by(DatasetModel.id)


def parse_sort_string(sort: str) -> List[tuple]:
    """Parse sort string into list of (field, direction) tuples."""
    result = []
    for part in sort.split(","):
        if ":" in part:
            field, direction = part.split(":", 1)
            direction = direction.lower()
            if direction not in ("asc", "desc"):
                direction = "asc"
        else:
            field = part
            direction = "asc"
        result.append((field.strip(), direction))
    return result
```

---

### Standard 5: Input Validation

#### 5.1 Path Parameter Validation

**ALWAYS use `Path()` with constraints:**

```python
from fastapi import Path
from typing import Annotated


# Define reusable path parameter types
PositiveIntId = Annotated[
    int,
    Path(
        ...,
        ge=1,
        description="Resource ID (positive integer)",
        examples=[1, 42, 100]
    )
]

UsernameParam = Annotated[
    str,
    Path(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (alphanumeric, underscore, hyphen)",
        examples=["admin", "curator1", "data-manager"]
    )
]


# Usage:
@router.get("/data-providers/{provider_id}")
async def get_provider(
    provider_id: PositiveIntId,  # Automatically validated!
    ...
):
    # No manual validation needed - FastAPI returns 422 if invalid
    ...


@router.get("/users/{username}")
async def get_user(
    username: UsernameParam,
    ...
):
    ...
```

#### 5.2 Query Parameter Validation

```python
from fastapi import Query
from typing import Optional, Annotated


# Reusable query parameter types
SearchQuery = Annotated[
    Optional[str],
    Query(
        None,
        min_length=1,
        max_length=200,
        description="Search query (1-200 characters)"
    )
]

LimitParam = Annotated[
    int,
    Query(
        20,
        ge=1,
        le=100,
        description="Maximum items to return (1-100)"
    )
]

DaysParam = Annotated[
    int,
    Query(
        30,
        ge=1,
        le=365,
        description="Number of days to look back (1-365)"
    )
]
```

#### 5.3 Request Body Validation

**Schema fields MUST have constraints:**

```python
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class UserCreate(BaseModel):
    """Schema for creating a user."""

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Username (3-50 chars, alphanumeric/underscore/hyphen)"
    )

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)"
    )

    email: Optional[str] = Field(
        None,
        max_length=254,
        description="Email address"
    )

    @field_validator("password")
    @classmethod
    def validate_password_complexity(cls, v: str) -> str:
        """Ensure password meets complexity requirements."""
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format."""
        if v is not None:
            email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_pattern, v):
                raise ValueError("Invalid email format")
        return v
```

---

### Standard 6: Response Consistency

#### 6.1 Naming Convention: camelCase

**All API responses MUST use camelCase:**

```python
from pydantic import BaseModel, Field, ConfigDict


class DataProvider(BaseModel):
    """Data provider schema - uses camelCase for all fields."""

    id: Optional[int] = None
    datacenter: str
    shortName: str  # camelCase
    name: str
    url: Optional[str] = None
    biocaseUrl: Optional[str] = None  # camelCase
    isDataCenter: bool = False  # camelCase
    createdAt: Optional[datetime] = None  # camelCase
    updatedAt: Optional[datetime] = None  # camelCase

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,  # Accept both camelCase and snake_case input
        alias_generator=None  # Don't auto-generate aliases
    )
```

#### 6.2 Null vs Missing Fields

**Explicit policy for null handling:**

```python
# Option A: Always include field, use null for missing values
{
    "id": 1,
    "name": "Provider",
    "url": null,  // Explicitly null
    "biocaseUrl": null
}

# Option B: Omit missing optional fields (PREFERRED)
{
    "id": 1,
    "name": "Provider"
    // url and biocaseUrl not included
}


# Implementation for Option B:
class DataProvider(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        # Exclude None values from serialization
        exclude_none=True  # Removed in Pydantic v2, use model_dump(exclude_none=True)
    )


# In endpoint:
@router.get("/providers/{id}")
async def get_provider(...) -> DataProvider:
    provider = await fetch_provider(id)
    return provider.model_dump(exclude_none=True)
```

#### 6.3 Empty Collections

**Empty lists MUST be returned as `[]`, not `null`:**

```python
# CORRECT
{
    "id": 1,
    "datasets": []
}

# WRONG
{
    "id": 1,
    "datasets": null
}
```

#### 6.4 Timestamps

**All timestamps MUST use ISO 8601 format with timezone:**

```python
from datetime import datetime, timezone


class TimestampMixin(BaseModel):
    """Mixin for timestamp fields."""

    createdAt: Optional[datetime] = Field(
        None,
        description="Creation timestamp (ISO 8601 UTC)"
    )
    updatedAt: Optional[datetime] = Field(
        None,
        description="Last update timestamp (ISO 8601 UTC)"
    )

    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.replace(tzinfo=timezone.utc).isoformat()
        }
    )


# Output format:
# "createdAt": "2024-01-08T12:00:00+00:00"
```

---

### Standard 7: HTTP Semantics

#### 7.1 HTTP Method Usage

| Method | Use Case | Request Body | Response Body | Idempotent |
|--------|----------|--------------|---------------|------------|
| GET | Retrieve resource(s) | No | Yes | Yes |
| POST | Create resource | Yes | Yes (created resource) | No |
| PUT | Full resource replacement | Yes | Yes (updated resource) | Yes |
| PATCH | Partial resource update | Yes | Yes (updated resource) | Yes |
| DELETE | Remove resource | No | No (204) | Yes |

#### 7.2 Status Code Rules

```python
# GET - Success
@router.get("/providers/{id}")
async def get_provider(...):
    return provider  # Returns 200 automatically


# POST - Create
@router.post("/providers", status_code=201)  # MUST be 201
async def create_provider(...):
    return new_provider


# PUT - Update
@router.put("/providers/{id}")
async def update_provider(...):
    return updated_provider  # Returns 200


# DELETE - Remove
@router.delete("/providers/{id}", status_code=204)
async def delete_provider(...):
    await db.delete(provider)
    await db.commit()
    return None  # MUST return None/nothing for 204!
```

#### 7.3 Location Header for POST

**POST responses SHOULD include Location header:**

```python
from fastapi import Response


@router.post("/providers", status_code=201)
async def create_provider(
    provider: DataProviderCreate,
    response: Response,
    ...
):
    new_provider = await create_provider_in_db(provider)

    # Set Location header to the new resource
    response.headers["Location"] = f"/api/v1/data-providers/{new_provider.id}"

    return new_provider
```

---

### Standard 8: Idempotency

#### 8.1 Idempotent DELETE

**DELETE MUST be idempotent - return 204 even if resource doesn't exist:**

```python
@router.delete("/users/{username}", status_code=204)
async def delete_user(
    username: str = Path(...),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user. Idempotent - succeeds even if user doesn't exist."""
    result = await db.execute(
        select(UserModel).where(UserModel.username == username)
    )
    user = result.scalar_one_or_none()

    if user:
        await db.delete(user)
        await db.commit()

    # Always return 204, even if user didn't exist
    return None
```

#### 8.2 Idempotency Keys for POST

**Support idempotency keys for non-idempotent operations:**

```python
from fastapi import Header
from typing import Optional
import hashlib


@router.post("/providers", status_code=201)
async def create_provider(
    provider: DataProviderCreate,
    idempotency_key: Optional[str] = Header(
        None,
        alias="X-Idempotency-Key",
        description="Unique key to ensure idempotent creation"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Create a provider. Use X-Idempotency-Key header to prevent duplicates."""

    if idempotency_key:
        # Check if we've seen this key before
        existing = await get_idempotency_record(idempotency_key)
        if existing:
            # Return the previously created resource
            return existing.response_data

    # Create the resource
    new_provider = await create_provider_in_db(provider)

    if idempotency_key:
        # Store the idempotency record
        await store_idempotency_record(
            key=idempotency_key,
            response_data=new_provider.model_dump()
        )

    return new_provider
```

---

### Standard 9: Security

#### 9.1 CSRF Protection

**All state-changing endpoints MUST have CSRF protection:**

```python
from fastapi_csrf_protect import CsrfProtect


# Apply to ALL POST, PUT, PATCH, DELETE endpoints:
@csrf_protect.validate_csrf
@router.post("/providers", status_code=201)
async def create_provider(...):
    ...


@csrf_protect.validate_csrf
@router.put("/providers/{id}")
async def update_provider(...):
    ...


@csrf_protect.validate_csrf
@router.delete("/providers/{id}", status_code=204)
async def delete_provider(...):
    ...
```

#### 9.2 Rate Limiting Strategy

```python
from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(key_func=get_remote_address)

# Rate limit categories:
RATE_LIMITS = {
    "auth": "5/minute",      # Login attempts
    "write": "30/minute",    # Create/Update operations
    "read": "100/minute",    # Read operations
    "bulk": "10/minute",     # Bulk operations
    "export": "5/minute",    # Data exports
}


@router.post("/auth-token")
@limiter.limit(RATE_LIMITS["auth"])
async def login(...):
    ...


@router.post("/providers")
@limiter.limit(RATE_LIMITS["write"])
async def create_provider(...):
    ...


@router.get("/providers")
@limiter.limit(RATE_LIMITS["read"])
async def list_providers(...):
    ...
```

#### 9.3 Authorization Patterns

```python
from enum import Enum
from typing import Callable


class Permission(str, Enum):
    """Standard permission types."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


def require_permission(
    resource_type: str,
    permission: Permission
) -> Callable:
    """Dependency factory for permission checking."""

    async def check_permission(
        resource_id: int,
        current_user: UserModel = Depends(get_current_user),
    ) -> UserModel:
        # Global admins have all permissions
        if current_user.is_global_admin:
            return current_user

        # Check resource-specific permission
        user_role = current_user.provider_roles.get(str(resource_id))

        if not user_role:
            raise_forbidden(
                f"No access to {resource_type} {resource_id}",
                required_permission=permission.value
            )

        # Check role has required permission
        role_permissions = {
            "admin": [Permission.READ, Permission.WRITE, Permission.DELETE],
            "curator": [Permission.READ, Permission.WRITE],
            "viewer": [Permission.READ],
        }

        if permission not in role_permissions.get(user_role, []):
            raise_forbidden(
                f"Insufficient permissions for {permission.value}",
                required_permission=permission.value
            )

        return current_user

    return check_permission


# Usage:
@router.delete("/providers/{provider_id}")
async def delete_provider(
    provider_id: PositiveIntId,
    current_user: UserModel = Depends(
        require_permission("provider", Permission.DELETE)
    ),
    ...
):
    ...
```

---

### Standard 10: Caching

#### 10.1 Cache Headers

```python
from fastapi import Response
from datetime import datetime


def set_cache_headers(
    response: Response,
    max_age: int = 300,
    private: bool = False,
    etag: str = None,
    last_modified: datetime = None
):
    """Set standard cache headers on response."""

    cache_control = f"{'private' if private else 'public'}, max-age={max_age}"
    response.headers["Cache-Control"] = cache_control

    if etag:
        response.headers["ETag"] = f'"{etag}"'

    if last_modified:
        response.headers["Last-Modified"] = last_modified.strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )


def set_no_cache_headers(response: Response):
    """Set no-cache headers for real-time data."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"


# Usage:
@router.get("/providers/{id}")
async def get_provider(
    provider_id: int,
    response: Response,
    ...
):
    provider = await fetch_provider(provider_id)

    # Generate ETag from data
    import hashlib
    etag = hashlib.md5(
        f"{provider.id}-{provider.updated_at}".encode()
    ).hexdigest()

    set_cache_headers(
        response,
        max_age=300,
        etag=etag,
        last_modified=provider.updated_at
    )

    return provider
```

#### 10.2 Conditional Requests

```python
from fastapi import Header, Response, status


@router.get("/providers/{id}")
async def get_provider(
    provider_id: int,
    response: Response,
    if_none_match: Optional[str] = Header(None),
    if_modified_since: Optional[str] = Header(None),
    ...
):
    provider = await fetch_provider(provider_id)

    # Calculate ETag
    current_etag = calculate_etag(provider)

    # Check If-None-Match
    if if_none_match and if_none_match.strip('"') == current_etag:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Check If-Modified-Since
    if if_modified_since:
        modified_since = parse_http_date(if_modified_since)
        if provider.updated_at <= modified_since:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    set_cache_headers(response, etag=current_etag, last_modified=provider.updated_at)
    return provider
```

---

### Standard 11: Partial Updates (PATCH)

#### 11.1 PATCH Endpoint Pattern

```python
from pydantic import BaseModel
from typing import Optional


class DataProviderPatch(BaseModel):
    """Schema for partial provider updates. All fields optional."""

    datacenter: Optional[str] = None
    shortName: Optional[str] = None
    name: Optional[str] = None
    url: Optional[str] = None
    biocaseUrl: Optional[str] = None
    isDataCenter: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")  # Reject unknown fields


@router.patch("/providers/{provider_id}")
async def patch_provider(
    provider_id: PositiveIntId,
    updates: DataProviderPatch,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update a provider. Only provided fields are updated."""

    provider = await get_provider_or_404(provider_id, db)

    # Only update fields that were explicitly provided
    update_data = updates.model_dump(exclude_unset=True)

    if not update_data:
        raise_bad_request("No fields to update")

    for field, value in update_data.items():
        setattr(provider, field, value)

    provider.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(provider)

    return provider
```

#### 11.2 PUT vs PATCH Guidelines

| Aspect | PUT | PATCH |
|--------|-----|-------|
| Request body | Complete resource | Partial fields |
| Missing fields | Set to default/null | Unchanged |
| Idempotent | Yes | Yes |
| Use case | Full replacement | Partial update |

```python
# PUT - Full replacement (missing fields become null/default)
PUT /providers/1
{
    "datacenter": "Berlin",
    "shortName": "MfN",
    "name": "Museum für Naturkunde",
    "url": null,  // Explicitly clearing
    "biocaseUrl": null
}

# PATCH - Partial update (only update name)
PATCH /providers/1
{
    "name": "Museum für Naturkunde Berlin"
}
// Other fields remain unchanged
```

---

### Standard 12: Bulk Operations

#### 12.1 Bulk Create

```python
from typing import List


class BulkCreateResponse(BaseModel):
    """Response for bulk create operations."""
    created: List[DataProvider]
    failed: List[dict]
    total_submitted: int
    total_created: int
    total_failed: int


@router.post("/providers/bulk", response_model=BulkCreateResponse)
async def bulk_create_providers(
    providers: List[DataProviderCreate] = Body(
        ...,
        max_length=100,  # Limit batch size
        description="List of providers to create (max 100)"
    ),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple providers in a single request."""

    check_global_admin(current_user)

    created = []
    failed = []

    for i, provider_data in enumerate(providers):
        try:
            new_provider = await create_provider_in_db(provider_data, db)
            created.append(new_provider)
        except Exception as e:
            failed.append({
                "index": i,
                "data": provider_data.model_dump(),
                "error": str(e)
            })

    await db.commit()

    return BulkCreateResponse(
        created=created,
        failed=failed,
        total_submitted=len(providers),
        total_created=len(created),
        total_failed=len(failed)
    )
```

#### 12.2 Bulk Delete

```python
class BulkDeleteRequest(BaseModel):
    """Request for bulk delete operations."""
    ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="IDs to delete (max 100)"
    )


class BulkDeleteResponse(BaseModel):
    """Response for bulk delete operations."""
    deleted_ids: List[int]
    not_found_ids: List[int]
    failed_ids: List[dict]
    total_deleted: int


@router.post("/providers/bulk-delete", response_model=BulkDeleteResponse)
async def bulk_delete_providers(
    request: BulkDeleteRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple providers in a single request."""

    check_global_admin(current_user)

    deleted_ids = []
    not_found_ids = []
    failed_ids = []

    for provider_id in request.ids:
        result = await db.execute(
            select(DataProviderModel).where(DataProviderModel.id == provider_id)
        )
        provider = result.scalar_one_or_none()

        if not provider:
            not_found_ids.append(provider_id)
            continue

        try:
            await db.delete(provider)
            deleted_ids.append(provider_id)
        except Exception as e:
            failed_ids.append({"id": provider_id, "error": str(e)})

    await db.commit()

    return BulkDeleteResponse(
        deleted_ids=deleted_ids,
        not_found_ids=not_found_ids,
        failed_ids=failed_ids,
        total_deleted=len(deleted_ids)
    )
```

---

## Implementation Checklist

### Endpoint Review Checklist

```markdown
## Endpoint: [METHOD] /path

### Error Handling
- [ ] Uses ErrorResponse schema for all errors
- [ ] Returns appropriate HTTP status codes
- [ ] Error messages are informative but don't leak internals
- [ ] All exceptions are caught and handled

### Pagination (for list endpoints)
- [ ] Uses PaginatedResponse wrapper
- [ ] Returns total count
- [ ] Has page/page_size (or skip/limit) parameters
- [ ] Parameters have proper constraints (ge, le)

### Filtering (for list endpoints)
- [ ] Supports relevant filters
- [ ] Filter parameters documented
- [ ] Filters use proper SQL (no injection)

### Sorting (for list endpoints)
- [ ] Has sort_by parameter
- [ ] Has sort_order parameter
- [ ] Validates allowed sort fields
- [ ] Has sensible default sort

### Input Validation
- [ ] Path params use Path() with constraints
- [ ] Query params use Query() with constraints
- [ ] Request body has Pydantic validation
- [ ] All constraints are documented

### Response Consistency
- [ ] Uses camelCase field names
- [ ] Empty collections return []
- [ ] Timestamps in ISO 8601
- [ ] Consistent null handling

### HTTP Semantics
- [ ] Correct HTTP method for operation
- [ ] Correct status code
- [ ] DELETE returns 204 with no body
- [ ] POST returns 201 with Location header

### Idempotency
- [ ] PUT is idempotent
- [ ] DELETE is idempotent (204 even if not found)
- [ ] POST supports idempotency key (if applicable)

### Security
- [ ] Has authentication (if required)
- [ ] Has authorization check
- [ ] Has CSRF protection (for state changes)
- [ ] Has rate limiting (if applicable)

### Caching
- [ ] Has appropriate Cache-Control headers
- [ ] Supports ETag/If-None-Match (for reads)
- [ ] Cache is invalidated on mutations
```

---

## Critical Bugs Found

### Bug 1: DELETE Returns Body with 204 Status

**Location:** `main.py:1390-1462`

**Problem:**
```python
@v1_router.delete(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    status_code=204,  # 204 No Content
)
async def delete_dataset(...):
    ...
    return {  # BUG: Returns body with 204!
        "message": "Dataset and all associated data deleted successfully",
        "deletion_summary": deletion_summary
    }
```

**Fix Options:**
1. Return `None` and truly use 204
2. Change to `status_code=200` and return body

**Recommended Fix:**
```python
@v1_router.delete(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    status_code=204,
)
async def delete_dataset(...):
    ...
    return None  # Correct for 204
```

---

### Bug 2: Inconsistent DELETE Idempotency

**Location:** Multiple endpoints

**Problem:**
- `DELETE /users/{username}` returns 404 if not found (not idempotent)
- `DELETE /data-providers/{id}` succeeds silently (idempotent)
- `DELETE /data-sets/{id}` returns 404 if not found (not idempotent)

**Fix:** All DELETE endpoints should return 204 regardless of whether resource existed.

---

### Bug 3: PaginatedResponse Never Used

**Location:** `app/schemas/common.py:13-28` (defined) vs all list endpoints (not used)

**Problem:**
- `PaginatedResponse` schema exists with `items`, `total`, `page`, `size`
- No list endpoint uses it
- All return bare `List[Model]`

**Fix:** Refactor all list endpoints to use `PaginatedResponse`.

---

### Bug 4: Inconsistent Parameter Naming

**Location:** `validators.py:168-169` vs other endpoints

**Problem:**
```python
# validators.py uses 'offset'
limit: int = 10,
offset: int = 0,

# main.py uses 'skip'
skip: int = Query(0, ...),
limit: int = Query(100, ...),
```

**Fix:** Standardize on one naming convention (`page`/`page_size` recommended).

---

## Priority Fixes

### Priority 0 - Critical (Fix Immediately)

| Bug | Location | Impact |
|-----|----------|--------|
| DELETE returns body with 204 | `main.py:1452-1455` | HTTP spec violation |
| PaginatedResponse not used | All list endpoints | Missing pagination metadata |

### Priority 1 - High

| Issue | Location | Impact |
|-------|----------|--------|
| No sorting support | All list endpoints | Feature gap |
| Inconsistent DELETE idempotency | Multiple | API contract issue |
| Manual path param validation | Multiple | Should use FastAPI |
| Missing CSRF on some endpoints | `tasks.py`, `validators.py` | Security gap |

### Priority 2 - Medium

| Issue | Location | Impact |
|-------|----------|--------|
| Inconsistent parameter naming | `validators.py` | Developer confusion |
| No error codes in HTTPException | Multiple | Less machine-readable |
| Missing date range filters | List endpoints | Feature gap |
| No PATCH endpoints | All resources | Feature gap |

### Priority 3 - Low

| Issue | Location | Impact |
|-------|----------|--------|
| No bulk operations | N/A | Feature gap |
| No ETag support | All GET endpoints | Bandwidth optimization |
| No Location header on POST | Create endpoints | Best practice |
| Mixed field naming conventions | Schemas | Inconsistency |

---

## Summary

The API has a solid foundation but requires significant work to meet REST best practices:

1. **Immediate Fixes:**
   - Fix 204 bug returning body
   - Implement proper pagination with totals

2. **Short-term Improvements:**
   - Add sorting to all list endpoints
   - Standardize error responses
   - Make DELETE idempotent everywhere

3. **Medium-term Enhancements:**
   - Add PATCH support for partial updates
   - Add bulk operations
   - Implement ETag caching

4. **Consistency Work:**
   - Standardize parameter naming
   - Apply CSRF to all state-changing endpoints
   - Move validation to Path()/Query() constraints

Following these standards will bring the API from ~45% to ~90%+ adherence to REST best practices.
