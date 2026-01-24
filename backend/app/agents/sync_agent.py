"""
Autonomous sync agent that can intelligently sync books from external platforms
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app import models
from app.integrations.base import IntegrationBase

logger = logging.getLogger(__name__)


class SyncAgent:
    """
    Autonomous agent that syncs books from external platforms.
    Can make decisions about when to sync, handle errors, and retry automatically.
    """
    
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id
        self.max_retries = 3
        self.retry_delay = 60  # seconds
    
    def should_sync(self, account: models.ExternalAccount) -> bool:
        """
        Decide if an account should be synced based on:
        - Last sync time
        - Sync enabled status
        - Account status
        """
        if not account.sync_enabled:
            logger.info(f"Sync disabled for {account.platform}")
            return False
        
        # If never synced, should sync
        if not account.last_synced_at:
            logger.info(f"Never synced {account.platform}, should sync")
            return True
        
        # If synced more than 24 hours ago, should sync
        time_since_sync = datetime.utcnow() - account.last_synced_at
        if time_since_sync > timedelta(hours=24):
            logger.info(f"Last sync was {time_since_sync} ago, should sync")
            return True
        
        logger.info(f"Synced recently ({time_since_sync} ago), skipping")
        return False
    
    def sync_account(self, account: models.ExternalAccount, integration: IntegrationBase) -> Dict[str, Any]:
        """
        Sync a single account with retry logic and error handling.
        The agent autonomously handles errors, retries, and data processing.
        """
        logger.info(f"Agent: Starting sync for {account.platform} (user {self.user_id})")
        
        books_synced = 0
        ratings_synced = 0
        errors = []
        
        for attempt in range(self.max_retries):
            try:
                # Authenticate (agent handles authentication autonomously)
                try:
                    auth_success = integration.authenticate()
                    if not auth_success:
                        error_msg = f"Authentication failed for {account.platform}"
                        logger.error(f"Agent: {error_msg}")
                        errors.append(error_msg)
                        if attempt < self.max_retries - 1:
                            logger.info(f"Agent: Retrying authentication in {self.retry_delay}s...")
                            import time
                            time.sleep(self.retry_delay)
                            continue
                        break
                except Exception as auth_error:
                    error_msg = f"Authentication error: {str(auth_error)}"
                    logger.error(f"Agent: {error_msg}")
                    errors.append(error_msg)
                    if attempt < self.max_retries - 1:
                        logger.info(f"Agent: Retrying authentication in {self.retry_delay}s...")
                        import time
                        time.sleep(self.retry_delay)
                        continue
                    break
                
                # Sync books (agent handles empty results for search-only platforms)
                books = integration.sync_books()
                if not books:
                    logger.info(f"Agent: {account.platform} is search-only, no books to sync")
                else:
                    from app.services import book_service
                    from app import schemas
                    
                    for book_data in books:
                        try:
                            # Check if book exists
                            existing_book = None
                            if book_data.get("isbn"):
                                existing_book = self.db.query(models.Book).filter(
                                    models.Book.isbn == book_data["isbn"]
                                ).first()
                            
                            if not existing_book:
                                # Create new book
                                book_create = schemas.BookCreate(**book_data)
                                book = book_service.create_book(self.db, book_create)
                                books_synced += 1
                            else:
                                books_synced += 1  # Count as synced
                        
                        except Exception as e:
                            logger.error(f"Agent: Error creating book {book_data.get('title')}: {e}")
                            errors.append(f"Error creating book: {str(e)}")
                
                # Sync ratings
                ratings = integration.sync_ratings()
                if ratings:
                    for rating_data in ratings:
                        try:
                            # Find book by ISBN
                            isbn = rating_data.get("book_id")
                            book = self.db.query(models.Book).filter(models.Book.isbn == isbn).first()
                            if book:
                                # Create or update preference
                                pref = self.db.query(models.BookPreference).filter(
                                    models.BookPreference.user_id == self.user_id,
                                    models.BookPreference.book_id == book.id
                                ).first()
                                
                                if pref:
                                    pref.rating = rating_data.get("rating")
                                    pref.review = rating_data.get("review")
                                else:
                                    pref = models.BookPreference(
                                        user_id=self.user_id,
                                        book_id=book.id,
                                        rating=rating_data.get("rating"),
                                        review=rating_data.get("review"),
                                        status="read" if rating_data.get("rating") else None
                                    )
                                    self.db.add(pref)
                                ratings_synced += 1
                        except Exception as e:
                            logger.error(f"Agent: Error syncing rating: {e}")
                            errors.append(f"Error syncing rating: {str(e)}")
                
                # Update last_synced_at
                account.last_synced_at = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Agent: Successfully synced {account.platform}: {books_synced} books, {ratings_synced} ratings")
                
                return {
                    "success": True,
                    "platform": account.platform,
                    "books_synced": books_synced,
                    "ratings_synced": ratings_synced,
                    "errors": errors
                }
            
            except Exception as e:
                error_msg = f"Sync attempt {attempt + 1} failed: {str(e)}"
                logger.error(f"Agent: {error_msg}", exc_info=True)
                errors.append(error_msg)
                
                if attempt < self.max_retries - 1:
                    logger.info(f"Agent: Retrying in {self.retry_delay}s...")
                    import time
                    time.sleep(self.retry_delay)
                else:
                    logger.error(f"Agent: All {self.max_retries} sync attempts failed")
                    return {
                        "success": False,
                        "platform": account.platform,
                        "books_synced": books_synced,
                        "ratings_synced": ratings_synced,
                        "errors": errors
                    }
        
        return {
            "success": False,
            "platform": account.platform,
            "books_synced": books_synced,
            "ratings_synced": ratings_synced,
            "errors": errors
        }
    
    def sync_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Sync all connected accounts that need syncing
        """
        accounts = self.db.query(models.ExternalAccount).filter(
            models.ExternalAccount.user_id == self.user_id,
            models.ExternalAccount.sync_enabled == True
        ).all()
        
        results = []
        
        for account in accounts:
            if not self.should_sync(account):
                continue
            
            # Get integration instance (this would need to be implemented per platform)
            # For now, we'll skip since we removed Audible
            # In the future, you'd do:
            # integration = self._get_integration(account)
            # result = self.sync_account(account, integration)
            # results.append(result)
            
            logger.info(f"Skipping {account.platform} - no integration available")
        
        return results
    
    def sync_specific_platform(self, platform: str, integration: IntegrationBase) -> Dict[str, Any]:
        """
        Sync a specific platform using the provided integration
        """
        account = self.db.query(models.ExternalAccount).filter(
            models.ExternalAccount.user_id == self.user_id,
            models.ExternalAccount.platform == platform
        ).first()
        
        if not account:
            return {
                "success": False,
                "platform": platform,
                "error": "Account not connected"
            }
        
        return self.sync_account(account, integration)

