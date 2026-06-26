"""
Configuration management for the application.
Settings are loaded from environment variables.
"""

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Configuration settings for the API loaded from environment variables.
    """

    model_config = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"
    LOG_LEVEL: str = "INFO"
    # Rate limiting settings
    LOGIN_RATE_LIMIT: str = "5/minute"
    HARVEST_RATE_LIMIT: str = "30/hour"
    CSRF_TOKEN_RATE_LIMIT: str = "20/minute"
    # Public, unauthenticated statistics reads (validation-stats + /statistics/*):
    # generous per-IP ceiling for a dashboard, so a single client cannot saturate
    # the DB pool. One explicit bounded value owns the shed-load behaviour (RH-08).
    PUBLIC_STATS_RATE_LIMIT: str = "60/minute"
    # Cache settings
    CACHE_ENABLED: bool = True
    CACHE_EXPIRE_SECONDS: int = 300
    # JWT settings
    TOKEN_AUDIENCE: str = "dataset-api"
    # Database connection pool settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    # Server-side query deadlines (milliseconds). A slow or lock-blocked query is
    # aborted by PostgreSQL instead of pinning a pooled connection until the pool
    # is exhausted (RH-01 / REQ-PG-1). Applied via connect_args on both engines.
    DB_STATEMENT_TIMEOUT_MS: int = 5000
    DB_LOCK_TIMEOUT_MS: int = 3000
    # Maximum inbound request body size, in bytes. A request whose body exceeds
    # this cap is rejected with HTTP 413 by BodySizeLimitMiddleware before it is
    # buffered into memory and parsed, closing a memory-exhaustion DoS on every
    # JSON route — including the public, unauthenticated POST /validation-stats
    # (RH-02 / REQ-ROUTE-1). A search page submits a few hundred short URNs, far
    # below 256 KiB, so this never clips a real request.
    MAX_REQUEST_BODY_BYTES: int = 256 * 1024
    # Maximum bytes streamed from a provider archive download before the transfer
    # is aborted with a typed XMLParsingError. SpooledTemporaryFile(max_size=…) is
    # only a memory→disk rollover threshold, not a cap, so a huge or hostile
    # archive would otherwise exhaust the stats worker's disk/memory (RH-04 /
    # REQ-OUT-1). The running byte counter is authoritative because an archive's
    # Content-Length may be absent (chunked) or lie. 200 MiB comfortably exceeds
    # any legitimate GFBio provider archive.
    MAX_ARCHIVE_BYTES: int = 200 * 1024 * 1024
    # Password policy
    MIN_PASSWORD_LENGTH: int = 8
    # Celery settings
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    # Resource allocation settings
    VALIDATOR_CPU_PERCENT: int = Field(default=75, ge=1, le=100)
    STATS_WORKER_CONCURRENCY: str | int = "auto"

    @field_validator("VALIDATOR_CPU_PERCENT")
    @classmethod
    def validate_cpu_percent(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("VALIDATOR_CPU_PERCENT must be between 1 and 100")
        return v

    @field_validator("STATS_WORKER_CONCURRENCY")
    @classmethod
    def validate_concurrency(cls, v):
        if isinstance(v, str):
            if v != "auto":
                try:
                    return int(v)
                except ValueError:
                    raise ValueError(
                        "STATS_WORKER_CONCURRENCY must be 'auto' or an integer"
                    ) from None
        return v

    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # Elasticsearch settings (harvest-success indicator; see EsGateway).
    # All have in-cluster defaults so no env is required. Empty creds ⇒
    # unauthenticated; non-empty ⇒ httpx basic auth.
    ES_BASE_URL: str = "http://index:9200"
    ES_INDEX: str = "portals_v1"
    ES_DOC_TYPE: str = "pansimple"
    ES_TIMEOUT_SECONDS: float = 5.0
    ES_USERNAME: str = ""
    ES_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return self.ALLOWED_ORIGINS.split(",")

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


# Create a settings instance for use throughout the application
settings = Settings()

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
