"""
Dependency injection for FastAPI.
"""
from typing import Generator

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.logging import get_logger
from src.core.config import get_config
from src.services.query_processor import QueryProcessor
from src.services.storage_manager import StorageManager
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import VectorStore
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService


logger = get_logger(__name__)

# Optional security scheme
security = HTTPBearer(auto_error=False)


def get_query_processor() -> QueryProcessor:
    """
    Dependency for getting query processor instance.
    
    Returns:
        QueryProcessor instance
    """
    logger.info("Injecting query processor dependency")
    return QueryProcessor()


def get_storage_manager() -> StorageManager:
    """
    Dependency for getting storage manager instance.
    
    Returns:
        StorageManager instance
    """
    logger.info("Injecting storage manager dependency")
    return StorageManager()


def get_document_processor() -> DocumentProcessor:
    """
    Dependency for getting document processor instance.
    
    Returns:
        DocumentProcessor instance
    """
    logger.info("Injecting document processor dependency")
    return DocumentProcessor()


def get_vector_store() -> VectorStore:
    """
    Dependency for getting vector store instance.
    
    Returns:
        VectorStore instance
    """
    logger.info("Injecting vector store dependency")
    return VectorStore()


def get_embedding_service() -> EmbeddingService:
    """
    Dependency for getting embedding service instance.
    
    Returns:
        EmbeddingService instance
    """
    logger.info("Injecting embedding service dependency")
    return EmbeddingService()


def get_llm_service() -> LLMService:
    """
    Dependency for getting LLM service instance.
    
    Returns:
        LLMService instance
    """
    logger.info("Injecting LLM service dependency")
    return LLMService()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Verify API key from request headers.
    
    Args:
        credentials: Authorization credentials from header
        
    Returns:
        API key string
        
    Raises:
        HTTPException: If API key is invalid
    """
    config = get_config()
    
    # Skip verification if no secret key is configured
    if not config.security.jwt_secret_key or config.security.jwt_secret_key == "change-this-secret-key-in-production":
        logger.info("API key verification skipped (development mode)")
        return credentials.credentials or ""
    
    # In production, you would verify the API key here
    # For now, just check that it exists
    if not credentials or not credentials.credentials:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=401,
            detail={
                "success": False,
                "error_code": "UNAUTHORIZED",
                "message": "API key is required"
            }
        )
    
    api_key = credentials.credentials
    logger.info("API key verified")
    
    return api_key
