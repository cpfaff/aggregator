"""Unit tests for EsGateway — the thin httpx-backed Elasticsearch test seam.

No live Elasticsearch: the underlying ``httpx.AsyncClient`` opened per call
inside the gateway is patched so canned ES 5.6 ``_count`` / ``_search`` bodies
can be returned (or transport errors raised). Every ES-down path must collapse
to the typed, non-throwing ``EsUnavailable`` outcome that T-7 maps to
``harvest_status = unknown`` — never a raw ``httpx.*`` leak, never a guessed
presence.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.config import Settings
from app.services.es_gateway import (
    ES_DATASET_ID_FIELD,
    ES_DATESTAMP_FIELD,
    URN_TEMPLATE,
    EsGateway,
    EsUnavailable,
    compose_dataset_urn,
)

TEST_URN = "urn:gfbio.org:abcd:17_42_99"


def _make_settings(**overrides) -> Settings:
    """Build a Settings instance with the required non-ES fields filled.

    DATABASE_URL and SECRET_KEY are mandatory on the model; ES_* default in
    code, so callers only override what a given test exercises.
    """
    base = {
        "DATABASE_URL": "postgresql+asyncpg://u:p@db/x",
        "SECRET_KEY": "test-secret",
    }
    base.update(overrides)
    return Settings(**base)


def _patch_async_client(post_result=None, post_side_effect=None):
    """Patch ``app.services.es_gateway.httpx.AsyncClient``.

    Returns ``(patcher, captured)`` where ``captured`` is a dict recording the
    kwargs ``AsyncClient(...)`` was constructed with and the inner client's
    ``.post`` mock, so tests can assert URL/body/timeout.
    """
    captured: dict = {}

    inner_client = MagicMock()
    inner_client.post = AsyncMock(return_value=post_result, side_effect=post_side_effect)
    captured["post"] = inner_client.post

    @asynccontextmanager
    async def fake_async_client(*args, **kwargs):
        captured["init_args"] = args
        captured["init_kwargs"] = kwargs
        yield inner_client

    def factory(*args, **kwargs):
        return fake_async_client(*args, **kwargs)

    patcher = patch("app.services.es_gateway.httpx.AsyncClient", side_effect=factory)
    return patcher, captured


def _canned_response(
    status_code: int, json_body: dict, *, method="POST", url="http://index:9200/x"
):
    """Build a real ``httpx.Response`` with an attached request (for raise_for_status)."""
    return httpx.Response(
        status_code,
        json=json_body,
        request=httpx.Request(method, url),
    )


# ---------------------------------------------------------------------------
# Pure URN helper (AC: URN string shape)
# ---------------------------------------------------------------------------


def test_compose_dataset_urn_formats_template():
    assert compose_dataset_urn(17, 42, 99) == "urn:gfbio.org:abcd:17_42_99"


def test_urn_template_is_the_gfbio_abcd_scheme():
    assert URN_TEMPLATE == "urn:gfbio.org:abcd:{provider_id}_{dataset_id}_{archive_id}"


def test_dataset_id_field_is_plain_per_t5_spike():
    # T-5 proved the plain field (.keyword sub-field returns 0).
    assert ES_DATASET_ID_FIELD == "abcdDatasetIdentifier"


# ---------------------------------------------------------------------------
# AC-2: count_for_urn parses an ES 5.6 _count body
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_count_for_urn_parses_es56_count():
    response = _canned_response(
        200, {"count": 4, "_shards": {"total": 5, "successful": 5, "failed": 0}}
    )
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        result = await gateway.count_for_urn(TEST_URN)

    assert result == 4

    # Assert the exact request: URL ends with type-in-path _count, body is a term query.
    call = captured["post"].call_args
    url = call.args[0] if call.args else call.kwargs["url"]
    assert url.endswith("/portals_v1/pansimple/_count")
    assert call.kwargs["json"] == {"query": {"term": {ES_DATASET_ID_FIELD: TEST_URN}}}


@pytest.mark.asyncio
async def test_count_for_urn_zero_is_valid_not_unavailable():
    response = _canned_response(200, {"count": 0, "_shards": {}})
    patcher, _ = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        result = await gateway.count_for_urn(TEST_URN)

    assert result == 0


# ---------------------------------------------------------------------------
# AC-3: latest_datestamp_for_urn parses a size-1 _search hit; empty != down
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latest_datestamp_parses_es56_search_hit():
    response = _canned_response(
        200,
        {
            "hits": {
                "total": 3,
                "hits": [
                    {
                        "_source": {ES_DATESTAMP_FIELD: "2026-06-20T03:14:00"},
                    }
                ],
            }
        },
    )
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        result = await gateway.latest_datestamp_for_urn(TEST_URN)

    assert result == datetime(2026, 6, 20, 3, 14, 0)

    # Assert the issued search body: size 1, term query, sort desc on the datestamp.
    call = captured["post"].call_args
    url = call.args[0] if call.args else call.kwargs["url"]
    assert url.endswith("/portals_v1/pansimple/_search")
    body = call.kwargs["json"]
    assert body["size"] == 1
    assert body["query"] == {"term": {ES_DATASET_ID_FIELD: TEST_URN}}
    assert body["sort"] == [{ES_DATESTAMP_FIELD: {"order": "desc"}}]


@pytest.mark.asyncio
async def test_latest_datestamp_empty_hits_returns_none_not_unavailable():
    response = _canned_response(200, {"hits": {"total": 0, "hits": []}})
    patcher, _ = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        result = await gateway.latest_datestamp_for_urn(TEST_URN)

    assert result is None


# ---------------------------------------------------------------------------
# AC-4: every ES-down path collapses to the typed EsUnavailable outcome
# ---------------------------------------------------------------------------

_COUNT_FAILURE_CASES = [
    pytest.param(
        {"post_side_effect": httpx.TimeoutException("timed out")},
        id="timeout",
    ),
    pytest.param(
        {"post_side_effect": httpx.ConnectError("connection refused")},
        id="connect-error",
    ),
    pytest.param(
        {"post_result_factory": lambda: _canned_response(503, {"error": "unavailable"})},
        id="non-2xx-503",
    ),
    pytest.param(
        {"post_result_factory": lambda: _canned_response(200, {})},
        id="garbled-body-missing-count",
    ),
]


@pytest.mark.parametrize("case", _COUNT_FAILURE_CASES)
@pytest.mark.asyncio
async def test_count_for_urn_es_down_raises_es_unavailable(case):
    result = case.get("post_result_factory", lambda: None)()
    patcher, _ = _patch_async_client(
        post_result=result, post_side_effect=case.get("post_side_effect")
    )
    with patcher, pytest.raises(EsUnavailable):
        gateway = EsGateway(settings=_make_settings())
        await gateway.count_for_urn(TEST_URN)


_SEARCH_FAILURE_CASES = [
    pytest.param(
        {"post_side_effect": httpx.TimeoutException("timed out")},
        id="timeout",
    ),
    pytest.param(
        {"post_side_effect": httpx.ConnectError("connection refused")},
        id="connect-error",
    ),
    pytest.param(
        {"post_result_factory": lambda: _canned_response(503, {"error": "unavailable"})},
        id="non-2xx-503",
    ),
    pytest.param(
        {"post_result_factory": lambda: _canned_response(200, {"hits": {}})},
        id="garbled-body-missing-hits",
    ),
]


@pytest.mark.parametrize("case", _SEARCH_FAILURE_CASES)
@pytest.mark.asyncio
async def test_latest_datestamp_es_down_raises_es_unavailable(case):
    result = case.get("post_result_factory", lambda: None)()
    patcher, _ = _patch_async_client(
        post_result=result, post_side_effect=case.get("post_side_effect")
    )
    with patcher, pytest.raises(EsUnavailable):
        gateway = EsGateway(settings=_make_settings())
        await gateway.latest_datestamp_for_urn(TEST_URN)


@pytest.mark.asyncio
async def test_es_unavailable_preserves_cause_chain():
    """B904: the wrapped httpx error is preserved as __cause__."""
    patcher, _ = _patch_async_client(post_side_effect=httpx.ConnectError("connection refused"))
    with patcher, pytest.raises(EsUnavailable) as exc_info:
        gateway = EsGateway(settings=_make_settings())
        await gateway.count_for_urn(TEST_URN)

    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


# ---------------------------------------------------------------------------
# AC-5: bounded explicit timeout is wired, not implicit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_configured_timeout_reaches_async_client():
    response = _canned_response(200, {"count": 1, "_shards": {}})
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings(ES_TIMEOUT_SECONDS=0.25))
        await gateway.count_for_urn(TEST_URN)

    timeout = captured["init_kwargs"]["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 0.25
    assert timeout.connect == 0.25


@pytest.mark.asyncio
async def test_default_timeout_is_five_seconds():
    response = _canned_response(200, {"count": 1, "_shards": {}})
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        await gateway.count_for_urn(TEST_URN)

    timeout = captured["init_kwargs"]["timeout"]
    assert timeout.read == 5.0


# ---------------------------------------------------------------------------
# Auth wiring: empty creds => no auth; non-empty => httpx.BasicAuth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_auth_when_credentials_empty():
    response = _canned_response(200, {"count": 1, "_shards": {}})
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings())
        await gateway.count_for_urn(TEST_URN)

    assert captured["init_kwargs"]["auth"] is None


@pytest.mark.asyncio
async def test_basic_auth_when_credentials_present():
    response = _canned_response(200, {"count": 1, "_shards": {}})
    patcher, captured = _patch_async_client(post_result=response)
    with patcher:
        gateway = EsGateway(settings=_make_settings(ES_USERNAME="elastic", ES_PASSWORD="changeme"))
        await gateway.count_for_urn(TEST_URN)

    assert isinstance(captured["init_kwargs"]["auth"], httpx.BasicAuth)
