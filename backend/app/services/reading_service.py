from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app import models, schemas
from typing import Optional, List
from datetime import datetime


def create_reading_session(
    db: Session,
    user_id: int,
    session_data: schemas.ReadingSessionCreate
) -> models.ReadingSession:
    """Create a new reading session"""
    from app.core.database import transaction
    
    with transaction(db):
        db_session = models.ReadingSession(
            user_id=user_id,
            **session_data.dict()
        )
        db.add(db_session)
        # Transaction context manager will commit automatically
    db.refresh(db_session)
    return db_session


def get_reading_sessions(
    db: Session,
    user_id: int,
    query: schemas.ReadingHistoryQuery
) -> List[models.ReadingSession]:
    """Get reading sessions with filters"""
    q = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id
    )
    
    if query.start_date:
        q = q.filter(models.ReadingSession.timestamp >= query.start_date)
    
    if query.end_date:
        q = q.filter(models.ReadingSession.timestamp <= query.end_date)
    
    if query.book_id:
        q = q.filter(models.ReadingSession.book_id == query.book_id)
    
    if query.mood:
        q = q.filter(models.ReadingSession.mood == query.mood)
    
    return q.order_by(desc(models.ReadingSession.timestamp)).offset(
        query.offset
    ).limit(query.limit).all()


def get_reading_statistics(db: Session, user_id: int) -> dict:
    """Get reading statistics for a user
    
    For pages calculation:
    - Counts pages_read from sessions that have it
    - For books marked as "read" in preferences but with no pages_read in sessions,
      uses book.page_count as an estimate (to handle Goodreads imports)
    """
    sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id
    ).all()
    
    total_sessions = len(sessions)
    total_duration = sum(s.duration_minutes or 0 for s in sessions)
    
    # Count pages from sessions
    total_pages = sum(s.pages_read or 0 for s in sessions)
    
    # Track which books have pages_read in sessions
    books_with_session_pages = set()
    for session in sessions:
        if session.pages_read:
            books_with_session_pages.add(session.book_id)
    
    # For books marked as "read" in preferences but with no pages_read in sessions,
    # add the book's page_count as an estimate (handles Goodreads imports)
    read_preferences = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.status == "read"
    ).all()
    
    for pref in read_preferences:
        if pref.book_id not in books_with_session_pages:
            # This book is marked read but has no pages_read in sessions
            # Check if we can get page_count from the book
            book = db.query(models.Book).filter(models.Book.id == pref.book_id).first()
            if book and book.page_count:
                total_pages += book.page_count
                books_with_session_pages.add(pref.book_id)  # Mark as counted
    
    # Mood distribution
    mood_counts = {}
    for session in sessions:
        if session.mood:
            mood_counts[session.mood] = mood_counts.get(session.mood, 0) + 1
    
    # Most read books
    book_counts = {}
    for session in sessions:
        book_counts[session.book_id] = book_counts.get(session.book_id, 0) + 1
    
    most_read_book_id = max(book_counts.items(), key=lambda x: x[1])[0] if book_counts else None
    
    return {
        "total_sessions": total_sessions,
        "total_duration_minutes": total_duration,
        "total_pages_read": total_pages,
        "average_session_duration": total_duration / total_sessions if total_sessions > 0 else 0,
        "mood_distribution": mood_counts,
        "most_read_book_id": most_read_book_id
    }

