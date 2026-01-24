"""
Core utilities and shared functionality
"""
from app.core.auth import get_current_user, get_current_user_id
from app.core.exceptions import (
    BookshelfException,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    ExternalAPIError,
    ConfigurationError
)
from app.core.database import transaction

__all__ = [
    "get_current_user",
    "get_current_user_id",
    "BookshelfException",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "ExternalAPIError",
    "ConfigurationError",
    "transaction",
]

