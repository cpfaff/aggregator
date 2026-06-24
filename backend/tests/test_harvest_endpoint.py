"""Tests for the legacy harvester feed endpoint (GET /v1/legacy-data-sets).

The harvester feed is gated on ``isHarvestReady``: only datasets a provider has
flipped to ready are offered to external harvesters, which is what keeps staged
datasets out of the public index. These tests exercise that gate through the
endpoint coroutine against a real database session (the codebase's endpoint-test
pattern, see ``tests/services/test_validation_service.py`` for the seeding style).
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from starlette.requests import Request

from app.api.v1.endpoints.harvest import harvest_datasets
from app.models import DataProviderModel, DatasetModel


def _make_request() -> Request:
    """Build a minimal real ``Request`` so the ``@limiter.limit`` decorator runs.

    slowapi reads ``request.client`` / ``request["path"]`` before reaching the
    query, so a bare mock would stop the call short. A unique client host per
    call gives each invocation its own rate-limit bucket, so repeated calls in
    the suite never exhaust ``HARVEST_RATE_LIMIT``.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/v1/legacy-data-sets",
        "headers": [],
        "query_string": b"",
        "client": (f"test-{uuid.uuid4()}", 12345),
    }
    return Request(scope)


async def _add_provider(db_session, *, id):
    provider = DataProviderModel(
        id=id,
        datacenter=f"dc-{id}",
        shortName=f"P{id}",
        name=f"Provider {id}",
    )
    db_session.add(provider)
    await db_session.flush()
    return provider


async def _add_dataset(db_session, *, id, provider_id, is_harvest_ready):
    dataset = DatasetModel(
        id=id,
        title=f"Dataset {id}",
        source=f"source-{id}",
        provider_id=provider_id,
        isHarvestReady=is_harvest_ready,
    )
    db_session.add(dataset)
    await db_session.flush()
    return dataset


@pytest.mark.asyncio
async def test_feed_returns_ready_and_excludes_not_ready_across_providers(db_session):
    """The feed contains exactly the harvest-ready dataset ids, across more than
    one provider, and none of the not-ready ids.

    AC3 happy-path reachability is folded in: the ``== {10, 20}`` assertion is
    non-empty, so a call that errored to ``[]`` before reaching the query would
    fail this test rather than pass it falsely.
    """
    await _add_provider(db_session, id=1)
    await _add_provider(db_session, id=2)
    # Each provider owns one ready and one not-ready dataset.
    await _add_dataset(db_session, id=10, provider_id=1, is_harvest_ready=True)
    await _add_dataset(db_session, id=11, provider_id=1, is_harvest_ready=False)
    await _add_dataset(db_session, id=20, provider_id=2, is_harvest_ready=True)
    await _add_dataset(db_session, id=21, provider_id=2, is_harvest_ready=False)

    result = await harvest_datasets(request=_make_request(), db=db_session)

    returned_ids = {ds.dataset_id for ds in result}
    # A ready dataset IS returned (guards against a false-empty green).
    assert 10 in returned_ids
    assert 20 in returned_ids
    # Exactly the ready ids, none of the not-ready ids.
    assert returned_ids == {10, 20}
    assert 11 not in returned_ids
    assert 21 not in returned_ids


@pytest.mark.asyncio
async def test_feed_is_empty_when_database_has_no_providers(db_session):
    """An empty database yields an empty feed, not an error."""
    result = await harvest_datasets(request=_make_request(), db=db_session)

    assert result == []


@pytest.mark.asyncio
async def test_provider_with_only_not_ready_datasets_contributes_nothing(db_session):
    """A provider whose datasets are all not-ready adds zero rows and must not
    error — the gate fully empties that provider's contribution."""
    await _add_provider(db_session, id=5)
    await _add_dataset(db_session, id=50, provider_id=5, is_harvest_ready=False)
    await _add_dataset(db_session, id=51, provider_id=5, is_harvest_ready=False)

    result = await harvest_datasets(request=_make_request(), db=db_session)

    assert result == []


@pytest.mark.asyncio
async def test_ready_dataset_without_archives_or_links_still_serializes(db_session):
    """A ready dataset with no xml archives and no useful links still appears in
    the feed, carrying empty archive/link lists."""
    await _add_provider(db_session, id=7)
    await _add_dataset(db_session, id=70, provider_id=7, is_harvest_ready=True)

    result = await harvest_datasets(request=_make_request(), db=db_session)

    assert len(result) == 1
    legacy = result[0]
    assert legacy.dataset_id == 70
    assert legacy.xml_archives == []
    assert legacy.useful_links == []


@pytest.mark.asyncio
async def test_harvest_500_does_not_leak_internal_exception_text():
    """The public harvest feed must not echo raw driver/infra text to clients (B15)."""

    class _BoomDB:
        async def execute(self, *args, **kwargs):
            raise OperationalError(
                "SELECT ...", {}, Exception("connection to host 192.168.0.184:5432 failed")
            )

    with pytest.raises(HTTPException) as exc_info:
        await harvest_datasets(request=_make_request(), db=_BoomDB())

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"
    assert "192.168.0.184" not in exc_info.value.detail
