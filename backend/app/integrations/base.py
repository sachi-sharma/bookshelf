from abc import ABC, abstractmethod
from typing import List, Dict, Any
from app.models import Book, BookPreference, ExternalAccount


class IntegrationBase(ABC):
    """Base class for external reading platform integrations"""
    
    def __init__(self, access_token: str, refresh_token: str = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass
    
    @abstractmethod
    def sync_books(self) -> List[Dict[str, Any]]:
        """Sync books from the platform"""
        pass
    
    @abstractmethod
    def sync_ratings(self) -> List[Dict[str, Any]]:
        """Sync ratings and reviews"""
        pass
    
    @abstractmethod
    def sync_reading_status(self) -> List[Dict[str, Any]]:
        """Sync current reading status"""
        pass
    
    def normalize_book_data(self, platform_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize platform-specific book data to our schema"""
        return {
            "title": platform_data.get("title", ""),
            "author": platform_data.get("author", ""),
            "isbn": platform_data.get("isbn"),
            "genre": platform_data.get("genre"),
            "description": platform_data.get("description"),
            "cover_image_url": platform_data.get("cover_image_url"),
            "page_count": platform_data.get("page_count"),
            "publication_date": platform_data.get("publication_date")
        }

