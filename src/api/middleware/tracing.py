"""
Tracing middleware for request tracing with trace_id.
"""
import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger, LogTag

# Context variable to store trace_id for the current request
trace_id_context: ContextVar[str] = ContextVar('trace_id', default='')


def get_trace_id() -> str:
    """
    Get the current trace_id from context.
    
    Returns:
        Current trace_id or empty string if not set
    """
    try:
        return trace_id_context.get()
    except LookupError:
        return ''


def set_trace_id(trace_id: str) -> None:
    """
    Set trace_id in context.
    
    Args:
        trace_id: Trace ID to set
    """
    trace_id_context.set(trace_id)


logger = get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for request tracing with trace_id.
    
    This middleware:
    1. Extracts x-trace-id from request headers or generates a new one
    2. Stores trace_id in context for the duration of the request
    3. Adds trace_id to response headers
    4. Binds trace_id to logger context for all logs in the request
    """
    
    def __init__(self, app: ASGIApp) -> None:
        """
        Initialize tracing middleware.

        Args:
            app: FastAPI application instance
        """
        super().__init__(app)
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and manage trace_id.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response with trace_id header
        """
        # Skip tracing for metrics endpoint
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Get or generate trace_id
        trace_id = request.headers.get("x-trace-id", "")
        if not trace_id:
            # Generate new trace_id if not provided
            trace_id = str(uuid.uuid4())
        
        # Set trace_id in context
        set_trace_id(trace_id)
        
        # Bind trace_id to logger context for this request
        # This ensures all logs in this request will include trace_id
        logger_with_trace = logger.bind(trace_id=trace_id)
        
        # Process request
        try:
            response = await call_next(request)
        finally:
            # Clear trace_id from context after request completes
            trace_id_context.set('')
        
        # Add trace_id to response headers
        response.headers["X-Trace-Id"] = trace_id
        
        return response


def add_tracing_middleware(app: ASGIApp) -> None:
    """
    Add tracing middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> add_tracing_middleware(app)
    """
    app.add_middleware(TracingMiddleware)
    logger.bind(tag=LogTag.MIDDLEWARE.value).info("Tracing middleware added to application")
