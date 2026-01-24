import requests
from typing import List, Dict, Any
from app.integrations.base import IntegrationBase


class OpenLibraryIntegration(IntegrationBase):
    """Open Library API integration - Free alternative to Goodreads"""
    
    BASE_URL = "https://openlibrary.org"
    
    def __init__(self, access_token: str = None, refresh_token: str = None):
        # Open Library doesn't require authentication for basic queries
        super().__init__(access_token or "", refresh_token)
    
    def authenticate(self) -> bool:
        """Open Library doesn't require authentication for public data"""
        return True
    
    def search_books(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for books using Open Library API"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/search.json",
                params={
                    "q": query,
                    "limit": limit,
                    "fields": "title,author_name,isbn,first_publish_year,number_of_pages_median,cover_i,subject"
                },
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            books = []
            for doc in data.get("docs", []):
                # Get cover image
                cover_id = doc.get("cover_i")
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
                
                # Get ISBN (prefer ISBN 13)
                isbn = None
                if "isbn" in doc:
                    isbns = doc["isbn"]
                    # Prefer ISBN-13 if available
                    isbn_13 = [i for i in isbns if len(i) == 13]
                    isbn = isbn_13[0] if isbn_13 else isbns[0]
                
                books.append({
                    "title": doc.get("title", ""),
                    "author": ", ".join(doc.get("author_name", [])),
                    "isbn": isbn,
                    "genre": ", ".join(doc.get("subject", [])[:3]) if doc.get("subject") else None,
                    "description": None,  # Open Library search doesn't include descriptions
                    "cover_image_url": cover_url,
                    "page_count": doc.get("number_of_pages_median"),
                    "publication_date": f"{doc.get('first_publish_year')}-01-01" if doc.get("first_publish_year") else None
                })
            
            return books
        except Exception as e:
            print(f"Error searching Open Library: {e}")
            return []
    
    def get_book_by_isbn(self, isbn: str) -> Dict[str, Any]:
        """Get book details by ISBN"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/isbn/{isbn}.json",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Get cover
            cover_id = data.get("covers", [None])[0] if data.get("covers") else None
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
            
            # Get authors
            authors = []
            if "authors" in data:
                for author_ref in data["authors"]:
                    author_key = author_ref.get("key", "").replace("/authors/", "")
                    author_response = requests.get(
                        f"{self.BASE_URL}/authors/{author_key}.json",
                        timeout=10
                    )
                    if author_response.status_code == 200:
                        author_data = author_response.json()
                        authors.append(author_data.get("name", ""))
            
            return {
                "title": data.get("title", ""),
                "author": ", ".join(authors),
                "isbn": isbn,
                "genre": ", ".join(data.get("subjects", [])[:3]) if data.get("subjects") else None,
                "description": data.get("description", {}).get("value") if isinstance(data.get("description"), dict) else data.get("description"),
                "cover_image_url": cover_url,
                "page_count": data.get("number_of_pages"),
                "publication_date": f"{data.get('publish_date')}-01-01" if data.get("publish_date") else None
            }
        except Exception as e:
            print(f"Error fetching book from Open Library: {e}")
            return {}
    
    def sync_books(self) -> List[Dict[str, Any]]:
        """Open Library doesn't have user accounts, so this is a search helper"""
        # This would be used for searching/importing books, not syncing user data
        return []
    
    def sync_ratings(self) -> List[Dict[str, Any]]:
        """Open Library doesn't track user ratings"""
        return []
    
    def sync_reading_status(self) -> List[Dict[str, Any]]:
        """Open Library doesn't track reading status"""
        return []

