"""
API endpoints for managing background tasks with Celery.
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.tasks.example import process_data
from app.tasks.statistics_tasks import (
    update_dataset_statistics,
    update_provider_biological_units,
    update_validation_statistics,
    collect_daily_statistics
)
from app.models import UserModel
from app.security import get_current_user, check_global_admin

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
    
    return TaskResponse(
        task_id=task.id,
        status="pending"
    )


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


@router.post("/statistics/dataset/{dataset_id}", response_model=TaskResponse)
async def trigger_dataset_statistics(
    dataset_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    """
    Manually trigger statistics collection for a specific dataset.
    
    Args:
        dataset_id: The ID of the dataset to update statistics for
        current_user: The current authenticated user (must be global admin)
        
    Returns:
        Information about the submitted task
    """
    # Only global admins can trigger statistics collection
    check_global_admin(current_user)
    
    # Submit the task to Celery
    task = update_dataset_statistics.delay(dataset_id, "manual_trigger")
    
    return TaskResponse(
        task_id=task.id,
        status="pending"
    )


@router.post("/statistics/provider/{provider_id}", response_model=TaskResponse)
async def trigger_provider_statistics(
    provider_id: int,
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    """
    Manually trigger biological units statistics collection for a specific provider.
    
    Args:
        provider_id: The ID of the provider to update statistics for
        current_user: The current authenticated user (must be global admin)
        
    Returns:
        Information about the submitted task
    """
    # Only global admins can trigger statistics collection
    check_global_admin(current_user)
    
    # Submit the task to Celery
    task = update_provider_biological_units.delay(provider_id, None, "manual_trigger")
    
    return TaskResponse(
        task_id=task.id,
        status="pending"
    )


@router.post("/statistics/validation", response_model=TaskResponse)
async def trigger_validation_statistics(
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    """
    Manually trigger validation statistics collection.
    
    Args:
        current_user: The current authenticated user (must be global admin)
        
    Returns:
        Information about the submitted task
    """
    # Only global admins can trigger statistics collection
    check_global_admin(current_user)
    
    # Submit the task to Celery
    task = update_validation_statistics.delay(None, "manual_trigger")
    
    return TaskResponse(
        task_id=task.id,
        status="pending"
    )


@router.post("/statistics/daily", response_model=TaskResponse)
async def trigger_daily_statistics(
    current_user: UserModel = Depends(get_current_user),
) -> TaskResponse:
    """
    Manually trigger full daily statistics collection.
    
    Args:
        current_user: The current authenticated user (must be global admin)
        
    Returns:
        Information about the submitted task
    """
    # Only global admins can trigger statistics collection
    check_global_admin(current_user)
    
    # Submit the task to Celery
    task = collect_daily_statistics.delay()
    
    return TaskResponse(
        task_id=task.id,
        status="pending"
    )
