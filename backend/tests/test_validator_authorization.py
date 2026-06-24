"""Provider-scoped authorization for validation endpoints (B12).

Validation resources are owned by a provider (archive -> dataset -> provider).
A user with no role on the owning provider must not read or trigger that
provider's validation work, and listing must be scoped to the user's providers.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.validators import (
    get_validation_job,
    list_validation_jobs,
    validate_dataset,
)
from app.models import DataProviderModel, DatasetModel, ValidationJobModel, XmlArchiveModel
from app.schemas.pagination import PaginationParams


async def _seed(db_session):
    db_session.add(DataProviderModel(id=7, datacenter="dc7", shortName="P7", name="P7"))
    db_session.add(DataProviderModel(id=5, datacenter="dc5", shortName="P5", name="P5"))
    db_session.add(DatasetModel(id=70, title="D70", source="s", provider_id=7))
    db_session.add(XmlArchiveModel(id=700, dataset_id=70, isLatest=True))
    db_session.add(
        ValidationJobModel(id=900, archive_id=700, task_id="t900", status="completed")
    )
    await db_session.flush()


def _user(provider_roles, *, admin=False):
    user = MagicMock()
    user.is_global_admin = admin
    user.provider_roles = provider_roles
    return user


@pytest.mark.asyncio
async def test_get_validation_job_denies_user_without_role_on_owner(db_session):
    await _seed(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await get_validation_job(job_id=900, current_user=_user({"5": "curator"}), db=db_session)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_validation_job_allows_owner(db_session):
    await _seed(db_session)
    job = await get_validation_job(job_id=900, current_user=_user({"7": "viewer"}), db=db_session)
    assert job.id == 900


@pytest.mark.asyncio
async def test_get_validation_job_allows_global_admin(db_session):
    await _seed(db_session)
    job = await get_validation_job(job_id=900, current_user=_user({}, admin=True), db=db_session)
    assert job.id == 900


@pytest.mark.asyncio
async def test_get_validation_job_missing_resource_is_404(db_session):
    await _seed(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await get_validation_job(job_id=99999, current_user=_user({}, admin=True), db=db_session)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_validate_dataset_denies_user_without_role_on_owner(db_session):
    await _seed(db_session)
    with pytest.raises(HTTPException) as exc_info:
        await validate_dataset(
            dataset_id=70, current_user=_user({"5": "curator"}), db=db_session, request=None
        )
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_list_validation_jobs_is_scoped_to_user_providers(db_session):
    await _seed(db_session)
    # A provider-5-owned job that the provider-5 user SHOULD see.
    db_session.add(DatasetModel(id=50, title="D50", source="s", provider_id=5))
    db_session.add(XmlArchiveModel(id=500, dataset_id=50, isLatest=True))
    db_session.add(
        ValidationJobModel(id=800, archive_id=500, task_id="t800", status="completed")
    )
    await db_session.flush()

    result = await list_validation_jobs(
        current_user=_user({"5": "curator"}),
        db=db_session,
        pagination=PaginationParams(limit=20),
        filters=[],
        sorts=[],
    )

    returned_ids = {job.id for job in result.data}
    assert returned_ids == {800}  # provider-7's job 900 is excluded
