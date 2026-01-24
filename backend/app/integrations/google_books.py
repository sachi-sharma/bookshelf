import requests
from typing import List, Dict, Any
from app.integrations.base import IntegrationBase
from app.config import settings


class GoogleBooksIntegration(IntegrationBase):
    """Google Books API integration - Free alternative to Goodreads"""
    
    BASE_URL = "https://www.googleapis.com/books/v1"
    
    def __init__(self, access_token: str = None, refresh_token: str = None):
        super().__init__(access_token or "", refresh_token)
        # Google Books API key is optional but recommended for higher rate limits
        self.api_key = getattr(settings, 'google_books_api_key', None)
    
    def authenticate(self) -> bool:
        """Google Books doesn't require authentication for basic queries"""
        return True
    
    def search_books(self, query: str, max_results: int = 20) -> List[Dict[str, Any]]:
        """Search for books using Google Books API"""
        try:
            params = {
                "q": query,
                "maxResults": max_results,
                "fields": "items(id,volumeInfo(title,authors,industryIdentifiers,description,pageCount,publishedDate,categories,imageLinks))"
            }
            
            if self.api_key:
                params["key"] = self.api_key
            
            response = requests.get(
                f"{self.BASE_URL}/volumes",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            books = []
            for item in data.get("items", []):
                volume_info = item.get("volumeInfo", {})
                
                # Get ISBN
                isbn = None
                if "industryIdentifiers" in volume_info:
                    for identifier in volume_info["industryIdentifiers"]:
                        if identifier.get("type") == "ISBN_13":
                            isbn = identifier.get("identifier")
                            break
                        elif identifier.get("type") == "ISBN_10" and not isbn:
                            isbn = identifier.get("identifier")
                
                # Get cover image
                image_links = volume_info.get("imageLinks", {})
                cover_url = image_links.get("thumbnail") or image_links.get("small") or image_links.get("medium")
                if cover_url:
                    # Replace http with https and remove zoom parameter for larger image
                    cover_url = cover_url.replace("http://", "https://").replace("&zoom=1", "&zoom=0")
                
                books.append({
                    "title": volume_info.get("title", ""),
                    "author": ", ".join(volume_info.get("authors", [])),
                    "isbn": isbn,
                    "genre": ", ".join(volume_info.get("categories", [])[:3]) if volume_info.get("categories") else None,
                    "description": volume_info.get("description"),
                    "cover_image_url": cover_url,
                    "page_count": volume_info.get("pageCount"),
                    "publication_date": volume_info.get("publishedDate")
                })
            
            return books
        except Exception as e:
            print(f"Error searching Google Books: {e}")
            return []
    
    def get_book_by_isbn(self, isbn: str) -> Dict[str, Any]:
        """Get book details by ISBN"""
        try:
            params = {"q": f"isbn:{isbn}"}
            if self.api_key:
                params["key"] = self.api_key
            
            response = requests.get(
                f"{self.BASE_URL}/volumes",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("items"):
                return {}
            
            item = data["items"][0]
            volume_info = item.get("volumeInfo", {})
            
            image_links = volume_info.get("imageLinks", {})
            cover_url = image_links.get("thumbnail") or image_links.get("small") or image_links.get("medium")
            if cover_url:
                cover_url = cover_url.replace("http://", "https://").replace("&zoom=1", "&zoom=0")
            
            return {
                "title": volume_info.get("title", ""),
                "author": ", ".join(volume_info.get("authors", [])),
                "isbn": isbn,
                "genre": ", ".join(volume_info.get("categories", [])[:3]) if volume_info.get("categories") else None,
                "description": volume_info.get("description"),
                "cover_image_url": cover_url,
                "page_count": volume_info.get("pageCount"),
                "publication_date": volume_info.get("publishedDate")
            }
        except Exception as e:
            print(f"Error fetching book from Google Books: {e}")
            return {}
    
    def sync_books(self) -> List[Dict[str, Any]]:
        """Google Books doesn't have user accounts, so this is a search helper"""
        # This would be used for searching/importing books, not syncing user data
        return []
    
    def sync_ratings(self) -> List[Dict[str, Any]]:
        """Google Books doesn't track user ratings"""
        return []
    
    def sync_reading_status(self) -> List[Dict[str, Any]]:
        """Google Books doesn't track reading status"""
        return []

