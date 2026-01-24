"""
Custom middleware for request/response logging and other cross-cutting concerns
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging
from typing import Callable

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests and responses with timing information"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log request
        start_time = time.time()
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        
        logger.info(f"→ {method} {path}{'?' + query_params if query_params else ''}")
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log response
            status_code = response.status_code
            logger.info(
                f"← {method} {path} {status_code} "
                f"({duration:.3f}s)"
            )
            
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"✗ {method} {path} ERROR after {duration:.3f}s: {e}",
                exc_info=True
            )
            raise

