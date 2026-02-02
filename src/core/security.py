"""
Security utilities for the RAG system.

This module provides security-related functionality including JWT token management,
password hashing, and input sanitization.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import get_config
from src.core.exceptions import UnauthorizedError

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("my_password")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> if verify_password(input_password, stored_hash):
        ...     print("Password is correct")
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Data to encode in the token (typically user_id, username, etc.)
        expires_delta: Optional expiration time delta. Uses default if not provided.
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token(
        ...     data={"user_id": "123", "username": "john"},
        ...     expires_delta=timedelta(hours=1)
        ... )
    """
    config = get_config()
    
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=config.security.jwt_expiration_hours)
    
    to_encode.update({"exp": expire})
    
    # Create and return JWT token
    encoded_jwt = jwt.encode(
        to_encode,
        config.security.jwt_secret_key,
        algorithm=config.security.jwt_algorithm
    )
    
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token data as a dictionary
        
    Raises:
        UnauthorizedError: If token is invalid or expired
        
    Example:
        >>> try:
        ...     payload = decode_access_token(token)
        ...     print(f"User ID: {payload.get('user_id')}")
        ... except UnauthorizedError as e:
        ...     print(f"Invalid token: {e}")
    """
    config = get_config()
    
    try:
        payload = jwt.decode(
            token,
            config.security.jwt_secret_key,
            algorithms=[config.security.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise UnauthorizedError("Invalid or expired token", details={"error": str(e)})


def generate_api_key() -> str:
    """
    Generate a secure random API key.
    
    Returns:
        Secure random API key string
        
    Example:
        >>> api_key = generate_api_key()
    """
    return secrets.token_urlsafe(32)


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    This function performs basic input sanitization by removing potentially
    dangerous characters and limiting the length of input.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length for the input
        
    Returns:
        Sanitized text string
        
    Example:
        >>> clean_input = sanitize_input(user_query, max_length=5000)
    """
    # Remove null bytes
    text = text.replace("\x00", "")
    
    # Limit length
    if len(text) > max_length:
        text = text[:max_length]
    
    return text.strip()


def generate_content_hash(content: str) -> str:
    """
    Generate a SHA-256 hash of content.
    
    This is useful for deduplication and integrity checking of documents.
    
    Args:
        content: Content string to hash
        
    Returns:
        Hexadecimal SHA-256 hash string
        
    Example:
        >>> content_hash = generate_content_hash(document_text)
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def verify_content_hash(content: str, expected_hash: str) -> bool:
    """
    Verify content against an expected hash.
    
    Args:
        content: Content string to verify
        expected_hash: Expected hash value
        
    Returns:
        True if hash matches, False otherwise
        
    Example:
        >>> if verify_content_hash(document_text, stored_hash):
        ...     print("Content is intact")
    """
    return generate_content_hash(content) == expected_hash


class RateLimiter:
    """
    Simple in-memory rate limiter for API requests.
    
    This class provides basic rate limiting functionality to prevent abuse.
    Note: For production use with multiple workers, consider using Redis or similar.
    
    Attributes:
        requests: Dictionary tracking request counts per identifier
        window: Time window in seconds
        max_requests: Maximum requests per window
        
    Example:
        >>> limiter = RateLimiter(max_requests=100, window=60)
        >>> if limiter.is_allowed(client_ip):
        ...     process_request()
        ... else:
        ...     raise RateLimitExceededError("Too many requests")
    """
    
    def __init__(self, max_requests: int = 100, window: int = 60) -> None:
        """
        Initialize the rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed per window
            window: Time window in seconds
        """
        self.requests: dict[str, list[float]] = {}
        self.max_requests = max_requests
        self.window = window
    
    def is_allowed(self, identifier: str) -> bool:
        """
        Check if a request is allowed for the given identifier.
        
        Args:
            identifier: Unique identifier for the client (e.g., IP address, API key)
            
        Returns:
            True if request is allowed, False otherwise
        """
        import time
        
        current_time = time.time()
        
        # Initialize if first request
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the time window
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if current_time - req_time < self.window
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) < self.max_requests:
            self.requests[identifier].append(current_time)
            return True
        
        return False
    
    def get_remaining_requests(self, identifier: str) -> int:
        """
        Get the number of remaining requests for an identifier.
        
        Args:
            identifier: Unique identifier for the client
            
        Returns:
            Number of remaining requests in the current window
        """
        import time
        
        current_time = time.time()
        
        if identifier not in self.requests:
            return self.max_requests
        
        # Count recent requests
        recent_requests = sum(
            1 for req_time in self.requests[identifier]
            if current_time - req_time < self.window
        )
        
        return max(0, self.max_requests - recent_requests)
    
    def reset(self, identifier: str | None = None) -> None:
        """
        Reset the rate limiter for an identifier or all identifiers.
        
        Args:
            identifier: Specific identifier to reset, or None to reset all
        """
        if identifier:
            self.requests.pop(identifier, None)
        else:
            self.requests.clear()


def validate_file_type(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Validate that a file has an allowed extension.
    
    Args:
        filename: Name of the file to validate
        allowed_extensions: List of allowed file extensions (without dots)
        
    Returns:
        True if file extension is allowed, False otherwise
        
    Example:
        >>> if validate_file_type("document.pdf", ["pdf", "docx"]):
        ...     process_file()
    """
    if not filename:
        return False
    
    # Extract extension
    ext = filename.lower().split(".")[-1] if "." in filename else ""
    
    return ext.lower() in [e.lower() for e in allowed_extensions]
