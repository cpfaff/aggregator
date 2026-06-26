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

import asyncio
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

import main
from app.core.config import settings
from app.db import get_db
from main import BodySizeLimitMiddleware

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


# --------------------------------------------------------------------------- #
# Concurrency safety (RH-02 follow-up)
#
# The middleware is a SINGLE shared instance reused for every request. On the
# streamed path it must not stash request-scoped state (the ASGI ``scope``) on
# ``self`` and read it back after an ``await``: between the stash and the read
# there is an ``await receive()`` suspension point, so under concurrency a second
# request can overwrite the first request's stashed scope before the first one
# resumes and emits its 413. Each request must drive its 413 entirely from its
# own local ``scope``.
# --------------------------------------------------------------------------- #


def _oversized_scope(marker: str) -> dict:
    """A minimal HTTP ASGI scope for a chunked oversized request (no Content-Length)."""
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "path": VALIDATION_STATS_PATH,
        "raw_path": VALIDATION_STATS_PATH.encode(),
        "query_string": b"",
        "root_path": "",
        "scheme": "http",
        "headers": [(b"content-type", b"application/json")],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        # Distinguishing marker we can later attribute back to this request.
        "_marker": marker,
    }


@pytest.mark.asyncio
async def test_two_concurrent_oversized_streamed_requests_each_get_413():
    """Two concurrent oversized streamed requests are each independently rejected.

    Forces the interleaving that exposes shared per-request state: request ``A``
    enters ``__call__`` and starts counting streamed bytes; while ``A`` is
    suspended at ``await receive()`` request ``B`` runs to completion (overwriting
    any scope stashed on ``self``); then ``A`` resumes and emits its 413. With a
    shared ``self._scope`` the response object ``A`` sends would be built from
    ``B``'s scope. We assert that whatever scope each 413 is rendered against is
    that request's OWN scope, and that both produce a 413.
    """
    cap = settings.MAX_REQUEST_BODY_BYTES
    over = b"x" * (cap + 4096)

    # The inner app must never run for an oversized body (rejected at the edge).
    async def inner_app(scope, receive, send):  # pragma: no cover - must not run
        raise AssertionError("inner app reached for an oversized body")

    middleware = BodySizeLimitMiddleware(inner_app, max_body_bytes=cap)

    # A barrier that lets us pause request A inside its receive() until B has fully
    # run, then resume A — guaranteeing the cross-request interleaving window.
    a_first_receive_started = asyncio.Event()
    b_done = asyncio.Event()

    def make_receive(marker: str):
        calls = {"n": 0}

        async def receive():
            calls["n"] += 1
            if marker == "A" and calls["n"] == 1:
                # A signals it is at its first await receive(), then waits for B to
                # finish before delivering its (oversized) body chunk.
                a_first_receive_started.set()
                await b_done.wait()
            return {"type": "http.request", "body": over, "more_body": False}

        return receive

    # Each request records (its own scope marker, the scope marker actually used to
    # render its 413 response) so we can detect cross-request scope bleed.
    rendered_against: dict[str, str] = {}
    statuses: dict[str, int] = {}

    def make_send(scope_marker: str):
        async def send(message):
            if message["type"] == "http.response.start":
                statuses[scope_marker] = message["status"]

        return send

    async def drive(marker: str, *, wait_for_a: bool):
        scope = _oversized_scope(marker)
        # Spy on the response render to capture which scope it was given.
        import main as main_mod

        orig_call = main_mod.PlainTextResponse.__call__

        async def spy_call(self, scope_arg, receive_arg, send_arg):
            rendered_against[marker] = scope_arg.get("_marker")
            return await orig_call(self, scope_arg, receive_arg, send_arg)

        if wait_for_a:
            await a_first_receive_started.wait()
        # Patch only around our own response render. Both coroutines share the same
        # class, so we restore carefully; the assertion is on the captured marker.
        main_mod.PlainTextResponse.__call__ = spy_call
        try:
            await middleware(scope, make_receive(marker), make_send(marker))
        finally:
            main_mod.PlainTextResponse.__call__ = orig_call
        if marker == "B":
            b_done.set()

    await asyncio.gather(
        drive("A", wait_for_a=False),
        drive("B", wait_for_a=True),
    )

    # Both oversized requests must be rejected with 413.
    assert statuses == {"A": 413, "B": 413}
    # And each 413 must have been rendered against its OWN request scope — the
    # core concurrency-safety property. Under the shared-self bug, A's 413 renders
    # against B's scope.
    assert rendered_against["A"] == "A", (
        f"request A's 413 was rendered against scope {rendered_against['A']!r}, "
        "not its own — shared per-request state leaked across requests"
    )
    assert rendered_against["B"] == "B"


@pytest.mark.asyncio
async def test_concurrent_oversized_requests_through_asgi_app_all_413():
    """End-to-end: many concurrent oversized streamed requests all return 413.

    Drives the real application through ``httpx.ASGITransport`` with
    ``asyncio.gather`` so the requests genuinely interleave through the shared
    middleware instance. Every one must be independently rejected with 413.
    """
    cap = settings.MAX_REQUEST_BODY_BYTES

    async def _chunked_body():
        # An async generator body makes httpx omit Content-Length and stream the
        # request (Transfer-Encoding: chunked) under the AsyncClient.
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
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:

            async def one():
                return await client.post(
                    VALIDATION_STATS_PATH,
                    content=_chunked_body(),
                    headers={"Content-Type": "application/json"},
                )

            responses = await asyncio.gather(*(one() for _ in range(8)))
    finally:
        main.app.dependency_overrides.clear()

    assert [r.status_code for r in responses] == [413] * 8
