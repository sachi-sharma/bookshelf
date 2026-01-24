#!/usr/bin/env python3
"""
Script to add a book for a user
Usage: python add_book.py "Book Title" "Author Name" [--username sachi] [--status want_to_read] [--rating 5]
"""
import sys
import argparse
import bcrypt
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models, schemas
from app.services import book_service

def get_or_create_user(db: Session, username: str, email: str = None) -> models.User:
    """Get existing user or create a new one"""
    user = db.query(models.User).filter(models.User.username == username).first()
    
    if not user:
        if not email:
            email = f"{username}@example.com"
        
        # Create user with default password
        hashed_password = bcrypt.hashpw("password123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = models.User(
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created new user: {username} (ID: {user.id})")
    else:
        print(f"Found existing user: {username} (ID: {user.id})")
    
    return user

def add_book_for_user(
    title: str,
    author: str = None,
    username: str = "sachi",
    status: str = None,
    rating: int = None,
    genre: str = None,
    isbn: str = None,
    publisher: str = None,
    page_count: int = None,
    description: str = None
):
    """Add a book and optionally associate it with a user"""
    db: Session = SessionLocal()
    
    try:
        # Get or create user
        user = get_or_create_user(db, username)
        
        # Check if book already exists (by ISBN or title+author)
        book = None
        if isbn:
            book = book_service.get_book_by_isbn(db, isbn)
        
        if not book and title and author:
            # Try to find by title and author
            book = db.query(models.Book).filter(
                models.Book.title.ilike(f"%{title}%"),
                models.Book.author.ilike(f"%{author}%")
            ).first()
        
        # Create book if it doesn't exist
        if not book:
            book_data = schemas.BookCreate(
                title=title,
                author=author,
                genre=genre,
                isbn=isbn,
                publisher=publisher,
                page_count=page_count,
                description=description
            )
            book = book_service.create_book(db, book_data)
            print(f"\n✓ Created new book: '{book.title}' by {book.author or 'Unknown'} (ID: {book.id})")
        else:
            print(f"\n✓ Found existing book: '{book.title}' by {book.author or 'Unknown'} (ID: {book.id})")
        
        # Create book preference to associate with user
        if status or rating is not None:
            # Check if preference already exists
            existing_pref = db.query(models.BookPreference).filter(
                models.BookPreference.user_id == user.id,
                models.BookPreference.book_id == book.id
            ).first()
            
            if existing_pref:
                # Update existing preference
                if status:
                    existing_pref.status = status
                if rating is not None:
                    existing_pref.rating = rating
                db.commit()
                db.refresh(existing_pref)
                print(f"✓ Updated book preference for user '{username}'")
            else:
                # Create new preference
                preference = models.BookPreference(
                    user_id=user.id,
                    book_id=book.id,
                    status=status,
                    rating=rating
                )
                db.add(preference)
                db.commit()
                db.refresh(preference)
                print(f"✓ Added book to user '{username}' collection")
                if status:
                    print(f"  Status: {status}")
                if rating:
                    print(f"  Rating: {rating}/5")
        
        print(f"\nBook successfully added!")
        return book
        
    except Exception as e:
        db.rollback()
        print(f"Error adding book: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a book for a user")
    parser.add_argument("title", help="Book title")
    parser.add_argument("author", nargs="?", help="Author name")
    parser.add_argument("--username", default="sachi", help="Username (default: sachi)")
    parser.add_argument("--status", choices=["want_to_read", "currently_reading", "read", "abandoned"], 
                       help="Reading status")
    parser.add_argument("--rating", type=int, choices=[1, 2, 3, 4, 5], help="Rating (1-5)")
    parser.add_argument("--genre", help="Book genre")
    parser.add_argument("--isbn", help="ISBN number")
    parser.add_argument("--publisher", help="Publisher name")
    parser.add_argument("--page-count", type=int, dest="page_count", help="Number of pages")
    parser.add_argument("--description", help="Book description")
    
    args = parser.parse_args()
    
    add_book_for_user(
        title=args.title,
        author=args.author,
        username=args.username,
        status=args.status,
        rating=args.rating,
        genre=args.genre,
        isbn=args.isbn,
        publisher=args.publisher,
        page_count=args.page_count,
        description=args.description
    )

