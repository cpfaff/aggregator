"""
API endpoints for managing background tasks with Celery.
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models import UserModel
from app.security import get_current_user
from app.tasks.example import process_data

router = APIRouter()


class TaskRequest(BaseModel):
    """
    Request model for submitting a task.
    """

    data: Dict[str, Any]


class TaskResponse(BaseModel):
    """
    Response model for a submitted task.
    """

    task_id: str
    status: str


@router.post("/", response_model=TaskResponse)
async def create_task(
    request: TaskRequest,
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    """
    Submit a task to be processed in the background.

    Args:
        request: The data to be processed
        current_user: The current authenticated user

    Returns:
        Information about the submitted task
    """
    # Submit the task to Celery
    task = process_data.delay(request.data, user_id=current_user.id)

    return TaskResponse(task_id=task.id, status="pending")


@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: str,
    current_user: UserModel = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Get the status of a task.

    Args:
        task_id: The ID of the task to check
        current_user: The current authenticated user

    Returns:
        Information about the task status and result
    """
    task = process_data.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": task.status,
    }

    # Include result if task is completed
    if task.status == "SUCCESS":
        response["result"] = task.result

    return response
