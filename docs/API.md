# API Reference

Complete API documentation for Smart Bookshelf.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

In development mode, endpoints default to user_id=1. Authentication is not required for the first version.

## Books

### List Books
```http
GET /books?q=search&author=author&genre=genre&limit=50&offset=0
```

### Get Book
```http
GET /books/{book_id}
```

### Create Book
```http
POST /books
Content-Type: application/json

{
  "title": "Book Title",
  "author": "Author Name",
  "isbn": "1234567890",
  "genre": "Fiction",
  "page_count": 300
}
```

### Get Books by IDs
```http
GET /books/bulk?ids=1,2,3
```


## Recommendations

### Get Recommendations
```http
GET /recommendations?current_mood=relaxed&limit=10
```

Returns personalized book recommendations using LLM based on reading preferences.

**Query Parameters:**
- `limit` (optional, default=3): Number of recommendations (1-50)
- `current_mood` (optional): Current mood (e.g., "relaxed", "focused", "curious")

**Response:**
```json
[
  {
    "id": 123,
    "book_id": 45,
    "book": {
      "id": 45,
      "title": "Book Title",
      "author": "Author Name",
      "genre": "Fiction",
      "cover_image_url": "https://...",
      "description": "..."
    },
    "score": 0.92,
    "reason": "Perfect match for your current mood...",
    "factors": {
      "genre_match": 0.9,
      "mood_match": 0.95
    },
    "user_id": 1,
    "created_at": "2026-01-17T19:00:00Z",
    "clicked": false,
    "dismissed": false
  }
]
```

### Get Quick Recommendation
```http
GET /recommendations/quick?mood=curious&location=home&available_time_minutes=60&only_available=true
```

Get a quick recommendation for "What should I read right now?" with contextual information.

**Query Parameters:**
- `mood` (optional): Current mood
- `location` (optional): Current location
- `available_time_minutes` (optional, 5-480): Available reading time in minutes
- `only_available` (optional, default=false): Only recommend books in physical shelf

**Response:**
```json
{
  "recommendation": {
    "id": 123,
    "book": {...},
    "score": 0.92,
    "reason": "Perfect for relaxed evening reading..."
  },
  "context": {
    "current_time": {
      "hour": 19,
      "time_of_day": "evening",
      "day_of_week": "Friday",
      "month": 1,
      "timestamp": "2026-01-17T19:00:00Z"
    },
    "user_context": {
      "mood": "curious",
      "location": "home",
      "available_time_minutes": 60
    },
    "available_books": [1, 5, 12],
    "recent_activity": {
      "sessions_count": 15,
      "recent_moods": ["relaxed", "focused"],
      "recent_locations": ["home", "cafe"]
    },
    "reading_stats": {
      "average_pace_pages_per_minute": 1.2,
      "total_sessions": 50
    }
  },
  "alternatives": [...]
}
```


## Reading Sessions

### Create Reading Session
```http
POST /reading-sessions
Content-Type: application/json

{
  "book_id": 1,
  "action": "taken",
  "duration_minutes": 30,
  "mood": "relaxed",
  "location": "home",
  "pages_read": 15,
  "status": "currently_reading",
  "tags": ["fiction", "evening"]
}
```

**Actions:**
- `taken`: Book taken from shelf
- `returned`: Book returned to shelf

### List Reading Sessions
```http
GET /reading-sessions?book_id=1&limit=50&offset=0
```

### Get Reading Session
```http
GET /reading-sessions/{session_id}
```

### Get Reading History
```http
GET /reading-sessions/history?start_date=2026-01-01&end_date=2026-01-31
```

## Book Preferences

### Get Book Preference
```http
GET /preferences/{book_id}
```

### Update Book Preference
```http
PUT /preferences/{book_id}
Content-Type: application/json

{
  "rating": 5,
  "review": "Great book!",
  "status": "read",
  "tags": ["favorite", "fiction"]
}
```

### List Preferences
```http
GET /preferences?status=read&limit=50
```

## Integrations

### Search Books (External APIs)
```http
GET /integrations/search-books?q=python&source=google_books&limit=20
```

Search for books using external APIs (Open Library or Google Books).

**Query Parameters:**
- `q` (required): Search query
- `source` (optional, default="google_books"): "google_books" or "openlibrary"
- `limit` (optional, default=20, max=40): Number of results

**Response:**
```json
{
  "source": "google_books",
  "query": "python",
  "count": 20,
  "books": [
    {
      "title": "Book Title",
      "author": "Author Name",
      "isbn": "1234567890",
      "genre": "Fiction",
      "description": "...",
      "cover_image_url": "https://...",
      "page_count": 300,
      "publication_date": "2020-01-01"
    }
  ]
}
```

### Get Book by ISBN
```http
GET /integrations/book-by-isbn?isbn=1234567890&source=google_books
```

Get book details by ISBN using external APIs.

### List Connected Platforms
```http
GET /integrations
```

Get all connected external platforms.

**Response:**
```json
[
  {
    "id": 1,
    "platform": "google_books",
    "platform_user_id": "user@example.com",
    "sync_enabled": true,
    "last_synced_at": "2026-01-17T19:00:00Z",
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

### Connect Platform
```http
POST /integrations/{platform}/connect
Content-Type: application/json

{
  "platform_user_id": "user@example.com",
  "access_token": "",
  "refresh_token": "",
  "sync_enabled": true
}
```

Connect an external platform. Currently supports:
- `openlibrary`: Search-only (no authentication required)
- `google_books`: Search-only (optional API key for higher rate limits)

### Sync Platform
```http
POST /integrations/{platform}/sync
```

Sync data from a connected platform using the **sync agent**. The agent autonomously:
- Handles authentication
- Retries on failures (up to 3 times)
- Syncs books and ratings
- Updates sync timestamp
- Returns detailed results

**Response:**
```json
{
  "status": "success",
  "platform": "google_books",
  "books_synced": 15,
  "ratings_synced": 10,
  "errors": []
}
```

**Note:** Currently, Open Library and Google Books are search-only platforms and don't support user data syncing. The sync endpoint is available for future platform integrations.

### Disconnect Platform
```http
DELETE /integrations/{platform}/disconnect
```

Disconnect an external platform.

## Error Responses

All endpoints may return standard HTTP error codes:

- `400 Bad Request`: Invalid input or validation error
- `401 Unauthorized`: Authentication required
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

## Interactive API Documentation

When the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These provide interactive API documentation with the ability to test endpoints directly.
