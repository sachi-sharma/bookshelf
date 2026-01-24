from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app import schemas
from app.services import book_service
from app.core.exceptions import NotFoundError, ValidationError
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/books", response_model=List[schemas.BookResponse])
def search_books(
    q: Optional[str] = Query(None, description="Search query"),
    author: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Search for books"""
    books = book_service.search_books(db, q, author, genre, limit, offset)
    return books


@router.get("/books/bulk", response_model=List[schemas.BookResponse])
def get_books_by_ids(
    ids: str = Query(..., description="Comma-separated list of book IDs"),
    db: Session = Depends(get_db)
):
    """Get multiple books by their IDs (for efficient bulk fetching)"""
    try:
        book_ids = [int(id.strip()) for id in ids.split(',') if id.strip()]
    except ValueError:
        raise ValidationError("Invalid book IDs format. Expected comma-separated integers.")
    
    if not book_ids:
        return []
    
    books = book_service.get_books_by_ids(db, book_ids)
    return books


@router.get("/books/{book_id}", response_model=schemas.BookResponse)
def get_book(book_id: int, db: Session = Depends(get_db)):
    """Get a book by ID"""
    book = book_service.get_book(db, book_id)
    if not book:
        raise NotFoundError("Book", f"id={book_id}")
    return book


@router.post("/books", response_model=schemas.BookResponse, status_code=201)
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db)):
    """Create a new book"""
    # Check if book with same ISBN exists
    if book.isbn:
        existing = book_service.get_book_by_isbn(db, book.isbn)
        if existing:
            return existing
    
    return book_service.create_book(db, book)

