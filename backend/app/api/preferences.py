from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import models, schemas
from app.core.auth import get_current_user_id
from app.core.exceptions import NotFoundError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/books/{book_id}/preference", response_model=schemas.BookPreferenceResponse)
def get_book_preference(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get user's preference/status for a book"""
    preference = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.book_id == book_id
    ).first()
    
    if not preference:
        raise NotFoundError("Preference", f"book_id={book_id}")
    
    return preference


@router.post("/books/{book_id}/preference", response_model=schemas.BookPreferenceResponse)
def create_or_update_preference(
    book_id: int,
    preference_data: schemas.BookPreferenceCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create or update book preference (status: read, want_to_read, currently_reading, etc.)"""
    # Verify book exists
    book = db.query(models.Book).filter(models.Book.id == book_id).first()
    if not book:
        raise NotFoundError("Book", f"id={book_id}")
    
    # Check if preference exists
    existing = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.book_id == book_id
    ).first()
    
    if existing:
        # Update existing
        if preference_data.status is not None:
            # Allow clearing status by passing empty string
            existing.status = preference_data.status if preference_data.status else None
        if preference_data.rating is not None:
            existing.rating = preference_data.rating
        if preference_data.review is not None:
            existing.review = preference_data.review
        if preference_data.favorite is not None:
            existing.favorite = preference_data.favorite
        if preference_data.tags is not None:
            existing.tags = preference_data.tags
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new - book_id comes from URL, not request body
        new_preference = models.BookPreference(
            user_id=user_id,
            book_id=book_id,  # From URL parameter
            status=preference_data.status or "want_to_read",
            rating=preference_data.rating,
            review=preference_data.review,
            favorite=preference_data.favorite or False,
            tags=preference_data.tags
        )
        db.add(new_preference)
        db.commit()
        db.refresh(new_preference)
        return new_preference


@router.get("/preferences", response_model=List[schemas.BookPreferenceResponse])
def get_all_preferences(
    status: Optional[str] = None,  # Filter by status: read, want_to_read, currently_reading, abandoned
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all book preferences, optionally filtered by status"""
    query = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id
    )
    
    if status:
        query = query.filter(models.BookPreference.status == status)
    
    preferences = query.all()
    return preferences


@router.delete("/books/{book_id}/preference")
def delete_preference(
    book_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Remove book preference"""
    preference = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.book_id == book_id
    ).first()
    
    if not preference:
        raise NotFoundError("Preference", f"book_id={book_id}")
    
    db.delete(preference)
    db.commit()
    return {"status": "deleted"}

