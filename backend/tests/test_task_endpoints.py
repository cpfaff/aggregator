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
    async def test_success_includes_result(self, mock_process):
        """Test that completed task includes result."""
        mock_result = MagicMock()
        mock_result.status = "SUCCESS"
        mock_result.result = {"processed": True}
        mock_process.AsyncResult.return_value = mock_result

        result = await get_task_status(task_id="task-456", current_user=MagicMock())

        assert result["status"] == "SUCCESS"
        assert result["result"] == {"processed": True}

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
