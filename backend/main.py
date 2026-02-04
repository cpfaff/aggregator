import logging
import time
import uuid
from datetime import datetime

# Import shared API dependencies
from app.api.deps import csrf_protect, limiter, provider_permission
from app.core.cache import cache_response, invalidate_cache

# Import application components
from app.core.config import settings
from app.core.utils import apply_entity_updates
from app.db import get_db
from app.models import (
    DataProviderModel,
    DatasetModel,
    UsefulLinkModel,
    UserModel,
    XmlArchiveModel,
)
from app.schemas import (
    DataProvider,
    Dataset,
    LegacyDataset,
    LegacyUsefulLink,
    LegacyXmlArchive,
    UsefulLink,
    XmlArchive,
)
from app.security import (
    check_global_admin,
    get_current_user,
    normalize_provider_roles,
)
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pythonjsonlogger import jsonlogger

# Import slowapi components for rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.middleware.base import BaseHTTPMiddleware

# ------------------- Logging Configuration -------------------
log_handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
log_handler.setFormatter(formatter)

logger = logging.getLogger("api")
logger.addHandler(log_handler)
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# ------------------- Database Setup -------------------
# Database configuration moved to app.db module
# - Engine configuration in app.db.base
# - Session management in app.db.session


# ------------------- Helper Functions -------------------
def trim_string(value: str):
    """Remove leading and trailing whitespace from a string."""
    if value is None:
        return None
    return value.strip()


# ------------------- Create FastAPI app and routers -------------------
app = FastAPI(
    title="Dataset Management API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Legacy router for old endpoints defined in main.py
# These should be migrated to the modular routers in app/api/v1/endpoints/
v1_router = APIRouter(prefix="/api/v1")

# Register rate limiter with the app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ------------------- CORS Middleware -------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)


# ------------------- Security Headers Middleware -------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)


# ------------------- Request Logging Middleware -------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and their completion status."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    logger.info(
        f"Request started: {request.method} {request.url.path}",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        },
    )
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Request-ID"] = request_id
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request failed: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": process_time,
            },
            exc_info=True,
        )
        raise


# ------------------- Exception Handlers -------------------
class ErrorResponse(BaseModel):
    detail: str
    code: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    path: str | None = None


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed field-specific messages."""
    logger.warning(
        f"Validation error at {request.url.path}",
        extra={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "path": request.url.path,
            "errors": exc.errors(),
        },
    )
    errors = [
        {
            "field": error.get("loc", ["unknown"])[-1],
            "message": error.get("msg", "Unknown error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "code": "validation_error",
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat(),
            "errors": errors,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "code": "http_exception",
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with logging."""
    logger.error(
        f"Unhandled exception at {request.url.path}",
        extra={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "code": "internal_server_error",
            "path": str(request.url.path),
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ------------------- Endpoints -------------------
# Note: Auth endpoints (csrf-token, auth-token, refresh-token) moved to app/api/v1/endpoints/auth.py
# Note: Health check endpoint moved to app/api/v1/endpoints/health.py
# Note: User endpoints (users, me/permissions, provider associations) moved to app/api/v1/endpoints/users.py


# Data Provider Endpoints
@v1_router.get("/data-providers", response_model=list[DataProvider], summary="List data providers")
@cache_response(prefix="providers", ttl_seconds=300)
async def get_providers(
    name: str | None = Query(None, description="Filter by provider name"),
    datacenter: str | None = Query(None, description="Filter by datacenter"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all data providers the current user has access to.

    Supports filtering by name or datacenter and pagination with skip/limit.
    """
    # Base query with filters
    query = select(DataProviderModel)

    # Apply text search filters if provided
    if name:
        query = query.filter(DataProviderModel.name.ilike(f"%{name}%"))
    if datacenter:
        query = query.filter(DataProviderModel.datacenter.ilike(f"%{datacenter}%"))

    # Apply permission filtering
    if not current_user.is_global_admin:
        # For non-admin users, filter by allowed provider IDs
        allowed_ids = [
            int(key)
            for key in normalize_provider_roles(current_user.provider_roles).keys()
            if key.isdigit()
        ]
        if not allowed_ids:
            return []
        query = query.filter(DataProviderModel.id.in_(allowed_ids))

    # Add eager loading for related entities
    query = query.options(
        selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
        selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
    )

    # Add consistent ordering by ID
    query = query.order_by(DataProviderModel.id)

    # Execute query with pagination
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@v1_router.get(
    "/data-providers/{provider_id}",
    response_model=DataProvider,
    summary="Get data provider by ID",
)
@cache_response(prefix="provider", ttl_seconds=300)
async def get_provider(
    provider_id: int,
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a data provider by its ID. Requires appropriate permissions.
    - **provider_id**: Must be a positive integer
    """
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

    result = await db.execute(
        select(DataProviderModel)
        .where(DataProviderModel.id == provider_id)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )
    )
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    return provider


@csrf_protect.validate_csrf
@v1_router.post(
    "/data-providers",
    response_model=DataProvider,
    status_code=201,
    summary="Create a new data provider",
)
async def create_provider(
    provider: DataProvider,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new data provider. Requires global admin privileges.
    - **datacenter**: Datacenter name
    - **shortName**: Short name of the provider
    - **name**: Full name of the provider
    - **url**: Optional provider URL
    - **biocaseUrl**: Optional BioCASe URL
    - **isDataCenter**: Optional boolean indicating if the provider is a data center (global admin only)
    - **datasets**: Optional list of datasets
    """
    check_global_admin(current_user)
    provider_data = provider.model_dump(exclude={"datasets", "id"}, exclude_unset=True)
    if provider_data.get("url"):
        provider_data["url"] = str(provider_data["url"])
    if provider_data.get("biocaseUrl"):
        provider_data["biocaseUrl"] = str(provider_data["biocaseUrl"])
    provider_obj = DataProviderModel(**provider_data)
    if provider.datasets:
        for dataset in provider.datasets:
            dataset_data = dataset.model_dump(
                exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
            )
            if dataset_data.get("landingPageUrl"):
                dataset_data["landingPageUrl"] = (
                    str(dataset_data["landingPageUrl"]) if dataset_data["landingPageUrl"] else None
                )
            db_dataset = DatasetModel(**dataset_data)
            if dataset.xmlArchives and len(dataset.xmlArchives) > 0:
                for archive in dataset.xmlArchives:
                    db_dataset.xmlArchives.append(
                        XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
                    )
            if dataset.usefulLinks and len(dataset.usefulLinks) > 0:
                for link in dataset.usefulLinks:
                    db_dataset.usefulLinks.append(
                        UsefulLinkModel(title=link.title, url=str(link.url), isLatest=link.isLatest)
                    )
            provider_obj.datasets.append(db_dataset)
    db.add(provider_obj)
    await db.commit()
    await db.refresh(provider_obj)
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )
        .where(DataProviderModel.id == provider_obj.id)
    )

    # Invalidate provider caches
    invalidate_cache("providers")

    return result.scalar_one()


@csrf_protect.validate_csrf
@v1_router.put(
    "/data-providers/{provider_id}",
    response_model=DataProvider,
    summary="Update data provider",
)
async def update_provider(
    provider_id: int,
    provider: DataProvider,
    current_user: UserModel = Depends(provider_permission("write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a data provider. Requires write permissions for the provider.
    - **provider_id**: Must be a positive integer

    Note: The isDataCenter field can only be modified by global admins.
    """
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )
        .where(DataProviderModel.id == provider_id)
    )
    db_provider = result.scalar_one_or_none()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    # Check if isDataCenter field is being updated
    provider_data = provider.model_dump(exclude={"datasets", "id"}, exclude_unset=True)

    # Only allow global admins to modify isDataCenter field
    if "isDataCenter" in provider_data and not current_user.is_global_admin:
        # Remove isDataCenter from update if user is not a global admin
        del provider_data["isDataCenter"]

    if provider_data.get("url"):
        provider_data["url"] = str(provider_data["url"])
    if provider_data.get("biocaseUrl"):
        provider_data["biocaseUrl"] = str(provider_data["biocaseUrl"])
    for key, value in provider_data.items():
        setattr(db_provider, key, value)
    async with db.begin_nested():
        # Only process datasets if they were explicitly included in the request
        if "datasets" in provider.model_dump(exclude_unset=True) and provider.datasets is not None:
            existing_datasets = {ds.id: ds for ds in db_provider.datasets if ds.id is not None}
            processed_dataset_ids = set()
            updated_datasets = []
            for dataset in provider.datasets:
                if dataset.id is not None and dataset.id in existing_datasets:
                    db_dataset = existing_datasets[dataset.id]
                    processed_dataset_ids.add(dataset.id)
                    dataset_data = dataset.model_dump(
                        exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
                    )
                    if "landingPageUrl" in dataset_data:
                        dataset_data["landingPageUrl"] = (
                            str(dataset_data["landingPageUrl"])
                            if dataset_data["landingPageUrl"]
                            else None
                        )
                    for key, value in dataset_data.items():
                        setattr(db_dataset, key, value)

                    # Update XML archives using the extracted utility function
                    if dataset.xmlArchives is not None:
                        new_archives = await apply_entity_updates(
                            db,
                            db_dataset.xmlArchives,
                            dataset.xmlArchives,
                            XmlArchiveModel,
                            db_dataset.id,
                        )
                        if new_archives:
                            db_dataset.xmlArchives = new_archives

                    # Update useful links using the extracted utility function
                    if dataset.usefulLinks is not None:
                        new_links = await apply_entity_updates(
                            db,
                            db_dataset.usefulLinks,
                            dataset.usefulLinks,
                            UsefulLinkModel,
                            db_dataset.id,
                        )
                        if new_links:
                            db_dataset.usefulLinks = new_links

                    updated_datasets.append(db_dataset)
                else:
                    new_dataset = DatasetModel(
                        provider_id=db_provider.id,
                        source=dataset.source,
                        title=dataset.title,
                        landingPageUrl=str(dataset.landingPageUrl)
                        if dataset.landingPageUrl
                        else None,
                    )
                    if dataset.xmlArchives:
                        for archive in dataset.xmlArchives:
                            new_dataset.xmlArchives.append(
                                XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
                            )
                    if dataset.usefulLinks:
                        for link in dataset.usefulLinks:
                            new_dataset.usefulLinks.append(
                                UsefulLinkModel(
                                    title=link.title,
                                    url=str(link.url),
                                    isLatest=link.isLatest,
                                )
                            )
                    updated_datasets.append(new_dataset)
            db_provider.datasets = updated_datasets
    await db.commit()
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )
        .where(DataProviderModel.id == provider_id)
    )

    # Invalidate provider caches
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("providers")

    # Trigger snapshot collection for any archives to capture unit count
    provider_result = result.scalar_one()
    if provider.datasets is not None:
        from app.tasks.snapshot_tasks import collect_single_archive_snapshot

        for dataset in provider_result.datasets:
            for archive in dataset.xmlArchives:
                collect_single_archive_snapshot.delay(archive.id)

    return provider_result


@csrf_protect.validate_csrf
@v1_router.delete("/data-providers/{provider_id}", status_code=204, summary="Delete data provider")
async def delete_provider(
    provider_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a data provider. Requires global admin privileges.
    - **provider_id**: Must be a positive integer
    """
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")
    check_global_admin(current_user)
    result = await db.execute(select(DataProviderModel).where(DataProviderModel.id == provider_id))
    provider = result.scalar_one_or_none()
    if provider:
        await db.delete(provider)
        await db.commit()

        # Invalidate provider caches
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")
        invalidate_cache("datasets")
    return


# Dataset Endpoints
@v1_router.get(
    "/data-providers/{provider_id}/data-sets",
    response_model=list[Dataset],
    summary="List datasets for provider",
)
@cache_response(prefix="datasets", ttl_seconds=300)
async def get_datasets(
    provider_id: int,
    title: str | None = Query(None, description="Filter by dataset title"),
    source: str | None = Query(None, description="Filter by dataset source"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of items to return"),
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all datasets for a specific data provider. Requires read permissions.
    - **provider_id**: Must be a positive integer

    Supports filtering by title or source and pagination with skip/limit.
    """
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

    # Base query
    query = select(DatasetModel).where(DatasetModel.provider_id == provider_id)

    # Apply filters if provided
    if title:
        query = query.filter(DatasetModel.title.ilike(f"%{title}%"))
    if source:
        query = query.filter(DatasetModel.source.ilike(f"%{source}%"))

    # Add eager loading
    query = query.options(
        selectinload(DatasetModel.xmlArchives), selectinload(DatasetModel.usefulLinks)
    )

    # Apply pagination
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    return result.scalars().all()


@v1_router.get(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    response_model=Dataset,
    summary="Get dataset by ID",
)
@cache_response(prefix="dataset", ttl_seconds=300)
async def get_dataset(
    provider_id: int,
    dataset_id: int,
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a dataset by its ID for a specific provider. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(DatasetModel)
        .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks),
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@csrf_protect.validate_csrf
@v1_router.post(
    "/data-providers/{provider_id}/data-sets",
    response_model=Dataset,
    status_code=201,
    summary="Create a new dataset",
)
async def create_dataset(
    provider_id: int,
    dataset: Dataset,
    current_user: UserModel = Depends(provider_permission("write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new dataset for a specific provider. Requires write permissions.
    - **provider_id**: Must be a positive integer
    """
    if provider_id <= 0:
        raise HTTPException(status_code=400, detail="Provider ID must be a positive integer")

    result = await db.execute(select(DataProviderModel).where(DataProviderModel.id == provider_id))
    provider = result.scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    dataset_data = dataset.model_dump(
        exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
    )
    if dataset_data.get("landingPageUrl"):
        dataset_data["landingPageUrl"] = str(dataset_data["landingPageUrl"])
    dataset_obj = DatasetModel(**dataset_data, provider_id=provider_id)
    if dataset.xmlArchives:
        for archive in dataset.xmlArchives:
            dataset_obj.xmlArchives.append(
                XmlArchiveModel(url=str(archive.url), isLatest=archive.isLatest)
            )
    if dataset.usefulLinks:
        for link in dataset.usefulLinks:
            dataset_obj.usefulLinks.append(
                UsefulLinkModel(title=link.title, url=str(link.url), isLatest=link.isLatest)
            )
    db.add(dataset_obj)
    await db.commit()
    await db.refresh(dataset_obj)
    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks),
        )
        .where(DatasetModel.id == dataset_obj.id)
    )

    # Invalidate dataset and provider caches
    invalidate_cache("datasets")
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("providers")

    # Trigger snapshot collection for any archives created with this dataset
    dataset_result = result.scalar_one()
    if dataset_result.xmlArchives:
        from app.tasks.snapshot_tasks import collect_single_archive_snapshot

        for archive in dataset_result.xmlArchives:
            collect_single_archive_snapshot.delay(archive.id)

    return dataset_result


@csrf_protect.validate_csrf
@v1_router.put(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    response_model=Dataset,
    summary="Update dataset",
)
async def update_dataset(
    provider_id: int,
    dataset_id: int,
    dataset: Dataset,
    current_user: UserModel = Depends(provider_permission("write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a dataset for a specific provider. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks),
        )
        .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
    )
    db_dataset = result.scalar_one_or_none()
    if not db_dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    dataset_data = dataset.model_dump(
        exclude={"id", "xmlArchives", "usefulLinks"}, exclude_unset=True
    )
    if dataset_data.get("landingPageUrl"):
        dataset_data["landingPageUrl"] = str(dataset_data["landingPageUrl"])
    for key, value in dataset_data.items():
        setattr(db_dataset, key, value)

    # Update XML archives
    if dataset.xmlArchives is not None:
        new_archives = await apply_entity_updates(
            db,
            db_dataset.xmlArchives,
            dataset.xmlArchives,
            XmlArchiveModel,
            db_dataset.id,
        )
        if new_archives:
            db_dataset.xmlArchives = new_archives

    # Update useful links
    if dataset.usefulLinks is not None:
        new_links = await apply_entity_updates(
            db,
            db_dataset.usefulLinks,
            dataset.usefulLinks,
            UsefulLinkModel,
            db_dataset.id,
        )
        if new_links:
            db_dataset.usefulLinks = new_links

    await db.commit()
    result = await db.execute(
        select(DatasetModel)
        .options(
            selectinload(DatasetModel.xmlArchives),
            selectinload(DatasetModel.usefulLinks),
        )
        .where(DatasetModel.id == dataset_id)
    )

    # Invalidate dataset and provider caches
    invalidate_cache(f"dataset:{dataset_id}")
    invalidate_cache("datasets")
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("providers")

    # Trigger snapshot collection for any new archives to capture unit count
    dataset_result = result.scalar_one()
    if dataset.xmlArchives is not None:
        from app.tasks.snapshot_tasks import collect_single_archive_snapshot

        for archive in dataset_result.xmlArchives:
            # Only trigger for archives that don't have snapshots yet
            # The task will handle the isLatest check
            collect_single_archive_snapshot.delay(archive.id)

    return dataset_result


@csrf_protect.validate_csrf
@v1_router.delete(
    "/data-providers/{provider_id}/data-sets/{dataset_id}",
    status_code=204,
    summary="Delete dataset",
)
async def delete_dataset(
    provider_id: int,
    dataset_id: int,
    current_user: UserModel = Depends(provider_permission("delete")),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a dataset for a specific provider. Requires delete permissions.

    This performs a complete cascade deletion, removing:
    - All statistics records for the dataset
    - All validation jobs for the dataset's archives
    - All XML archives
    - All useful links
    - The dataset itself

    After deletion, provider statistics are automatically re-aggregated.

    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    # First verify the dataset exists and belongs to this provider
    result = await db.execute(
        select(DatasetModel).where(
            DatasetModel.id == dataset_id, DatasetModel.provider_id == provider_id
        )
    )
    dataset_obj = result.scalar_one_or_none()
    if not dataset_obj:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Use the cascade deletion service
    from app.services.dataset_deletion import DatasetDeletionService

    deletion_service = DatasetDeletionService(db)

    try:
        # Perform cascade deletion
        deletion_summary = await deletion_service.delete_dataset_cascade(
            dataset_id=dataset_id, provider_id=provider_id
        )

        # Log the deletion summary
        logger.info(f"Dataset {dataset_id} cascade deletion completed: {deletion_summary}")

        # Invalidate dataset and provider caches
        invalidate_cache(f"dataset:{dataset_id}")
        invalidate_cache("datasets")
        invalidate_cache(f"provider:{provider_id}")
        invalidate_cache("providers")

        # Return deletion summary for transparency
        return {
            "message": "Dataset and all associated data deleted successfully",
            "deletion_summary": deletion_summary,
        }

    except Exception as e:
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete dataset: {str(e)}")


# XML Archive Endpoints
@v1_router.get(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/xml-archives",
    response_model=list[XmlArchive],
    summary="List XML archives",
)
@cache_response(prefix="xml-archives", ttl_seconds=300)
async def get_xml_archives(
    provider_id: int,
    dataset_id: int,
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all XML archives for a specific dataset. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(XmlArchiveModel)
        .join(DatasetModel)
        .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
    )
    return result.scalars().all()


@csrf_protect.validate_csrf
@v1_router.post(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/xml-archives",
    response_model=XmlArchive,
    status_code=201,
    summary="Create XML archive",
)
async def create_xml_archive(
    provider_id: int,
    dataset_id: int,
    xml_archive: XmlArchive,
    current_user: UserModel = Depends(provider_permission("write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new XML archive for a specific dataset. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(DatasetModel).where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    xml_data = xml_archive.model_dump(exclude={"id"}, exclude_unset=True)
    if xml_data.get("url"):
        xml_data["url"] = str(xml_data["url"])
    xml_obj = XmlArchiveModel(**xml_data, dataset_id=dataset_id)
    db.add(xml_obj)
    await db.commit()
    await db.refresh(xml_obj)

    # Invalidate related caches
    invalidate_cache(f"dataset:{dataset_id}")
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("xml-archives")
    invalidate_cache("providers")
    invalidate_cache("datasets")

    # Automatically trigger validation task
    from app.tasks.validator_tasks import validate_archive

    validate_archive.delay(xml_obj.id)

    # Trigger snapshot collection for this archive to capture unit count immediately
    from app.tasks.snapshot_tasks import collect_single_archive_snapshot

    collect_single_archive_snapshot.delay(xml_obj.id)

    return xml_obj


# Useful Link Endpoints
@v1_router.get(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/useful-links",
    response_model=list[UsefulLink],
    summary="List useful links",
)
@cache_response(prefix="useful-links", ttl_seconds=300)
async def get_useful_links(
    provider_id: int,
    dataset_id: int,
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all useful links for a specific dataset. Requires read permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(UsefulLinkModel)
        .join(DatasetModel)
        .where(and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id))
    )
    return result.scalars().all()


@csrf_protect.validate_csrf
@v1_router.post(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/useful-links",
    response_model=UsefulLink,
    status_code=201,
    summary="Create useful link",
)
async def create_useful_link(
    provider_id: int,
    dataset_id: int,
    useful_link: UsefulLink,
    current_user: UserModel = Depends(provider_permission("write")),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new useful link for a specific dataset. Requires write permissions.
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(DatasetModel).where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    link_data = useful_link.model_dump(exclude={"id"}, exclude_unset=True)
    if link_data.get("url"):
        link_data["url"] = str(link_data["url"])
    link_obj = UsefulLinkModel(**link_data, dataset_id=dataset_id)
    db.add(link_obj)
    await db.commit()
    await db.refresh(link_obj)

    # Invalidate related caches
    invalidate_cache(f"dataset:{dataset_id}")
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("useful-links")
    invalidate_cache("providers")
    invalidate_cache("datasets")

    return link_obj


# Legacy Harvesting Endpoint
@v1_router.get("/legacy-data-sets", response_model=list[LegacyDataset])
@limiter.limit(settings.HARVEST_RATE_LIMIT)
async def harvest_datasets(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all datasets in a legacy format for harvesting purposes.
    """
    try:
        # Query all providers with their datasets, xml archives, and useful links
        query = select(DataProviderModel).options(
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.xmlArchives),
            selectinload(DataProviderModel.datasets).selectinload(DatasetModel.usefulLinks),
        )

        result = await db.execute(query)
        providers = result.scalars().all()

        # Transform to legacy format
        legacy_datasets = []
        for provider in providers:
            sorted_datasets = sorted(provider.datasets, key=lambda ds: ds.id)
            for ds in sorted_datasets:
                # Convert XML archives to legacy format
                xml_archives = []
                for archive in ds.xmlArchives:
                    xml_archives.append(
                        LegacyXmlArchive(
                            archive_id=archive.id,
                            xml_archive=archive.url,
                            latest=archive.isLatest,
                        )
                    )

                # Convert useful links to legacy format
                useful_links = []
                for link in ds.usefulLinks:
                    useful_links.append(
                        LegacyUsefulLink(
                            link_id=link.id,
                            title=link.title,
                            url=link.url,
                            is_latest=link.isLatest,
                        )
                    )

                # Create legacy dataset
                legacy_dataset = LegacyDataset(
                    dataset_id=ds.id,
                    datasource=ds.source,
                    dataset=ds.title,
                    custom_landingpage=ds.landingPageUrl,
                    provider_id=provider.id,
                    xml_archives=xml_archives,
                    useful_links=useful_links,
                    provider_datacenter=provider.datacenter,
                    provider_shortname=provider.shortName,
                    provider_name=provider.name,
                    provider_url=provider.url,
                    biocase_url=provider.biocaseUrl,
                    is_data_center=provider.isDataCenter,
                )
                legacy_datasets.append(legacy_dataset)

        return legacy_datasets
    except Exception as e:
        logger.error(f"Error in harvest endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Include the API router with proper versioning and backwards compatibility
from app.api.router import api_router

app.include_router(api_router, prefix="/api")

# Also include api_v1_router directly without prefix for backwards compatibility
# This allows existing clients to use /users instead of /api/v1/users or /api/users
from app.api.v1.router import api_v1_router

app.include_router(api_v1_router)


# ------------------- Startup Event -------------------
@app.on_event("startup")
async def on_startup():
    # We now use Alembic for all database migrations and initialization
    # No need to create tables here as they are managed by migrations
    logger.info("Application started - database managed by Alembic migrations")


# ------------------- Main Entry Point -------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
