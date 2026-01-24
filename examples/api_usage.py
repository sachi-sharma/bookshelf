"""
Example usage of the Smart Bookshelf API

This script demonstrates how to interact with the API endpoints.
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

# Example 1: Register a new user
def register_user():
    """Register a new user"""
    response = requests.post(
        f"{BASE_URL}/users/register",
        json={
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password": "securepassword123"
        }
    )
    print("Register User:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 2: Login and get token
def login():
    """Login and get access token"""
    response = requests.post(
        f"{BASE_URL}/users/login",
        json={
            "username": "johndoe",
            "password": "securepassword123"
        }
    )
    print("\nLogin:", response.status_code)
    data = response.json()
    print(json.dumps(data, indent=2))
    return data.get("access_token")


# Example 3: Create a book
def create_book(token):
    """Create a new book in the catalog"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/books",
        headers=headers,
        json={
            "isbn": "9780439708180",
            "title": "Harry Potter and the Philosopher's Stone",
            "author": "J.K. Rowling",
            "genre": "Fantasy",
            "description": "A young wizard discovers his magical heritage...",
            "page_count": 320,
            "cover_image_url": "https://example.com/harry-potter.jpg"
        }
    )
    print("\nCreate Book:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 4: Create a reading session (book taken)
def create_reading_session(token, book_id):
    """Record that a book was taken"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/reading-sessions",
        headers=headers,
        json={
            "book_id": book_id,
            "action": "taken",
            "mood": "relaxed",
            "location": "home",
            "notes": "Reading in the garden on a sunny afternoon"
        }
    )
    print("\nCreate Reading Session (Taken):", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 5: Create a reading session (book returned)
def return_book(token, book_id):
    """Record that a book was returned with reading details"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/reading-sessions",
        headers=headers,
        json={
            "book_id": book_id,
            "action": "returned",
            "duration_minutes": 45.5,
            "mood": "relaxed",
            "pages_read": 25,
            "reading_pace": 0.55,
            "location": "home",
            "notes": "Great reading session!",
            "context": {
                "co_read_books": [],
                "session_notes": "Beautiful day for reading"
            }
        }
    )
    print("\nCreate Reading Session (Returned):", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 6: Get reading history
def get_reading_history(token):
    """Get user's reading history"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/reading-sessions",
        headers=headers,
        params={
            "limit": 10,
            "mood": "relaxed"  # Optional filter
        }
    )
    print("\nReading History:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 7: Get reading statistics
def get_statistics(token):
    """Get reading statistics"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/reading-sessions/statistics",
        headers=headers
    )
    print("\nReading Statistics:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 8: Get recommendations
def get_recommendations(token, mood=None):
    """Get personalized book recommendations"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"limit": 5}
    if mood:
        params["mood"] = mood
    
    response = requests.get(
        f"{BASE_URL}/recommendations",
        headers=headers,
        params=params
    )
    print("\nRecommendations:", response.status_code)
    recommendations = response.json()
    print(json.dumps(recommendations, indent=2))
    
    # Show recommendation details
    for rec in recommendations:
        print(f"\n📚 {rec['book']['title'] if rec.get('book') else 'Book #' + str(rec['book_id'])}")
        print(f"   Score: {rec['score']:.2%}")
        print(f"   Reason: {rec['reason']}")
        if rec.get('factors'):
            print(f"   Factors: {rec['factors']}")
    
    return recommendations


# Example 9: Search for books
def search_books(token, query):
    """Search for books"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{BASE_URL}/books",
        headers=headers,
        params={"q": query, "limit": 5}
    )
    print(f"\nSearch Books ('{query}'):", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 10: Connect external platform
def connect_goodreads(token):
    """Connect Goodreads account"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/integrations/goodreads/connect",
        headers=headers,
        json={
            "platform_user_id": "12345",
            "access_token": "oauth_token_here",
            "refresh_token": "refresh_token_here"
        }
    )
    print("\nConnect Goodreads:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


# Example 11: Sync external platform
def sync_goodreads(token):
    """Sync data from Goodreads"""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{BASE_URL}/integrations/goodreads/sync",
        headers=headers
    )
    print("\nSync Goodreads:", response.status_code)
    print(json.dumps(response.json(), indent=2))
    return response.json()


def main():
    """Run all examples"""
    print("=" * 60)
    print("Smart Bookshelf API Usage Examples")
    print("=" * 60)
    
    # Note: In a real scenario, you would handle errors and use the token
    # For this example, we'll assume the server is running and user exists
    
    # Step 1: Register (or skip if user exists)
    # user = register_user()
    
    # Step 2: Login
    # token = login()
    # if not token:
    #     print("Login failed!")
    #     return
    
    # Step 3: Create a book
    # book = create_book(token)
    # book_id = book["id"]
    
    # Step 4: Create reading sessions
    # create_reading_session(token, book_id)
    # return_book(token, book_id)
    
    # Step 5: Get history and statistics
    # get_reading_history(token)
    # get_statistics(token)
    
    # Step 6: Get recommendations
    # get_recommendations(token, mood="relaxed")
    
    # Step 7: Search books
    # search_books(token, "harry potter")
    
    # Step 8: External integrations
    # connect_goodreads(token)
    # sync_goodreads(token)
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
    print("\nNote: Uncomment the code above and ensure the API server is running")
    print("to test these examples.")


if __name__ == "__main__":
    main()

