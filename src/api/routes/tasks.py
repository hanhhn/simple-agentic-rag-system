"""
Task status tracking endpoints.
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from celery.result import AsyncResult

from src.core.logging import get_logger
from src.core.exceptions import ServiceError
from src.api.models.task import TaskResponse, TaskListResponse, TaskStatus
from src.tasks.celery_app import celery_app


logger = get_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _get_task_status(task: AsyncResult) -> TaskStatus:
    """Convert Celery task state to TaskStatus enum."""
    state = task.state
    
    if state == "PENDING":
        return TaskStatus.PENDING
    elif state == "STARTED":
        return TaskStatus.STARTED
    elif state == "SUCCESS":
        return TaskStatus.SUCCESS
    elif state == "FAILURE":
        return TaskStatus.FAILURE
    elif state == "RETRY":
        return TaskStatus.RETRY
    elif state == "REVOKED":
        return TaskStatus.REVOKED
    else:
        return TaskStatus.PENDING


@router.get(
    "/{task_id}", 
    response_model=TaskResponse,
    status_code=200,
    summary="Get task status",
    description="""
    Retrieve the current status and result of a background task.
    
    **Task Statuses:**
    - `PENDING`: Task is waiting to be processed
    - `STARTED`: Task is currently being processed
    - `SUCCESS`: Task completed successfully
    - `FAILURE`: Task failed with an error
    - `RETRY`: Task is being retried
    - `REVOKED`: Task was cancelled
    
    **Parameters:**
    - `task_id`: Celery task ID (returned from document upload endpoint)
    
    **Returns:**
    - Task status, result (if completed), or error (if failed)
    """
)
async def get_task_status(task_id: str) -> TaskResponse:
    """
    Get the status of a task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        TaskResponse with task status and result
    """
    try:
        logger.info("Getting task status", task_id=task_id)
        
        # Get task result
        task = AsyncResult(task_id, app=celery_app)
        
        # Get task info
        task_info = task.info
        
        # Determine status
        status = _get_task_status(task)
        
        # Prepare response
        response_data = {
            "task_id": task_id,
            "status": status,
            "task_name": task.name or "unknown",
            "result": None,
            "error": None,
            "traceback": None,
            "created_at": None,
            "started_at": None,
            "completed_at": None,
            "progress": None,
            "metadata": {}
        }
        
        # Add result or error based on status
        if status == TaskStatus.SUCCESS:
            response_data["result"] = task_info if isinstance(task_info, dict) else {"result": task_info}
            response_data["completed_at"] = task.date_done
        elif status == TaskStatus.FAILURE:
            response_data["error"] = str(task_info) if task_info else "Task failed"
            if hasattr(task, "traceback"):
                response_data["traceback"] = task.traceback
            response_data["completed_at"] = task.date_done
        elif status == TaskStatus.STARTED:
            if isinstance(task_info, dict) and "progress" in task_info:
                response_data["progress"] = task_info["progress"]
            # date_started might not be available in all Celery versions
            response_data["started_at"] = getattr(task, "date_started", None)
        
        # Get task metadata if available
        if hasattr(task, "request") and task.request:
            response_data["created_at"] = getattr(task.request, "created_at", None)
            if not response_data["started_at"]:
                response_data["started_at"] = getattr(task.request, "started_at", None)
        
        logger.info(
            "Task status retrieved",
            task_id=task_id,
            status=status.value
        )
        
        return TaskResponse(**response_data)
        
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to get task status: {str(e)}"
            }
        )


@router.post(
    "/{task_id}/revoke",
    status_code=200,
    summary="Cancel a task",
    description="""
    Cancel (revoke) a running or pending task.
    
    **Parameters:**
    - `task_id`: Celery task ID to cancel
    
    **Returns:**
    - Confirmation of task cancellation
    """
)
async def revoke_task(task_id: str) -> dict:
    """
    Revoke (cancel) a task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Dictionary with revocation result
    """
    try:
        logger.info("Revoking task", task_id=task_id)
        
        # Revoke task
        celery_app.control.revoke(task_id, terminate=True)
        
        logger.info("Task revoked", task_id=task_id)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": "Task revoked successfully"
        }
        
    except Exception as e:
        logger.error("Failed to revoke task", task_id=task_id, error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to revoke task: {str(e)}"
            }
        )


@router.get(
    "", 
    response_model=TaskListResponse,
    status_code=200,
    summary="List active tasks",
    description="""
    List currently active tasks (running or pending).
    
    **Note:** Celery doesn't provide a built-in way to list all tasks.
    This endpoint shows only active tasks from workers.
    
    **Parameters:**
    - `status`: Optional filter by task status (PENDING, STARTED, SUCCESS, etc.)
    - `limit`: Maximum number of tasks to return (1-1000, default: 100)
    
    **Returns:**
    - List of active tasks with their status
    """
)
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return")
) -> TaskListResponse:
    """
    List active tasks (limited functionality).
    
    Note: Celery doesn't provide a built-in way to list all tasks.
    This endpoint provides basic task inspection capabilities.
    
    Args:
        status: Optional status filter
        limit: Maximum number of tasks to return
        
    Returns:
        TaskListResponse with task list
    """
    try:
        logger.info("Listing tasks", status=status, limit=limit)
        
        # Get active tasks from workers
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active() or {}
        reserved_tasks = inspect.reserved() or {}
        
        # Combine active and reserved tasks
        all_task_ids = set()
        for worker_tasks in active_tasks.values():
            all_task_ids.update(task["id"] for task in worker_tasks)
        for worker_tasks in reserved_tasks.values():
            all_task_ids.update(task["id"] for task in worker_tasks)
        
        # Get task details
        tasks = []
        for task_id in list(all_task_ids)[:limit]:
            try:
                task = AsyncResult(task_id, app=celery_app)
                task_status = _get_task_status(task)
                
                # Apply status filter if provided
                if status and task_status != status:
                    continue
                
                task_response = TaskResponse(
                    task_id=task_id,
                    status=task_status,
                    task_name=task.name or "unknown",
                    result=None,
                    error=None,
                    metadata={}
                )
                tasks.append(task_response)
            except Exception as e:
                logger.warning("Failed to get task info", task_id=task_id, error=str(e))
                continue
        
        logger.info("Tasks listed", count=len(tasks))
        
        return TaskListResponse(
            tasks=tasks,
            total=len(tasks)
        )
        
    except Exception as e:
        logger.error("Failed to list tasks", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error_code": "INTERNAL_ERROR",
                "message": f"Failed to list tasks: {str(e)}"
            }
        )
