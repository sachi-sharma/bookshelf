"""
Chat API endpoint

Provides a read-only endpoint for the Chat Agent to explain signals and answer questions.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from app.database import get_db
from app import schemas
from app.core.auth import get_current_user_id
from app.agents import ChatAgent, BookAgent, ReflectionAgent, decide_agent_output
from app.services import reading_service
from app.services.recommendation_service import get_recommendation_context
from app import models

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/chat", response_model=schemas.ChatResponse)
def chat(
    request: schemas.ChatRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Chat endpoint that explains existing signals and answers reflective questions.
    
    This endpoint uses the agent coordinator to decide which agent (if any) should surface output.
    User-invoked requests are always allowed.
    
    The agent does NOT query the database directly - it works with pre-assembled context.
    """
    try:
        # Assemble context based on context_type
        context_data = _assemble_context(
            db=db,
            user_id=user_id,
            context_type=request.context_type,
            context_data=request.context_data
        )
        
        # Extract book_id from context_data if available
        book_id = context_data.get("book_id") or request.context_data.get("book_id")
        
        # Use coordinator to decide which agent should surface
        # User-invoked requests are always allowed (is_user_invoked=True)
        decision = decide_agent_output(
            db=db,
            user_id=user_id,
            book_id=book_id,
            context_type=request.context_type,
            context_data=context_data,
            is_user_invoked=True  # User explicitly invoked this endpoint
        )
        
        # If coordinator returns None, it means silence (shouldn't happen for user-invoked, but handle it)
        if decision is None:
            # This shouldn't happen for user-invoked, but if it does, return a default response
            logger.warning(f"Coordinator returned None for user-invoked chat request")
            return {
                "response": "I don't have anything to share right now.",
                "primary_insight": None,
                "context_type": None,
                "insights": [],
                "follow_up_prompts": []
            }
        
        # Execute the agent based on coordinator decision
        if decision["agent"] == "chat":
            agent = ChatAgent()
            response = agent.respond(
                context_type=decision["payload"]["context_type"],
                context_data=decision["payload"]["context_data"],
                user_question=request.user_question
            )
            return response
        else:
            # Coordinator decided on reflection, but this is a chat endpoint
            # This shouldn't happen for user-invoked, but handle gracefully
            logger.warning(f"Coordinator returned {decision['agent']} for chat endpoint")
            return {
                "response": "I don't have anything to share right now.",
                "primary_insight": None,
                "context_type": None,
                "insights": [],
                "follow_up_prompts": []
            }
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )


def _assemble_context(
    db: Session,
    user_id: int,
    context_type: str,
    context_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Assemble context data from services based on context type.
    
    This function queries services and assembles the context that the ChatAgent needs.
    The ChatAgent itself does NOT query the database.
    """
    assembled = {}
    
    if context_type == "dashboard_summary":
        # Get reading statistics
        stats = reading_service.get_reading_statistics(db, user_id)
        assembled["reading_statistics"] = stats
        
        # Get recent activity (last 30 days and last 14 days)
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.now() - timedelta(days=30)
        fourteen_days_ago = datetime.now() - timedelta(days=14)
        
        recent_sessions_30d = db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.timestamp >= thirty_days_ago
        ).all()
        
        recent_sessions_14d = db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.timestamp >= fourteen_days_ago
        ).all()
        
        assembled["recent_activity"] = {
            "sessions_count": len(recent_sessions_30d),
            "sessions_count_14d": len(recent_sessions_14d),
            "recent_moods": list(set([s.mood for s in recent_sessions_30d if s.mood])),
            "recent_locations": list(set([s.location for s in recent_sessions_30d if s.location]))
        }
        
        # Get BookAgent observations
        book_agent = BookAgent(db, user_id)
        agent_result = book_agent.run()
        assembled["agent_observations"] = agent_result.get("observations", {})
        
        # Merge any additional context_data provided
        assembled.update(context_data)
        
    elif context_type == "recommendation_explanation":
        # Get recommendation data from context_data
        recommendation_id = context_data.get("recommendation_id")
        if recommendation_id:
            rec = db.query(models.Recommendation).filter(
                models.Recommendation.id == recommendation_id,
                models.Recommendation.user_id == user_id
            ).first()
            
            if rec:
                assembled["recommendation"] = {
                    "id": rec.id,
                    "score": rec.score,
                    "reason": rec.reason,
                    "factors": rec.factors or {},
                    "book": {
                        "id": rec.book.id if rec.book else None,
                        "title": rec.book.title if rec.book else None,
                        "author": rec.book.author if rec.book else None,
                        "genre": rec.book.genre if rec.book else None,
                        "page_count": rec.book.page_count if rec.book else None
                    } if rec.book else {}
                }
        
        # Merge any additional context_data provided
        assembled.update(context_data)
        
    elif context_type == "book_reflection":
        # Get book data from context_data
        book_id = context_data.get("book_id")
        if book_id:
            book = db.query(models.Book).filter(models.Book.id == book_id).first()
            if book:
                assembled["book"] = {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "genre": book.genre,
                    "page_count": book.page_count,
                    "description": book.description
                }
                
                # Get reading sessions for this book
                sessions = db.query(models.ReadingSession).filter(
                    models.ReadingSession.user_id == user_id,
                    models.ReadingSession.book_id == book_id
                ).all()
                
                assembled["sessions"] = [
                    {
                        "id": s.id,
                        "timestamp": s.timestamp.isoformat(),
                        "pages_read": s.pages_read,
                        "duration_minutes": s.duration_minutes,
                        "mood": s.mood,
                        "location": s.location,
                        "status": s.status
                    }
                    for s in sessions
                ]
                
                # Get preference
                pref = db.query(models.BookPreference).filter(
                    models.BookPreference.user_id == user_id,
                    models.BookPreference.book_id == book_id
                ).first()
                
                if pref:
                    assembled["preference"] = {
                        "rating": pref.rating,
                        "status": pref.status,
                        "review": pref.review,
                        "favorite": pref.favorite
                    }
                
                # Get reading stats for this book
                if sessions:
                    total_pages = sum(s.pages_read or 0 for s in sessions)
                    total_duration = sum(s.duration_minutes or 0 for s in sessions)
                    assembled["reading_stats"] = {
                        "total_sessions": len(sessions),
                        "total_pages_read": total_pages,
                        "total_duration_minutes": total_duration
                    }
        
        # Merge any additional context_data provided
        assembled.update(context_data)
    
    return assembled


@router.post("/reflection", response_model=schemas.ReflectionResponse)
def get_reflection(
    request: schemas.ReflectionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Generate a reflective prompt using ReflectionAgent.
    
    This endpoint uses the agent coordinator to decide if ReflectionAgent should surface.
    User-invoked requests are always allowed.
    
    If context_data is empty, it will fetch the first relevant book from agent observations.
    If coordinator decides on silence, returns a null response (agent returns None).
    """
    try:
        context_data = request.context_data.copy() if request.context_data else {}
        
        # If context_data doesn't have book info, fetch it from agent observations
        book_id = context_data.get("book_id")
        if not context_data.get("book_title") and not book_id:
            book_agent = BookAgent(db, user_id)
            agent_result = book_agent.run()
            observations = agent_result.get("observations", {})
            
            if request.context_type == "finished_unrated":
                finished_unrated = observations.get("finished_unrated", [])
                if finished_unrated:
                    first_book = finished_unrated[0]
                    context_data["book_title"] = first_book.get("book_title", "this book")
                    context_data["book_author"] = first_book.get("book_author")
                    book_id = first_book.get("book_id")
            elif request.context_type == "paused_book":
                paused = observations.get("paused", [])
                if paused:
                    first_book = paused[0]
                    context_data["book_title"] = first_book.get("book_title", "this book")
                    context_data["book_author"] = first_book.get("book_author")
                    book_id = first_book.get("book_id")
        
        # Use coordinator to decide if ReflectionAgent should surface
        # User-invoked requests are always allowed (is_user_invoked=True)
        decision = decide_agent_output(
            db=db,
            user_id=user_id,
            book_id=book_id,
            context_type=request.context_type,
            context_data=context_data,
            is_user_invoked=True  # User explicitly invoked this endpoint
        )
        
        # If coordinator returns None, return silence (null response)
        if decision is None:
            # ReflectionAgent can return None - this is silence
            raise HTTPException(
                status_code=204,  # No Content
                detail="No reflection available at this time."
            )
        
        # Execute the agent based on coordinator decision
        if decision["agent"] == "reflection":
            response = ReflectionAgent.generate(
                context_type=decision["payload"]["context_type"],
                context_data=decision["payload"]["context_data"]
            )
            return response
        else:
            # Coordinator decided on chat, but this is a reflection endpoint
            # This shouldn't happen, but handle gracefully
            logger.warning(f"Coordinator returned {decision['agent']} for reflection endpoint")
            raise HTTPException(
                status_code=204,  # No Content
                detail="No reflection available at this time."
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating reflection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating reflection: {str(e)}"
        )

