"""
Goodreads CSV Importer

Imports historical reading data from Goodreads library export CSV.
This is a one-time + repeatable (idempotent) importer that populates:
- Book (upsert by ISBN or Title+Author)
- BookPreference (rating, review, status, favorite)
- ReadingSession (synthetic sessions for Date Read entries)

Strategy:
- Do NOT overwrite existing richer metadata
- Create lightweight synthetic sessions for historical grounding
- Agents will infer patterns from this data later
"""
import csv
import logging
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app import models
from app.schemas import BookCreate

logger = logging.getLogger(__name__)


def ensure_tag_in_list(tags: Optional[List[str]], tag: str) -> List[str]:
    """
    Ensure a tag exists in the tags list, returning updated list.
    Handles both list and None cases safely.
    """
    if tags is None:
        tags = []
    elif not isinstance(tags, list):
        tags = list(tags) if tags else []
    
    # Ensure tag is not already present (case-insensitive check)
    tag_lower = tag.lower()
    if not any(t.lower() == tag_lower for t in tags):
        tags = tags + [tag]
    
    return tags


def parse_goodreads_date(date_str: Optional[str]) -> Optional[datetime]:
    """
    Parse Goodreads date format.
    Common formats: "YYYY/MM/DD", "YYYY-MM-DD", "YYYY", or empty string.
    """
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip()
    
    # Try YYYY/MM/DD
    try:
        return datetime.strptime(date_str, "%Y/%m/%d")
    except ValueError:
        pass
    
    # Try YYYY-MM-DD
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass
    
    # Try YYYY only
    try:
        if len(date_str) == 4 and date_str.isdigit():
            return datetime(int(date_str), 1, 1)
    except (ValueError, TypeError):
        pass
    
    logger.warning(f"Could not parse date: {date_str}")
    return None


def normalize_isbn(isbn: Optional[str]) -> Optional[str]:
    """
    Normalize ISBN by removing hyphens and spaces.
    Returns None if ISBN is empty or invalid.
    """
    if not isbn:
        return None
    
    # Remove hyphens, spaces, and convert to string
    normalized = str(isbn).replace("-", "").replace(" ", "").strip()
    
    # ISBN-10 is 10 digits, ISBN-13 is 13 digits (may start with 978/979)
    if normalized and (len(normalized) == 10 or len(normalized) == 13):
        return normalized
    
    return None


def find_or_create_book(
    db: Session,
    row: Dict[str, str]
) -> models.Book:
    """
    Find or create a Book using:
    1. ISBN if present
    2. Title + Author as fallback
    
    Do NOT overwrite existing richer metadata.
    """
    # Extract fields
    title = row.get("Title", "").strip()
    author = row.get("Author", "").strip()
    isbn = normalize_isbn(row.get("ISBN") or row.get("ISBN13"))
    page_count_str = row.get("Number of Pages", "").strip()
    
    if not title:
        raise ValueError("Book title is required")
    
    # Try to find by ISBN first
    book = None
    if isbn:
        book = db.query(models.Book).filter(models.Book.isbn == isbn).first()
    
    # Fallback to Title + Author
    if not book and title and author:
        book = db.query(models.Book).filter(
            and_(
                models.Book.title == title,
                models.Book.author == author
            )
        ).first()
    
    # If found, only update missing fields (don't overwrite existing data)
    if book:
        updated = False
        
        # Only set ISBN if it's missing and we have one
        if not book.isbn and isbn:
            book.isbn = isbn
            updated = True
        
        # Only set page_count if it's missing and we have one
        if book.page_count is None and page_count_str:
            try:
                book.page_count = int(page_count_str)
                updated = True
            except (ValueError, TypeError):
                pass
        
        if updated:
            db.commit()
            db.refresh(book)
        
        return book
    
    # Create new book
    page_count = None
    if page_count_str:
        try:
            page_count = int(page_count_str)
        except (ValueError, TypeError):
            pass
    
    book_data = BookCreate(
        title=title,
        author=author if author else None,
        isbn=isbn,
        page_count=page_count
    )
    
    db_book = models.Book(**book_data.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    
    return db_book


def parse_status_from_shelves(
    exclusive_shelf: Optional[str] = None,
    shelves: Optional[str] = None
) -> Optional[str]:
    """
    Parse status from Goodreads CSV.
    Checks Exclusive Shelf first (explicit user intent), then falls back to Bookshelves.
    
    Returns: "read", "currently_reading", "want_to_read", "paused", or None
    """
    # Check Exclusive Shelf first (explicit user intent)
    if exclusive_shelf:
        exclusive_lower = exclusive_shelf.strip().lower()
        if exclusive_lower == "read":
            return "read"
        elif exclusive_lower == "currently-reading" or exclusive_lower == "currently reading":
            return "currently_reading"
        elif exclusive_lower == "to-read" or exclusive_lower == "to read":
            return "want_to_read"
        elif exclusive_lower == "paused":
            return "paused"
    
    # Fallback to Bookshelves column (less explicit)
    if not shelves:
        return None
    
    shelves_lower = shelves.lower()
    
    # Check for "read" shelf
    if "read" in shelves_lower:
        return "read"
    
    # Check for "currently-reading" or "currently reading"
    if "currently-reading" in shelves_lower or "currently reading" in shelves_lower:
        return "currently_reading"
    
    # Check for "to-read" or "to read"
    if "to-read" in shelves_lower or "to read" in shelves_lower:
        return "want_to_read"
    
    # Check for "paused" shelf
    if "paused" in shelves_lower:
        return "paused"
    
    return None


def create_or_update_preference(
    db: Session,
    book_id: int,
    user_id: int,
    row: Dict[str, str],
    has_date_read: bool = False
) -> models.BookPreference:
    """
    Create or update BookPreference from Goodreads row.
    Idempotent: updates existing preference if found.
    
    Args:
        has_date_read: If True and no status from shelves, default to "read"
    """
    # Check if preference already exists
    existing = db.query(models.BookPreference).filter(
        and_(
            models.BookPreference.user_id == user_id,
            models.BookPreference.book_id == book_id
        )
    ).first()
    
    # Extract data
    rating_str = row.get("My Rating", "").strip()
    review = row.get("My Review", "").strip() or None
    exclusive_shelf = row.get("Exclusive Shelf", "").strip()
    shelves = row.get("Bookshelves", "").strip()
    
    # Parse rating (1-5)
    rating = None
    if rating_str:
        try:
            rating_int = int(rating_str)
            if 1 <= rating_int <= 5:
                rating = rating_int
        except (ValueError, TypeError):
            pass
    
    # Parse status from Exclusive Shelf (preferred) or Bookshelves (fallback)
    status = parse_status_from_shelves(
        exclusive_shelf=exclusive_shelf if exclusive_shelf else None,
        shelves=shelves if shelves else None
    )
    
    # If we have a Date Read, the book was read - override "want_to_read" to "read"
    # This handles cases where Goodreads has both "to-read" status and a Date Read
    if has_date_read and status == "want_to_read":
        status = "read"
    
    # If no status from shelves but we have a Date Read, infer "read"
    # BUT: Do NOT override explicit "paused" status
    if not status and has_date_read:
        status = "read"
    
    # Determine favorite (rating >= 4)
    favorite = rating is not None and rating >= 4
    
    # Prepare tags list
    tags = existing.tags if existing and existing.tags else []
    
    # Add shelf:paused tag if status is paused
    if status == "paused":
        tags = ensure_tag_in_list(tags, "shelf:paused")
    
    if existing:
        # Update existing preference
        # Only update if we have new data (don't overwrite with empty)
        # IMPORTANT: Do NOT overwrite existing non-null status if it's already set
        # (unless we have an explicit status from CSV)
        if rating is not None:
            existing.rating = rating
        if review:
            existing.review = review
        # Only update status if:
        # 1. We have a status from CSV, AND
        # 2. Either existing status is None, OR we're setting paused (explicit intent)
        if status:
            if existing.status is None or status == "paused":
                existing.status = status
        if tags:
            existing.tags = tags
        existing.favorite = favorite
        
        db.commit()
        db.refresh(existing)
        return existing
    
    # Prepare tags for new preference
    new_tags = []
    if status == "paused":
        new_tags = ["shelf:paused"]
    
    # Create new preference
    preference = models.BookPreference(
        user_id=user_id,
        book_id=book_id,
        rating=rating,
        review=review,
        status=status,  # May be None if no status inferred
        favorite=favorite,
        tags=new_tags if new_tags else None
    )
    
    db.add(preference)
    db.commit()
    db.refresh(preference)
    
    return preference


def create_synthetic_session(
    db: Session,
    book_id: int,
    user_id: int,
    date_read: Optional[datetime]
) -> Optional[models.ReadingSession]:
    """
    Create a synthetic ReadingSession for historical grounding.
    Only creates if date_read exists and session doesn't already exist.
    Idempotent: checks for existing session with same timestamp.
    """
    if not date_read:
        return None
    
    # Check if session already exists (idempotency)
    existing = db.query(models.ReadingSession).filter(
        and_(
            models.ReadingSession.user_id == user_id,
            models.ReadingSession.book_id == book_id,
            models.ReadingSession.action == "returned",
            models.ReadingSession.timestamp == date_read,
            models.ReadingSession.notes == "Imported from Goodreads"
        )
    ).first()
    
    if existing:
        return existing
    
    # Create synthetic session
    session = models.ReadingSession(
        user_id=user_id,
        book_id=book_id,
        action="returned",
        timestamp=date_read,
        notes="Imported from Goodreads"
    )
    
    db.add(session)
    db.commit()
    db.refresh(session)
    
    return session


def import_goodreads_csv(
    csv_path: str,
    user_id: int,
    db: Session
) -> Dict[str, int]:
    """
    Import Goodreads library export CSV.
    
    Args:
        csv_path: Path to Goodreads CSV file
        user_id: User ID to associate imported data with
        user_id: Database session
    
    Returns:
        Dictionary with stats:
        - books_created: Number of new books created
        - books_updated: Number of existing books updated
        - preferences_created: Number of new preferences created
        - preferences_updated: Number of existing preferences updated
        - sessions_created: Number of synthetic sessions created
    
    This function is idempotent and safe to run multiple times.
    """
    stats = {
        "books_created": 0,
        "books_updated": 0,
        "preferences_created": 0,
        "preferences_updated": 0,
        "sessions_created": 0,
        "rows_processed": 0,
        "rows_skipped": 0
    }
    
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    logger.info(f"Starting Goodreads import for user {user_id}")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Try to detect delimiter (Goodreads uses comma, but handle edge cases)
            sample = f.read(1024)
            f.seek(0)
            
            # Goodreads CSV typically uses comma
            delimiter = ','
            if '\t' in sample and sample.count('\t') > sample.count(','):
                delimiter = '\t'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            # Track books and preferences we've processed in this run
            processed_book_ids = set()
            processed_preference_ids = set()
            
            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                try:
                    stats["rows_processed"] += 1
                    
                    # Skip rows without title
                    if not row.get("Title", "").strip():
                        stats["rows_skipped"] += 1
                        logger.warning(f"Row {row_num}: Skipping row without title")
                        continue
                    
                    # Check if book already exists (for accurate create/update counting)
                    isbn = normalize_isbn(row.get("ISBN") or row.get("ISBN13"))
                    title = row.get("Title", "").strip()
                    author = row.get("Author", "").strip()
                    
                    existing_book = None
                    if isbn:
                        existing_book = db.query(models.Book).filter(models.Book.isbn == isbn).first()
                    if not existing_book and title and author:
                        existing_book = db.query(models.Book).filter(
                            and_(
                                models.Book.title == title,
                                models.Book.author == author
                            )
                        ).first()
                    
                    # Find or create book
                    book = find_or_create_book(db, row)
                    
                    # Track book create/update
                    if book.id not in processed_book_ids:
                        if existing_book:
                            stats["books_updated"] += 1
                        else:
                            stats["books_created"] += 1
                        processed_book_ids.add(book.id)
                    
                    # Check if preference already exists
                    existing_pref = db.query(models.BookPreference).filter(
                        and_(
                            models.BookPreference.user_id == user_id,
                            models.BookPreference.book_id == book.id
                        )
                    ).first()
                    
                    # Check if we have a Date Read (for status inference)
                    date_read_str = row.get("Date Read", "").strip()
                    date_read = None
                    has_date_read = False
                    if date_read_str:
                        date_read = parse_goodreads_date(date_read_str)
                        has_date_read = date_read is not None
                    
                    # Create or update preference
                    preference = create_or_update_preference(
                        db, book.id, user_id, row, has_date_read=has_date_read
                    )
                    
                    # Track preference create/update
                    if preference.id not in processed_preference_ids:
                        if existing_pref:
                            stats["preferences_updated"] += 1
                        else:
                            stats["preferences_created"] += 1
                        processed_preference_ids.add(preference.id)
                    
                    # Create synthetic session if Date Read exists
                    if date_read:
                        session = create_synthetic_session(db, book.id, user_id, date_read)
                        if session:
                            stats["sessions_created"] += 1
                    
                except Exception as e:
                    stats["rows_skipped"] += 1
                    logger.error(f"Row {row_num}: Error processing row: {e}", exc_info=True)
                    continue
            
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}", exc_info=True)
        raise
    
    # Recalculate book stats more accurately
    # Count books that were created in this session vs updated
    # Since we can't perfectly track this without additional state,
    # we'll use a simpler metric: total books processed
    # For now, let's just report what we can track accurately
    
    logger.info(f"Import complete. Stats: {stats}")
    return stats

