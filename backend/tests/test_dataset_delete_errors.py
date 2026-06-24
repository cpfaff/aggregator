"""Regression test for dataset-delete error sanitization (B15 follow-up).

DatasetService.delete_dataset echoed raw exception text into the 500 detail,
leaking driver/infra messages — the same class of leak fixed for the public
harvest feed (B15), here on the authenticated delete path.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models import DataProviderModel, DatasetModel
from app.services.dataset_service import DatasetService


@pytest.mark.asyncio
async def test_delete_dataset_500_does_not_leak_exception_text(db_session):
    db_session.add(
        DataProviderModel(id=1, datacenter="dc", shortName="P1", name="Provider 1")
    )
    db_session.add(DatasetModel(id=5, title="T", source="s", provider_id=1))
    await db_session.flush()

    service = DatasetService(db_session)
    with patch(
        "app.services.dataset_service.DatasetDeletionService.delete_dataset_cascade",
        side_effect=Exception("connection to host 192.168.0.184:5432 failed"),
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.delete_dataset(dataset_id=5, provider_id=1)

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Failed to delete dataset"
    assert "192.168.0.184" not in exc_info.value.detail
