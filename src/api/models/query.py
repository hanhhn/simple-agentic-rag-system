"""
Query-related API models.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for query."""
    
    query: str = Field(
        ..., 
        min_length=1, 
        max_length=2000, 
        description="Query text",
        examples=["What is machine learning?", "Explain the concept of embeddings"]
    )
    collection: str = Field(
        ..., 
        min_length=1, 
        max_length=64, 
        description="Collection name",
        examples=["my_documents", "research_papers"]
    )
    top_k: int = Field(
        default=5, 
        ge=1, 
        le=100, 
        description="Number of results to retrieve",
        examples=[5, 10, 20]
    )
    score_threshold: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="Minimum similarity score (0.0 to 1.0)",
        examples=[0.0, 0.5, 0.7]
    )
    use_rag: bool = Field(
        default=True, 
        description="Whether to use RAG generation (if False, only returns retrieved documents)"
    )
    stream: bool = Field(
        default=False, 
        description="Whether to stream response (for real-time answer generation)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "What is the main topic of the document?",
                "collection": "my_documents",
                "top_k": 5,
                "score_threshold": 0.0,
                "use_rag": True,
                "stream": False
            }
        }
    }


class RetrievedDocument(BaseModel):
    """Retrieved document model."""
    
    id: str = Field(description="Document ID", examples=["doc_123", "chunk_456"])
    score: float = Field(description="Similarity score (0.0 to 1.0)", examples=[0.95, 0.87, 0.72])
    text: str = Field(description="Document text content", examples=["This is a sample document chunk..."])
    metadata: dict = Field(
        default_factory=dict, 
        description="Document metadata",
        examples=[{"filename": "document.pdf", "chunk_index": 0, "collection": "my_documents"}]
    )


class QueryResponse(BaseModel):
    """Response model for query."""
    
    query: str = Field(description="Original query")
    answer: Optional[str] = Field(description="Generated answer (if use_rag=True)")
    answer_chunks: Optional[list[str]] = Field(description="Streaming answer chunks (if stream=True)")
    retrieved_documents: list[RetrievedDocument] = Field(description="Retrieved documents")
    retrieval_count: int = Field(description="Number of documents retrieved")
    collection: str = Field(description="Collection searched")
    top_k: int = Field(description="Number of documents requested")
    score_threshold: float = Field(description="Score threshold used")
    use_rag: bool = Field(description="Whether RAG was used")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Query timestamp")
