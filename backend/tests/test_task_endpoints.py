"""Tests for background task API endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.endpoints.tasks import create_task, get_task_status

# ---------------------------------------------------------------------------
# POST / (create task)
# ---------------------------------------------------------------------------


class TestCreateTask:
    """Tests for POST / endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.tasks.process_data")
    async def test_submits_task_and_returns_pending(self, mock_process):
        """Test that task is submitted to Celery and returns pending status."""
        mock_task = MagicMock()
        mock_task.id = "celery-task-abc123"
        mock_process.delay.return_value = mock_task

        mock_request = MagicMock()
        mock_request.data = {"key": "value"}

        mock_user = MagicMock()
        mock_user.id = 42

        result = await create_task(request=mock_request, current_user=mock_user)

        assert result.task_id == "celery-task-abc123"
        assert result.status == "pending"
        mock_process.delay.assert_called_once_with({"key": "value"}, user_id=42)


# ---------------------------------------------------------------------------
# GET /{task_id}
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    """Tests for GET /{task_id} endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.tasks.process_data")
    async def test_returns_pending_status(self, mock_process):
        """Test that pending task returns status without result."""
        mock_result = MagicMock()
        mock_result.status = "PENDING"
        mock_process.AsyncResult.return_value = mock_result

        result = await get_task_status(task_id="task-123", current_user=MagicMock())

        assert result["task_id"] == "task-123"
        assert result["status"] == "PENDING"
        assert "result" not in result

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.tasks.process_data")
    async def test_success_includes_result_for_owner(self, mock_process):
        """The task owner receives the completed result."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.result = {"processed": True, "user_id": 7}
        mock_process.AsyncResult.return_value = mock_result

        owner = MagicMock()
        owner.id = 7
        result = await get_task_status(task_id="task-456", current_user=owner)

        assert result["status"] == "SUCCESS"
        assert result["result"] == {"processed": True, "user_id": 7}

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.tasks.process_data")
    async def test_non_owner_cannot_read_result(self, mock_process):
        """A different authenticated user must not read another user's result (B13)."""
        from fastapi import HTTPException

        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.result = {"processed": True, "user_id": 1}
        mock_process.AsyncResult.return_value = mock_result

        other = MagicMock()
        other.id = 2
        with pytest.raises(HTTPException) as exc_info:
            await get_task_status(task_id="task-owned-by-1", current_user=other)
        assert exc_info.value.status_code in (403, 404)

    @pytest.mark.asyncio
    @patch("app.api.v1.endpoints.tasks.process_data")
    async def test_failure_status_no_result(self, mock_process):
        """Test that failed task returns status without result key."""
        mock_result = MagicMock()
        mock_result.status = "FAILURE"
        mock_process.AsyncResult.return_value = mock_result

        result = await get_task_status(task_id="task-789", current_user=MagicMock())

        assert result["status"] == "FAILURE"
        assert "result" not in result
