"""
Collection-related API models.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CollectionCreateRequest(BaseModel):
    """Request model for collection creation."""
    
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=64, 
        description="Collection name (alphanumeric, underscores, hyphens)",
        examples=["my_documents", "research_papers", "legal_docs"]
    )
    dimension: Optional[int] = Field(
        default=None, 
        ge=1, 
        le=10000, 
        description="Embedding dimension (auto-detected from model if not provided)",
        examples=[384, 768, 1536]
    )
    distance_metric: str = Field(
        default="Cosine",
        description="Distance metric for similarity search",
        examples=["Cosine", "Euclid", "Dot"]
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "my_documents",
                "dimension": 384,
                "distance_metric": "Cosine"
            }
        }
    }


class CollectionInfo(BaseModel):
    """Collection information model."""
    
    name: str = Field(description="Collection name", examples=["my_documents"])
    vector_count: int = Field(description="Number of vectors in collection", examples=[100, 500, 1000])
    dimension: int = Field(description="Vector dimension", examples=[384, 768])
    status: str = Field(description="Collection status", examples=["ready", "indexing"])
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    distance_metric: str = Field(description="Distance metric used", examples=["Cosine", "Euclid"])


class CollectionListResponse(BaseModel):
    """Response model for collection list."""
    
    collections: list[CollectionInfo] = Field(description="List of collections")
    total: int = Field(description="Total number of collections")


class CollectionResponse(BaseModel):
    """Response model for collection operations."""
    
    collection: CollectionInfo = Field(description="Collection information")
    message: str = Field(
        description="Operation message",
        examples=["Collection 'my_documents' created successfully"]
    )
