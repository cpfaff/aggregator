# API Documentation Standards

> Comprehensive review and uniform standards for outstanding API documentation

**Document Version:** 1.0.0
**Last Updated:** 2025-01-08
**Applies To:** GFBio Aggregator Backend API

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Assessment](#current-state-assessment)
   - [What's Done Well](#whats-done-well)
   - [Critical Issues Found](#critical-issues-found)
3. [Uniform Documentation Standard](#uniform-documentation-standard)
   - [Rule 1: FastAPI Application Metadata](#rule-1-fastapi-application-metadata)
   - [Rule 2: Route Decorator Standard](#rule-2-route-decorator-standard)
   - [Rule 3: Docstring Standard (Google Style)](#rule-3-docstring-standard-google-style)
   - [Rule 4: Path Parameter Documentation](#rule-4-path-parameter-documentation)
   - [Rule 5: Query Parameter Documentation](#rule-5-query-parameter-documentation)
   - [Rule 6: Schema Field Documentation](#rule-6-schema-field-documentation)
   - [Rule 7: Error Response Model](#rule-7-error-response-model)
   - [Rule 8: Endpoint Responses Dictionary](#rule-8-endpoint-responses-dictionary)
   - [Rule 9: Authentication Documentation](#rule-9-authentication-documentation)
   - [Rule 10: Deprecation Marking](#rule-10-deprecation-marking)
4. [Documentation Checklist](#documentation-checklist)
5. [Priority Fixes](#priority-fixes)
6. [Examples](#examples)
   - [Complete Endpoint Example](#complete-endpoint-example)
   - [Complete Schema Example](#complete-schema-example)

---

## Executive Summary

After reviewing **~50+ endpoints** across 4 API modules, the current documentation is assessed at approximately **60% completeness**. The API has good foundations but lacks consistency and several best practices required for outstanding documentation.

### Files Reviewed

| File | Lines | Endpoints | Purpose |
|------|-------|-----------|---------|
| `main.py` | ~1759 | ~30+ | Core CRUD operations |
| `app/api/v1/endpoints/snapshots.py` | ~340 | ~14 | Statistics endpoints |
| `app/api/v1/endpoints/validators.py` | ~411 | ~6 | Validation endpoints |
| `app/api/v1/endpoints/tasks.py` | ~108 | ~3 | Background tasks |
| `app/schemas/*.py` | ~200 | N/A | Request/Response models |

### Assessment Score

| Category | Current | Target | Gap |
|----------|---------|--------|-----|
| API-level metadata | 40% | 100% | Missing description, contact, tags |
| Endpoint documentation | 65% | 100% | Inconsistent format, missing responses |
| Parameter documentation | 50% | 100% | Path params undocumented |
| Schema documentation | 70% | 100% | Missing examples, some fields undocumented |
| Error documentation | 20% | 100% | No error response models |
| **Overall** | **60%** | **95%+** | **35% improvement needed** |

---

## Current State Assessment

### What's Done Well

| Aspect | Assessment | Location Examples |
|--------|------------|-------------------|
| **Docstrings Present** | Most endpoints have them | `main.py:391-396`, `validators.py:84-94` |
| **Summary Parameter** | Consistently used | `summary="Get CSRF token"` |
| **Response Models** | Good coverage | `response_model=TokenResponse` |
| **Query Descriptions** | Generally good | `Query(0, ge=0, description="...")` |
| **Status Codes** | Proper 201/204 usage | `status_code=201` for POST |
| **Module Docstrings** | Files are documented | `snapshots.py:1-8` |
| **Schema Field Docs** | Statistics schemas good | `statistics.py:15-17` |

### Critical Issues Found

#### Issue 1: Docstring Format Inconsistency

Three different styles are used across the codebase:

**Style A - Markdown bullets (main.py):**
```python
"""
Authenticate a user and return JWT access and refresh tokens.

- **username**: The user's username
- **password**: The user's password

Returns a JSON object containing the access token, refresh token, token type, and expiration time.
"""
```

**Style B - Google docstring (validators.py):**
```python
"""
Start a validation job for an XML archive.

Args:
    request: The validation request with archive ID
    current_user: The current authenticated user
    db: Database session

Returns:
    Information about the submitted validation job
"""
```

**Style C - Single sentence (snapshots.py):**
```python
"""Get registry overview statistics using live database counts."""
```

**Problem:** This inconsistency creates a fragmented developer experience and makes the OpenAPI documentation appear unprofessional.

---

#### Issue 2: Missing OpenAPI Metadata

**Current app definition (`main.py:198-204`):**
```python
app = FastAPI(
    title="Dataset Management API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
```

**Missing elements:**
- `description` - No API overview or feature list
- `contact` - No maintainer information
- `license_info` - No license details
- `terms_of_service` - No terms URL
- `openapi_tags` - No tag descriptions for grouping
- `servers` - No production/staging URLs

---

#### Issue 3: No Tag Grouping

Endpoints lack the `tags` parameter, making Swagger UI disorganized with all endpoints in a flat list.

**Current (problematic):**
```python
@v1_router.get("/users", response_model=List[User], summary="List all users")
```

**Should be:**
```python
@v1_router.get("/users", response_model=List[User], summary="List all users", tags=["Users"])
```

---

#### Issue 4: Path Parameters Undocumented

Path parameters are not documented with `Path()`, losing valuable metadata.

**Current (`main.py:542`):**
```python
async def get_user_endpoint(
    username: str,  # No description, no constraints
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

**Should be:**
```python
async def get_user_endpoint(
    username: str = Path(
        ...,
        description="Unique username to retrieve",
        min_length=1,
        max_length=50,
        examples=["admin", "curator1"],
    ),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

---

#### Issue 5: No Error Response Documentation

Endpoints don't document possible error responses in the OpenAPI spec.

**Current (missing):**
```python
@v1_router.get("/users/{username}", response_model=User)
```

**Should include:**
```python
@v1_router.get(
    "/users/{username}",
    response_model=User,
    responses={
        401: {"description": "Not authenticated", "model": ErrorResponse},
        403: {"description": "Not authorized - admin only", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
    }
)
```

---

#### Issue 6: Schema Documentation Gaps

**TokenResponse (`common.py:31-37`) missing field descriptions:**
```python
class TokenResponse(BaseModel):
    access_token: str  # No description!
    refresh_token: str  # No description!
    token_type: str = "bearer"
    expires_in: int  # No description!
```

**PaginatedResponse fields also lack descriptions.**

---

#### Issue 7: No Response Examples

Schemas lack `json_schema_extra` with examples, making Swagger UI less useful for testing.

---

## Uniform Documentation Standard

### Rule 1: FastAPI Application Metadata

**Every FastAPI app MUST include comprehensive metadata:**

```python
from fastapi import FastAPI

# Define tag metadata for endpoint grouping
tags_metadata = [
    {
        "name": "Authentication",
        "description": "Endpoints for user authentication and token management.",
    },
    {
        "name": "Users",
        "description": "User management operations. **Requires admin privileges.**",
    },
    {
        "name": "Data Providers",
        "description": "CRUD operations for data provider organizations.",
    },
    {
        "name": "Datasets",
        "description": "Dataset management within data providers.",
    },
    {
        "name": "XML Archives",
        "description": "XML archive management for datasets.",
    },
    {
        "name": "Useful Links",
        "description": "External link management for datasets.",
    },
    {
        "name": "Statistics",
        "description": "Registry statistics and metrics. Some endpoints are public.",
    },
    {
        "name": "Validation",
        "description": "XML archive validation job management.",
    },
    {
        "name": "Tasks",
        "description": "Background task management and monitoring.",
    },
    {
        "name": "System",
        "description": "Health checks and system status endpoints.",
    },
]

app = FastAPI(
    title="GFBio Dataset Management API",
    description="""
## Overview

The GFBio Dataset Management API provides comprehensive dataset cataloging
and management capabilities for the German Federation for Biological Data.

## Features

- **Data Provider Management** - Register and manage biological data providers
- **Dataset Cataloging** - Track datasets with XML archives and metadata
- **Validation** - Automated ABCD schema validation for XML archives
- **Statistics** - Real-time registry metrics and growth analytics

## Authentication

Most endpoints require JWT Bearer token authentication:

```
Authorization: Bearer <access_token>
```

Obtain tokens via `POST /api/v1/auth-token`.

## Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Login (`/auth-token`) | 5 requests/minute |
| Legacy harvest (`/legacy-data-sets`) | 30 requests/hour |
| CSRF token (`/csrf-token`) | 20 requests/minute |

## Pagination

List endpoints support pagination via query parameters:
- `skip` - Number of records to skip (default: 0)
- `limit` - Maximum records to return (default: 100, max: 1000)

## Versioning

This API uses URL path versioning. Current version: **v1**

All endpoints are prefixed with `/api/v1/`.
    """,
    version="2.0.0",
    contact={
        "name": "GFBio Development Team",
        "url": "https://www.gfbio.org",
        "email": "support@gfbio.org",
    },
    license_info={
        "name": "Apache 2.0",
        "identifier": "Apache-2.0",
    },
    openapi_tags=tags_metadata,
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
```

---

### Rule 2: Route Decorator Standard

**Every endpoint MUST include these decorator parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `response_model` | Yes | Pydantic model for success response |
| `summary` | Yes | Short (5-10 words) action description |
| `description` | Yes | Detailed markdown documentation |
| `tags` | Yes | List of applicable tags |
| `status_code` | Conditional | Required for non-200 responses |
| `responses` | Yes | Dict documenting error responses |
| `deprecated` | Conditional | Required if endpoint is deprecated |

**Example:**

```python
@v1_router.get(
    "/users/{username}",
    response_model=User,
    summary="Retrieve user by username",
    description="""
Fetch detailed user information by their unique username.

## Permissions

Requires **global admin** privileges.

## Response

Returns the complete user profile including:
- Username and admin status
- Provider role assignments
- Account timestamps

## Error Codes

| Code | Reason |
|------|--------|
| 401 | No valid authentication token |
| 403 | Authenticated user is not admin |
| 404 | Username does not exist |
    """,
    tags=["Users"],
    responses={
        200: {"description": "User found and returned successfully"},
        401: {"description": "Authentication required", "model": ErrorResponse},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
    },
)
```

---

### Rule 3: Docstring Standard (Google Style)

**All docstrings MUST follow Google Python Style Guide format:**

```python
async def get_user_endpoint(
    username: str = Path(..., description="Unique username identifier"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Retrieve a user by their username.

    Fetches the complete user profile including their provider role
    assignments. This endpoint is restricted to global administrators.

    Args:
        username: The unique username to look up. Case-sensitive.
        current_user: The authenticated user making the request.
            Injected by dependency.
        db: Async database session for the query. Injected by dependency.

    Returns:
        User: The complete user object with all profile data including
            username, admin status, and provider roles.

    Raises:
        HTTPException: 401 if no valid authentication token provided.
        HTTPException: 403 if the authenticated user is not a global admin.
        HTTPException: 404 if no user exists with the given username.

    Example:
        ```
        GET /api/v1/users/curator1
        Authorization: Bearer <admin_token>

        Response: {"username": "curator1", "is_global_admin": false, ...}
        ```

    Note:
        This endpoint performs a single database query with no caching.
        For bulk user retrieval, use the list endpoint with pagination.
    """
```

**Docstring Sections (in order):**

1. **Summary line** - One line, imperative mood ("Retrieve" not "Retrieves")
2. **Extended description** - Optional, detailed explanation
3. **Args** - All parameters with types and descriptions
4. **Returns** - Return type and description
5. **Raises** - All exceptions that can be raised
6. **Example** - Optional, usage example
7. **Note** - Optional, special considerations

---

### Rule 4: Path Parameter Documentation

**All path parameters MUST use `Path()` with:**

| Attribute | Required | Description |
|-----------|----------|-------------|
| `description` | Yes | What the parameter represents |
| `ge`/`le`/`gt`/`lt` | Conditional | Numeric constraints |
| `min_length`/`max_length` | Conditional | String length constraints |
| `pattern` | Conditional | Regex pattern for validation |
| `examples` | Recommended | List of example values |

**Examples:**

```python
from fastapi import Path

# Integer path parameter
async def get_provider(
    provider_id: int = Path(
        ...,
        description="Unique identifier of the data provider",
        ge=1,
        examples=[1, 42, 100],
    ),
):

# String path parameter
async def get_user(
    username: str = Path(
        ...,
        description="Unique username identifier",
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_-]+$",
        examples=["admin", "curator1", "data-manager"],
    ),
):
```

---

### Rule 5: Query Parameter Documentation

**All query parameters MUST use `Query()` with:**

| Attribute | Required | Description |
|-----------|----------|-------------|
| Default value | Yes | First positional argument |
| `description` | Yes | Clear explanation of filter/behavior |
| `ge`/`le` | Conditional | Value constraints |
| `min_length`/`max_length` | Conditional | String constraints |
| `examples` | Recommended | Typical values |
| `deprecated` | Conditional | If parameter is deprecated |

**Examples:**

```python
from fastapi import Query
from typing import Optional

async def list_datasets(
    # Optional filter parameter
    title: Optional[str] = Query(
        None,
        description="Filter datasets by title (case-insensitive partial match)",
        min_length=1,
        max_length=200,
        examples=["Fungi", "Marine Species", "Biodiversity"],
    ),
    # Optional filter parameter
    source: Optional[str] = Query(
        None,
        description="Filter datasets by data source identifier",
        examples=["GBIF", "PANGAEA"],
    ),
    # Pagination - skip
    skip: int = Query(
        0,
        ge=0,
        description="Number of records to skip for pagination",
        examples=[0, 10, 100],
    ),
    # Pagination - limit
    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Maximum number of records to return",
        examples=[10, 50, 100],
    ),
):
```

---

### Rule 6: Schema Field Documentation

**All Pydantic model fields MUST include:**

| Attribute | Required | Description |
|-----------|----------|-------------|
| `description` | Yes | Clear field explanation |
| `examples` | Recommended | Representative values |
| `ge`/`le`/`gt`/`lt` | Conditional | Numeric constraints |
| `min_length`/`max_length` | Conditional | String constraints |
| `pattern` | Conditional | Regex for string validation |

**Every schema MUST include `model_config` with `json_schema_extra` example:**

```python
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class TokenResponse(BaseModel):
    """Response model for successful authentication.

    Returned after successful login via POST /api/v1/auth-token.
    Contains JWT tokens for API authentication.
    """

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication. "
                    "Include in Authorization header as 'Bearer <token>'.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens "
                    "without re-authentication. Valid for 7 days.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header. Always 'bearer'.",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token validity duration in seconds. "
                    "Default is 1800 (30 minutes).",
        ge=1,
        examples=[1800, 3600],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTcwNDcwMDAwMH0.abc123",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTcwNTMwMDAwMH0.xyz789",
                "token_type": "bearer",
                "expires_in": 1800,
            }
        }
    )
```

---

### Rule 7: Error Response Model

**Define a standard error response model used across all endpoints:**

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class ErrorDetail(BaseModel):
    """Individual field-level error detail for validation errors."""

    field: str = Field(
        ...,
        description="Name of the field that caused the error",
        examples=["username", "provider_id"],
    )
    message: str = Field(
        ...,
        description="Human-readable error message for this field",
        examples=["Field is required", "Must be at least 3 characters"],
    )


class ErrorResponse(BaseModel):
    """Standard error response model for all API errors.

    All 4xx and 5xx responses use this format for consistency.
    """

    detail: str = Field(
        ...,
        description="Human-readable error message summarizing the problem",
        examples=["User not found", "Invalid credentials", "Permission denied"],
    )
    code: str = Field(
        ...,
        description="Machine-readable error code for programmatic handling",
        examples=["not_found", "unauthorized", "forbidden", "validation_error"],
    )
    path: Optional[str] = Field(
        None,
        description="Request path that caused the error",
        examples=["/api/v1/users/unknown", "/api/v1/data-providers/999"],
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp when the error occurred (ISO 8601 format)",
    )
    errors: Optional[List[ErrorDetail]] = Field(
        None,
        description="List of field-level validation errors. "
                    "Only present for 422 Validation Error responses.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": {
                "not_found": {
                    "summary": "Resource Not Found",
                    "value": {
                        "detail": "User not found",
                        "code": "not_found",
                        "path": "/api/v1/users/unknown",
                        "timestamp": "2024-01-08T12:00:00Z",
                    },
                },
                "unauthorized": {
                    "summary": "Not Authenticated",
                    "value": {
                        "detail": "Not authenticated",
                        "code": "not_authenticated",
                        "path": "/api/v1/users",
                        "timestamp": "2024-01-08T12:00:00Z",
                    },
                },
                "validation_error": {
                    "summary": "Validation Error",
                    "value": {
                        "detail": "Validation error",
                        "code": "validation_error",
                        "path": "/api/v1/users",
                        "timestamp": "2024-01-08T12:00:00Z",
                        "errors": [
                            {"field": "username", "message": "Field is required"},
                            {"field": "password", "message": "Must be at least 8 characters"},
                        ],
                    },
                },
            }
        }
    )
```

---

### Rule 8: Endpoint Responses Dictionary

**Define reusable response definitions and use them consistently:**

```python
from app.schemas.errors import ErrorResponse

# Reusable response definitions
RESPONSE_401_UNAUTHORIZED = {
    "description": "Authentication required - no valid token provided",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": {
                "detail": "Not authenticated",
                "code": "not_authenticated",
                "path": "/api/v1/resource",
                "timestamp": "2024-01-08T12:00:00Z",
            }
        }
    },
}

RESPONSE_403_FORBIDDEN = {
    "description": "Forbidden - insufficient permissions for this operation",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": {
                "detail": "Admin privileges required",
                "code": "forbidden",
                "path": "/api/v1/resource",
                "timestamp": "2024-01-08T12:00:00Z",
            }
        }
    },
}

RESPONSE_404_NOT_FOUND = {
    "description": "Resource not found",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": {
                "detail": "Resource not found",
                "code": "not_found",
                "path": "/api/v1/resource/123",
                "timestamp": "2024-01-08T12:00:00Z",
            }
        }
    },
}

RESPONSE_422_VALIDATION = {
    "description": "Validation error - invalid request data",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": {
                "detail": "Validation error",
                "code": "validation_error",
                "path": "/api/v1/resource",
                "timestamp": "2024-01-08T12:00:00Z",
                "errors": [
                    {"field": "name", "message": "Field is required"}
                ],
            }
        }
    },
}

RESPONSE_500_INTERNAL = {
    "description": "Internal server error - unexpected error occurred",
    "model": ErrorResponse,
    "content": {
        "application/json": {
            "example": {
                "detail": "An unexpected error occurred",
                "code": "internal_server_error",
                "path": "/api/v1/resource",
                "timestamp": "2024-01-08T12:00:00Z",
            }
        }
    },
}

# Common responses bundle for authenticated endpoints
COMMON_AUTH_RESPONSES = {
    401: RESPONSE_401_UNAUTHORIZED,
    403: RESPONSE_403_FORBIDDEN,
    422: RESPONSE_422_VALIDATION,
    500: RESPONSE_500_INTERNAL,
}

# Usage in endpoints:
@v1_router.get(
    "/users/{username}",
    response_model=User,
    responses={
        **COMMON_AUTH_RESPONSES,
        404: RESPONSE_404_NOT_FOUND,
    },
)
async def get_user(...):
```

---

### Rule 9: Authentication Documentation

**Endpoints requiring authentication MUST document it clearly:**

```python
@v1_router.delete(
    "/data-providers/{provider_id}",
    status_code=204,
    summary="Delete data provider",
    description="""
Delete a data provider and all associated datasets.

## Authentication

**Required:** Bearer token with **global admin** privileges.

```
Authorization: Bearer <access_token>
```

## Permissions

Only users with `is_global_admin=true` can perform this operation.
Provider-level admin roles are not sufficient.

## Side Effects

This operation performs a **cascade deletion**:

| Entity | Action |
|--------|--------|
| Datasets | Deleted |
| XML Archives | Deleted |
| Useful Links | Deleted |
| Archive Snapshots | Deleted |
| Validation Jobs | Deleted |
| Related Cache | Invalidated |

## Warning

This operation **cannot be undone**. All associated data will be
permanently deleted from the database.
    """,
    tags=["Data Providers"],
    responses={
        204: {"description": "Provider successfully deleted"},
        **COMMON_AUTH_RESPONSES,
        404: {"description": "Provider not found", "model": ErrorResponse},
    },
)
```

---

### Rule 10: Deprecation Marking

**Deprecated endpoints MUST be clearly marked:**

```python
@v1_router.get(
    "/legacy-data-sets",
    response_model=List[LegacyDataset],
    deprecated=True,
    summary="[DEPRECATED] Legacy dataset harvest endpoint",
    description="""
## Deprecation Notice

> **Warning:** This endpoint is deprecated and will be removed in **v3.0.0**.

### Migration Guide

Use the new paginated endpoints instead:

| Old Endpoint | New Endpoint |
|--------------|--------------|
| `GET /legacy-data-sets` | `GET /data-providers` with pagination |

### New Approach

```python
# Fetch all providers with their datasets
GET /api/v1/data-providers?skip=0&limit=100

# For each provider, fetch datasets
GET /api/v1/data-providers/{id}/data-sets?skip=0&limit=100
```

### Reason for Deprecation

- Returns unbounded result set (no pagination)
- Uses legacy field naming conventions
- Performance issues with large datasets
- Inconsistent with REST API best practices

### Timeline

| Version | Status |
|---------|--------|
| v2.0.0 | Deprecated (current) |
| v2.5.0 | Warning headers added |
| v3.0.0 | **Removed** |
    """,
    tags=["System"],
    responses={
        200: {"description": "Legacy datasets returned"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
```

---

## Documentation Checklist

Use this checklist when creating or reviewing API endpoints:

### API Level

- [ ] `title` - Clear, descriptive API title
- [ ] `description` - Comprehensive markdown overview with features, auth, rate limits
- [ ] `version` - Semantic versioning (e.g., "2.0.0")
- [ ] `contact` - Name, email, URL for support
- [ ] `license_info` - License name and identifier
- [ ] `openapi_tags` - Tag metadata with descriptions for all endpoint groups

### Endpoint Level

- [ ] `summary` - 5-10 word action description (imperative mood)
- [ ] `description` - Markdown with auth requirements, permissions, side effects
- [ ] `tags` - At least one relevant tag from defined tags
- [ ] `response_model` - Pydantic schema for success response
- [ ] `status_code` - Explicit status code (especially 201, 204)
- [ ] `responses` - Dict with all possible error responses (401, 403, 404, 422, 500)
- [ ] `deprecated` - Flag set if endpoint is deprecated

### Parameter Level

- [ ] **Path params** - Use `Path()` with description, constraints, examples
- [ ] **Query params** - Use `Query()` with description, constraints, examples
- [ ] **Body params** - Use `Body()` or Pydantic model with field documentation
- [ ] **All params** - Have appropriate validation constraints (ge, le, min_length, etc.)

### Schema Level

- [ ] **Class docstring** - Explains the model's purpose and usage
- [ ] **Field descriptions** - Every field has a description via `Field()`
- [ ] **Field examples** - Every field has examples via `Field()` or `json_schema_extra`
- [ ] **Constraints** - All applicable constraints (min_length, ge, le, pattern)
- [ ] **model_config** - Include `json_schema_extra` with complete example

### Docstring Level (Google Style)

- [ ] **Summary line** - One line, imperative mood, ends with period
- [ ] **Extended description** - Present if operation is complex
- [ ] **Args section** - All parameters documented with types
- [ ] **Returns section** - Return type and description
- [ ] **Raises section** - All HTTPException codes documented
- [ ] **Example section** - Present for complex operations
- [ ] **Note section** - Present if special considerations exist

---

## Priority Fixes

Prioritized list of documentation improvements for this codebase:

### Priority 0 - Critical (Do First)

| Issue | Files | Effort | Impact |
|-------|-------|--------|--------|
| Add tags to all endpoints | `main.py`, all endpoint files | Low | High |
| Add FastAPI app description & metadata | `main.py:198-204` | Low | High |
| Create ErrorResponse schema | `app/schemas/errors.py` (new) | Low | High |

### Priority 1 - High

| Issue | Files | Effort | Impact |
|-------|-------|--------|--------|
| Standardize all docstrings to Google style | All API files | Medium | High |
| Add `responses` dict for errors to all endpoints | All API files | Medium | High |
| Document all path parameters with `Path()` | `main.py`, `validators.py` | Low | Medium |

### Priority 2 - Medium

| Issue | Files | Effort | Impact |
|-------|-------|--------|--------|
| Add Field descriptions to all schema fields | All schema files | Medium | Medium |
| Add `json_schema_extra` examples to all schemas | All schema files | Medium | Medium |
| Add `description` parameter to all endpoints | All API files | Medium | Medium |

### Priority 3 - Low

| Issue | Files | Effort | Impact |
|-------|-------|--------|--------|
| Add deprecation flag to legacy endpoint | `main.py:1667` | Low | Low |
| Add rate limit documentation to endpoint descriptions | `main.py` | Low | Low |
| Add example requests to complex endpoint docstrings | All API files | Medium | Low |

---

## Examples

### Complete Endpoint Example

Here's a fully documented endpoint following all rules:

```python
from fastapi import APIRouter, Depends, Path, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db import get_db
from app.models import UserModel, DataProviderModel
from app.schemas import DataProvider
from app.schemas.errors import ErrorResponse, COMMON_AUTH_RESPONSES
from app.security import get_current_user
from app.security.permissions import check_provider_permission

router = APIRouter()


@router.get(
    "/data-providers/{provider_id}",
    response_model=DataProvider,
    summary="Retrieve data provider by ID",
    description="""
Fetch detailed information about a specific data provider.

## Authentication

**Required:** Bearer token authentication.

```
Authorization: Bearer <access_token>
```

## Permissions

User must have at least **read** permission for this provider:
- Global admins can access all providers
- Users with provider roles can access their assigned providers

## Response

Returns the complete provider profile including:
- Basic information (name, datacenter, URLs)
- All associated datasets with archives and links
- Data center status flag

## Caching

Responses are cached for 5 minutes. Cache is invalidated on provider updates.
    """,
    tags=["Data Providers"],
    responses={
        200: {"description": "Provider found and returned successfully"},
        400: {
            "description": "Invalid provider ID format",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Provider ID must be a positive integer",
                        "code": "bad_request",
                        "path": "/api/v1/data-providers/0",
                        "timestamp": "2024-01-08T12:00:00Z",
                    }
                }
            },
        },
        **COMMON_AUTH_RESPONSES,
        404: {
            "description": "Provider not found",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Provider not found",
                        "code": "not_found",
                        "path": "/api/v1/data-providers/999",
                        "timestamp": "2024-01-08T12:00:00Z",
                    }
                }
            },
        },
    },
)
async def get_provider(
    provider_id: int = Path(
        ...,
        description="Unique identifier of the data provider to retrieve",
        ge=1,
        examples=[1, 42, 100],
    ),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DataProvider:
    """Retrieve a data provider by its unique identifier.

    Fetches the complete provider profile including all associated datasets,
    XML archives, and useful links. The response is cached for 5 minutes.

    Args:
        provider_id: The unique identifier of the provider. Must be a
            positive integer.
        current_user: The authenticated user making the request. Used for
            permission checking. Injected by FastAPI dependency.
        db: Async database session for executing queries. Injected by
            FastAPI dependency.

    Returns:
        DataProvider: Complete provider object with nested datasets,
            including all XML archives and useful links for each dataset.

    Raises:
        HTTPException: 400 if provider_id is not a positive integer.
        HTTPException: 401 if no valid authentication token is provided.
        HTTPException: 403 if user lacks read permission for this provider.
        HTTPException: 404 if no provider exists with the given ID.

    Example:
        ```
        GET /api/v1/data-providers/42
        Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

        Response:
        {
            "id": 42,
            "name": "Museum of Natural History",
            "shortName": "MNH",
            "datacenter": "Berlin",
            "url": "https://mnh.example.org",
            "datasets": [...]
        }
        ```

    Note:
        For listing multiple providers, use GET /data-providers with
        pagination parameters instead of making multiple single requests.
    """
    # Validate provider_id
    if provider_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provider ID must be a positive integer",
        )

    # Check permissions
    check_provider_permission(provider_id, current_user, "read")

    # Fetch provider from database
    provider = await get_provider_by_id(db, provider_id)

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Provider not found",
        )

    return provider
```

### Complete Schema Example

Here's a fully documented Pydantic schema following all rules:

```python
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict, AnyUrl, field_validator


class DataProvider(BaseModel):
    """Data provider organization schema.

    Represents a biological data provider organization that contributes
    datasets to the GFBio registry. Providers are typically research
    institutions, museums, or data centers.

    Used for:
    - Response model for GET /data-providers/{id}
    - Request/Response model for POST/PUT /data-providers
    - Nested in dataset responses
    """

    id: Optional[int] = Field(
        None,
        description="Unique identifier for the provider. "
                    "Auto-generated on creation, read-only.",
        ge=1,
        examples=[1, 42, 100],
    )
    datacenter: str = Field(
        ...,
        description="Name of the data center or institution hosting the data. "
                    "Used for organizational grouping.",
        min_length=1,
        max_length=200,
        examples=["Berlin", "Munich", "Hamburg"],
    )
    shortName: str = Field(
        ...,
        description="Short identifier or acronym for the provider. "
                    "Should be unique and recognizable.",
        min_length=1,
        max_length=50,
        examples=["MfN", "SNSB", "SMNS"],
    )
    name: str = Field(
        ...,
        description="Full official name of the data provider organization.",
        min_length=1,
        max_length=500,
        examples=[
            "Museum für Naturkunde Berlin",
            "Staatliche Naturwissenschaftliche Sammlungen Bayerns",
        ],
    )
    url: Optional[AnyUrl] = Field(
        None,
        description="Official website URL of the provider organization.",
        examples=["https://www.museumfuernaturkunde.berlin"],
    )
    biocaseUrl: Optional[AnyUrl] = Field(
        None,
        description="BioCASe portal URL for accessing the provider's data. "
                    "Used for data harvesting and synchronization.",
        examples=["https://biocase.mfn-berlin.de"],
    )
    isDataCenter: bool = Field(
        default=False,
        description="Flag indicating if this provider is a data center "
                    "(aggregates data from multiple sources) rather than "
                    "a primary data provider. Only modifiable by global admins.",
    )
    datasets: Optional[List["Dataset"]] = Field(
        None,
        description="List of datasets contributed by this provider. "
                    "Populated in detail responses, may be null in list responses.",
    )
    created_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the provider was registered. "
                    "Auto-generated, read-only.",
    )
    updated_at: Optional[datetime] = Field(
        None,
        description="Timestamp of last provider update. "
                    "Auto-updated on modifications, read-only.",
    )

    @field_validator("datacenter", "shortName", "name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Remove leading and trailing whitespace from string fields."""
        if isinstance(v, str):
            return v.strip()
        return v

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={AnyUrl: str},
        json_schema_extra={
            "example": {
                "id": 42,
                "datacenter": "Berlin",
                "shortName": "MfN",
                "name": "Museum für Naturkunde Berlin",
                "url": "https://www.museumfuernaturkunde.berlin",
                "biocaseUrl": "https://biocase.mfn-berlin.de",
                "isDataCenter": False,
                "datasets": [
                    {
                        "id": 101,
                        "source": "MfN-Collection",
                        "title": "Entomology Collection",
                        "landingPageUrl": "https://www.museumfuernaturkunde.berlin/entomology",
                    }
                ],
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-08T12:00:00Z",
            }
        },
    )
```

---

## Conclusion

Implementing these 10 rules consistently across all API endpoints will transform the documentation from 60% to 95%+ completeness. The key improvements are:

1. **Consistency** - Single format for docstrings (Google style)
2. **Discoverability** - Tag-based grouping in Swagger UI
3. **Completeness** - All parameters and errors documented
4. **Usability** - Examples throughout for easy testing
5. **Maintainability** - Reusable response definitions

Start with Priority 0 items (tags, app metadata, error schema) for immediate high-impact improvements with minimal effort.
