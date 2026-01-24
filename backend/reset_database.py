#!/usr/bin/env python3
"""
Script to reset the database - drops all tables and recreates them
⚠️ WARNING: This will delete all data!
"""
import sys
from sqlalchemy import text
from app.database import engine, Base
from app import models

def reset_database():
    """Drop all tables and recreate them"""
    print("⚠️  WARNING: This will delete ALL data from the database!")
    response = input("Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("Cancelled.")
        return
    
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database reset complete!")

if __name__ == "__main__":
    reset_database()

