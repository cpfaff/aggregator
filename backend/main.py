import os
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from functools import lru_cache, wraps
from typing import List, Optional, Dict, Any, Generic, TypeVar

import jwt
import bcrypt
from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    status,
    Request,
    Body,
    APIRouter,
    Query,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, AnyUrl, Field, field_validator, ConfigDict
from pydantic.generics import GenericModel
from pydantic_settings import BaseSettings
from sqlalchemy import (
    text,
    Column,
    Integer,
    String,
    Boolean,
    JSON,
    ForeignKey,
    select,
    and_,
    Index,
    func,
    DateTime,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship, selectinload
from pythonjsonlogger import jsonlogger
from fastapi_csrf_protect import CsrfProtect

# Import application components
from app.core.config import Settings, settings
from app.core.utils import apply_entity_updates
from app.core.cache import cache, cache_response, invalidate_cache
from app.models import (
    Base,
    UserModel,
    DataProviderModel,
    DatasetModel,
    XmlArchiveModel,
    UsefulLinkModel,
)
from app.db import async_session, engine, get_db
from app.schemas import (
    User, 
    UserCreate, 
    UserUpdate, 
    UserPermissions,
    DataProvider, 
    ProviderAssociation,
    Dataset, 
    XmlArchive, 
    UsefulLink,
    LegacyDataset, 
    LegacyXmlArchive, 
    LegacyUsefulLink,
    PaginatedResponse,
    TokenResponse,
    PaginatedProviders,
    PaginatedDatasets
)
from app.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    authenticate_user,
    check_provider_permission,
    get_user_model,
    normalize_provider_roles,
    check_global_admin
)
from app.security.token import oauth2_scheme

# Import slowapi components for rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

# ------------------- Configuration Management -------------------
class Settings(BaseSettings):
    """
    Configuration settings for the API loaded from environment variables.
    """

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,http://localhost:5173,http://localhost"
    )
    LOG_LEVEL: str = "INFO"
    # Rate limiting settings
    LOGIN_RATE_LIMIT: str = "5/minute"
    HARVEST_RATE_LIMIT: str = "30/hour"
    CSRF_TOKEN_RATE_LIMIT: str = "20/minute"
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_EXPIRE_SECONDS: int = 300
    # JWT settings
    TOKEN_AUDIENCE: str = "dataset-api"
    # Database connection pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    # Password policy
    MIN_PASSWORD_LENGTH: int = 8

    @property
    def allowed_origins_list(self) -> List[str]:
        """Convert comma-separated ALLOWED_ORIGINS string to a list of strings."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# Ensure SECRET_KEY is set for security
if not settings.SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is not set. This is required for application security."
    )
# Ensure DATABASE_URL is set for database connectivity
if not settings.DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is not set. This is required for database connectivity."
    )

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

# ------------------- Dependencies -------------------
# Database dependency moved to app.db.session

def provider_permission(operation: str = "read"):
    """Dependency factory for provider permission checking."""

    async def dependency(
        provider_id: int, current_user: UserModel = Depends(get_current_user)
    ):
        check_provider_permission(provider_id, current_user, operation)
        return current_user

    return dependency

# ------------------- Create FastAPI app and routers -------------------
app = FastAPI(
    title="Dataset Management API",
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

v1_router = APIRouter(prefix="/api/v1")

# Note: The tokenUrl is updated to include the v1 prefix
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth-token")

# Initialize rate limiter with IP address as the key
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ------------------- CSRF Protection Settings -------------------
class CsrfSettings(BaseSettings):
    secret_key: str = settings.SECRET_KEY
    cookie_samesite: str = "lax"
    cookie_secure: bool = False  # Set to True in production with HTTPS


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


csrf_protect = CsrfProtect()

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
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
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
    path: Optional[str] = None


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


# CSRF Token endpoint
@v1_router.get("/csrf-token", summary="Get CSRF token")
@limiter.limit(settings.CSRF_TOKEN_RATE_LIMIT)
async def get_csrf_token(request: Request):
    """
    Retrieve a CSRF token to protect against cross-site request forgery in subsequent requests.
    Returns a JSON object with the token.

    This endpoint is rate-limited to prevent abuse.
    """
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse(content={"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


# Authentication endpoint
@v1_router.post("/auth-token", response_model=TokenResponse)
@limiter.limit(settings.LOGIN_RATE_LIMIT)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticate a user and return JWT access and refresh tokens.

    - **username**: The user's username
    - **password**: The user's password

    Returns a JSON object containing the access token, refresh token, token type, and expiration time.
    """
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        logger.warning(
            f"Failed login attempt",
            extra={
                "username": form_data.username,
                "ip_address": request.client.host if request.client else None,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.username})

    logger.info(
        f"User authenticated",
        extra={
            "username": user.username,
            "is_admin": user.is_global_admin,
            "ip_address": request.client.host if request.client else None,
        },
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@v1_router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(
    refresh_token: str = Body(...), db: AsyncSession = Depends(get_db)
):
    """
    Get a new access token using a refresh token.

    - **refresh_token**: A valid refresh token previously issued

    Returns a new access token and refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=f"{settings.TOKEN_AUDIENCE}:refresh",  # Verify audience claim for refresh
        )
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = await get_user_model(username, db)
    if user is None:
        raise credentials_exception

    # Create new tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(data={"sub": user.username})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# User Endpoints
@v1_router.get(
    "/me/permissions",
    response_model=UserPermissions,
    summary="Get current user's permissions",
)
async def get_user_permissions(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve the permissions of the currently authenticated user.
    Returns the username, global admin status, and provider-specific roles.
    """
    provider_roles = normalize_provider_roles(current_user.provider_roles)
    return UserPermissions(
        username=current_user.username,
        is_global_admin=current_user.is_global_admin,
        provider_roles=provider_roles,
    )


@v1_router.get("/users", response_model=List[User], summary="List all users")
async def list_users(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Number of users to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of users to return"
    ),
):
    """
    List all users in the system. Requires global admin privileges.

    Supports pagination with skip/limit parameters.
    """
    check_global_admin(current_user)
    result = await db.execute(select(UserModel).offset(skip).limit(limit))
    return result.scalars().all()


@v1_router.get("/users/{username}", response_model=User, summary="Get user by username")
async def get_user_endpoint(
    username: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve a user by their username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    return user_obj


@csrf_protect.validate_csrf
@v1_router.put("/users/{username}", response_model=User, summary="Update user")
async def update_user(
    username: str,
    user: UserUpdate,
    old_password: Optional[str] = Body(None),
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a user's information. Requires global admin privileges.
    If updating own password, provide `old_password` for verification.
    - **username**: The username of the user to update
    - **password**: Optional new password
    - **provider_roles**: Optional updated provider roles
    - **is_global_admin**: Optional updated global admin status
    - **old_password**: Required if updating own password
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password is not None:
        if current_user.username == username:
            if not old_password or not verify_password(
                old_password, user_obj.hashed_password
            ):
                raise HTTPException(status_code=400, detail="Old password is incorrect")
        hashed_pw = get_password_hash(user.password)
        if hashed_pw:
            user_obj.hashed_password = hashed_pw
    if user.provider_roles is not None:
        user_obj.provider_roles = normalize_provider_roles(user.provider_roles)
    if user.is_global_admin is not None:
        user_obj.is_global_admin = user.is_global_admin
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate any cached data related to this user
    invalidate_cache(f"user:{username}")

    return user_obj


@csrf_protect.validate_csrf
@v1_router.post(
    "/users", response_model=User, status_code=201, summary="Create a new user"
)
async def create_user(
    user: UserCreate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new user. Requires global admin privileges.
    - **username**: Unique username for the user
    - **password**: User's password
    - **provider_roles**: Optional dictionary of provider IDs to roles (e.g., {"1": "admin"})
    - **is_global_admin**: Optional boolean to set global admin status
    """
    check_global_admin(current_user)
    existing = await get_user_model(user.username, db)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_pw = get_password_hash(user.password)
    provider_roles = normalize_provider_roles(user.provider_roles)
    user_obj = UserModel(
        username=user.username,
        hashed_password=hashed_pw,
        provider_roles=provider_roles,
        is_global_admin=user.is_global_admin,
    )
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user list cache
    invalidate_cache("users")

    return user_obj


@csrf_protect.validate_csrf
@v1_router.delete("/users/{username}", status_code=204, summary="Delete user")
async def delete_user(
    username: str,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a user by username. Requires global admin privileges.
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if user_obj:
        await db.delete(user_obj)
        await db.commit()

        # Invalidate user caches
        invalidate_cache("users")
        invalidate_cache(f"user:{username}")
    else:
        raise HTTPException(status_code=404, detail="User not found")
    return


# Provider Association Endpoints
@csrf_protect.validate_csrf
@v1_router.post(
    "/users/{username}/data-providers",
    response_model=User,
    summary="Add provider association",
)
async def add_provider_association(
    username: str,
    association: ProviderAssociation,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a provider association to a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider
    - **role**: The role to assign (e.g., "admin", "curator")
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(association.provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user cache
    invalidate_cache(f"user:{username}")

    return user_obj


@csrf_protect.validate_csrf
@v1_router.put(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Update provider association",
)
async def update_provider_association(
    username: str,
    provider_id: int,
    association: ProviderAssociation,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a provider association for a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to update
    - **role**: The new role to assign
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (
        normalize_provider_roles(user_obj.provider_roles)
        and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)
    ):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles[str(provider_id)] = association.role
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user and provider caches
    invalidate_cache(f"user:{username}")
    invalidate_cache(f"provider:{provider_id}")

    return user_obj


@csrf_protect.validate_csrf
@v1_router.delete(
    "/users/{username}/data-providers/{provider_id}",
    response_model=User,
    summary="Remove provider association",
)
async def remove_provider_association(
    username: str,
    provider_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove a provider association from a user. Requires global admin privileges.
    - **provider_id**: The ID of the provider to remove
    """
    check_global_admin(current_user)
    user_obj = await get_user_model(username, db)
    if not user_obj or not (
        normalize_provider_roles(user_obj.provider_roles)
        and str(provider_id) in normalize_provider_roles(user_obj.provider_roles)
    ):
        raise HTTPException(status_code=404, detail="User or association not found")
    roles = normalize_provider_roles(user_obj.provider_roles)
    roles.pop(str(provider_id))
    user_obj.provider_roles = roles
    db.add(user_obj)
    await db.commit()
    await db.refresh(user_obj)

    # Invalidate user and provider caches
    invalidate_cache(f"user:{username}")
    invalidate_cache(f"provider:{provider_id}")

    return user_obj


# Data Provider Endpoints
@v1_router.get(
    "/data-providers", response_model=List[DataProvider], summary="List data providers"
)
@cache_response(prefix="providers", ttl_seconds=300)
async def get_providers(
    name: Optional[str] = Query(None, description="Filter by provider name"),
    datacenter: Optional[str] = Query(None, description="Filter by datacenter"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of items to return"
    ),
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
        raise HTTPException(
            status_code=400, detail="Provider ID must be a positive integer"
        )

    result = await db.execute(
        select(DataProviderModel)
        .where(DataProviderModel.id == provider_id)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.xmlArchives
            ),
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.usefulLinks
            ),
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
                    str(dataset_data["landingPageUrl"])
                    if dataset_data["landingPageUrl"]
                    else None
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
                        UsefulLinkModel(
                            title=link.title, url=str(link.url), isLatest=link.isLatest
                        )
                    )
            provider_obj.datasets.append(db_dataset)
    db.add(provider_obj)
    await db.commit()
    await db.refresh(provider_obj)
    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.xmlArchives
            ),
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.usefulLinks
            ),
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
    """
    if provider_id <= 0:
        raise HTTPException(
            status_code=400, detail="Provider ID must be a positive integer"
        )

    result = await db.execute(
        select(DataProviderModel)
        .options(
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.xmlArchives
            ),
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.usefulLinks
            ),
        )
        .where(DataProviderModel.id == provider_id)
    )
    db_provider = result.scalar_one_or_none()
    if not db_provider:
        raise HTTPException(status_code=404, detail="Provider not found")
    provider_data = provider.model_dump(exclude={"datasets", "id"}, exclude_unset=True)
    if provider_data.get("url"):
        provider_data["url"] = str(provider_data["url"])
    if provider_data.get("biocaseUrl"):
        provider_data["biocaseUrl"] = str(provider_data["biocaseUrl"])
    for key, value in provider_data.items():
        setattr(db_provider, key, value)
    async with db.begin_nested():
        if provider.datasets is not None:
            existing_datasets = {
                ds.id: ds for ds in db_provider.datasets if ds.id is not None
            }
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
                                XmlArchiveModel(
                                    url=str(archive.url), isLatest=archive.isLatest
                                )
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
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.xmlArchives
            ),
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.usefulLinks
            ),
        )
        .where(DataProviderModel.id == provider_id)
    )

    # Invalidate provider caches
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("providers")

    return result.scalar_one()


@csrf_protect.validate_csrf
@v1_router.delete(
    "/data-providers/{provider_id}", status_code=204, summary="Delete data provider"
)
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
        raise HTTPException(
            status_code=400, detail="Provider ID must be a positive integer"
        )
    check_global_admin(current_user)
    result = await db.execute(
        select(DataProviderModel).where(DataProviderModel.id == provider_id)
    )
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
    response_model=List[Dataset],
    summary="List datasets for provider",
)
@cache_response(prefix="datasets", ttl_seconds=300)
async def get_datasets(
    provider_id: int,
    title: Optional[str] = Query(None, description="Filter by dataset title"),
    source: Optional[str] = Query(None, description="Filter by dataset source"),
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of items to return"
    ),
    current_user: UserModel = Depends(provider_permission("read")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all datasets for a specific data provider. Requires read permissions.
    - **provider_id**: Must be a positive integer

    Supports filtering by title or source and pagination with skip/limit.
    """
    if provider_id <= 0:
        raise HTTPException(
            status_code=400, detail="Provider ID must be a positive integer"
        )

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
        .where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
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
        raise HTTPException(
            status_code=400, detail="Provider ID must be a positive integer"
        )

    result = await db.execute(
        select(DataProviderModel).where(DataProviderModel.id == provider_id)
    )
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
                UsefulLinkModel(
                    title=link.title, url=str(link.url), isLatest=link.isLatest
                )
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

    return result.scalar_one()


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
        .where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
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

    return result.scalar_one()


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
    - **provider_id**: Must be a positive integer
    - **dataset_id**: Must be a positive integer
    """
    if provider_id <= 0 or dataset_id <= 0:
        raise HTTPException(status_code=400, detail="IDs must be positive integers")

    result = await db.execute(
        select(DatasetModel).where(
            DatasetModel.id == dataset_id, DatasetModel.provider_id == provider_id
        )
    )
    dataset_obj = result.scalar_one_or_none()
    if not dataset_obj:
        raise HTTPException(status_code=404, detail="Dataset not found")
    await db.delete(dataset_obj)
    await db.commit()

    # Invalidate dataset and provider caches
    invalidate_cache(f"dataset:{dataset_id}")
    invalidate_cache("datasets")
    invalidate_cache(f"provider:{provider_id}")
    invalidate_cache("providers")

    return


# XML Archive Endpoints
@v1_router.get(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/xml-archives",
    response_model=List[XmlArchive],
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
        .where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
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

    return xml_obj


# Useful Link Endpoints
@v1_router.get(
    "/data-providers/{provider_id}/data-sets/{dataset_id}/useful-links",
    response_model=List[UsefulLink],
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
        .where(
            and_(DatasetModel.provider_id == provider_id, DatasetModel.id == dataset_id)
        )
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


# Health Check Endpoint
@v1_router.get("/health-check", status_code=200, summary="Health check")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Check the health of the API and database connection.
    Returns a JSON object with the status and database connection state.
    """
    try:
        # Time the database query
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = time.time() - start_time

        # Return enhanced health check information
        return {
            "status": "healthy",
            "database": {
                "status": "connected",
                "response_time_ms": round(db_response_time * 1000, 2),
            },
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": {"status": "disconnected", "error": str(e)},
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# Legacy Harvesting Endpoint
@v1_router.get("/legacy-data-sets", response_model=List[LegacyDataset])
@limiter.limit(settings.HARVEST_RATE_LIMIT)
async def harvest_datasets(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all datasets in a legacy format for harvesting purposes.
    """
    try:
        # Query all providers with their datasets, xml archives, and useful links
        query = select(DataProviderModel).options(
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.xmlArchives
            ),
            selectinload(DataProviderModel.datasets).selectinload(
                DatasetModel.usefulLinks
            ),
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
                )
                legacy_datasets.append(legacy_dataset)

        return legacy_datasets
    except Exception as e:
        logger.error(f"Error in harvest endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Include v1 router in the main app
app.include_router(v1_router)

# Include the new API router with proper versioning
from app.api.router import api_router
app.include_router(api_router, prefix="/api")

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
