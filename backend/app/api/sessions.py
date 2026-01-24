from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import schemas, models
from app.services import reading_service
from app.api.users import get_password_hash
from app.core.auth import get_current_user_id
from app.core.exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)


def get_or_create_user(db: Session, user_id: int) -> models.User:
    """Get user by ID, or create a default user if it doesn't exist"""
    import logging
    logger = logging.getLogger(__name__)
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    
    if not user:
        # Use the centralized password hashing function
        password = "pass123"  # Simple ASCII password, definitely < 72 bytes
        hashed_password = get_password_hash(password)
        # Try to create with specified ID, but let database assign if it fails
        try:
            user = models.User(
                id=user_id,
                username=f"user_{user_id}",
                email=f"user_{user_id}@example.com",
                hashed_password=hashed_password
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Created user with ID {user_id}")
        except Exception as e:
            # If ID assignment fails, get the first user or create without ID
            logger.warning(f"Failed to create user with ID {user_id}: {e}")
            db.rollback()
            user = db.query(models.User).first()
            if not user:
                try:
                    user = models.User(
                        username=f"user_{user_id}",
                        email=f"user_{user_id}@example.com",
                        hashed_password=hashed_password
                    )
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                    logger.info(f"Created user without specifying ID, got ID {user.id}")
                except Exception as e2:
                    logger.error(f"Failed to create user: {e2}")
                    db.rollback()
                    raise
    
    return user

router = APIRouter()


@router.post("/reading-sessions", response_model=schemas.ReadingSessionResponse, status_code=201)
def create_reading_session(
    session: schemas.ReadingSessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new reading session (book taken or returned)"""
    # Ensure user exists
    get_or_create_user(db, user_id)
    return reading_service.create_reading_session(db, user_id, session)


@router.get("/reading-sessions", response_model=List[schemas.ReadingSessionResponse])
def get_reading_sessions(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    book_id: Optional[int] = Query(None),
    mood: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get reading sessions with filters"""
    query = schemas.ReadingHistoryQuery(
        start_date=start_date,
        end_date=end_date,
        book_id=book_id,
        mood=mood,
        limit=limit,
        offset=offset
    )
    sessions = reading_service.get_reading_sessions(db, user_id, query)
    return sessions


@router.get("/reading-sessions/book-ids")
def get_books_with_sessions(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get unique book IDs that have reading sessions (for My Books page)"""
    from sqlalchemy import distinct
    book_ids = db.query(distinct(models.ReadingSession.book_id)).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.book_id.isnot(None)
    ).all()
    return {"book_ids": [bid[0] for bid in book_ids]}


@router.get("/reading-sessions/statistics")
def get_reading_statistics(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get reading statistics"""
    try:
        # Ensure user exists
        get_or_create_user(db, user_id)
        return reading_service.get_reading_statistics(db, user_id)
    except Exception as e:
        logger.error(f"Error getting reading statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting reading statistics: {str(e)}")

