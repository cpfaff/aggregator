"""Tests for validation API endpoints.

Tests the HTTP contract layer: correct service wiring, response models,
status codes, and error handling. Service logic is tested separately
in tests/services/test_validation_service.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.validators import (
    create_validation_job,
    get_dataset_validation_status,
    get_validation_job,
    get_validation_results,
    list_validation_jobs,
    validate_dataset_latest_archive,
)

# ---------------------------------------------------------------------------
# POST / (create validation job)
# ---------------------------------------------------------------------------


class TestCreateValidationJob:
    """Tests for POST / endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_creates_job_and_returns_201(self, MockServiceClass):
        """Test happy path creates a validation job."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.create_validation_job = AsyncMock(
            return_value={
                "task_id": "celery-task-123",
                "job_id": 1,
                "archive_id": 42,
                "status": "pending",
            }
        )

        mock_request = MagicMock()
        mock_request.archive_id = 42

        result = await create_validation_job(
            request=mock_request, current_user=MagicMock(), db=MagicMock()
        )

        assert result["task_id"] == "celery-task-123"
        assert result["job_id"] == 1
        assert result["status"] == "pending"
        mock_service.create_validation_job.assert_awaited_once_with(42)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_archive_not_found_raises_404(self, MockServiceClass):
        """Test that submitting job for non-existent archive raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.create_validation_job = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Archive not found")
        )

        mock_request = MagicMock()
        mock_request.archive_id = 999

        with pytest.raises(HTTPException) as exc_info:
            await create_validation_job(
                request=mock_request, current_user=MagicMock(), db=MagicMock()
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /{job_id}
# ---------------------------------------------------------------------------


class TestGetValidationJob:
    """Tests for GET /{job_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_returns_job_details(self, MockServiceClass):
        """Test happy path returns validation job."""
        mock_job = MagicMock()
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_validation_job = AsyncMock(return_value=mock_job)

        result = await get_validation_job(
            job_id=1, current_user=MagicMock(), db=MagicMock()
        )

        assert result is mock_job
        mock_service.get_validation_job.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_job_not_found_raises_404(self, MockServiceClass):
        """Test that missing job raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_validation_job = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Job not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_validation_job(
                job_id=999, current_user=MagicMock(), db=MagicMock()
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET / (list validation jobs)
# ---------------------------------------------------------------------------


class TestListValidationJobs:
    """Tests for GET / endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_returns_list_of_jobs(self, MockServiceClass):
        """Test happy path returns list of jobs."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.list_validation_jobs = AsyncMock(return_value=[])

        result = await list_validation_jobs(
            current_user=MagicMock(), db=MagicMock()
        )

        assert result == []

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_forwards_filter_params(self, MockServiceClass):
        """Test that archive_id, status, limit, offset params are forwarded."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.list_validation_jobs = AsyncMock(return_value=[])

        await list_validation_jobs(
            current_user=MagicMock(),
            db=MagicMock(),
            archive_id=42,
            status="completed",
            limit=5,
            offset=10,
        )

        mock_service.list_validation_jobs.assert_awaited_once_with(
            archive_id=42, status_filter="completed", limit=5, offset=10
        )

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_defaults_no_filters(self, MockServiceClass):
        """Test that default params use None for optional filters."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.list_validation_jobs = AsyncMock(return_value=[])

        await list_validation_jobs(
            current_user=MagicMock(), db=MagicMock()
        )

        mock_service.list_validation_jobs.assert_awaited_once_with(
            archive_id=None, status_filter=None, limit=10, offset=0
        )


# ---------------------------------------------------------------------------
# GET /{job_id}/results
# ---------------------------------------------------------------------------


class TestGetValidationResults:
    """Tests for GET /{job_id}/results endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_returns_results_dict(self, MockServiceClass):
        """Test happy path returns validation results."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_validation_results = AsyncMock(
            return_value={"summary": {"total_files": 10, "valid_files": 8}}
        )

        result = await get_validation_results(
            job_id=1, current_user=MagicMock(), db=MagicMock()
        )

        assert result["summary"]["total_files"] == 10
        mock_service.get_validation_results.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_job_not_completed_raises_400(self, MockServiceClass):
        """Test that incomplete job raises 400."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_validation_results = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Job not completed")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_validation_results(
                job_id=1, current_user=MagicMock(), db=MagicMock()
            )

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_results_not_found_raises_404(self, MockServiceClass):
        """Test that missing results raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_validation_results = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Results not found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_validation_results(
                job_id=1, current_user=MagicMock(), db=MagicMock()
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# GET /datasets/{dataset_id}/validation-status
# ---------------------------------------------------------------------------


class TestGetDatasetValidationStatus:
    """Tests for GET /datasets/{dataset_id}/validation-status endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_returns_status_model(self, MockServiceClass):
        """Test happy path returns DatasetValidationStatus model."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_dataset_validation_status = AsyncMock(
            return_value={
                "dataset_id": 1,
                "archive_id": 10,
                "has_latest_archive": True,
                "validation_status": "completed",
                "validation_id": 5,
                "last_validated_at": None,
                "is_valid": True,
                "quality_score": 0.95,
                "validation_results": None,
            }
        )

        result = await get_dataset_validation_status(
            dataset_id=1, current_user=MagicMock(), db=MagicMock()
        )

        assert result.dataset_id == 1
        assert result.has_latest_archive is True
        assert result.is_valid is True
        assert result.quality_score == 0.95

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_no_archive_returns_default(self, MockServiceClass):
        """Test that dataset with no archive returns has_latest_archive=False."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.get_dataset_validation_status = AsyncMock(
            return_value={
                "dataset_id": 99,
                "archive_id": None,
                "has_latest_archive": False,
                "validation_status": None,
                "validation_id": None,
                "last_validated_at": None,
                "is_valid": None,
                "quality_score": None,
                "validation_results": None,
            }
        )

        result = await get_dataset_validation_status(
            dataset_id=99, current_user=MagicMock(), db=MagicMock()
        )

        assert result.has_latest_archive is False
        assert result.validation_status is None


# ---------------------------------------------------------------------------
# POST /datasets/{dataset_id}/validate
# ---------------------------------------------------------------------------


class TestValidateDatasetLatestArchive:
    """Tests for POST /datasets/{dataset_id}/validate endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_creates_new_validation(self, MockServiceClass):
        """Test happy path creates validation for dataset's latest archive."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.validate_dataset_latest_archive = AsyncMock(
            return_value={
                "task_id": "celery-task-456",
                "job_id": 2,
                "archive_id": 10,
                "status": "pending",
            }
        )

        result = await validate_dataset_latest_archive(
            dataset_id=1, current_user=MagicMock(), db=MagicMock()
        )

        assert result["task_id"] == "celery-task-456"
        assert result["status"] == "pending"
        mock_service.validate_dataset_latest_archive.assert_awaited_once_with(1, force=False)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_force_flag_forwarded(self, MockServiceClass):
        """Test that force=True is forwarded to service."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.validate_dataset_latest_archive = AsyncMock(
            return_value={
                "task_id": "celery-task-789",
                "job_id": 3,
                "archive_id": 10,
                "status": "pending",
            }
        )

        await validate_dataset_latest_archive(
            dataset_id=1, current_user=MagicMock(), db=MagicMock(), force=True
        )

        mock_service.validate_dataset_latest_archive.assert_awaited_once_with(1, force=True)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.validators.ValidationService")
    async def test_no_archive_raises_404(self, MockServiceClass):
        """Test that dataset with no latest archive raises 404."""
        mock_service = MagicMock()
        MockServiceClass.return_value = mock_service
        mock_service.validate_dataset_latest_archive = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="No latest archive found")
        )

        with pytest.raises(HTTPException) as exc_info:
            await validate_dataset_latest_archive(
                dataset_id=999, current_user=MagicMock(), db=MagicMock()
            )

        assert exc_info.value.status_code == 404
