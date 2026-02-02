"""
Structured logging configuration for the RAG system.

This module provides centralized logging setup using structlog for structured logging.
It supports both JSON and text formats and integrates with the application configuration.
"""
import logging
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import Processor

from src.core.config import get_config

# Flag to track if logging has been configured
_logging_configured = False


def configure_logging() -> None:
    """
    Configure structured logging for the application.
    
    This function sets up structlog with appropriate processors based on the
    configured log format (JSON or text). It also configures standard logging
    to integrate with structlog.
    
    Note: This function is idempotent - calling it multiple times will not
    cause duplicate handlers or log messages.
    """
    global _logging_configured
    
    # Prevent duplicate configuration
    if _logging_configured:
        return
    
    config = get_config()
    
    # Get log directory and ensure it exists
    log_dir = config.storage.log_path
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Define file paths for different log types
    app_log_path = log_dir / "app.log"
    error_log_path = log_dir / "error.log"
    
    # Configure standard logging (only if not already configured)
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(
            format="%(message)s",
            stream=sys.stdout,
            level=config.logging.level,
        )
    
    # Define common processors
    shared_processors: list[Processor] = [
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add exception info if present
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    
    # Format-specific processors
    if config.logging.format == "json":
        # JSON format for production
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        dev_processors: list[Processor] = [
            structlog.processors.JSONRenderer()
        ]
    else:
        # Text format for development
        processors = shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ]
        dev_processors = [
            structlog.dev.ConsoleRenderer(
                colors=config.app.app_debug,
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
        wrapper_class=structlog.stdlib.BoundLogger,
    )
    
    # Set up processors for standard logging
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(structlog.stdlib.ProcessorFormatter(*dev_processors))
    
    # Add file handler for all logs
    file_handler = logging.FileHandler(app_log_path)
    file_handler.setFormatter(structlog.stdlib.ProcessorFormatter(*dev_processors))
    file_handler.setLevel(config.logging.level)
    
    # Add file handler for errors only
    error_handler = logging.FileHandler(error_log_path)
    error_handler.setFormatter(structlog.stdlib.ProcessorFormatter(*dev_processors))
    error_handler.setLevel(logging.ERROR)
    
    # Apply handlers to root logger only if they don't already exist
    # This prevents duplicate handlers when configure_logging is called multiple times
    if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in root_logger.handlers):
        root_logger.addHandler(handler)
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(app_log_path) for h in root_logger.handlers):
        root_logger.addHandler(file_handler)
    
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(error_log_path) for h in root_logger.handlers):
        root_logger.addHandler(error_handler)
    
    # Set log level for third-party libraries to WARNING
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
    
    # Mark logging as configured to prevent duplicate setup
    _logging_configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name, typically __name__ of the module
        
    Returns:
        Configured structlog logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing document", document_id="123")
    """
    return structlog.get_logger(name)


class LoggingContext:
    """
    Context manager for adding contextual information to logs.
    
    This class provides a convenient way to add contextual information to logs
    within a specific scope using a context manager.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> with LoggingContext(logger, user_id="123", action="upload"):
        ...     logger.info("Starting operation")
        ...     # Logs will include user_id and action
        ...     logger.info("Operation completed")
    """
    
    def __init__(self, logger: structlog.stdlib.BoundLogger, **kwargs: Any) -> None:
        """
        Initialize the logging context.
        
        Args:
            logger: The logger instance to bind context to
            **kwargs: Key-value pairs to bind to the logger context
        """
        self.logger = logger
        self.context = kwargs
        self.original_context = {}
    
    def __enter__(self) -> structlog.stdlib.BoundLogger:
        """Enter the context and bind values to the logger."""
        # Store original context
        self.original_context = dict(self.logger._context)
        
        # Bind new context
        self.logger = self.logger.bind(**self.context)
        return self.logger
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit the context and restore original logger context."""
        # Restore original context
        self.logger._context.clear()
        self.logger._context.update(self.original_context)


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """
    Log a function call with its arguments.
    
    This is a utility function for consistent logging of function calls
    throughout the application.
    
    Args:
        func_name: Name of the function being called
        **kwargs: Function arguments to log
        
    Example:
        >>> def process_document(doc_id: str, content: str) -> str:
        ...     log_function_call("process_document", doc_id=doc_id, content_length=len(content))
        ...     # Function implementation
    """
    logger = get_logger(__name__)
    logger.info(
        "Function called",
        function=func_name,
        arguments={k: str(v)[:100] if isinstance(v, str) else v for k, v in kwargs.items()}
    )


def log_exception(exception: Exception, context: dict[str, Any] | None = None) -> None:
    """
    Log an exception with additional context.
    
    This function provides a consistent way to log exceptions throughout
    the application, optionally adding contextual information.
    
    Args:
        exception: The exception to log
        context: Optional dictionary of contextual information
        
    Example:
        >>> try:
        ...     process_document(doc_id)
        ... except DocumentProcessingError as e:
        ...     log_exception(e, context={"document_id": doc_id, "attempt": 2})
    """
    logger = get_logger(__name__)
    error_context = {
        "exception_type": type(exception).__name__,
        "exception_message": str(exception),
    }
    
    if context:
        error_context.update(context)
    
    # Add error_code if it's a BaseRAGException
    if hasattr(exception, "error_code"):
        error_context["error_code"] = exception.error_code
    
    logger.error("Exception occurred", **error_context, exc_info=exception)
