"""
Rate limiting middleware.
"""
from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.middleware import Middleware
from starlette.types import ASGIApp
from starlette.middleware.base import BaseHTTPMiddleware

from src.core.logging import get_logger
from src.core.exceptions import RateLimitExceededError
from src.core.security import RateLimiter
from src.core.config import get_config


logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    This middleware implements rate limiting based on client IP
    or API key to prevent abuse.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        requests_per_minute: int | None = None
    ) -> None:
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application instance
            requests_per_minute: Request limit per minute
        """
        super().__init__(app)

        config = get_config()
        max_requests = requests_per_minute or config.security.rate_limit_requests
        
        self.limiter = RateLimiter(
            max_requests=max_requests,
            window=config.security.rate_limit_window
        )

        logger.info(
            "Rate limiting middleware initialized",
            max_requests=max_requests,
            window=config.security.rate_limit_window
        )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """
        Process request and check rate limit.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        # Get client identifier (IP or API key)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        if not self.limiter.is_allowed(client_id):
            remaining = self.limiter.get_remaining_requests(client_id)
            
            logger.warning(
                "Rate limit exceeded",
                client_id=client_id,
                remaining=remaining
            )
            
            raise HTTPException(
                status_code=429,
                detail={
                    "success": False,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Rate limit exceeded. Please try again later.",
                    "details": {
                        "remaining_requests": remaining,
                        "retry_after": self.limiter.window
                    }
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.limiter.get_remaining_requests(client_id)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(self.limiter.window)
        
        return response
    
    def _get_client_id(self, request: Request) -> str:
        """
        Get client identifier for rate limiting.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            Client identifier string
        """
        # Check for API key in headers
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}"
        
        # Fall back to IP address
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"


def add_rate_limit_middleware(
    app: ASGIApp,
    requests_per_minute: int | None = None
) -> None:
    """
    Add rate limiting middleware to FastAPI application.
    
    Args:
        app: FastAPI application instance
        requests_per_minute: Request limit per minute
        
    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> add_rate_limit_middleware(app, requests_per_minute=100)
    """
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=requests_per_minute
    )
    logger.info("Rate limiting middleware added to application")
