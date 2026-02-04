"""Tests for application configuration settings and validators."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, settings


class TestSettingsInstance:
    """Tests for the global settings instance."""

    def test_settings_loaded(self):
        """Test that settings instance is created."""
        assert settings is not None
        assert settings.SECRET_KEY

    def test_algorithm_default(self):
        """Test default algorithm is HS256."""
        assert settings.ALGORITHM == "HS256"

    def test_allowed_origins_list(self):
        """Test that allowed_origins_list splits correctly."""
        origins = settings.allowed_origins_list
        assert isinstance(origins, list)
        assert len(origins) >= 1

    def test_redis_url_without_password(self):
        """Test redis_url property builds URL correctly."""
        url = settings.redis_url
        assert url.startswith("redis://")
        assert str(settings.REDIS_PORT) in url


class TestValidatorCpuPercent:
    """Tests for VALIDATOR_CPU_PERCENT validation."""

    def test_default_value(self):
        """Test that default CPU percent is 75."""
        assert settings.VALIDATOR_CPU_PERCENT == 75


class TestStatsWorkerConcurrency:
    """Tests for STATS_WORKER_CONCURRENCY validation."""

    def test_auto_value_accepted(self):
        """Test that 'auto' string is accepted."""
        # The default or env value should be valid
        assert settings.STATS_WORKER_CONCURRENCY is not None

    def test_integer_string_converted(self):
        """Test that numeric string is converted to int."""
        s = Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "SECRET_KEY": "test-secret-key",
                "STATS_WORKER_CONCURRENCY": "4",
            }
        )
        assert s.STATS_WORKER_CONCURRENCY == 4

    def test_invalid_string_rejected(self):
        """Test that non-numeric, non-auto string is rejected."""
        with pytest.raises(ValidationError):
            Settings.model_validate(
                {
                    "DATABASE_URL": "postgresql://test:test@localhost/test",
                    "SECRET_KEY": "test-secret-key",
                    "STATS_WORKER_CONCURRENCY": "invalid",
                }
            )

    def test_auto_string_preserved(self):
        """Test that 'auto' string is preserved as-is."""
        s = Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "SECRET_KEY": "test-secret-key",
                "STATS_WORKER_CONCURRENCY": "auto",
            }
        )
        assert s.STATS_WORKER_CONCURRENCY == "auto"


class TestRedisUrlProperty:
    """Tests for the redis_url property."""

    def test_redis_url_with_password(self):
        """Test redis_url includes auth when password is set."""
        s = Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "SECRET_KEY": "test-secret-key",
                "REDIS_PASSWORD": "mypass",
                "REDIS_HOST": "myhost",
                "REDIS_PORT": 6380,
                "REDIS_DB": 1,
            }
        )
        assert s.redis_url == "redis://:mypass@myhost:6380/1"

    def test_redis_url_without_password(self):
        """Test redis_url omits auth when no password."""
        s = Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://test:test@localhost/test",
                "SECRET_KEY": "test-secret-key",
                "REDIS_PASSWORD": "",
                "REDIS_HOST": "localhost",
                "REDIS_PORT": 6379,
                "REDIS_DB": 0,
            }
        )
        assert s.redis_url == "redis://localhost:6379/0"
