from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import schemas
from app.services import llm_recommendation_service
from app.services.recommendation_service import (
    get_recommendation_context,
    filter_recommendations_by_time,
    get_available_books,
    get_recommendation_feedback_stats
)
from app.core.auth import get_current_user_id
from app.core.exceptions import ConfigurationError, ExternalAPIError
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/recommendations", response_model=List[schemas.RecommendationResponse])
def get_recommendations(
    limit: int = Query(3, ge=1, le=50),  # Default to 3 top recommendations
    mood: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get personalized book recommendations using LLM based on reading preferences"""
    try:
        recommendations = llm_recommendation_service.generate_llm_recommendations(
            db, user_id, limit, mood
        )
        return recommendations
    except ValueError as e:
        # Configuration errors
        raise ConfigurationError(str(e))
    except Exception as e:
        logger.error(f"Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/recommendations/stream")
async def get_recommendations_streaming(
    limit: int = Query(3, ge=1, le=50),  # Default to 3 top recommendations
    mood: Optional[str] = Query(None),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Stream recommendations with thinking updates"""
    thinking_messages = []
    
    def thinking_callback(message: str):
        thinking_messages.append(message)
    
    async def generate():
        try:
            # Start generating in background
            import concurrent.futures
            loop = asyncio.get_event_loop()
            
            with concurrent.futures.ThreadPoolExecutor() as pool:
                # Yield thinking messages as they come
                future = loop.run_in_executor(
                    pool,
                    lambda: llm_recommendation_service.generate_llm_recommendations(
                        db, user_id, limit, mood, thinking_callback=thinking_callback
                    )
                )
                
                # Stream thinking messages
                last_count = 0
                while not future.done():
                    if len(thinking_messages) > last_count:
                        for msg in thinking_messages[last_count:]:
                            yield f"data: {json.dumps({'type': 'thinking', 'message': msg})}\n\n"
                        last_count = len(thinking_messages)
                    await asyncio.sleep(0.2)
                
                # Get final recommendations
                recommendations = await future
                
                # Serialize recommendations with book data
                from app import schemas, models
                serialized_recs = []
                for r in recommendations:
                    rec_dict = {
                        'id': r.id,
                        'book_id': r.book_id,
                        'score': r.score,
                        'reason': r.reason,
                        'factors': r.factors,
                        'user_id': r.user_id,
                        'created_at': r.created_at.isoformat() if r.created_at else None,
                        'clicked': r.clicked,
                        'dismissed': r.dismissed
                    }
                    # Load book data if not already loaded
                    try:
                        if hasattr(r, 'book') and r.book:
                            book = r.book
                        else:
                            # Manually load book if relationship not loaded
                            book = db.query(models.Book).filter(models.Book.id == r.book_id).first()
                        
                        if book:
                            rec_dict['book'] = {
                                'id': book.id,
                                'title': book.title,
                                'author': book.author,
                                'genre': book.genre,
                                'cover_image_url': book.cover_image_url,
                                'description': book.description,
                                'isbn': book.isbn
                            }
                    except Exception as e:
                        import logging
                        logging.warning(f"Could not load book for recommendation {r.id}: {e}")
                    
                    serialized_recs.append(rec_dict)
                
                # Yield final recommendations
                yield f"data: {json.dumps({'type': 'recommendations', 'data': serialized_recs})}\n\n"
                yield "data: [DONE]\n\n"
                
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/recommendations/{recommendation_id}/click")
def track_recommendation_click(
    recommendation_id: int,
    db: Session = Depends(get_db)
):
    """Track when a recommendation is clicked (user is interested)"""
    from app import models
    from datetime import datetime
    
    rec = db.query(models.Recommendation).filter(
        models.Recommendation.id == recommendation_id
    ).first()
    if rec:
        rec.clicked = True
        if not rec.shown_at:
            rec.shown_at = datetime.now()
        db.commit()
    return {"status": "tracked"}


@router.post("/recommendations/{recommendation_id}/dismiss")
def dismiss_recommendation(
    recommendation_id: int,
    db: Session = Depends(get_db)
):
    """Dismiss a recommendation"""
    from app import models
    rec = db.query(models.Recommendation).filter(
        models.Recommendation.id == recommendation_id
    ).first()
    if rec:
        rec.dismissed = True
        db.commit()
    return {"status": "dismissed"}


@router.get("/recommendations/quick")
def get_quick_recommendation(
    mood: Optional[str] = Query(None, description="Current mood"),
    location: Optional[str] = Query(None, description="Current location"),
    available_time_minutes: Optional[int] = Query(None, ge=5, le=480, description="Available reading time in minutes"),
    only_available: bool = Query(False, description="Only recommend books currently in physical bookshelf"),
    refresh: bool = Query(False, description="Force refresh by calling LLM (otherwise returns stored recommendation)"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get a quick recommendation for "What should I read right now?"
    
    By default, returns the most recent stored recommendation from the database.
    Set refresh=true to generate a new recommendation using LLM.
    
    This is a product-focused endpoint that provides contextual recommendations
    based on current time, mood, location, and available reading time.
    """
    try:
        # Get context
        context = get_recommendation_context(
            db, user_id, mood, location, available_time_minutes
        )
        
        recommendations = []
        
        if refresh:
            # Generate new recommendations using LLM
            recommendations = llm_recommendation_service.generate_llm_recommendations(
                db, user_id, limit=5, current_mood=mood
            )
        else:
            # Get most recent stored recommendation from database
            from app import models
            from sqlalchemy import desc
            from datetime import datetime, timedelta
            
            # Get the most recent recommendation that hasn't been dismissed
            # Prefer recommendations shown in the last 7 days, but allow older ones
            recent_cutoff = datetime.now() - timedelta(days=7)
            
            stored_rec = db.query(models.Recommendation).filter(
                models.Recommendation.user_id == user_id,
                models.Recommendation.dismissed == False,
                models.Recommendation.shown_at >= recent_cutoff
            ).order_by(desc(models.Recommendation.shown_at)).first()
            
            # If no recent recommendation, get the most recent one regardless of date
            if not stored_rec:
                stored_rec = db.query(models.Recommendation).filter(
                    models.Recommendation.user_id == user_id,
                    models.Recommendation.dismissed == False
                ).order_by(desc(models.Recommendation.created_at)).first()
            
            if stored_rec:
                # Load book relationship
                if not hasattr(stored_rec, 'book') or stored_rec.book is None:
                    stored_rec.book = db.query(models.Book).filter(
                        models.Book.id == stored_rec.book_id
                    ).first()
                
                # Mark as shown if not already
                if not stored_rec.shown_at:
                    stored_rec.shown_at = datetime.now()
                    db.commit()
                
                recommendations = [stored_rec]
        
        # Filter by available books if requested
        if only_available:
            available_book_ids = context["available_books"]
            recommendations = [
                r for r in recommendations
                if r.book_id in available_book_ids
            ]
        
        # Filter by available time if specified
        if available_time_minutes:
            recommendations = filter_recommendations_by_time(
                db, user_id, recommendations, available_time_minutes
            )
        
        # Return top recommendation with context
        if recommendations:
            top_rec = recommendations[0]
            
            # Ensure book data is loaded and serialized properly
            
            # Load book if not already loaded
            book = None
            if hasattr(top_rec, 'book') and top_rec.book:
                book = top_rec.book
            else:
                book = db.query(models.Book).filter(models.Book.id == top_rec.book_id).first()
            
            # Serialize recommendation properly
            rec_dict = {
                "id": top_rec.id,
                "book_id": top_rec.book_id,
                "score": top_rec.score,
                "reason": top_rec.reason,
                "factors": top_rec.factors,
            }
            
            # Add book data if available
            if book:
                rec_dict["book"] = {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "genre": getattr(book, 'genre', None),
                    "cover_image_url": getattr(book, 'cover_image_url', None),
                    "description": getattr(book, 'description', None),
                    "isbn": getattr(book, 'isbn', None),
                    "page_count": getattr(book, 'page_count', None),
                }
            
            # Serialize alternatives similarly
            alternatives = []
            for alt_rec in recommendations[1:3]:
                alt_dict = {
                    "id": alt_rec.id,
                    "book_id": alt_rec.book_id,
                    "score": alt_rec.score,
                    "reason": alt_rec.reason,
                    "factors": alt_rec.factors,
                }
                # Load book for alternative
                alt_book = None
                if hasattr(alt_rec, 'book') and alt_rec.book:
                    alt_book = alt_rec.book
                else:
                    alt_book = db.query(models.Book).filter(models.Book.id == alt_rec.book_id).first()
                
                if alt_book:
                    alt_dict["book"] = {
                        "id": alt_book.id,
                        "title": alt_book.title,
                        "author": alt_book.author,
                        "genre": getattr(alt_book, 'genre', None),
                        "cover_image_url": getattr(alt_book, 'cover_image_url', None),
                        "description": getattr(alt_book, 'description', None),
                        "isbn": getattr(alt_book, 'isbn', None),
                        "page_count": getattr(alt_book, 'page_count', None),
                    }
                alternatives.append(alt_dict)
            
            return {
                "recommendation": rec_dict,
                "context": context,
                "alternatives": alternatives
            }
        else:
            return {
                "recommendation": None,
                "context": context,
                "message": "No recommendations found matching your criteria. Try adjusting filters."
            }
            
    except Exception as e:
        logger.error(f"Error getting quick recommendation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting recommendation: {str(e)}")


@router.get("/recommendations/context")
def get_recommendation_context_endpoint(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current recommendation context (time, available books, etc.)"""
    context = get_recommendation_context(db, user_id)
    return context


@router.get("/recommendations/feedback-stats")
def get_recommendation_feedback(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get statistics about recommendation feedback to improve recommendations"""
    stats = get_recommendation_feedback_stats(db, user_id, days)
    return stats


@router.get("/books/available")
def get_available_books_endpoint(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get list of books currently available in physical bookshelf"""
    from app.services import book_service
    
    available_ids = get_available_books(db, user_id)
    if not available_ids:
        return {"books": [], "count": 0}
    
    books = book_service.get_books_by_ids(db, available_ids)
    return {
        "books": books,
        "count": len(books)
    }

