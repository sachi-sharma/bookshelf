"""
Agent Coordinator

A lightweight orchestration layer that governs when agents are allowed to surface output.

Core Rule: At most ONE agent output may surface per book at a time.
If no output is appropriate, return nothing.

Philosophy: Intelligence is not speaking often. Intelligence is knowing when to stay quiet.
Silence is success.
"""
import logging
from typing import Dict, Any, Optional, Literal
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Cooldown periods (in days)
CHAT_AGENT_COOLDOWN_DAYS = 7  # User-invoked ChatAgent suppresses others for 7 days
REFLECTION_COOLDOWN_DAYS = 7  # No reflection shown for same book in last 7 days


def decide_agent_output(
    db: Session,
    user_id: int,
    book_id: Optional[int],
    context_type: str,
    context_data: Dict[str, Any],
    is_user_invoked: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Decide which agent (if any) is allowed to surface output.
    
    This function does NOT generate content - it only selects which agent (if any) is allowed.
    
    Priority order:
    1. User-invoked ChatAgent (always allowed, suppresses all others for X days)
    2. Decision state pending (future-proof, suppresses ReflectionAgent)
    3. ReflectionAgent (only if conditions met)
    4. Silence (if none apply)
    
    Args:
        db: Database session
        user_id: User ID
        book_id: Book ID (optional, None for dashboard-level contexts)
        context_type: Context type (e.g., "book_reflection", "dashboard_summary")
        context_data: Context data
        is_user_invoked: Whether this is a user-initiated request (always allowed)
        
    Returns:
        {
            "agent": "reflection" | "chat" | null,
            "payload": {...}
        } or None if silence
    """
    # Priority 1: User-invoked requests
    # Always allowed - user explicitly requested it
    # Determine which agent based on context_type
    if is_user_invoked:
        # For reflection contexts, return reflection agent
        if context_type in ["finished_unrated", "paused_book", "re_read"]:
            return {
                "agent": "reflection",
                "payload": {
                    "context_type": context_type,
                    "context_data": context_data
                }
            }
        # For other contexts (chat, dashboard_summary, etc.), return chat agent
        else:
            return {
                "agent": "chat",
                "payload": {
                    "context_type": context_type,
                    "context_data": context_data
                }
            }
    
    # For book-specific contexts, check cooldowns
    if book_id:
        # Check if ChatAgent was recently invoked for this book (suppresses ReflectionAgent)
        if _has_recent_chat_interaction(db, user_id, book_id, CHAT_AGENT_COOLDOWN_DAYS):
            logger.debug(f"ChatAgent recently invoked for book {book_id}, suppressing ReflectionAgent")
            return None  # Silence
        
        # Priority 2: Decision state pending (future-proof)
        # This would check for pending decisions that suppress ReflectionAgent
        # For now, we'll skip this as it's future-proof
        
        # Priority 3: ReflectionAgent
        # Allowed only if:
        # - No reflection shown for this book in last X days
        # - No ChatAgent interaction recently (already checked above)
        # - Book state unchanged since last reflection
        if context_type in ["finished_unrated", "paused_book", "re_read"]:
            if _should_show_reflection(db, user_id, book_id, context_type, context_data):
                return {
                    "agent": "reflection",
                    "payload": {
                        "context_type": context_type,
                        "context_data": context_data
                    }
                }
    
    # Priority 4: Silence
    # If none of the above apply, return nothing
    return None


def _has_recent_chat_interaction(
    db: Session,
    user_id: int,
    book_id: int,
    cooldown_days: int
) -> bool:
    """
    Check if there was a recent ChatAgent interaction for this book.
    
    We infer this from:
    - Recent reading sessions (user activity suggests they may have interacted)
    - Recent preference updates (user may have interacted via chat)
    
    This is coarse-grained - we don't persist chat interaction history.
    """
    from app import models
    from datetime import datetime, timedelta
    
    cooldown_date = datetime.now() - timedelta(days=cooldown_days)
    
    # Check for recent sessions for this book
    recent_sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.book_id == book_id,
        models.ReadingSession.timestamp >= cooldown_date
    ).count()
    
    # Check for recent preference updates for this book
    # Note: updated_at is only set when record is updated, not on creation
    # So we check both updated_at and created_at
    from sqlalchemy import or_
    recent_prefs = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.book_id == book_id
    ).filter(
        or_(
            models.BookPreference.updated_at >= cooldown_date,
            models.BookPreference.created_at >= cooldown_date
        )
    ).count()
    
    # If there's recent activity, assume potential chat interaction
    # This is conservative - we err on the side of silence
    return recent_sessions > 0 or recent_prefs > 0


def _should_show_reflection(
    db: Session,
    user_id: int,
    book_id: int,
    context_type: str,
    context_data: Dict[str, Any]
) -> bool:
    """
    Determine if ReflectionAgent should be allowed to surface.
    
    Conditions:
    1. No reflection shown for this book in last X days
    2. Book state unchanged since last potential reflection
    3. Context is appropriate for reflection
    """
    from app import models
    from datetime import datetime, timedelta
    
    cooldown_date = datetime.now() - timedelta(days=REFLECTION_COOLDOWN_DAYS)
    
    # Check 1: No recent reflection opportunity
    # We infer this from:
    # - No recent status changes that would trigger reflection
    # - No recent sessions that would suggest reflection was already shown
    
    # Get the most recent session for this book
    last_session = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id,
        models.ReadingSession.book_id == book_id
    ).order_by(models.ReadingSession.timestamp.desc()).first()
    
    # Get the preference
    preference = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.book_id == book_id
    ).first()
    
    # If there's a very recent session (within cooldown), don't show reflection
    # This suggests the book state is actively changing
    if last_session and last_session.timestamp >= cooldown_date:
        # Check if status changed recently
        if preference and preference.updated_at:
            if preference.updated_at >= cooldown_date:
                # Status changed recently, don't show reflection yet
                return False
    
    # Check 2: Book state unchanged since last reflection opportunity
    # If status hasn't changed in a while, it's safe to show reflection
    if preference:
        # For finished_unrated, check if book was finished recently
        if context_type == "finished_unrated":
            if preference.status == "read" and preference.updated_at:
                # If finished more than cooldown days ago, allow reflection
                if preference.updated_at < cooldown_date:
                    return True
                else:
                    # Finished recently, wait
                    return False
        
        # For paused_book, check if paused recently
        elif context_type == "paused_book":
            if preference.status == "paused" and preference.updated_at:
                # If paused more than cooldown days ago, allow reflection
                if preference.updated_at < cooldown_date:
                    return True
                else:
                    # Paused recently, wait
                    return False
    
    # Check 3: Context is appropriate
    # If we have the required context data, allow reflection
    if context_type in ["finished_unrated", "paused_book", "re_read"]:
        if context_data.get("book_title"):
            return True
    
    # Default: don't show reflection if conditions aren't met
    return False

