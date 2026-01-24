"""
Database utilities and transaction management
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session
from typing import Generator
import logging

logger = logging.getLogger(__name__)


@contextmanager
def transaction(db: Session) -> Generator[Session, None, None]:
    """
    Context manager for database transactions with automatic rollback on error.
    
    Usage:
        with transaction(db) as session:
            # Do database operations
            session.add(...)
            # Commit happens automatically on success
    """
    try:
        yield db
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back due to error: {e}", exc_info=True)
        raise

