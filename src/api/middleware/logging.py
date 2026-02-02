"""
Logging middleware for API requests.
"""
import time
from typing import Callable

from fastapi import Request, Response
from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger, LogTag


logger = get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all API requests and responses.
    
    This middleware logs request information, response status,
    and processing time for monitoring and debugging.
    """
    
    def __init__(self, app: ASGIApp) -> None:
        """
        Initialize logging middleware.

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
        Process request and log information.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip logging for metrics endpoint (frequently polled by Prometheus)
        if request.url.path == "/metrics":
            return await call_next(request)
        
        start_time = time.time()
        
        # Get trace_id from context
        from src.api.middleware.tracing import get_trace_id
        trace_id = get_trace_id()
        
        # Log request
        logger.bind(tag=LogTag.REQUEST.value, trace_id=trace_id).info(
            "Incoming request",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else "unknown"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000
        formatted_time = f"{process_time:.2f}ms"
        
        # Add custom header with processing time
        response.headers["X-Process-Time"] = formatted_time
        
        # Get trace_id from context
        from src.api.middleware.tracing import get_trace_id
        trace_id = get_trace_id()
        
        # Log response
        logger.bind(tag=LogTag.RESPONSE.value, trace_id=trace_id).info(
            "Request processed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            process_time=formatted_time,
            client=request.client.host if request.client else "unknown"
        )
        
        return response


def add_logging_middleware(app: ASGIApp) -> None:
    """
    Add logging middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> add_logging_middleware(app)
    """
    app.add_middleware(LoggingMiddleware)
    logger.bind(tag=LogTag.MIDDLEWARE.value).info("Logging middleware added to application")
