#!/usr/bin/env python3
"""
Development script to import Goodreads library export CSV.

Usage:
    python app/dev/import_goodreads.py [--csv-path PATH] [--user-id ID]

Default CSV path: /mnt/data/goodreads_library_export.csv
Default user_id: 1
"""
import argparse
import sys
import os
import logging

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.database import SessionLocal
from app.importers.goodreads_importer import import_goodreads_csv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='Import Goodreads library export CSV into Smart Bookshelf'
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
        help='User ID to associate imported data with (default: 1)'
    )
    
    args = parser.parse_args()
    
    # Validate CSV file exists
    if not os.path.exists(args.csv_path):
        logger.error(f"CSV file not found: {args.csv_path}")
        logger.info("Please provide a valid path to your Goodreads library export CSV")
        sys.exit(1)
    
    logger.info(f"Starting Goodreads import...")
    logger.info(f"CSV path: {args.csv_path}")
    logger.info(f"User ID: {args.user_id}")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Run import
        stats = import_goodreads_csv(
            csv_path=args.csv_path,
            user_id=args.user_id,
            db=db
        )
        
        # Print summary
        print("\n" + "="*60)
        print("Import Summary")
        print("="*60)
        print(f"Rows processed: {stats['rows_processed']}")
        print(f"Rows skipped: {stats['rows_skipped']}")
        print(f"\nBooks:")
        print(f"  Created: {stats['books_created']}")
        print(f"  Updated: {stats['books_updated']}")
        print(f"\nPreferences:")
        print(f"  Created: {stats['preferences_created']}")
        print(f"  Updated: {stats['preferences_updated']}")
        print(f"\nSessions:")
        print(f"  Created: {stats['sessions_created']}")
        print("="*60)
        print("\nImport complete! Your Goodreads data has been imported.")
        print("You can safely run this script again - it's idempotent.")
        
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == '__main__':
    main()

