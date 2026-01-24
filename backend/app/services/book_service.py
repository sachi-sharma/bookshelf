from sqlalchemy.orm import Session
from sqlalchemy import or_
from app import models, schemas
from typing import Optional, List


def get_book(db: Session, book_id: int) -> Optional[models.Book]:
    """Get a book by ID"""
    return db.query(models.Book).filter(models.Book.id == book_id).first()


def get_books_by_ids(db: Session, book_ids: List[int]) -> List[models.Book]:
    """Get multiple books by their IDs"""
    if not book_ids:
        return []
    return db.query(models.Book).filter(models.Book.id.in_(book_ids)).all()


def get_book_by_isbn(db: Session, isbn: str) -> Optional[models.Book]:
    """Get a book by ISBN"""
    return db.query(models.Book).filter(models.Book.isbn == isbn).first()


def search_books(
    db: Session,
    query: Optional[str] = None,
    author: Optional[str] = None,
    genre: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> List[models.Book]:
    """Search books by title, author, or genre"""
    q = db.query(models.Book)
    
    if query:
        q = q.filter(
            or_(
                models.Book.title.ilike(f"%{query}%"),
                models.Book.author.ilike(f"%{query}%")
            )
        )
    
    if author:
        q = q.filter(models.Book.author.ilike(f"%{author}%"))
    
    if genre:
        q = q.filter(models.Book.genre == genre)
    
    return q.offset(offset).limit(limit).all()


def create_book(db: Session, book: schemas.BookCreate) -> models.Book:
    """Create a new book"""
    from app.core.database import transaction
    
    with transaction(db):
        db_book = models.Book(**book.dict())
        db.add(db_book)
        # Transaction context manager will commit automatically
    db.refresh(db_book)
    return db_book


def update_book(db: Session, book_id: int, book_update: schemas.BookCreate) -> Optional[models.Book]:
    """Update a book"""
    from app.core.database import transaction
    
    db_book = get_book(db, book_id)
    if not db_book:
        return None
    
    with transaction(db):
        for key, value in book_update.dict(exclude_unset=True).items():
            setattr(db_book, key, value)
        db.refresh(db_book)
    return db_book

