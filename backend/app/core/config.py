"""
Configuration management for the application.
Settings are loaded from environment variables.
"""
from typing import List, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


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
    # Celery settings
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    # Resource allocation settings
    VALIDATOR_CPU_PERCENT: int = Field(default=75, ge=1, le=100)
    STATS_WORKER_CONCURRENCY: Union[str, int] = "auto"
    
    @field_validator('VALIDATOR_CPU_PERCENT')
    @classmethod
    def validate_cpu_percent(cls, v):
        if not 1 <= v <= 100:
            raise ValueError("VALIDATOR_CPU_PERCENT must be between 1 and 100")
        return v
    
    @field_validator('STATS_WORKER_CONCURRENCY')
    @classmethod
    def validate_concurrency(cls, v):
        if isinstance(v, str):
            if v != 'auto':
                try:
                    return int(v)
                except ValueError:
                    raise ValueError("STATS_WORKER_CONCURRENCY must be 'auto' or an integer")
        return v
    # Redis settings
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    @property
    def allowed_origins_list(self) -> List[str]:
        return self.ALLOWED_ORIGINS.split(",")

    @property
    def redis_url(self) -> str:
        """Build Redis URL from components"""
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"


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
