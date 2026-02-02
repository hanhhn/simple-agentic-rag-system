"""
Input validators for the RAG system.

This module provides various validation functions for user inputs,
including document validation, query validation, and collection validation.
"""
import re
from typing import List

from src.core.exceptions import (
    DocumentValidationError,
    DocumentSizeError,
    DocumentFormatError,
    ValidationError,
)
from src.core.config import get_config


class DocumentValidator:
    """
    Validator for document-related inputs.
    
    This class provides methods to validate document files, ensuring they
    meet the requirements for processing and storage.
    
    Attributes:
        max_size: Maximum allowed file size in bytes
        supported_formats: List of supported file extensions
    """
    
    def __init__(self, max_size: int | None = None, supported_formats: List[str] | None = None) -> None:
        """
        Initialize the document validator.
        
        Args:
            max_size: Maximum file size in bytes (uses config default if None)
            supported_formats: List of supported file extensions (uses config default if None)
        """
        config = get_config()
        
        self.max_size = max_size or config.document.max_size
        self.supported_formats = supported_formats or config.document.supported_formats
    
    def validate_file_size(self, file_size: int) -> None:
        """
        Validate that a file size is within limits.
        
        Args:
            file_size: Size of the file in bytes
            
        Raises:
            DocumentSizeError: If file size exceeds maximum
            
        Example:
            >>> validator = DocumentValidator()
            >>> validator.validate_file_size(1024 * 1024)  # 1MB
        """
        if file_size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise DocumentSizeError(
                f"File size ({file_size} bytes) exceeds maximum allowed size ({max_mb:.1f}MB)",
                details={
                    "file_size": file_size,
                    "max_size": self.max_size
                }
            )
    
    def validate_file_format(self, filename: str) -> None:
        """
        Validate that a file has a supported format.
        
        Args:
            filename: Name of the file to validate
            
        Raises:
            DocumentFormatError: If file format is not supported
            
        Example:
            >>> validator = DocumentValidator()
            >>> validator.validate_file_format("document.pdf")
        """
        if not filename:
            raise DocumentFormatError("Filename cannot be empty")
        
        # Extract extension
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        if ext not in self.supported_formats:
            raise DocumentFormatError(
                f"Unsupported file format: {ext}. Supported formats: {', '.join(self.supported_formats)}",
                details={
                    "filename": filename,
                    "format": ext,
                    "supported_formats": self.supported_formats
                }
            )
    
    def validate_filename(self, filename: str) -> None:
        """
        Validate that a filename is valid and safe.
        
        Args:
            filename: Name of the file to validate
            
        Raises:
            DocumentValidationError: If filename is invalid
            
        Example:
            >>> validator = DocumentValidator()
            >>> validator.validate_filename("safe_document.pdf")
        """
        if not filename:
            raise DocumentValidationError("Filename cannot be empty")
        
        # Check for path traversal attempts
        if ".." in filename or filename.startswith(("/", "\\")):
            raise DocumentValidationError(
                "Invalid filename: path traversal detected",
                details={"filename": filename}
            )
        
        # Check for suspicious characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in filename for char in dangerous_chars):
            raise DocumentValidationError(
                f"Invalid filename: contains dangerous characters",
                details={"filename": filename, "dangerous_chars": dangerous_chars}
            )
        
        # Check length
        if len(filename) > 255:
            raise DocumentValidationError(
                "Filename too long (maximum 255 characters)",
                details={"filename": filename, "length": len(filename)}
            )
    
    def validate_document(self, filename: str, file_size: int) -> None:
        """
        Validate a document (filename and size).
        
        This is a convenience method that validates both filename and file size.
        
        Args:
            filename: Name of the file
            file_size: Size of the file in bytes
            
        Raises:
            DocumentValidationError: If validation fails
            
        Example:
            >>> validator = DocumentValidator()
            >>> validator.validate_document("document.pdf", 1024 * 1024)
        """
        self.validate_filename(filename)
        self.validate_file_format(filename)
        self.validate_file_size(file_size)


class QueryValidator:
    """
    Validator for query-related inputs.
    
    This class provides methods to validate user queries, ensuring they
    are appropriate for processing and search.
    
    Attributes:
        min_length: Minimum query length
        max_length: Maximum query length
    """
    
    def __init__(self, min_length: int = 1, max_length: int = 2000) -> None:
        """
        Initialize the query validator.
        
        Args:
            min_length: Minimum query length in characters
            max_length: Maximum query length in characters
        """
        self.min_length = min_length
        self.max_length = max_length
    
    def validate_query(self, query: str) -> None:
        """
        Validate a user query.
        
        Args:
            query: Query string to validate
            
        Raises:
            ValidationError: If query is invalid
            
        Example:
            >>> validator = QueryValidator()
            >>> validator.validate_query("What is the main topic?")
        """
        if not query:
            raise ValidationError("Query cannot be empty")
        
        query = query.strip()
        
        if len(query) < self.min_length:
            raise ValidationError(
                f"Query too short (minimum {self.min_length} characters)",
                details={"query": query, "length": len(query)}
            )
        
        if len(query) > self.max_length:
            raise ValidationError(
                f"Query too long (maximum {self.max_length} characters)",
                details={"query": query[:100] + "...", "length": len(query)}
            )
        
        # Check for suspicious patterns
        if re.search(r'<script|javascript:|data:', query, re.IGNORECASE):
            raise ValidationError(
                "Query contains potentially malicious content",
                details={"query": query}
            )
    
    def validate_top_k(self, top_k: int) -> None:
        """
        Validate the top_k parameter for search results.
        
        Args:
            top_k: Number of results to retrieve
            
        Raises:
            ValidationError: If top_k is invalid
            
        Example:
            >>> validator = QueryValidator()
            >>> validator.validate_top_k(5)
        """
        if not isinstance(top_k, int) or top_k < 1:
            raise ValidationError(
                "top_k must be a positive integer",
                details={"top_k": top_k}
            )
        
        if top_k > 100:
            raise ValidationError(
                "top_k cannot exceed 100",
                details={"top_k": top_k}
            )
    
    def validate_search_params(self, query: str, top_k: int, score_threshold: float = 0.0) -> None:
        """
        Validate all search parameters.
        
        Args:
            query: Query string
            top_k: Number of results
            score_threshold: Minimum similarity score (0.0 to 1.0)
            
        Raises:
            ValidationError: If any parameter is invalid
            
        Example:
            >>> validator = QueryValidator()
            >>> validator.validate_search_params("query", 5, 0.5)
        """
        self.validate_query(query)
        self.validate_top_k(top_k)
        
        if not 0.0 <= score_threshold <= 1.0:
            raise ValidationError(
                "score_threshold must be between 0.0 and 1.0",
                details={"score_threshold": score_threshold}
            )


class CollectionValidator:
    """
    Validator for collection-related inputs.
    
    This class provides methods to validate collection names and parameters.
    
    Attributes:
        min_name_length: Minimum collection name length
        max_name_length: Maximum collection name length
    """
    
    def __init__(self, min_name_length: int = 1, max_name_length: int = 64) -> None:
        """
        Initialize the collection validator.
        
        Args:
            min_name_length: Minimum collection name length
            max_name_length: Maximum collection name length
        """
        self.min_name_length = min_name_length
        self.max_name_length = max_name_length
    
    def validate_collection_name(self, name: str) -> None:
        """
        Validate a collection name.
        
        Args:
            name: Collection name to validate
            
        Raises:
            ValidationError: If collection name is invalid
            
        Example:
            >>> validator = CollectionValidator()
            >>> validator.validate_collection_name("my_documents")
        """
        if not name:
            raise ValidationError("Collection name cannot be empty")
        
        name = name.strip()
        
        if len(name) < self.min_name_length:
            raise ValidationError(
                f"Collection name too short (minimum {self.min_name_length} characters)",
                details={"name": name, "length": len(name)}
            )
        
        if len(name) > self.max_name_length:
            raise ValidationError(
                f"Collection name too long (maximum {self.max_name_length} characters)",
                details={"name": name, "length": len(name)}
            )
        
        # Check for valid characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            raise ValidationError(
                "Collection name can only contain letters, numbers, underscores, and hyphens",
                details={"name": name}
            )
        
        # Check for reserved names
        reserved_names = ['default', 'system', 'admin', 'test']
        if name.lower() in reserved_names:
            raise ValidationError(
                f"'{name}' is a reserved collection name",
                details={"name": name, "reserved_names": reserved_names}
            )
    
    def validate_embedding_dimension(self, dimension: int) -> None:
        """
        Validate embedding dimension.
        
        Args:
            dimension: Embedding dimension size
            
        Raises:
            ValidationError: If dimension is invalid
            
        Example:
            >>> validator = CollectionValidator()
            >>> validator.validate_embedding_dimension(384)
        """
        if not isinstance(dimension, int) or dimension < 1:
            raise ValidationError(
                "Embedding dimension must be a positive integer",
                details={"dimension": dimension}
            )
        
        if dimension > 10000:
            raise ValidationError(
                "Embedding dimension too large (maximum 10000)",
                details={"dimension": dimension}
            )


def validate_email(email: str) -> bool:
    """
    Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if email is valid, False otherwise
        
    Example:
        >>> if validate_email("user@example.com"):
        ...     print("Valid email")
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_url(url: str) -> bool:
    """
    Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        True if URL is valid, False otherwise
        
    Example:
        >>> if validate_url("https://example.com"):
        ...     print("Valid URL")
    """
    if not url:
        return False
    
    pattern = r'^https?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+$'
    return re.match(pattern, url) is not None


def sanitize_string(text: str, max_length: int = 1000, remove_html: bool = True) -> str:
    """
    Sanitize a string by removing potentially dangerous content.
    
    Args:
        text: Text to sanitize
        max_length: Maximum length of the result
        remove_html: Whether to remove HTML tags
        
    Returns:
        Sanitized string
        
    Example:
        >>> safe_text = sanitize_string(user_input)
    """
    if not text:
        return ""
    
    # Remove HTML tags if requested
    if remove_html:
        text = re.sub(r'<[^>]+>', ' ', text)
    
    # Remove potentially dangerous patterns
    text = re.sub(r'<script|javascript:|data:', '', text, flags=re.IGNORECASE)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if necessary
    if len(text) > max_length:
        text = text[:max_length].strip()
    
    return text.strip()
