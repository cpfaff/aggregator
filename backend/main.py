import http
import logging
import time
import uuid

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse

# Import slowapi components for rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Import shared API dependencies
from app.api.deps import limiter

# Import application components
from app.core.config import settings

# RFC 7807 Problem Details error responses
# See: https://datatracker.ietf.org/doc/html/rfc7807
from app.core.exceptions import APIError
from app.core.logging_config import configure_logging, request_id_var
from app.schemas.errors import ProblemDetail, ValidationProblemDetail
from app.utils.filtering import FilterError
from app.utils.pagination import CursorError
from app.utils.sorting import SortError

# ------------------- Logging Configuration -------------------
configure_logging(level=settings.LOG_LEVEL)
logger = logging.getLogger("api")

# ------------------- Database Setup -------------------
# Database configuration moved to app.db module
# - Engine configuration in app.db.base
# - Session management in app.db.session


# ------------------- Create FastAPI app -------------------
# RFC 7807 Problem Details error responses for OpenAPI documentation
error_responses = {
    400: {"model": ProblemDetail, "description": "Bad Request"},
    401: {"model": ProblemDetail, "description": "Unauthorized"},
    403: {"model": ProblemDetail, "description": "Forbidden"},
    404: {"model": ProblemDetail, "description": "Not Found"},
    422: {"model": ValidationProblemDetail, "description": "Validation Error"},
    429: {"model": ProblemDetail, "description": "Rate Limit Exceeded"},
    500: {"model": ProblemDetail, "description": "Internal Server Error"},
}

app = FastAPI(
    title="Dataset Management API",
    version="2.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    responses=error_responses,
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


# ------------------- Request Body Size Limit Middleware -------------------
class BodySizeLimitMiddleware:
    """Reject requests whose body exceeds ``MAX_REQUEST_BODY_BYTES`` with HTTP 413.

    Closes a memory-exhaustion DoS on every JSON route — including the public,
    unauthenticated ``POST /validation-stats`` — which otherwise buffers the full
    body into memory before any handler runs (RH-02 / REQ-ROUTE-1).

    One explicit bounded value (``settings.MAX_REQUEST_BODY_BYTES``) owns the wire
    behaviour. It is a pure-ASGI middleware (not ``BaseHTTPMiddleware``) so it can
    short-circuit *before* the handler resolves and reject a stream without ever
    buffering the whole body:

    * a declared ``Content-Length`` over the cap is rejected immediately, before a
      single body byte is read;
    * because ``Content-Length`` is absent on a chunked upload, streamed bytes are
      also counted as they arrive and the request is rejected with 413 the moment
      the running total exceeds the cap.

    Per-request and stateless — no shared state, safe under concurrency.
    """

    def __init__(self, app: ASGIApp, max_body_bytes: int) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def _send_413(self, send: Send) -> None:
        response = PlainTextResponse(
            "Request body too large",
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        )
        await response(self._scope, self._noop_receive, send)

    @staticmethod
    async def _noop_receive() -> Message:
        return {"type": "http.disconnect"}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        self._scope = scope

        # Fast path: a declared Content-Length over the cap is rejected before any
        # body byte is read.
        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = None
                if declared is not None and declared > self.max_body_bytes:
                    await self._send_413(send)
                    return
                break

        # Chunked / unknown-length path: count streamed bytes as they arrive and
        # reject once the running total exceeds the cap. Body chunks consumed
        # before the cap is reached are held so the app still sees the whole body
        # of a legitimately-sized request; buffering is bounded to at most
        # ``max_body_bytes`` + one chunk and is released the moment the cap is hit.
        prefetched: list[Message] = []
        received = 0
        while True:
            message = await receive()
            prefetched.append(message)
            if message["type"] != "http.request":
                break
            received += len(message.get("body", b""))
            if received > self.max_body_bytes:
                await self._send_413(send)
                return
            if not message.get("more_body", False):
                break

        async def replay_receive() -> Message:
            if prefetched:
                return prefetched.pop(0)
            # Defensive: once the prefetched body is drained, fall through to the
            # live stream (relevant only if a chunk lacked the more_body flag).
            return await receive()

        await self.app(scope, replay_receive, send)


app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=settings.MAX_REQUEST_BODY_BYTES)


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
# RFC 7807 Problem Details error responses
# See: https://datatracker.ietf.org/doc/html/rfc7807

BASE_ERROR_URL = "https://api.gfbio.org/errors"
PROBLEM_JSON_MEDIA_TYPE = "application/problem+json"


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle custom API errors with RFC 7807 Problem Details format."""
    logger.warning(
        f"API error at {request.url.path}: {exc.title}",
        extra={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "path": request.url.path,
            "error_type": exc.error_type,
            "status_code": exc.status_code,
        },
    )
    problem = ProblemDetail(
        type=f"{BASE_ERROR_URL}/{exc.error_type}",
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with RFC 7807 Problem Details format."""
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
            "field": ".".join(str(loc) for loc in error.get("loc", ["unknown"])),
            "message": error.get("msg", "Unknown error"),
            "type": error.get("type", "unknown"),
        }
        for error in exc.errors()
    ]
    problem = ValidationProblemDetail(
        type=f"{BASE_ERROR_URL}/validation-error",
        title="Validation Error",
        status=422,
        detail="Request validation failed",
        instance=str(request.url.path),
        errors=errors,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with RFC 7807 Problem Details format."""
    # Map status codes to error types
    error_type_map = {
        400: "bad-request",
        401: "unauthorized",
        403: "forbidden",
        404: "not-found",
        405: "method-not-allowed",
        409: "conflict",
        422: "validation-error",
        429: "rate-limit-exceeded",
        500: "internal-server-error",
    }
    error_type = error_type_map.get(exc.status_code, "http-error")

    problem = ProblemDetail(
        type=f"{BASE_ERROR_URL}/{error_type}",
        title=http.HTTPStatus(exc.status_code).phrase,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
        headers=exc.headers,
    )


@app.exception_handler(CursorError)
@app.exception_handler(FilterError)
@app.exception_handler(SortError)
async def query_param_error_handler(request: Request, exc: Exception):
    """Map invalid pagination/filter/sort query params to RFC 7807 400.

    Without this, these client-input errors fell through to the catch-all
    Exception handler and surfaced as 500 (B9).
    """
    logger.warning(
        f"Invalid query parameter at {request.url.path}: {exc}",
        extra={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "path": request.url.path,
            "error_type": type(exc).__name__,
        },
    )
    problem = ProblemDetail(
        type=f"{BASE_ERROR_URL}/bad-request",
        title="Bad Request",
        status=400,
        detail=str(exc),
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with RFC 7807 Problem Details format."""
    logger.error(
        f"Unhandled exception at {request.url.path}",
        extra={
            "request_id": getattr(request.state, "request_id", str(uuid.uuid4())),
            "path": request.url.path,
            "error": str(exc),
        },
        exc_info=True,
    )
    problem = ProblemDetail(
        type=f"{BASE_ERROR_URL}/internal-server-error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",
        instance=str(request.url.path),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_JSON_MEDIA_TYPE,
    )


# ------------------- Router Includes -------------------
# Include the API router with proper versioning
# All endpoints are accessible at /api/v1/... (industry-standard REST versioning)
from app.api.router import api_router  # noqa: E402

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
