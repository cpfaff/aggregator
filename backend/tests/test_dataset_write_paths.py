"""Tests for carrying ``isHarvestReady`` through the dataset write paths.

``isHarvestReady`` is the per-dataset harvest gate (see the harvest-ready-flag
PRD). It must survive every write path that creates or updates a dataset, while
the authenticated management read paths stay un-gated so a provider can still see
and tune their staged datasets.

These tests drive the services directly against a real database session (the
codebase's service-test seam, mirroring ``tests/test_harvest_endpoint.py`` and
``tests/services/``). They cover four behaviours:

* primary create/update (``DatasetService``) persists the submitted flag;
* the nested provider-update *create* branch honours a provider-supplied flag;
* the nested provider-update *update* branch never clobbers an already-ready
  dataset back to staged (the sanctioned toggle is the dataset ``PUT``);
* a not-ready dataset still surfaces in the provider-scoped list and provider
  detail (the gate must not bleed past the harvester feed).
"""

from types import SimpleNamespace

import pytest

from app.models import DataProviderModel
from app.schemas import DataProvider, Dataset
from app.services.dataset_service import DatasetService
from app.services.provider_service import ProviderService


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


def _stub_user(*, is_global_admin=True):
    """A minimal stand-in for the request user.

    ``update_provider`` only reads ``is_global_admin`` and only when an
    ``isDataCenter`` change is submitted, which these tests never do.
    """
    return SimpleNamespace(is_global_admin=is_global_admin)


@pytest.mark.asyncio
async def test_nested_create_persists_provider_supplied_flag(db_session):
    """A *new* dataset created through a provider update with
    ``isHarvestReady=True`` reads back ``True``.

    The nested-create branch built the row field-by-field and dropped the flag,
    silently forcing the model default ``False`` — this is the documented drop
    site the fix closes.
    """
    await _add_provider(db_session, id=1)

    service = ProviderService(db_session)
    provider_data = DataProvider(
        datacenter="dc-1",
        shortName="P1",
        name="Provider 1",
        datasets=[Dataset(source="src", title="nested ready", isHarvestReady=True)],
    )

    result = await service.update_provider(1, provider_data, _stub_user())

    created = {ds.title: ds for ds in result.datasets}["nested ready"]
    assert created.isHarvestReady is True


@pytest.mark.asyncio
async def test_nested_create_defaults_false_when_flag_omitted(db_session):
    """A new dataset created through a provider update without the flag reads
    back ``False`` — the schema/model default, staged by design."""
    await _add_provider(db_session, id=1)

    service = ProviderService(db_session)
    provider_data = DataProvider(
        datacenter="dc-1",
        shortName="P1",
        name="Provider 1",
        datasets=[Dataset(source="src", title="nested staged")],
    )

    result = await service.update_provider(1, provider_data, _stub_user())

    created = {ds.title: ds for ds in result.datasets}["nested staged"]
    assert created.isHarvestReady is False


@pytest.mark.asyncio
async def test_primary_create_persists_explicit_ready(db_session):
    """The primary create path persists a submitted ``isHarvestReady=True``."""
    await _add_provider(db_session, id=1)

    service = DatasetService(db_session)
    created = await service.create_dataset(
        1, Dataset(source="src", title="ready", isHarvestReady=True)
    )

    assert created.isHarvestReady is True


@pytest.mark.asyncio
async def test_primary_create_defaults_false_when_omitted(db_session):
    """The primary create path defaults to ``False`` (staged) when the flag is
    omitted from the payload."""
    await _add_provider(db_session, id=1)

    service = DatasetService(db_session)
    created = await service.create_dataset(1, Dataset(source="src", title="staged"))

    assert created.isHarvestReady is False


@pytest.mark.asyncio
async def test_primary_update_toggles_flag_both_ways(db_session):
    """The primary update path persists the flag in both directions —
    ``False -> True`` (publish) and ``True -> False`` (re-stage)."""
    await _add_provider(db_session, id=1)
    service = DatasetService(db_session)
    created = await service.create_dataset(
        1, Dataset(source="src", title="t", isHarvestReady=False)
    )

    flipped_on = await service.update_dataset(
        created.id, 1, Dataset(source="src", title="t", isHarvestReady=True)
    )
    assert flipped_on.isHarvestReady is True

    flipped_off = await service.update_dataset(
        created.id, 1, Dataset(source="src", title="t", isHarvestReady=False)
    )
    assert flipped_off.isHarvestReady is False


@pytest.mark.asyncio
async def test_nested_update_does_not_clobber_ready_flag(db_session):
    """Editing an unrelated field of a *ready* dataset through a provider update
    must NOT re-stage it.

    The nested provider-update path is not a harvest-ready toggle path (the
    dataset ``PUT`` is). Because the ``Dataset`` schema defaults the flag to
    ``False``, assigning it here on an edit that omits it would silently stage a
    previously-ready dataset — the AC 3 footgun.
    """
    await _add_provider(db_session, id=1)
    ds_service = DatasetService(db_session)
    created = await ds_service.create_dataset(
        1, Dataset(source="src", title="orig", isHarvestReady=True)
    )

    prov_service = ProviderService(db_session)
    provider_data = DataProvider(
        datacenter="dc-1",
        shortName="P1",
        name="Provider 1",
        datasets=[Dataset(id=created.id, source="src", title="renamed")],
    )

    result = await prov_service.update_provider(1, provider_data, _stub_user())

    updated = {ds.id: ds for ds in result.datasets}[created.id]
    # The edit took effect (guards against a false-green where nothing happened).
    assert updated.title == "renamed"
    # ...but the ready flag survived untouched.
    assert updated.isHarvestReady is True


@pytest.mark.asyncio
async def test_not_ready_dataset_stays_in_provider_scoped_list(db_session):
    """A not-ready dataset still appears in the provider-scoped dataset list and
    carries its ``isHarvestReady`` field — the management list is un-gated."""
    await _add_provider(db_session, id=1)
    service = DatasetService(db_session)
    staged = await service.create_dataset(
        1, Dataset(source="src", title="staged", isHarvestReady=False)
    )

    listing = await service.list_datasets(1)

    returned = {ds.id: ds for ds in listing.data}
    assert staged.id in returned
    assert returned[staged.id].isHarvestReady is False


@pytest.mark.asyncio
async def test_not_ready_dataset_stays_in_provider_detail(db_session):
    """A not-ready dataset still appears in provider detail and carries the
    ``isHarvestReady`` field — the gate must not bleed past the harvester feed."""
    await _add_provider(db_session, id=1)
    ds_service = DatasetService(db_session)
    staged = await ds_service.create_dataset(
        1, Dataset(source="src", title="staged", isHarvestReady=False)
    )

    prov_service = ProviderService(db_session)
    provider = await prov_service.get_provider_or_404(1)

    detail = {ds.id: ds for ds in provider.datasets}
    assert staged.id in detail
    assert detail[staged.id].isHarvestReady is False
