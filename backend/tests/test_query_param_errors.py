"""Query-parameter errors must map to HTTP 400, not an unhandled 500 (B9).

CursorError (invalid pagination cursor), FilterError (bad filter field/operator
or non-castable value) and SortError (bad sort field/direction) are raised while
resolving list endpoints. Without a registered handler they fall through to the
catch-all Exception handler and surface as 500. These tests pin the 400 mapping
on the real application instance.
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

import main
from app.db import get_db
from app.security import get_current_user
from app.utils.filtering import FilterError
from app.utils.pagination import CursorError
from app.utils.sorting import SortError


def _fake_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/api/v1/x", "headers": []})


@pytest.mark.parametrize("exc_cls", [CursorError, FilterError, SortError])
def test_query_param_error_is_registered_and_returns_400(exc_cls):
    handler = main.app.exception_handlers.get(exc_cls)
    assert handler is not None, f"{exc_cls.__name__} has no exception handler"

    response = asyncio.run(handler(_fake_request(), exc_cls("bad query parameter")))

    assert response.status_code == 400


def _fake_admin():
    user = MagicMock()
    user.is_global_admin = True
    user.username = "admin"
    user.provider_roles = {}
    return user


def test_bad_filter_field_returns_400_through_full_http_stack():
    """End-to-end: a FilterError raised in a real dependency routes through the
    middleware chain to the 400 handler (not the catch-all 500). Guards B9
    against middleware/handler-routing regressions, per review."""
    main.app.dependency_overrides[get_current_user] = _fake_admin
    main.app.dependency_overrides[get_db] = lambda: MagicMock()
    try:
        client = TestClient(main.app)
        response = client.get("/api/v1/data-providers?filter[notafield]=x")
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["type"].endswith("/bad-request")
