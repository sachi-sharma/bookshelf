"""
Custom exceptions for the application
"""
from fastapi import HTTPException, status


class BookshelfException(HTTPException):
    """Base exception for all application errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundError(BookshelfException):
    """Resource not found"""
    def __init__(self, resource: str, identifier: str = None):
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


class ValidationError(BookshelfException):
    """Validation error"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


class AuthenticationError(BookshelfException):
    """Authentication error"""
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail=detail, status_code=status.HTTP_401_UNAUTHORIZED)


class AuthorizationError(BookshelfException):
    """Authorization error"""
    def __init__(self, detail: str = "Not authorized"):
        super().__init__(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


class ExternalAPIError(BookshelfException):
    """External API error"""
    def __init__(self, service: str, detail: str = None):
        detail = detail or f"Error calling {service} API"
        super().__init__(detail=detail, status_code=status.HTTP_502_BAD_GATEWAY)


class ConfigurationError(BookshelfException):
    """Configuration error"""
    def __init__(self, detail: str):
        super().__init__(detail=detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

