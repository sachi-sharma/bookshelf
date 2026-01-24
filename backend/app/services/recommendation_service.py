"""
Enhanced recommendation service with product-focused features
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc
from app import models, schemas
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


def get_available_books(db: Session, user_id: int) -> List[int]:
    """
    Get list of book IDs that are currently available in physical bookshelf.
    A book is 'available' if it was taken but not yet returned.
    """
    # Get all unique books that have reading sessions
    all_books = db.query(
        models.ReadingSession.book_id
    ).filter(
        models.ReadingSession.user_id == user_id
    ).distinct().all()
    
    available_ids = []
    
    # For each book, check if the most recent action was "taken"
    for (book_id,) in all_books:
        # Get the most recent session for this book
        latest_session = db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.book_id == book_id
        ).order_by(desc(models.ReadingSession.timestamp)).first()
        
        # If the most recent action was "taken", the book is available
        if latest_session and latest_session.action == "taken":
            available_ids.append(book_id)
    
    return available_ids


def estimate_reading_time(
    db: Session,
    user_id: int,
    book_id: int,
    pages: Optional[int] = None
) -> Optional[float]:
    """
    Estimate reading time for a book based on user's historical reading pace.
    Returns time in minutes.
    """
    # Get user's average reading pace (pages per minute)
    sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.pages_read.isnot(None),
        models.ReadingSession.duration_minutes.isnot(None),
        models.ReadingSession.duration_minutes > 0
    ).all()
    
    if not sessions:
        # Default: 1 page per minute (60 pages/hour)
        default_pace = 1.0
    else:
        total_pages = sum(s.pages_read for s in sessions if s.pages_read)
        total_minutes = sum(s.duration_minutes for s in sessions if s.duration_minutes)
        if total_minutes > 0:
            default_pace = total_pages / total_minutes
        else:
            default_pace = 1.0
    
    # Get book page count
    if not pages:
        book = db.query(models.Book).filter(models.Book.id == book_id).first()
        if book and book.page_count:
            pages = book.page_count
        else:
            return None  # Can't estimate without page count
    
    # Estimate reading time
    estimated_minutes = pages / default_pace
    return estimated_minutes


def get_recommendation_context(
    db: Session,
    user_id: int,
    current_mood: Optional[str] = None,
    current_location: Optional[str] = None,
    available_time_minutes: Optional[int] = None
) -> Dict[str, Any]:
    """
    Get comprehensive context for recommendations including:
    - Current time, day, month
    - User's mood and location
    - Available reading time
    - Available books in physical shelf
    - Recent reading patterns
    """
    now = datetime.now()
    current_month = now.month
    current_day_of_week = now.strftime("%A")
    current_hour = now.hour
    current_time_of_day = (
        "morning" if 5 <= current_hour < 12
        else "afternoon" if 12 <= current_hour < 17
        else "evening" if 17 <= current_hour < 21
        else "night"
    )
    
    # Get available books
    available_book_ids = get_available_books(db, user_id)
    
    # Get recent reading activity (last 30 days)
    thirty_days_ago = now - timedelta(days=30)
    recent_sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.timestamp >= thirty_days_ago
    ).all()
    
    # Get user's average reading pace
    all_sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.pages_read.isnot(None),
        models.ReadingSession.duration_minutes.isnot(None),
        models.ReadingSession.duration_minutes > 0
    ).all()
    
    avg_pace = None
    if all_sessions:
        total_pages = sum(s.pages_read for s in all_sessions if s.pages_read)
        total_minutes = sum(s.duration_minutes for s in all_sessions if s.duration_minutes)
        if total_minutes > 0:
            avg_pace = total_pages / total_minutes
    
    return {
        "current_time": {
            "hour": current_hour,
            "time_of_day": current_time_of_day,
            "day_of_week": current_day_of_week,
            "month": current_month,
            "timestamp": now.isoformat()
        },
        "user_context": {
            "mood": current_mood,
            "location": current_location,
            "available_time_minutes": available_time_minutes
        },
        "available_books": available_book_ids,
        "recent_activity": {
            "sessions_count": len(recent_sessions),
            "recent_moods": list(set([s.mood for s in recent_sessions if s.mood])),
            "recent_locations": list(set([s.location for s in recent_sessions if s.location]))
        },
        "reading_stats": {
            "average_pace_pages_per_minute": avg_pace,
            "total_sessions": len(all_sessions)
        }
    }


def filter_recommendations_by_time(
    db: Session,
    user_id: int,
    recommendations: List,  # Can be List[models.Recommendation] or List[schemas.RecommendationResponse]
    max_time_minutes: Optional[int] = None
) -> List:
    """
    Filter recommendations to only include books that can be read within available time.
    Works with both SQLAlchemy model objects and Pydantic schema objects.
    """
    if not max_time_minutes:
        return recommendations
    
    filtered = []
    for rec in recommendations:
        # Get book_id - works for both model and schema objects
        book_id = rec.book_id if hasattr(rec, 'book_id') else None
        if not book_id:
            # If no book_id, include it anyway (can't filter)
            filtered.append(rec)
            continue
        
        # Get page count - handle both SQLAlchemy models and Pydantic schemas
        page_count = None
        
        # Check if rec.book exists and get page_count from it
        if hasattr(rec, 'book') and rec.book:
            # Could be SQLAlchemy model or Pydantic schema
            if hasattr(rec.book, 'page_count'):
                page_count = rec.book.page_count
            elif hasattr(rec.book, '__dict__') and 'page_count' in rec.book.__dict__:
                page_count = rec.book.__dict__.get('page_count')
        
        # If we still don't have page_count, load book from database
        if page_count is None:
            book = db.query(models.Book).filter(models.Book.id == book_id).first()
            if book:
                page_count = book.page_count
        
        estimated_time = estimate_reading_time(db, user_id, book_id, page_count)
        if estimated_time and estimated_time <= max_time_minutes:
            filtered.append(rec)
        elif not estimated_time:
            # If we can't estimate, include it anyway
            filtered.append(rec)
    
    return filtered


def get_recommendation_feedback_stats(
    db: Session,
    user_id: int,
    days: int = 30
) -> Dict[str, Any]:
    """
    Get statistics about recommendation feedback to improve future recommendations.
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    # Get recommendations shown in the period
    recommendations = db.query(models.Recommendation).filter(
        models.Recommendation.user_id == user_id,
        models.Recommendation.shown_at >= cutoff_date
    ).all()
    
    # Get recommendations that were clicked (interested)
    clicked = [r for r in recommendations if r.clicked]
    
    # Get recommendations that were dismissed
    dismissed = [r for r in recommendations if r.dismissed]
    
    # Get recommendations that led to actual reading
    # (user created a reading session for the book after recommendation)
    read_books = []
    for rec in clicked:
        # Check if user created a reading session for this book after recommendation
        if not rec.shown_at:
            continue  # Skip if recommendation was never shown
        
        session = db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.book_id == rec.book_id,
            models.ReadingSession.timestamp >= rec.shown_at
        ).first()
        if session:
            read_books.append(rec)
    
    return {
        "total_shown": len(recommendations),
        "clicked": len(clicked),
        "dismissed": len(dismissed),
        "actually_read": len(read_books),
        "click_rate": len(clicked) / len(recommendations) if recommendations else 0,
        "read_rate": len(read_books) / len(clicked) if clicked else 0,
        "dismiss_rate": len(dismissed) / len(recommendations) if recommendations else 0
    }

