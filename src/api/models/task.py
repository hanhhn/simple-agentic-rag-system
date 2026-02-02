"""
Task-related API models.
"""
from datetime import datetime
from typing import Optional, Literal
from enum import Enum

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enumeration."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskResponse(BaseModel):
    """Response model for task status."""
    
    task_id: str = Field(description="Celery task ID", examples=["abc123-def456-ghi789"])
    status: TaskStatus = Field(description="Task status", examples=[TaskStatus.PENDING, TaskStatus.SUCCESS])
    task_name: str = Field(description="Task name", examples=["process_document_task"])
    result: Optional[dict] = Field(
        default=None, 
        description="Task result (if completed)",
        examples=[{"document_id": "doc_123", "chunks_created": 10}]
    )
    error: Optional[str] = Field(
        default=None, 
        description="Error message (if failed)",
        examples=["File format not supported"]
    )
    traceback: Optional[str] = Field(default=None, description="Error traceback (if failed)")
    created_at: Optional[datetime] = Field(default=None, description="Task creation time")
    started_at: Optional[datetime] = Field(default=None, description="Task start time")
    completed_at: Optional[datetime] = Field(default=None, description="Task completion time")
    progress: Optional[float] = Field(
        default=None, 
        ge=0.0, 
        le=1.0, 
        description="Task progress (0.0-1.0)",
        examples=[0.0, 0.5, 1.0]
    )
    metadata: dict = Field(
        default_factory=dict, 
        description="Additional task metadata",
        examples=[{"filename": "document.pdf", "collection": "my_documents"}]
    )


class TaskListResponse(BaseModel):
    """Response model for task list."""
    
    tasks: list[TaskResponse] = Field(description="List of tasks")
    total: int = Field(description="Total number of tasks")
