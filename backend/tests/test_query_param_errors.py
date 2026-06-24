"""Query-parameter errors must map to HTTP 400, not an unhandled 500 (B9).

CursorError (invalid pagination cursor), FilterError (bad filter field/operator
or non-castable value) and SortError (bad sort field/direction) are raised while
resolving list endpoints. Without a registered handler they fall through to the
catch-all Exception handler and surface as 500. These tests pin the 400 mapping
on the real application instance.
"""

import asyncio

import pytest
from starlette.requests import Request

import main
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
