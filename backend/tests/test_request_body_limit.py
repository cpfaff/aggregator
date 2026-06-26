"""Oversized request bodies must be rejected with HTTP 413 at the edge (RH-02).

Every JSON route — including the public, unauthenticated ``POST
/api/v1/validation-stats`` — buffers the full request body into memory and parses
it into a model before any handler logic. With no body-size guard and no infra
cap that is a memory-exhaustion DoS (REQ-ROUTE-1 / F-BODY-01).

These tests pin the guard on the real application instance through the full
middleware stack:

* an oversized body declared via an explicit ``Content-Length`` header is
  rejected with 413 *before* the handler (and therefore before the DB) is
  touched — proven by overriding ``get_db`` with a sentinel that fails the test
  if the handler is ever reached;
* a chunked oversized body (no ``Content-Length``) is rejected by the
  streamed-byte counter, since ``Content-Length`` alone cannot be trusted;
* a normal small body still flows through (guard is not over-eager).

House idiom mirrors ``tests/test_query_param_errors.py``: import ``main``, drive
``TestClient(main.app)``, override ``get_db`` to keep the DB out of the way.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import main
from app.core.config import settings
from app.db import get_db

VALIDATION_STATS_PATH = "/api/v1/validation-stats"


def _fail_if_handler_runs():
    """A ``get_db`` override that fails the test if the handler is ever reached.

    The 413 path must short-circuit in the middleware before FastAPI resolves
    the route's dependencies, so this generator must never be entered.
    """
    pytest.fail("handler dependency (get_db) was resolved — body was not rejected at edge")
    yield  # pragma: no cover - never reached


def test_oversized_body_rejected_with_413():
    """A body over the cap, declared via Content-Length, is rejected with 413.

    The payload is otherwise-valid JSON that passes the per-field item-count
    limit (a single identifier) yet exceeds ``MAX_REQUEST_BODY_BYTES`` — so a
    422/200 here would mean the body was buffered and parsed, never the 413 the
    guard must produce.
    """
    cap = settings.MAX_REQUEST_BODY_BYTES
    # One long-but-valid identifier string padded to push the JSON body over the
    # cap. The list still has a single item, so the 500-item limit is not what
    # rejects it — only the size guard can.
    padding = "x" * (cap + 1024)
    body = ('{"identifiers": ["urn:gfbio.org:abcd:1_204_' + padding + '"]}').encode()
    assert len(body) > cap

    main.app.dependency_overrides[get_db] = _fail_if_handler_runs
    try:
        client = TestClient(main.app)
        response = client.post(
            VALIDATION_STATS_PATH,
            content=body,
            headers={"Content-Type": "application/json"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 413


def test_oversized_chunked_body_rejected_with_413():
    """A chunked oversized body (no Content-Length) is rejected by the byte counter.

    ``Content-Length`` is omitted for a streamed/chunked upload, so the guard
    cannot rely on the header alone; the streamed-byte counter must still enforce
    the cap and reject with 413.
    """
    cap = settings.MAX_REQUEST_BODY_BYTES

    def _chunked_body():
        # Stream more than the cap in chunks; httpx omits Content-Length and uses
        # Transfer-Encoding: chunked for a generator body.
        emitted = 0
        chunk = b"x" * 8192
        prefix = b'{"identifiers": ["urn:gfbio.org:abcd:1_204_'
        yield prefix
        emitted += len(prefix)
        while emitted <= cap + 8192:
            yield chunk
            emitted += len(chunk)
        yield b'375"]}'

    main.app.dependency_overrides[get_db] = _fail_if_handler_runs
    try:
        client = TestClient(main.app)
        response = client.post(
            VALIDATION_STATS_PATH,
            content=_chunked_body(),
            headers={"Content-Type": "application/json"},
        )
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code == 413


def test_normal_body_passes():
    """A small, well-formed body flows through the guard to the handler (not 413).

    Proves the guard is not over-eager: a ~2 KiB body reaches the handler and
    returns its usual 2xx, never a 413.
    """
    identifiers = [f"urn:gfbio.org:abcd:1_{i}_375" for i in range(50)]
    payload = {"identifiers": identifiers}

    fake_service = MagicMock()

    def _override_get_db():
        yield MagicMock()

    main.app.dependency_overrides[get_db] = _override_get_db
    try:
        from unittest.mock import AsyncMock, patch

        with patch("app.api.v1.endpoints.validation_stats.ValidationService") as MockService:
            MockService.return_value = fake_service
            fake_service.get_validation_stats_for_datasets = AsyncMock(return_value={})
            client = TestClient(main.app)
            response = client.post(VALIDATION_STATS_PATH, json=payload)
    finally:
        main.app.dependency_overrides.clear()

    assert response.status_code != 413
    assert response.status_code == 200
