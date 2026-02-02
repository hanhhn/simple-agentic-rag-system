"""
Helper functions for the RAG system.

This module provides common helper functions used throughout the application.
"""
import asyncio
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Coroutine, List, Optional, TypeVar, Callable
import functools


T = TypeVar('T')


def generate_id() -> str:
    """
    Generate a unique ID using UUID4.
    
    Returns:
        Unique identifier string
        
    Example:
        >>> doc_id = generate_id()
        >>> print(doc_id)  # "550e8400-e29b-41d4-a716-446655440000"
    """
    return str(uuid.uuid4())


def generate_short_id() -> str:
    """
    Generate a short unique ID.
    
    Returns:
        Short unique identifier string (8 characters)
        
    Example:
        >>> short_id = generate_short_id()
        >>> print(short_id)  # "a3f9c2d1"
    """
    return uuid.uuid4().hex[:8]


def get_timestamp() -> str:
    """
    Get current timestamp in ISO 8601 format.
    
    Returns:
        ISO 8601 formatted timestamp string
        
    Example:
        >>> timestamp = get_timestamp()
        >>> print(timestamp)  # "2024-01-15T10:30:45.123456"
    """
    return datetime.utcnow().isoformat() + "Z"


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string (e.g., "1.5 MB", "256 KB")
        
    Example:
        >>> print(format_size(1572864))  # "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def hash_string(text: str) -> str:
    """
    Generate a SHA-256 hash of a string.
    
    Args:
        text: Text to hash
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> doc_hash = hash_string("Hello World")
        >>> print(doc_hash)  # "a591a6d40bf420404a011733cfb7b190d62c65bf0bcda32b57b277d9ad9f146e"
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
        
    Example:
        >>> short = truncate_text("This is a very long text", 10)
        >>> print(short)  # "This is..."
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def safe_json_loads(text: str, default: Any = None) -> Any:
    """
    Safely parse JSON text with a default value on failure.
    
    Args:
        text: JSON string to parse
        default: Default value to return if parsing fails
        
    Returns:
        Parsed JSON data or default value
        
    Example:
        >>> data = safe_json_loads('{"key": "value"}', {})
        >>> print(data)  # {"key": "value"}
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


def ensure_dir(directory: Path | str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        Path object for the directory
        
    Example:
        >>> data_dir = ensure_dir("./data/documents")
        >>> # Creates directory if it doesn't exist
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def file_exists(filepath: Path | str) -> bool:
    """
    Check if a file exists.
    
    Args:
        filepath: Path to the file
        
    Returns:
        True if file exists, False otherwise
        
    Example:
        >>> if file_exists("document.txt"):
        ...     process_document()
    """
    return Path(filepath).exists()


def get_file_extension(filepath: Path | str) -> str:
    """
    Get the file extension from a filepath.
    
    Args:
        filepath: Path to the file
        
    Returns:
        File extension (without the dot)
        
    Example:
        >>> ext = get_file_extension("document.pdf")
        >>> print(ext)  # "pdf"
    """
    path = Path(filepath)
    return path.suffix.lstrip('.').lower()


def is_empty(text: str) -> bool:
    """
    Check if text is empty or only whitespace.
    
    Args:
        text: Text to check
        
    Returns:
        True if text is empty or whitespace only
        
    Example:
        >>> if is_empty(user_input):
        ...     raise ValidationError("Input cannot be empty")
    """
    return not text or not text.strip()


def chunks_list(lst: List[T], chunk_size: int) -> List[List[T]]:
    """
    Split a list into chunks.
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
        
    Example:
        >>> data = [1, 2, 3, 4, 5]
        >>> chunked = chunks_list(data, 2)
        >>> print(chunked)  # [[1, 2], [3, 4], [5]]
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_list(nested_list: List[List[T]]) -> List[T]:
    """
    Flatten a nested list.
    
    Args:
        nested_list: Nested list to flatten
        
    Returns:
        Flattened list
        
    Example:
        >>> nested = [[1, 2], [3, 4], [5]]
        >>> flat = flatten_list(nested)
        >>> print(flat)  # [1, 2, 3, 4, 5]
    """
    return [item for sublist in nested_list for item in sublist]


def remove_duplicates(lst: List[T]) -> List[T]:
    """
    Remove duplicates from a list while preserving order.
    
    Args:
        lst: List to deduplicate
        
    Returns:
        List with duplicates removed
        
    Example:
        >>> items = [1, 2, 2, 3, 1, 4]
        >>> unique = remove_duplicates(items)
        >>> print(unique)  # [1, 2, 3, 4]
    """
    seen = []
    result = []
    for item in lst:
        if item not in seen:
            seen.append(item)
            result.append(item)
    return result


def retry(
    func: Callable[..., T],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[..., T]:
    """
    Decorator for retrying a function on failure.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated function with retry logic
        
    Example:
        >>> @retry(max_retries=3, delay=1.0)
        ... def fetch_data():
        ...     # Function that might fail
        ...     return requests.get(url)
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        import time
        
        last_exception = None
        current_delay = delay
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(current_delay)
                    current_delay *= backoff
                continue
        
        raise last_exception  # type: ignore
    
    return wrapper


async def async_retry(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator for retrying an async function on failure.
    
    Args:
        func: Async function to retry
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
        
    Returns:
        Decorated async function with retry logic
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        last_exception = None
        current_delay = delay
        
        for attempt in range(max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
                continue
        
        raise last_exception
    
    return wrapper


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to measure
        
    Returns:
        Decorated function that logs execution time
        
    Example:
        >>> @measure_time
        ... def process_document():
        ...     # Long-running operation
        ...     pass
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        import time
        from src.core.logging import get_logger
        
        logger = get_logger(__name__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"{func.__name__} completed",
                function=func.__name__,
                execution_time=f"{execution_time:.3f}s"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"{func.__name__} failed",
                function=func.__name__,
                execution_time=f"{execution_time:.3f}s",
                error=str(e)
            )
            raise
    
    return wrapper


async def async_measure_time(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
    """
    Decorator to measure async function execution time.
    
    Args:
        func: Async function to measure
        
    Returns:
        Decorated async function that logs execution time
    """
    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        import time
        from src.core.logging import get_logger
        
        logger = get_logger(__name__)
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"{func.__name__} completed",
                function=func.__name__,
                execution_time=f"{execution_time:.3f}s"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"{func.__name__} failed",
                function=func.__name__,
                execution_time=f"{execution_time:.3f}s",
                error=str(e)
            )
            raise
    
    return wrapper


def camel_to_snake(name: str) -> str:
    """
    Convert CamelCase to snake_case.
    
    Args:
        name: CamelCase string
        
    Returns:
        snake_case string
        
    Example:
        >>> print(camel_to_snake("CamelCase"))  # "camel_case"
    """
    import re
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def snake_to_camel(name: str) -> str:
    """
    Convert snake_case to CamelCase.
    
    Args:
        name: snake_case string
        
    Returns:
        CamelCase string
        
    Example:
        >>> print(snake_to_camel("snake_case"))  # "SnakeCase"
    """
    components = name.split('_')
    return ''.join(x.title() for x in components)


def merge_dicts(*dicts: dict[str, Any]) -> dict[str, Any]:
    """
    Merge multiple dictionaries recursively.
    
    Args:
        *dicts: Dictionaries to merge
        
    Returns:
        Merged dictionary
        
    Example:
        >>> result = merge_dicts({"a": 1}, {"b": 2}, {"a": 3})
        >>> print(result)  # {"a": 3, "b": 2}
    """
    result: dict[str, Any] = {}
    
    for dictionary in dicts:
        for key, value in dictionary.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dicts(result[key], value)
            else:
                result[key] = value
    
    return result


def get_nested_value(data: dict[str, Any], path: str, default: Any = None) -> Any:
    """
    Get a value from a nested dictionary using a dot-separated path.
    
    Args:
        data: Nested dictionary
        path: Dot-separated path (e.g., "user.address.city")
        default: Default value if path doesn't exist
        
    Returns:
        Value at the path or default
        
    Example:
        >>> data = {"user": {"address": {"city": "NYC"}}}
        >>> city = get_nested_value(data, "user.address.city")
        >>> print(city)  # "NYC"
    """
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current


def set_nested_value(data: dict[str, Any], path: str, value: Any) -> None:
    """
    Set a value in a nested dictionary using a dot-separated path.
    
    Args:
        data: Nested dictionary
        path: Dot-separated path (e.g., "user.address.city")
        value: Value to set
        
    Example:
        >>> data = {"user": {}}
        >>> set_nested_value(data, "user.address.city", "NYC")
        >>> print(data)  # {"user": {"address": {"city": "NYC"}}}
    """
    keys = path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value
