"""
Custom exceptions for the RAG system.

This module defines all custom exception classes used throughout the application.
Each exception class includes appropriate error codes and messages for better error handling.
"""
from typing import Any


class BaseRAGException(Exception):
    """
    Base exception class for all RAG system exceptions.
    
    Attributes:
        message: Human-readable error message
        error_code: Machine-readable error code
        details: Additional error details
    """
    
    def __init__(self, message: str, error_code: str | None = None, details: dict[str, Any] | None = None) -> None:
        """Initialize the base exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code (default: class name in uppercase)
            details: Additional error details as a dictionary
        """
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary format.
        
        Returns:
            Dictionary containing error information suitable for API responses.
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


# Configuration Exceptions
class ConfigurationError(BaseRAGException):
    """Raised when there's an issue with application configuration."""
    pass


class EnvironmentVariableError(ConfigurationError):
    """Raised when required environment variables are missing or invalid."""
    pass


# Document Processing Exceptions
class DocumentProcessingError(BaseRAGException):
    """Base exception for document processing errors."""
    pass


class DocumentValidationError(DocumentProcessingError):
    """Raised when document validation fails."""
    pass


class DocumentSizeError(DocumentValidationError):
    """Raised when document exceeds maximum allowed size."""
    pass


class DocumentFormatError(DocumentValidationError):
    """Raised when document format is not supported."""
    pass


class DocumentParseError(DocumentProcessingError):
    """Raised when document parsing fails."""
    pass


class ChunkingError(DocumentProcessingError):
    """Raised when text chunking fails."""
    pass


# Embedding Exceptions
class EmbeddingError(BaseRAGException):
    """Base exception for embedding-related errors."""
    pass


class EmbeddingModelNotFoundError(EmbeddingError):
    """Raised when embedding model cannot be found or loaded."""
    pass


class EmbeddingGenerationError(EmbeddingError):
    """Raised when embedding generation fails."""
    pass


class EmbeddingCacheError(EmbeddingError):
    """Raised when embedding cache operations fail."""
    pass


# Vector Store Exceptions
class VectorStoreError(BaseRAGException):
    """Base exception for vector store errors."""
    pass


class CollectionNotFoundError(VectorStoreError):
    """Raised when a collection cannot be found in the vector store."""
    pass


class CollectionCreationError(VectorStoreError):
    """Raised when collection creation fails."""
    pass


class VectorInsertionError(VectorStoreError):
    """Raised when vector insertion fails."""
    pass


class VectorSearchError(VectorStoreError):
    """Raised when vector search fails."""
    pass


class VectorStoreConnectionError(VectorStoreError):
    """Raised when connection to vector store fails."""
    pass


# LLM Exceptions
class LLMError(BaseRAGException):
    """Base exception for LLM-related errors."""
    pass


class LLMConnectionError(LLMError):
    """Raised when connection to LLM service fails."""
    pass


class LLMGenerationError(LLMError):
    """Raised when LLM text generation fails."""
    pass


class LLMModelNotFoundError(LLMError):
    """Raised when LLM model cannot be found."""
    pass


class PromptError(LLMError):
    """Raised when prompt construction or processing fails."""
    pass


# API Exceptions
class APIError(BaseRAGException):
    """Base exception for API-related errors."""
    pass


class ResourceNotFoundError(APIError):
    """Raised when a requested resource cannot be found."""
    pass


class BadRequestError(APIError):
    """Raised when a request is malformed or contains invalid data."""
    pass


class UnauthorizedError(APIError):
    """Raised when authentication fails."""
    pass


class ForbiddenError(APIError):
    """Raised when user lacks permission for the requested action."""
    pass


class RateLimitExceededError(APIError):
    """Raised when rate limit is exceeded."""
    pass


class ValidationError(APIError):
    """Raised when request validation fails."""
    pass


# Storage Exceptions
class StorageError(BaseRAGException):
    """Base exception for storage-related errors."""
    pass


class FileStorageError(StorageError):
    """Raised when file storage operations fail."""
    pass


class FileNotFoundError(FileStorageError):
    """Raised when a file cannot be found in storage."""
    pass


class FileUploadError(FileStorageError):
    """Raised when file upload fails."""
    pass


class FileDeletionError(FileStorageError):
    """Raised when file deletion fails."""
    pass


# Parser Exceptions
class ParserError(BaseRAGException):
    """Base exception for parser errors."""
    pass


class UnsupportedParserError(ParserError):
    """Raised when no parser is available for a file type."""
    pass


# Service Exceptions
class ServiceError(BaseRAGException):
    """Base exception for service layer errors."""
    pass


class ServiceUnavailableError(ServiceError):
    """Raised when a service is temporarily unavailable."""
    pass


class ServiceTimeoutError(ServiceError):
    """Raised when a service request times out."""
    pass


# Utility function to convert exceptions to HTTP status codes
def get_http_status_code(exception: BaseRAGException) -> int:
    """
    Map exception types to appropriate HTTP status codes.
    
    Args:
        exception: The exception to map
        
    Returns:
        HTTP status code (integer)
    """
    status_map: dict[type[BaseRAGException], int] = {
        ResourceNotFoundError: 404,
        CollectionNotFoundError: 404,
        LLMModelNotFoundError: 404,
        EmbeddingModelNotFoundError: 404,
        FileNotFoundError: 404,
        
        BadRequestError: 400,
        ValidationError: 400,
        DocumentValidationError: 400,
        DocumentSizeError: 400,
        DocumentFormatError: 400,
        
        UnauthorizedError: 401,
        ForbiddenError: 403,
        
        RateLimitExceededError: 429,
        
        ServiceUnavailableError: 503,
        ServiceTimeoutError: 504,
        
        VectorStoreConnectionError: 503,
        LLMConnectionError: 503,
    }
    
    for exc_type, status in status_map.items():
        if isinstance(exception, exc_type):
            return status
    
    # Default to 500 for unhandled exceptions
    return 500
