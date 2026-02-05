import logging
import time
import uuid
from datetime import datetime

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import slowapi components for rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

# Import shared API dependencies
from app.api.deps import limiter

# Import application components
from app.core.config import settings
from app.core.logging_config import configure_logging, request_id_var

# ------------------- Logging Configuration -------------------
configure_logging(level=settings.LOG_LEVEL)
logger = logging.getLogger("api")

# ------------------- Database Setup -------------------
# Database configuration moved to app.db module
# - Engine configuration in app.db.base
# - Session management in app.db.session


# ------------------- Create FastAPI app -------------------
app = FastAPI(
    title="Dataset Management API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

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

    # Set request_id in contextvars so all loggers automatically include it
    token = request_id_var.set(request_id)
    try:
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Request-ID"] = request_id
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
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
                "method": request.method,
                "path": request.url.path,
                "error": str(e),
                "process_time": process_time,
            },
            exc_info=True,
        )
        raise
    finally:
        request_id_var.reset(token)


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


# ------------------- Router Includes -------------------
# Include the API router with proper versioning and backwards compatibility
from app.api.router import api_router  # noqa: E402

app.include_router(api_router, prefix="/api")

# Also include api_v1_router directly without prefix for backwards compatibility
# This allows existing clients to use /users instead of /api/v1/users or /api/users
from app.api.v1.router import api_v1_router  # noqa: E402

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
