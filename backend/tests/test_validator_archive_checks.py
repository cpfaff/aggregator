"""Archive-wide checks stored in validation results and exposed in the status."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.validation_service import ValidationService
from app.tasks.validator.service import ValidatorService
from tests.abcd_zip_fixtures import build_abcd_zip

CROSS_FILE = {
    "response.00001.xml": ["ZFMK-Ac-00987", "ZFMK-Ac-00712", "ZFMK-Ac-00712"],
    "response.00002.xml": ["ZFMK-Ac-00987", "ZFMK-Ac-00001"],
}


@pytest.fixture
def archive(tmp_path):
    return build_abcd_zip(tmp_path / "archive.zip", CROSS_FILE)


def test_report_contains_archive_checks(archive):
    report = ValidatorService().validate_archive("file://unused", archive_path=str(archive))

    check = report["validation_results"]["archive_checks"]["duplicate_unit_ids"]
    assert check["units_not_indexable"] == 2
    assert check["duplicated_unit_ids"] == 2
    assert report["summary"]["units_not_indexable"] == 2


def test_check_error_is_recorded_not_raised(archive):
    with patch(
        "app.tasks.validator.service.find_duplicate_unit_ids",
        side_effect=ValueError("boom"),
    ):
        report = ValidatorService().validate_archive("file://unused", archive_path=str(archive))

    assert report["validation_results"]["archive_checks"]["duplicate_unit_ids"] == {"error": "boom"}
    assert "units_not_indexable" not in report["summary"]


def _service_with_results(results):
    service = ValidationService(MagicMock())
    service.repo = MagicMock()
    service.repo.get_latest_archive_for_dataset = AsyncMock(return_value=MagicMock(id=7))
    service.repo.get_latest_non_obsolete_job = AsyncMock(
        return_value=MagicMock(
            id=3, status="completed", results=results, completed_at=None, started_at=None
        )
    )
    service.cleanup_obsolete_pending_jobs = AsyncMock()
    return service


@pytest.mark.asyncio
async def test_status_exposes_units_not_indexable():
    service = _service_with_results(
        {"summary": {"total_files": 2, "valid_files": 2, "units_not_indexable": 2124}}
    )
    status = await service.get_dataset_validation_status(1)
    assert status["units_not_indexable"] == 2124


@pytest.mark.asyncio
async def test_status_without_archive_checks_returns_none():
    service = _service_with_results({"summary": {"total_files": 2, "valid_files": 2}})
    status = await service.get_dataset_validation_status(1)
    assert status["units_not_indexable"] is None
