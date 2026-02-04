"""
Unit tests for ValidationService.

Tests all validation job management operations with real database via testcontainers,
following TDD principles and covering edge cases.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException

from app.models.dataset import DatasetModel, XmlArchiveModel
from app.models.provider import DataProviderModel
from app.models.validation import ValidationJobModel
from app.services.validation_service import ValidationService


@pytest_asyncio.fixture
async def validation_service(db_session):
    """Create ValidationService instance with test database session."""
    return ValidationService(db_session)


@pytest_asyncio.fixture
async def sample_provider(db_session):
    """Create a sample data provider for testing."""
    provider = DataProviderModel(
        id=1,
        datacenter="test-datacenter",
        shortName="TP",
        name="Test Provider",
    )
    db_session.add(provider)
    await db_session.flush()
    return provider


@pytest_asyncio.fixture
async def sample_dataset(db_session, sample_provider):
    """Create a sample dataset for testing."""
    dataset = DatasetModel(
        id=1,
        title="Test Dataset",
        source="test-source",
        provider_id=sample_provider.id,
        landingPageUrl="http://example.com/landing",
    )
    db_session.add(dataset)
    await db_session.flush()
    return dataset


@pytest_asyncio.fixture
async def sample_archive(db_session, sample_dataset):
    """Create a sample XML archive for testing."""
    archive = XmlArchiveModel(
        id=1,
        dataset_id=sample_dataset.id,
        url="http://example.com/archive.xml",
        isLatest=True,
    )
    db_session.add(archive)
    await db_session.flush()
    return archive


@pytest_asyncio.fixture
async def another_archive(db_session, sample_dataset):
    """Create another XML archive for testing."""
    archive = XmlArchiveModel(
        id=2,
        dataset_id=sample_dataset.id,
        url="http://example.com/archive2.xml",
        isLatest=False,
    )
    db_session.add(archive)
    await db_session.flush()
    return archive


@pytest_asyncio.fixture
async def sample_validation_job(db_session, sample_archive):
    """Create a sample validation job for testing."""
    job = ValidationJobModel(
        id=1,
        archive_id=sample_archive.id,
        status="pending",
        task_id="test-task-123",
    )
    db_session.add(job)
    await db_session.flush()
    return job


# Test get_archive_or_404
@pytest.mark.asyncio
async def test_get_archive_or_404_found(validation_service, sample_archive):
    """Test getting archive by ID when it exists."""
    archive = await validation_service.get_archive_or_404(sample_archive.id)
    assert archive.id == sample_archive.id
    assert archive.isLatest is True


@pytest.mark.asyncio
async def test_get_archive_or_404_not_found(validation_service):
    """Test getting archive by ID when it doesn't exist raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await validation_service.get_archive_or_404(999)
    assert exc_info.value.status_code == 404
    assert "Archive with ID 999 not found" in exc_info.value.detail


# Test create_validation_job (happy path + archive not found)
@pytest.mark.asyncio
@patch("app.services.validation_service.validate_archive")
async def test_create_validation_job_success(mock_validate, validation_service, sample_archive):
    """Test creating a validation job successfully."""
    mock_task = MagicMock()
    mock_task.id = "celery-task-abc123"
    mock_validate.delay.return_value = mock_task

    result = await validation_service.create_validation_job(sample_archive.id)

    assert result["archive_id"] == sample_archive.id
    assert result["task_id"] == "celery-task-abc123"
    assert result["status"] == "pending"
    assert "job_id" in result

    mock_validate.delay.assert_called_once_with(sample_archive.id, job_id=result["job_id"])


@pytest.mark.asyncio
async def test_create_validation_job_archive_not_found(validation_service):
    """Test creating validation job for non-existent archive raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await validation_service.create_validation_job(999)
    assert exc_info.value.status_code == 404


# Test get_validation_job (found + not found)
@pytest.mark.asyncio
async def test_get_validation_job_found(validation_service, sample_validation_job):
    """Test getting validation job by ID when it exists."""
    job = await validation_service.get_validation_job(sample_validation_job.id)
    assert job.id == sample_validation_job.id
    assert job.status == "pending"
    assert job.task_id == "test-task-123"


@pytest.mark.asyncio
async def test_get_validation_job_not_found(validation_service):
    """Test getting validation job when it doesn't exist raises 404."""
    with pytest.raises(HTTPException) as exc_info:
        await validation_service.get_validation_job(999)
    assert exc_info.value.status_code == 404
    assert "Validation job with ID 999 not found" in exc_info.value.detail


# Test list_validation_jobs (filters, pagination)
@pytest.mark.asyncio
async def test_list_validation_jobs_empty(validation_service):
    """Test listing validation jobs when none exist."""
    jobs = await validation_service.list_validation_jobs()
    assert jobs == []


@pytest.mark.asyncio
async def test_list_validation_jobs_with_data(
    validation_service, db_session, sample_archive, another_archive
):
    """Test listing all validation jobs."""
    # Create multiple jobs
    job1 = ValidationJobModel(archive_id=sample_archive.id, status="completed", task_id="task-1")
    job2 = ValidationJobModel(archive_id=another_archive.id, status="pending", task_id="task-2")
    db_session.add_all([job1, job2])
    await db_session.flush()

    jobs = await validation_service.list_validation_jobs()
    assert len(jobs) == 2


@pytest.mark.asyncio
async def test_list_validation_jobs_filter_by_archive(
    validation_service, db_session, sample_archive, another_archive
):
    """Test filtering validation jobs by archive ID."""
    job1 = ValidationJobModel(archive_id=sample_archive.id, status="completed", task_id="task-1")
    job2 = ValidationJobModel(archive_id=another_archive.id, status="pending", task_id="task-2")
    db_session.add_all([job1, job2])
    await db_session.flush()

    jobs = await validation_service.list_validation_jobs(archive_id=sample_archive.id)
    assert len(jobs) == 1
    assert jobs[0].archive_id == sample_archive.id


@pytest.mark.asyncio
async def test_list_validation_jobs_filter_by_status(
    validation_service, db_session, sample_archive
):
    """Test filtering validation jobs by status."""
    job1 = ValidationJobModel(archive_id=sample_archive.id, status="completed", task_id="task-1")
    job2 = ValidationJobModel(archive_id=sample_archive.id, status="pending", task_id="task-2")
    db_session.add_all([job1, job2])
    await db_session.flush()

    jobs = await validation_service.list_validation_jobs(status_filter="completed")
    assert len(jobs) == 1
    assert jobs[0].status == "completed"


@pytest.mark.asyncio
async def test_list_validation_jobs_pagination(validation_service, db_session, sample_archive):
    """Test pagination with limit and offset."""
    # Create 5 jobs
    for i in range(5):
        job = ValidationJobModel(
            archive_id=sample_archive.id,
            status="pending",
            task_id=f"task-{i}",
        )
        db_session.add(job)
    await db_session.flush()

    # Test limit
    jobs = await validation_service.list_validation_jobs(limit=2)
    assert len(jobs) == 2

    # Test offset
    jobs = await validation_service.list_validation_jobs(limit=10, offset=3)
    assert len(jobs) == 2

    # Test offset + limit
    jobs = await validation_service.list_validation_jobs(limit=2, offset=1)
    assert len(jobs) == 2


# Test get_validation_results (completed + not completed + no results)
@pytest.mark.asyncio
async def test_get_validation_results_completed_with_results(
    validation_service, db_session, sample_archive
):
    """Test getting validation results for completed job with results."""
    job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="completed",
        task_id="task-1",
        results={"summary": {"total_files": 10, "valid_files": 8}},
    )
    db_session.add(job)
    await db_session.flush()

    results = await validation_service.get_validation_results(job.id)
    assert results == {"summary": {"total_files": 10, "valid_files": 8}}


@pytest.mark.asyncio
async def test_get_validation_results_not_completed(validation_service, sample_validation_job):
    """Test getting results for non-completed job raises 400."""
    with pytest.raises(HTTPException) as exc_info:
        await validation_service.get_validation_results(sample_validation_job.id)
    assert exc_info.value.status_code == 400
    assert "not completed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_validation_results_no_results(validation_service, db_session, sample_archive):
    """Test getting results for completed job without results raises 404."""
    job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="completed",
        task_id="task-1",
        results=None,  # No results
    )
    db_session.add(job)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await validation_service.get_validation_results(job.id)
    assert exc_info.value.status_code == 404
    assert "Validation results not found" in exc_info.value.detail


# Test cleanup_obsolete_pending_jobs (matching completed jobs)
@pytest.mark.asyncio
async def test_cleanup_obsolete_pending_jobs_marks_obsolete(
    validation_service, db_session, sample_archive
):
    """Test cleanup marks pending jobs as obsolete when completed job exists."""
    # Create pending job
    pending_job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="pending",
        task_id="abc123",
    )
    # Create completed job with matching task ID prefix (simulates worker UUID addition)
    completed_job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="completed",
        task_id="abc123-worker-uuid-456",
    )
    db_session.add_all([pending_job, completed_job])
    await db_session.flush()

    await validation_service.cleanup_obsolete_pending_jobs(sample_archive.id)
    await db_session.refresh(pending_job)

    assert pending_job.status == "obsolete"


@pytest.mark.asyncio
async def test_cleanup_obsolete_pending_jobs_no_matching_completed(
    validation_service, db_session, sample_archive
):
    """Test cleanup doesn't mark pending jobs obsolete without matching completed job."""
    pending_job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="pending",
        task_id="abc123",
    )
    db_session.add(pending_job)
    await db_session.flush()

    await validation_service.cleanup_obsolete_pending_jobs(sample_archive.id)
    await db_session.refresh(pending_job)

    assert pending_job.status == "pending"  # Should remain pending


# Test get_dataset_validation_status (with/without archive, various states)
@pytest.mark.asyncio
async def test_get_dataset_validation_status_no_archive(validation_service, sample_dataset):
    """Test getting validation status when dataset has no latest archive."""
    status = await validation_service.get_dataset_validation_status(sample_dataset.id)

    assert status["dataset_id"] == sample_dataset.id
    assert status["archive_id"] is None
    assert status["has_latest_archive"] is False
    assert status["validation_status"] is None


@pytest.mark.asyncio
async def test_get_dataset_validation_status_no_validation(
    validation_service, sample_dataset, sample_archive
):
    """Test getting validation status when archive has no validation."""
    status = await validation_service.get_dataset_validation_status(sample_dataset.id)

    assert status["dataset_id"] == sample_dataset.id
    assert status["archive_id"] == sample_archive.id
    assert status["has_latest_archive"] is True
    assert status["validation_status"] == "not_validated"


@pytest.mark.asyncio
async def test_get_dataset_validation_status_pending_validation(
    validation_service, db_session, sample_dataset, sample_archive
):
    """Test getting validation status with pending validation."""
    job = ValidationJobModel(archive_id=sample_archive.id, status="pending", task_id="task-1")
    db_session.add(job)
    await db_session.flush()

    status = await validation_service.get_dataset_validation_status(sample_dataset.id)

    assert status["validation_status"] == "pending"
    assert status["validation_id"] == job.id
    assert status["is_valid"] is None


@pytest.mark.asyncio
async def test_get_dataset_validation_status_completed_validation(
    validation_service, db_session, sample_dataset, sample_archive
):
    """Test getting validation status with completed validation and quality metrics."""
    job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="completed",
        task_id="task-1",
        completed_at=datetime.utcnow(),
        results={
            "summary": {
                "total_files": 10,
                "valid_files": 10,  # Fully valid
                "data_quality": {"total_weighted_quality": 0.95},
            }
        },
    )
    db_session.add(job)
    await db_session.flush()

    status = await validation_service.get_dataset_validation_status(sample_dataset.id)

    assert status["validation_status"] == "completed"
    assert status["is_valid"] is True  # All files valid
    assert status["quality_score"] == 0.95
    assert status["validation_results"] is not None


@pytest.mark.asyncio
async def test_get_dataset_validation_status_cleanup_obsolete(
    validation_service, db_session, sample_dataset, sample_archive
):
    """Test that get_dataset_validation_status calls cleanup."""
    # Create pending and completed jobs
    pending_job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="pending",
        task_id="abc123",
    )
    completed_job = ValidationJobModel(
        archive_id=sample_archive.id,
        status="completed",
        task_id="abc123-uuid",
    )
    db_session.add_all([pending_job, completed_job])
    await db_session.flush()

    status = await validation_service.get_dataset_validation_status(sample_dataset.id)

    # Pending job should be marked obsolete
    await db_session.refresh(pending_job)
    assert pending_job.status == "obsolete"

    # Status should show latest non-obsolete (completed)
    assert status["validation_status"] == "completed"


# Test get_latest_archive_for_dataset (found + not found)
@pytest.mark.asyncio
async def test_get_latest_archive_for_dataset_found(
    validation_service, sample_dataset, sample_archive
):
    """Test getting latest archive when it exists."""
    archive = await validation_service.get_latest_archive_for_dataset(sample_dataset.id)
    assert archive.id == sample_archive.id
    assert archive.isLatest is True


@pytest.mark.asyncio
async def test_get_latest_archive_for_dataset_not_found(validation_service, sample_dataset):
    """Test getting latest archive when none exist raises 404."""
    # Update sample archive to not be latest
    _ = sample_dataset  # Keep dataset but no latest archive

    with pytest.raises(HTTPException) as exc_info:
        await validation_service.get_latest_archive_for_dataset(999)
    assert exc_info.value.status_code == 404
    assert "No latest XML archive found" in exc_info.value.detail


# Test find_existing_active_validation (pending, running, none)
@pytest.mark.asyncio
async def test_find_existing_active_validation_pending(
    validation_service, db_session, sample_archive
):
    """Test finding existing pending validation."""
    job = ValidationJobModel(archive_id=sample_archive.id, status="pending", task_id="task-1")
    db_session.add(job)
    await db_session.flush()

    found = await validation_service.find_existing_active_validation(sample_archive.id)
    assert found is not None
    assert found.id == job.id
    assert found.status == "pending"


@pytest.mark.asyncio
async def test_find_existing_active_validation_running(
    validation_service, db_session, sample_archive
):
    """Test finding existing running validation."""
    job = ValidationJobModel(archive_id=sample_archive.id, status="running", task_id="task-1")
    db_session.add(job)
    await db_session.flush()

    found = await validation_service.find_existing_active_validation(sample_archive.id)
    assert found is not None
    assert found.status == "running"


@pytest.mark.asyncio
async def test_find_existing_active_validation_none(validation_service, db_session, sample_archive):
    """Test finding active validation when only completed jobs exist."""
    job = ValidationJobModel(archive_id=sample_archive.id, status="completed", task_id="task-1")
    db_session.add(job)
    await db_session.flush()

    found = await validation_service.find_existing_active_validation(sample_archive.id)
    assert found is None


@pytest.mark.asyncio
async def test_find_existing_active_validation_returns_latest(
    validation_service, db_session, sample_archive
):
    """Test that find_existing_active_validation returns the most recent active job."""
    # Create two pending jobs
    old_job = ValidationJobModel(archive_id=sample_archive.id, status="pending", task_id="task-old")
    db_session.add(old_job)
    await db_session.flush()

    # Add delay to ensure different created_at timestamps
    import asyncio

    await asyncio.sleep(0.01)

    new_job = ValidationJobModel(archive_id=sample_archive.id, status="pending", task_id="task-new")
    db_session.add(new_job)
    await db_session.flush()

    found = await validation_service.find_existing_active_validation(sample_archive.id)
    assert found.id == new_job.id  # Should return newest


# Test validate_dataset_latest_archive (force=True/False, existing validation)
@pytest.mark.asyncio
@patch("app.services.validation_service.validate_archive")
async def test_validate_dataset_latest_archive_no_existing(
    mock_validate, validation_service, sample_dataset, sample_archive
):
    """Test validating dataset when no active validation exists."""
    mock_task = MagicMock()
    mock_task.id = "new-task-123"
    mock_validate.delay.return_value = mock_task

    result = await validation_service.validate_dataset_latest_archive(
        sample_dataset.id, force=False
    )

    assert result["archive_id"] == sample_archive.id
    assert result["task_id"] == "new-task-123"
    assert result["status"] == "pending"


@pytest.mark.asyncio
async def test_validate_dataset_latest_archive_existing_not_forced(
    validation_service, db_session, sample_dataset, sample_archive
):
    """Test validating dataset returns existing job when not forced."""
    existing_job = ValidationJobModel(
        archive_id=sample_archive.id, status="pending", task_id="existing-task"
    )
    db_session.add(existing_job)
    await db_session.flush()

    result = await validation_service.validate_dataset_latest_archive(
        sample_dataset.id, force=False
    )

    assert result["job_id"] == existing_job.id
    assert result["task_id"] == "existing-task"
    assert result["status"] == "pending"


@pytest.mark.asyncio
@patch("app.services.validation_service.validate_archive")
async def test_validate_dataset_latest_archive_existing_forced(
    mock_validate, validation_service, db_session, sample_dataset, sample_archive
):
    """Test validating dataset creates new job when forced."""
    # Create existing job
    existing_job = ValidationJobModel(
        archive_id=sample_archive.id, status="pending", task_id="existing-task"
    )
    db_session.add(existing_job)
    await db_session.flush()

    mock_task = MagicMock()
    mock_task.id = "forced-new-task"
    mock_validate.delay.return_value = mock_task

    result = await validation_service.validate_dataset_latest_archive(sample_dataset.id, force=True)

    # Should create new job, not return existing
    assert result["task_id"] == "forced-new-task"
    assert result["job_id"] != existing_job.id


@pytest.mark.asyncio
async def test_validate_dataset_latest_archive_no_archive(validation_service, sample_dataset):
    """Test validating dataset without latest archive raises 404."""
    # sample_dataset exists but has no isLatest archive
    with pytest.raises(HTTPException) as exc_info:
        await validation_service.validate_dataset_latest_archive(sample_dataset.id, force=False)
    assert exc_info.value.status_code == 404
    assert "No latest XML archive found" in exc_info.value.detail
