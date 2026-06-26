"""Public, unauthenticated statistics reads must shed excess load with 429 (RH-08).

``POST /api/v1/validation-stats`` (a batched read of up to 500 dataset summaries)
and the public ``GET /api/v1/statistics/*`` reads run non-trivial DB queries with
no authentication. Without a per-IP rate limit a single client can saturate the
DB pool, while ``login`` / ``csrf`` / ``harvest`` already carry an ``@limiter.limit``
(REQ-ROUTE-2 / F-RATELIMIT-01).

These tests pin the limit on the real application instance through the full
middleware stack, mirroring the house idiom in ``tests/test_request_body_limit.py``:
import ``main``, drive ``TestClient(main.app)``, override ``get_db`` and patch the
service so the handler returns its normal 2xx without touching a real database —
the only thing under test is whether the limiter fires.

The limiter keeps per-IP counters in shared in-process storage, so the fixture
resets that storage before and after each test to keep them independent (the
harvest endpoint test instead rotates the client host for the same reason —
either way proves slowapi is live in tests and not disabled by a flag).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from limits import parse

import main
from app.api.deps import limiter
from app.core.config import settings
from app.db import get_db

VALIDATION_STATS_PATH = "/api/v1/validation-stats"


@pytest.fixture
def reset_limiter():
    """Clear the limiter's per-IP counters around each test (no cross-test bleed)."""
    limiter.reset()
    yield
    limiter.reset()


def _limit_amount() -> int:
    """The configured number of requests allowed per window for the public reads."""
    return parse(settings.PUBLIC_STATS_RATE_LIMIT).amount


def _override_get_db():
    yield MagicMock()


def test_public_validation_stats_is_rate_limited(reset_limiter):
    """A burst beyond the configured per-IP limit yields at least one 429.

    From one client host we issue ``limit + 1`` POSTs within a single window. With
    no ``@limiter.limit`` on the handler every request returns 200 and this fails;
    once the decorator is applied the request past the limit returns 429.
    """
    limit = _limit_amount()
    payload = {"identifiers": ["urn:gfbio.org:abcd:1_204_375"]}

    main.app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch("app.api.v1.endpoints.validation_stats.ValidationService") as MockService:
            fake_service = MagicMock()
            MockService.return_value = fake_service
            fake_service.get_validation_stats_for_datasets = AsyncMock(return_value={})
            client = TestClient(main.app)
            statuses = [
                client.post(VALIDATION_STATS_PATH, json=payload).status_code
                for _ in range(limit + 1)
            ]
    finally:
        main.app.dependency_overrides.clear()

    assert 429 in statuses, f"expected a 429 within {limit + 1} requests, got {statuses}"


def test_public_stats_single_call_ok(reset_limiter):
    """A single call is well within the limit and returns its normal 2xx, not 429."""
    payload = {"identifiers": ["urn:gfbio.org:abcd:1_204_375"]}

    main.app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch("app.api.v1.endpoints.validation_stats.ValidationService") as MockService:
            fake_service = MagicMock()
            MockService.return_value = fake_service
            fake_service.get_validation_stats_for_datasets = AsyncMock(return_value={})
            client = TestClient(main.app)
            response = client.post(VALIDATION_STATS_PATH, json=payload)
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 200
