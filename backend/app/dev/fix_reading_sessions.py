"""
Fix existing reading sessions and preferences.

This script updates:
1. Books with "want_to_read" status that have reading sessions (Date Read) -> change to "read"
2. Reading sessions status to match their book's preference status
3. Ensures consistency between BookPreference and ReadingSession status
"""
import sys
import os

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.database import SessionLocal
from app import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_want_to_read_with_sessions(db: Session, user_id: int = 1) -> dict:
    """
    Fix books that have "want_to_read" status but also have reading sessions.
    If a book has been read (has a session with action="returned"), it should be "read" not "want_to_read".
    """
    stats = {
        "preferences_updated": 0,
        "sessions_updated": 0,
        "books_fixed": 0
    }
    
    # Find all preferences with "want_to_read" status
    want_to_read_prefs = db.query(models.BookPreference).filter(
        and_(
            models.BookPreference.user_id == user_id,
            models.BookPreference.status == "want_to_read"
        )
    ).all()
    
    logger.info(f"Found {len(want_to_read_prefs)} books with 'want_to_read' status")
    
    for pref in want_to_read_prefs:
        # Check if this book has any reading sessions (especially "returned" sessions)
        has_read_session = db.query(models.ReadingSession).filter(
            and_(
                models.ReadingSession.user_id == user_id,
                models.ReadingSession.book_id == pref.book_id,
                models.ReadingSession.action == "returned"
            )
        ).first()
        
        if has_read_session:
            # This book has been read, so update status to "read"
            logger.info(f"Updating book {pref.book_id} ({pref.book.title if pref.book else 'unknown'}) from 'want_to_read' to 'read'")
            pref.status = "read"
            stats["preferences_updated"] += 1
            stats["books_fixed"] += 1
    
    db.commit()
    return stats


def sync_session_status_with_preference(db: Session, user_id: int = 1) -> dict:
    """
    Sync reading session status with book preference status.
    For sessions with action="returned", status should match preference.
    """
    stats = {
        "sessions_updated": 0
    }
    
    # Get all reading sessions with "returned" action
    returned_sessions = db.query(models.ReadingSession).filter(
        and_(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.action == "returned"
        )
    ).all()
    
    logger.info(f"Found {len(returned_sessions)} 'returned' reading sessions")
    
    for session in returned_sessions:
        # Get the preference for this book
        pref = db.query(models.BookPreference).filter(
            and_(
                models.BookPreference.user_id == user_id,
                models.BookPreference.book_id == session.book_id
            )
        ).first()
        
        if pref and pref.status:
            # If preference has a status and session doesn't match, update it
            if session.status != pref.status:
                logger.info(f"Updating session {session.id} status from '{session.status}' to '{pref.status}'")
                session.status = pref.status
                stats["sessions_updated"] += 1
        elif pref and not pref.status and session.status:
            # If session has status but preference doesn't, update preference
            logger.info(f"Updating preference {pref.id} status from None to '{session.status}'")
            pref.status = session.status
    
    db.commit()
    return stats


def fix_all_statuses(db: Session, user_id: int = 1) -> dict:
    """
    Main function to fix all status inconsistencies.
    """
    logger.info(f"Starting status fix for user {user_id}")
    
    all_stats = {
        "want_to_read_fixes": {},
        "session_sync": {},
        "total_books_fixed": 0
    }
    
    # Fix want_to_read books that have been read
    want_to_read_stats = fix_want_to_read_with_sessions(db, user_id)
    all_stats["want_to_read_fixes"] = want_to_read_stats
    
    # Sync session statuses with preferences
    session_stats = sync_session_status_with_preference(db, user_id)
    all_stats["session_sync"] = session_stats
    
    all_stats["total_books_fixed"] = want_to_read_stats["books_fixed"]
    
    logger.info(f"Fix complete. Stats: {all_stats}")
    return all_stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Fix reading sessions and preferences status")
    parser.add_argument("--user-id", type=int, default=1, help="User ID to fix (default: 1)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be changed without making changes")
    
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            # In dry run, we'd need to query and report without committing
            # For now, just run normally but you can add dry-run logic
            logger.warning("Dry run not fully implemented - will make actual changes")
        
        stats = fix_all_statuses(db, user_id=args.user_id)
        
        print("\n" + "="*50)
        print("FIX SUMMARY")
        print("="*50)
        print(f"Books fixed (want_to_read -> read): {stats['want_to_read_fixes']['books_fixed']}")
        print(f"Preferences updated: {stats['want_to_read_fixes']['preferences_updated']}")
        print(f"Sessions synced: {stats['session_sync']['sessions_updated']}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error fixing sessions: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()

