"""Tests for in-memory cache and rate limiter utilities."""

import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from app.core import cache as cache_module
from app.core.cache import (
    RateLimiter,
    SimpleCache,
    cache_response,
    invalidate_cache,
)


class TestDetailCacheInvalidation:
    """Detail caches must be invalidatable by entity id (B23)."""

    @pytest.mark.asyncio
    async def test_detail_cache_invalidated_by_entity_id(self):
        cache_module.cache.invalidate()  # start clean
        calls = []
        with patch.object(cache_module.settings, "CACHE_ENABLED", True):

            @cache_response(prefix="dataset", id_param="dataset_id")
            async def get_dataset(provider_id, dataset_id, current_user, db):
                calls.append(1)
                return f"v{len(calls)}"

            user = MagicMock()
            user.username = "admin"
            db = MagicMock()

            await get_dataset(provider_id=5, dataset_id=123, current_user=user, db=db)
            await get_dataset(provider_id=5, dataset_id=123, current_user=user, db=db)
            assert len(calls) == 1  # second call served from cache

            # The key must lead with the prefix:id services invalidate on.
            assert any(k.startswith("dataset:123") for k in cache_module.cache.cache)

            invalidate_cache("dataset:123")
            await get_dataset(provider_id=5, dataset_id=123, current_user=user, db=db)
            assert len(calls) == 2  # re-executed after invalidation
        cache_module.cache.invalidate()

# ---------------------------------------------------------------------------
# SimpleCache
# ---------------------------------------------------------------------------


class TestSimpleCache:
    """Tests for the SimpleCache class."""

    def test_get_returns_none_for_missing_key(self):
        """Test that missing key returns None."""
        c = SimpleCache(ttl_seconds=60)
        assert c.get("nonexistent") is None

    def test_set_and_get_returns_value(self):
        """Test that set value can be retrieved."""
        c = SimpleCache(ttl_seconds=60)
        c.set("key", "value")
        assert c.get("key") == "value"

    def test_expired_entry_returns_none(self):
        """Test that expired entry returns None and is removed."""
        c = SimpleCache(ttl_seconds=1)
        c.set("key", "value", ttl_seconds=0)
        # Force expiration by setting the entry directly
        c.cache["key"] = ("value", datetime.now(UTC) - timedelta(seconds=1))
        assert c.get("key") is None
        assert "key" not in c.cache

    def test_custom_ttl_on_set(self):
        """Test that per-key TTL overrides default."""
        c = SimpleCache(ttl_seconds=1)
        c.set("key", "value", ttl_seconds=3600)
        assert c.get("key") == "value"

    def test_invalidate_with_prefix(self):
        """Test that invalidate removes only matching prefix keys."""
        c = SimpleCache(ttl_seconds=60)
        c.set("user:1", "alice")
        c.set("user:2", "bob")
        c.set("post:1", "hello")
        c.invalidate("user")
        assert c.get("user:1") is None
        assert c.get("user:2") is None
        assert c.get("post:1") == "hello"

    def test_invalidate_without_prefix_clears_all(self):
        """Test that invalidate without prefix clears entire cache."""
        c = SimpleCache(ttl_seconds=60)
        c.set("a", 1)
        c.set("b", 2)
        c.invalidate()
        assert c.get("a") is None
        assert c.get("b") is None


# ---------------------------------------------------------------------------
# invalidate_cache (module-level helper)
# ---------------------------------------------------------------------------


class TestInvalidateCache:
    """Tests for the invalidate_cache helper function."""

    def test_invalidates_global_cache(self):
        """Test that the module-level invalidate_cache calls cache.invalidate."""
        from app.core.cache import cache

        cache.set("test:key", "value")
        invalidate_cache("test")
        assert cache.get("test:key") is None


# ---------------------------------------------------------------------------
# cache_response decorator
# ---------------------------------------------------------------------------


class TestCacheResponseDecorator:
    """Tests for the cache_response decorator."""

    @pytest.mark.asyncio
    @patch("app.core.cache.settings")
    async def test_caches_function_result(self, mock_settings):
        """Test that decorated function result is cached."""
        mock_settings.CACHE_ENABLED = True
        mock_settings.CACHE_EXPIRE_SECONDS = 300

        call_count = 0

        @cache_response("test_prefix")
        async def my_func(x):
            nonlocal call_count
            call_count += 1
            return {"result": x}

        result1 = await my_func(42)
        result2 = await my_func(42)

        assert result1 == {"result": 42}
        assert result2 == {"result": 42}
        assert call_count == 1  # Second call was cached

    @pytest.mark.asyncio
    @patch("app.core.cache.settings")
    async def test_cache_disabled_bypasses(self, mock_settings):
        """Test that cache is bypassed when disabled."""
        mock_settings.CACHE_ENABLED = False

        call_count = 0

        @cache_response("test_prefix")
        async def my_func():
            nonlocal call_count
            call_count += 1
            return "result"

        await my_func()
        await my_func()

        assert call_count == 2  # Cache disabled, both calls executed

    @pytest.mark.asyncio
    @patch("app.core.cache.settings")
    async def test_skips_request_and_session_in_key(self, mock_settings):
        """Test that Request and AsyncSession args are excluded from cache key."""
        mock_settings.CACHE_ENABLED = True
        mock_settings.CACHE_EXPIRE_SECONDS = 300

        from fastapi import Request
        from sqlalchemy.ext.asyncio import AsyncSession

        @cache_response("prefix")
        async def my_func(request, db, value):
            return value

        mock_request = MagicMock(spec=Request)
        mock_db = MagicMock(spec=AsyncSession)

        result = await my_func(mock_request, mock_db, "hello")
        assert result == "hello"

    @pytest.mark.asyncio
    @patch("app.core.cache.settings")
    async def test_includes_username_in_key(self, mock_settings):
        """Test that current_user username is included in cache key."""
        mock_settings.CACHE_ENABLED = True
        mock_settings.CACHE_EXPIRE_SECONDS = 300

        call_count = 0

        @cache_response("user_prefix")
        async def my_func(current_user=None):
            nonlocal call_count
            call_count += 1
            return f"data_for_{current_user.username}" if current_user else "anon"

        user1 = MagicMock()
        user1.username = "alice"
        user2 = MagicMock()
        user2.username = "bob"

        await my_func(current_user=user1)
        await my_func(current_user=user2)

        assert call_count == 2  # Different users = different cache keys


# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    def test_allows_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter()
        assert limiter.is_allowed("user1", limit=5, window=60) is True
        assert limiter.is_allowed("user1", limit=5, window=60) is True

    def test_blocks_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter()
        for _ in range(5):
            limiter.is_allowed("user1", limit=5, window=60)
        assert limiter.is_allowed("user1", limit=5, window=60) is False

    def test_different_identifiers_are_independent(self):
        """Test that limits are tracked per identifier."""
        limiter = RateLimiter()
        for _ in range(5):
            limiter.is_allowed("user1", limit=5, window=60)
        # user2 should still be allowed
        assert limiter.is_allowed("user2", limit=5, window=60) is True

    def test_expired_requests_are_cleaned(self):
        """Test that old requests outside window are cleaned up."""
        limiter = RateLimiter()
        # Manually insert old timestamps
        limiter._requests["user1"] = [time.time() - 120]  # 2 minutes ago
        # With a 60 second window, old request should be cleaned
        assert limiter.is_allowed("user1", limit=1, window=60) is True
