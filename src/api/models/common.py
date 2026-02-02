"""
Common API models.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """Standard success response model."""
    
    success: bool = Field(default=True, description="Success status")
    message: str = Field(default="Operation successful", description="Success message")
    data: Optional[Any] = Field(default=None, description="Response data")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    success: bool = Field(default=False, description="Success status")
    error_code: str = Field(description="Error code")
    message: str = Field(description="Error message")
    details: Optional[dict[str, Any]] = Field(default=None, description="Additional error details")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(description="Service status")
    version: str = Field(description="API version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    services: dict[str, str] = Field(description="Status of dependent services")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseModel):
    """Paginated response model."""
    
    items: list[Any] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: list[Any],
        total: int,
        page: int,
        page_size: int
    ) -> "PaginatedResponse":
        """Create paginated response."""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
