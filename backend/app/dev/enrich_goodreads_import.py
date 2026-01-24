#!/usr/bin/env python3
"""
Goodreads Import Enrichment Script

Non-destructive enrichment pass that adds metadata to existing imported records:
- Page counts (only if NULL)
- source:goodreads tag
- Semantic tags from shelves (favorites, re-read, dnf, abandoned)
- Publication year (only if NULL)
- Fixes "want_to_read" status for books that have been read (have Date Read)

Safe to run multiple times - only updates NULL fields and adds missing tags.
"""
import argparse
import sys
import os
import csv
import logging
from typing import Dict, Optional, List, Set
from datetime import datetime

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal
from app import models
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def normalize_isbn(isbn: Optional[str]) -> Optional[str]:
    """Normalize ISBN by removing hyphens and spaces."""
    if not isbn:
        return None
    
    normalized = str(isbn).replace("-", "").replace(" ", "").strip()
    
    if normalized and (len(normalized) == 10 or len(normalized) == 13):
        return normalized
    
    return None


def find_existing_book(
    db: Session,
    row: Dict[str, str]
) -> Optional[models.Book]:
    """
    Find existing Book using:
    1. ISBN if present
    2. Title + Author as fallback
    
    Returns None if book doesn't exist (enrichment only, no creation).
    """
    title = row.get("Title", "").strip()
    author = row.get("Author", "").strip()
    isbn = normalize_isbn(row.get("ISBN") or row.get("ISBN13"))
    
    if not title:
        return None
    
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
    
    return book


def ensure_tag_in_list(tags: Optional[List[str]], tag: str) -> List[str]:
    """
    Ensure a tag exists in the tags list, returning updated list.
    Handles both list and None cases safely.
    """
    if tags is None:
        tags = []
    elif not isinstance(tags, list):
        # Handle case where tags might be stored as something else
        tags = list(tags) if tags else []
    
    # Ensure tag is not already present (case-insensitive check)
    tag_lower = tag.lower()
    if not any(t.lower() == tag_lower for t in tags):
        tags = tags + [tag]
    
    return tags


def parse_status_from_exclusive_shelf(exclusive_shelf: Optional[str]) -> Optional[str]:
    """
    Parse status from Goodreads Exclusive Shelf column.
    Returns: "read", "currently_reading", "want_to_read", "paused", or None
    """
    if not exclusive_shelf:
        return None
    
    exclusive_lower = exclusive_shelf.strip().lower()
    if exclusive_lower == "read":
        return "read"
    elif exclusive_lower == "currently-reading" or exclusive_lower == "currently reading":
        return "currently_reading"
    elif exclusive_lower == "to-read" or exclusive_lower == "to read":
        return "want_to_read"
    elif exclusive_lower == "paused":
        return "paused"
    
    return None


def parse_semantic_tags_from_shelves(shelves: Optional[str]) -> Set[str]:
    """
    Parse semantic tags from Goodreads bookshelves.
    Only extracts: favorites, re-read, dnf, abandoned
    """
    semantic_tags = set()
    
    if not shelves:
        return semantic_tags
    
    shelves_lower = shelves.lower()
    
    # Check for semantic tags (case-insensitive)
    if "favorites" in shelves_lower or "favourite" in shelves_lower:
        semantic_tags.add("favorites")
    
    if "re-read" in shelves_lower or "reread" in shelves_lower:
        semantic_tags.add("re-read")
    
    if "dnf" in shelves_lower or "did not finish" in shelves_lower:
        semantic_tags.add("dnf")
    
    if "abandoned" in shelves_lower:
        semantic_tags.add("abandoned")
    
    return semantic_tags


def parse_publication_year(year_str: Optional[str]) -> Optional[datetime]:
    """
    Parse publication year from Goodreads CSV.
    Returns datetime set to January 1st of that year, or None if invalid.
    """
    if not year_str or not year_str.strip():
        return None
    
    year_str = year_str.strip()
    
    # Try to extract year (4 digits)
    try:
        if len(year_str) == 4 and year_str.isdigit():
            year = int(year_str)
            if 1000 <= year <= 2100:  # Reasonable year range
                return datetime(year, 1, 1)
    except (ValueError, TypeError):
        pass
    
    # Try to parse as date and extract year
    try:
        # Try YYYY/MM/DD or YYYY-MM-DD
        date_obj = datetime.strptime(year_str, "%Y/%m/%d")
        return datetime(date_obj.year, 1, 1)
    except ValueError:
        try:
            date_obj = datetime.strptime(year_str, "%Y-%m-%d")
            return datetime(date_obj.year, 1, 1)
        except ValueError:
            pass
    
    return None


def enrich_goodreads_import(
    csv_path: str,
    user_id: int,
    db: Session
) -> Dict[str, int]:
    """
    Enrich existing Goodreads-imported records with additional metadata.
    
    Returns statistics about what was enriched.
    """
    stats = {
        "books_enriched_with_pages": 0,
        "books_tagged_goodreads": 0,
        "preferences_tagged": 0,
        "preferences_status_updated": 0,
        "preferences_set_paused": 0,
        "preferences_fixed_want_to_read": 0,
        "publication_years_added": 0,
        "rows_processed": 0,
        "books_not_found": 0,
    }
    
    # Verify user exists
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    logger.info(f"Starting Goodreads enrichment for user {user_id}")
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Try to detect delimiter
            sample = f.read(1024)
            f.seek(0)
            
            delimiter = ','
            if '\t' in sample and sample.count('\t') > sample.count(','):
                delimiter = '\t'
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row_num, row in enumerate(reader, start=2):
                try:
                    stats["rows_processed"] += 1
                    
                    # Skip rows without title
                    if not row.get("Title", "").strip():
                        continue
                    
                    # Find existing book (do NOT create)
                    book = find_existing_book(db, row)
                    
                    if not book:
                        stats["books_not_found"] += 1
                        continue
                    
                    book_updated = False
                    
                    # 1. Enrich page count (only if NULL)
                    page_count_str = row.get("Number of Pages", "").strip()
                    if page_count_str and book.page_count is None:
                        try:
                            book.page_count = int(page_count_str)
                            book_updated = True
                            stats["books_enriched_with_pages"] += 1
                        except (ValueError, TypeError):
                            pass
                    
                    # 2. Add source:goodreads tag
                    current_tags = book.tags if book.tags else []
                    if "source:goodreads" not in current_tags:
                        book.tags = ensure_tag_in_list(current_tags, "source:goodreads")
                        book_updated = True
                        stats["books_tagged_goodreads"] += 1
                    
                    # 3. Add publication year (only if NULL)
                    publication_year_str = row.get("Original Publication Year", "").strip()
                    if publication_year_str and book.publication_date is None:
                        pub_year = parse_publication_year(publication_year_str)
                        if pub_year:
                            book.publication_date = pub_year
                            book_updated = True
                            stats["publication_years_added"] += 1
                    
                    # Commit book changes
                    if book_updated:
                        db.commit()
                        db.refresh(book)
                    
                    # 4. Enrich BookPreference: status and tags from shelves
                    # Find preference for this book and user
                    preference = db.query(models.BookPreference).filter(
                        and_(
                            models.BookPreference.user_id == user_id,
                            models.BookPreference.book_id == book.id
                        )
                    ).first()
                    
                    if preference:
                        pref_updated = False
                        current_pref_tags = preference.tags if preference.tags else []
                        
                        # Get status from Exclusive Shelf (the authoritative source)
                        exclusive_shelf = row.get("Exclusive Shelf", "").strip()
                        exclusive_shelf_status = parse_status_from_exclusive_shelf(exclusive_shelf)
                        
                        # Check Date Read
                        date_read_str = row.get("Date Read", "").strip()
                        has_date_read = bool(date_read_str)
                        
                        # If Exclusive Shelf has a status, use it (it's the authoritative source)
                        # But respect Date Read: if there's a Date Read, "to-read" should become "read"
                        if exclusive_shelf_status:
                            # If Exclusive Shelf says "to-read" but there's a Date Read, it should be "read"
                            if exclusive_shelf_status == "want_to_read" and has_date_read:
                                # Check if there's actually a reading session for this book
                                has_read_session = db.query(models.ReadingSession).filter(
                                    and_(
                                        models.ReadingSession.user_id == user_id,
                                        models.ReadingSession.book_id == book.id,
                                        models.ReadingSession.action == "returned"
                                    )
                                ).first()
                                
                                if has_read_session:
                                    logger.info(f"Fixing book {book.id} ({book.title}): Exclusive Shelf says 'to-read' but has Date Read -> 'read'")
                                    exclusive_shelf_status = "read"
                                    stats.setdefault("preferences_fixed_want_to_read", 0)
                                    stats["preferences_fixed_want_to_read"] += 1
                            
                            # Update status from Exclusive Shelf if:
                            # 1. Current status is None, OR
                            # 2. Current status doesn't match Exclusive Shelf (Exclusive Shelf is authoritative)
                            if preference.status != exclusive_shelf_status:
                                logger.info(f"Updating book {book.id} ({book.title}) status: '{preference.status}' -> '{exclusive_shelf_status}' (from Exclusive Shelf)")
                                preference.status = exclusive_shelf_status
                                pref_updated = True
                                stats["preferences_status_updated"] += 1
                                
                                if exclusive_shelf_status == "paused":
                                    stats["preferences_set_paused"] += 1
                        else:
                            # No Exclusive Shelf status, but check if we need to fix want_to_read with Date Read
                            if preference.status == "want_to_read" and has_date_read:
                                has_read_session = db.query(models.ReadingSession).filter(
                                    and_(
                                        models.ReadingSession.user_id == user_id,
                                        models.ReadingSession.book_id == book.id,
                                        models.ReadingSession.action == "returned"
                                    )
                                ).first()
                                
                                if has_read_session:
                                    logger.info(f"Fixing book {book.id} ({book.title}): want_to_read -> read (has Date Read)")
                                    preference.status = "read"
                                    pref_updated = True
                                    stats.setdefault("preferences_fixed_want_to_read", 0)
                                    stats["preferences_fixed_want_to_read"] += 1
                        
                        # Add shelf:paused tag if status is paused
                        if preference.status == "paused":
                            if "shelf:paused" not in current_pref_tags:
                                current_pref_tags = ensure_tag_in_list(current_pref_tags, "shelf:paused")
                                pref_updated = True
                        
                        # Add semantic tags from Bookshelves
                        shelves = row.get("Bookshelves", "").strip()
                        semantic_tags = parse_semantic_tags_from_shelves(shelves)
                        
                        if semantic_tags:
                            for tag in semantic_tags:
                                if tag not in current_pref_tags:
                                    current_pref_tags = ensure_tag_in_list(current_pref_tags, tag)
                                    pref_updated = True
                        
                        if pref_updated:
                            preference.tags = current_pref_tags
                            db.commit()
                            db.refresh(preference)
                            stats["preferences_tagged"] += 1
                    
                except Exception as e:
                    logger.error(f"Row {row_num}: Error processing row: {e}", exc_info=True)
                    continue
            
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found: {csv_path}")
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}", exc_info=True)
        raise
    
    logger.info(f"Enrichment complete. Stats: {stats}")
    return stats


def main():
    parser = argparse.ArgumentParser(
        description='Enrich existing Goodreads-imported records with additional metadata'
    )
    parser.add_argument(
        '--csv-path',
        type=str,
        default='/mnt/data/goodreads_library_export.csv',
        help='Path to Goodreads CSV file (default: /mnt/data/goodreads_library_export.csv)'
    )
    parser.add_argument(
        '--user-id',
        type=int,
        default=1,
        help='User ID to enrich data for (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    if not os.path.exists(args.csv_path):
        logger.error(f"CSV file not found: {args.csv_path}")
        logger.info("Please provide a valid path to your Goodreads library export CSV")
        sys.exit(1)
    
    logger.info(f"Starting Goodreads enrichment...")
    logger.info(f"CSV path: {args.csv_path}")
    logger.info(f"User ID: {args.user_id}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Run enrichment
        stats = enrich_goodreads_import(
            csv_path=args.csv_path,
            user_id=args.user_id,
            db=db
        )
        
        # Print summary
        print("\n" + "="*60)
        print("Goodreads Enrichment Complete")
        print("="*60)
        print(f"Rows processed: {stats['rows_processed']}")
        print(f"Books not found (skipped): {stats['books_not_found']}")
        print(f"\nEnrichment Results:")
        print(f"  Books updated with page count: {stats['books_enriched_with_pages']}")
        print(f"  Books tagged source:goodreads: {stats['books_tagged_goodreads']}")
        print(f"  Preferences tagged (favorites/re-read/etc): {stats['preferences_tagged']}")
        if stats.get('preferences_status_updated', 0) > 0:
            print(f"  Preferences status updated from Exclusive Shelf: {stats['preferences_status_updated']}")
        if stats.get('preferences_set_paused', 0) > 0:
            print(f"  Preferences set to paused: {stats['preferences_set_paused']}")
        if stats.get('preferences_fixed_want_to_read', 0) > 0:
            print(f"  Preferences fixed (want_to_read -> read): {stats['preferences_fixed_want_to_read']}")
        print(f"  Publication years added: {stats['publication_years_added']}")
        print("="*60)
        print("\nEnrichment complete! Your Goodreads data has been enriched.")
        print("You can safely run this script again - it's idempotent.")
        
    except Exception as e:
        logger.error(f"Enrichment failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()

