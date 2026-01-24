#!/usr/bin/env python3
"""
Simple script to read books from the database
"""
import sys
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models

def read_books(limit: int = 10):
    """Read books from the database"""
    db: Session = SessionLocal()
    try:
        books = db.query(models.Book).limit(limit).all()
        
        if not books:
            print("No books found in the database.")
            return
        
        print(f"\nFound {len(books)} book(s):\n")
        print("-" * 80)
        
        for book in books:
            print(f"ID: {book.id}")
            print(f"Title: {book.title}")
            print(f"Author: {book.author or 'N/A'}")
            print(f"ISBN: {book.isbn or 'N/A'}")
            print(f"Genre: {book.genre or 'N/A'}")
            print(f"Publisher: {book.publisher or 'N/A'}")
            print(f"Pages: {book.page_count or 'N/A'}")
            print(f"Created: {book.created_at}")
            print("-" * 80)
        
    except Exception as e:
        print(f"Error reading books: {e}", file=sys.stderr)
    finally:
        db.close()

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    read_books(limit)

