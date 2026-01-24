from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import logging
from app.database import get_db
from app.integrations.openlibrary import OpenLibraryIntegration
from app.integrations.google_books import GoogleBooksIntegration
from app import models, schemas
from app.core.auth import get_current_user_id
from app.core.exceptions import NotFoundError, ValidationError, ExternalAPIError

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/integrations/search-books")
def search_books_external(
    q: str = Query(..., description="Search query"),
    source: str = Query("google_books", description="Source: 'google_books' or 'openlibrary'"),
    limit: int = Query(20, ge=1, le=40)
):
    """
    Search for books using external APIs (Open Library or Google Books)
    
    These are free alternatives to Goodreads API which was deprecated in 2020.
    No authentication required for basic searches.
    """
    if source == "openlibrary":
        integration = OpenLibraryIntegration()
        books = integration.search_books(q, limit)
    elif source == "google_books":
        # GoogleBooksIntegration reads API key from settings internally
        integration = GoogleBooksIntegration()
        books = integration.search_books(q, limit)
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Use 'google_books' or 'openlibrary'")
    
    return {
        "source": source,
        "query": q,
        "count": len(books),
        "books": books
    }


@router.get("/integrations/book-by-isbn")
def get_book_by_isbn(
    isbn: str = Query(..., description="ISBN-10 or ISBN-13"),
    source: str = Query("google_books", description="Source: 'google_books' or 'openlibrary'")
):
    """Get book details by ISBN using external APIs"""
    if source == "openlibrary":
        integration = OpenLibraryIntegration()
        book = integration.get_book_by_isbn(isbn)
    elif source == "google_books":
        integration = GoogleBooksIntegration()
        book = integration.get_book_by_isbn(isbn)
    else:
        raise HTTPException(status_code=400, detail="Invalid source. Use 'google_books' or 'openlibrary'")
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    return book


@router.get("/integrations", response_model=List[schemas.ExternalAccountResponse])
def get_connected_platforms(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all connected external platforms"""
    accounts = db.query(models.ExternalAccount).filter(
        models.ExternalAccount.user_id == user_id
    ).all()
    return accounts


@router.post("/integrations/{platform}/connect", response_model=schemas.ExternalAccountResponse)
def connect_platform(
    platform: str,
    account_data: schemas.ExternalAccountCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Connect an external platform (Open Library and Google Books are search-only)
    """
    logger.info(f"Connecting {platform} for user {user_id}")
    
    # Validate platform
    valid_platforms = ["openlibrary", "google_books"]
    if platform not in valid_platforms:
        raise ValidationError(f"Invalid platform. Must be one of: {', '.join(valid_platforms)}")
    
    try:
        # Check if account already exists
        existing = db.query(models.ExternalAccount).filter(
            models.ExternalAccount.user_id == user_id,
            models.ExternalAccount.platform == platform
        ).first()
        
        if existing:
            # Update existing account
            logger.info(f"Updating existing {platform} account")
            existing.platform_user_id = account_data.platform_user_id
            # Only update password if provided (don't overwrite with empty string)
            if account_data.access_token:
                existing.access_token = account_data.access_token
            existing.refresh_token = account_data.refresh_token
            existing.sync_enabled = account_data.sync_enabled
            db.commit()
            db.refresh(existing)
            logger.info(f"Successfully updated {platform} account")
            return existing
        else:
            # Create new account
            logger.info(f"Creating new {platform} account")
            new_account = models.ExternalAccount(
                user_id=user_id,
                platform=platform,
                platform_user_id=account_data.platform_user_id,
                access_token=account_data.access_token or "",  # Can be empty if using auth files
                refresh_token=account_data.refresh_token,
                sync_enabled=account_data.sync_enabled
            )
            db.add(new_account)
            db.commit()
            db.refresh(new_account)
            logger.info(f"Successfully created {platform} account")
            return new_account
    except Exception as e:
        logger.error(f"Error connecting {platform}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting {platform}: {str(e)}"
        )


@router.post("/integrations/{platform}/sync")
def sync_platform(
    platform: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Sync data from a connected platform using the sync agent.
    The agent handles retries, error recovery, and intelligent syncing.
    """
    from app.agents import SyncAgent
    
    # Get the external account
    account = db.query(models.ExternalAccount).filter(
        models.ExternalAccount.user_id == user_id,
        models.ExternalAccount.platform == platform
    ).first()
    
    if not account:
        raise NotFoundError(f"{platform} account", "not connected")
    
    if not account.sync_enabled:
        raise ValidationError(f"Sync is disabled for {platform}")
    
    try:
        # Create sync agent - the agent handles all sync logic autonomously
        agent = SyncAgent(db, user_id)
        
        # Get integration instance based on platform
        if platform == "openlibrary":
            integration = OpenLibraryIntegration()
        elif platform == "google_books":
            integration = GoogleBooksIntegration()
        else:
            raise HTTPException(
                status_code=501, 
                detail=f"Sync for {platform} is not yet implemented. Only search is available for {platform}."
            )
        
        # Use agent to sync - agent handles retries, errors, and data processing
        result = agent.sync_specific_platform(platform, integration)
        
        if result["success"]:
            return {
                "status": "success",
                "platform": platform,
                "books_synced": result["books_synced"],
                "ratings_synced": result["ratings_synced"],
                "errors": result.get("errors", [])
            }
        else:
            error_msg = result.get("error", "Sync failed")
            if result.get("errors"):
                error_msg = "; ".join(result["errors"])
            raise ExternalAPIError(platform, error_msg)
        
    except (HTTPException, NotFoundError, ValidationError, ExternalAPIError):
        raise
    except Exception as e:
        logger.error(f"Error syncing {platform}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error syncing {platform}: {str(e)}"
        )


@router.delete("/integrations/{platform}/disconnect")
def disconnect_platform(
    platform: str,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disconnect an external platform.
    """
    # Get the external account
    account = db.query(models.ExternalAccount).filter(
        models.ExternalAccount.user_id == user_id,
        models.ExternalAccount.platform == platform
    ).first()
    
    if not account:
        raise NotFoundError(f"{platform} account", "not connected")
    
    try:
        # Delete the account from database
        db.delete(account)
        db.commit()
        
        logger.info(f"Disconnected {platform} account for user {user_id}")
        
        return {
            "status": "disconnected",
            "platform": platform,
            "message": f"{platform} account disconnected successfully"
        }
        
    except Exception as e:
        logger.error(f"Error disconnecting {platform}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error disconnecting {platform}: {str(e)}"
        )

