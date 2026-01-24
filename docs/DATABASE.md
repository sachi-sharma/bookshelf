# Database Schema & Data Models

## Overview

The database uses PostgreSQL (or SQLite for development) with a relational schema designed to track reading habits, store book metadata, and support recommendation generation.

## Entity Relationship Diagram

```
┌─────────────┐
│    Users    │
│─────────────│
│ id (PK)     │
│ email       │
│ username    │
│ password    │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────────┐
│  Reading Sessions        │
│──────────────────────────│
│ id (PK)                  │
│ user_id (FK)             │
│ book_id (FK)             │
│ action                   │
│ timestamp                │
│ duration_minutes         │
│ mood                     │
│ context (JSON)           │
│ location                 │
│ notes                    │
└──────┬───────────────────┘
       │
       │ N:1
       │
┌──────▼──────┐
│    Books    │
│─────────────│
│ id (PK)     │
│ isbn        │
│ title       │
│ author      │
│ genre       │
│ tags (JSON) │
│ description │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐
│ Book Preferences    │
│─────────────────────│
│ id (PK)             │
│ user_id (FK)        │
│ book_id (FK)        │
│ rating              │
│ review              │
│ status              │
│ favorite            │
└─────────────────────┘

┌─────────────┐
│    Users    │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────────┐
│ External Accounts       │
│─────────────────────────│
│ id (PK)                 │
│ user_id (FK)            │
│ platform                │
│ platform_user_id        │
│ access_token            │
│ refresh_token           │
│ last_synced_at          │
└─────────────────────────┘

┌─────────────┐
│    Users    │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────────────┐
│ Recommendations     │
│─────────────────────│
│ id (PK)             │
│ user_id (FK)        │
│ book_id (FK)       │
│ score               │
│ reason              │
│ factors (JSON)      │
│ clicked             │
│ dismissed           │
└─────────────────────┘
```

## Table Definitions

### users

Stores user account information.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing user ID |
| email | VARCHAR | UNIQUE, NOT NULL | User email address |
| username | VARCHAR | UNIQUE, NOT NULL | Username |
| hashed_password | VARCHAR | NOT NULL | Bcrypt hashed password |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation timestamp |
| updated_at | TIMESTAMP | | Last update timestamp |

**Indexes:**
- `idx_users_email` on `email`
- `idx_users_username` on `username`

### books

Catalog of books in the system.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing book ID |
| isbn | VARCHAR | INDEX | ISBN-10 or ISBN-13 |
| title | VARCHAR | NOT NULL, INDEX | Book title |
| author | VARCHAR | INDEX | Author name |
| publisher | VARCHAR | | Publisher name |
| publication_date | TIMESTAMP | | Publication date |
| genre | VARCHAR | INDEX | Genre category |
| tags | JSONB | | Array of tags |
| description | TEXT | | Book description |
| cover_image_url | VARCHAR | | Cover image URL |
| page_count | INTEGER | | Number of pages |
| language | VARCHAR | DEFAULT 'en' | Language code |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_books_isbn` on `isbn`
- `idx_books_title` on `title`
- `idx_books_author` on `author`
- `idx_books_genre` on `genre`

### reading_sessions

Tracks individual reading events (book taken/returned).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing session ID |
| user_id | INTEGER | FK → users.id, NOT NULL | User who read the book |
| book_id | INTEGER | FK → books.id, NOT NULL | Book being read |
| action | VARCHAR | NOT NULL | 'taken' or 'returned' |
| timestamp | TIMESTAMP | NOT NULL, DEFAULT NOW() | Event timestamp |
| duration_minutes | FLOAT | | Reading duration in minutes |
| mood | VARCHAR | | User's mood (relaxed, focused, etc.) |
| context | JSONB | | Additional context data |
| location | VARCHAR | | Reading location |
| notes | TEXT | | Session notes |
| status | VARCHAR | | Reading status |
| tags | JSONB | | User-defined tags array |
| pages_read | INTEGER | | Pages read in session |
| reading_pace | FLOAT | | Pages per minute |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_sessions_user_id` on `user_id`
- `idx_sessions_book_id` on `book_id`
- `idx_sessions_timestamp` on `timestamp`
- `idx_sessions_mood` on `mood`

### book_preferences

User ratings, reviews, and reading status for books.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing preference ID |
| user_id | INTEGER | FK → users.id, NOT NULL | User ID |
| book_id | INTEGER | FK → books.id, NOT NULL | Book ID |
| rating | INTEGER | | Rating 1-5 stars |
| review | TEXT | | Written review |
| status | VARCHAR | | 'want_to_read', 'currently_reading', 'read', 'abandoned' |
| favorite | BOOLEAN | DEFAULT FALSE | Favorite flag |
| tags | JSONB | | User-defined tags |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |
| updated_at | TIMESTAMP | | Last update timestamp |

**Indexes:**
- `idx_preferences_user_id` on `user_id`
- `idx_preferences_book_id` on `book_id`
- `idx_preferences_status` on `status`

### external_accounts

Stores credentials for external reading platforms.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing account ID |
| user_id | INTEGER | FK → users.id, NOT NULL | User ID |
| platform | VARCHAR | NOT NULL | Platform name (openlibrary, google_books, etc.) |
| platform_user_id | VARCHAR | NOT NULL | User ID on external platform |
| access_token | VARCHAR | | OAuth access token |
| refresh_token | VARCHAR | | OAuth refresh token |
| sync_enabled | BOOLEAN | DEFAULT TRUE | Whether to auto-sync |
| last_synced_at | TIMESTAMP | | Last sync timestamp |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |
| updated_at | TIMESTAMP | | Last update timestamp |

**Indexes:**
- `idx_external_accounts_user_id` on `user_id`
- `idx_external_accounts_platform` on `platform`
- UNIQUE constraint on `(user_id, platform)`

### recommendations

Generated book recommendations for users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Auto-incrementing recommendation ID |
| user_id | INTEGER | FK → users.id, NOT NULL | User ID |
| book_id | INTEGER | FK → books.id, NOT NULL | Recommended book ID |
| score | FLOAT | NOT NULL | Recommendation score (0-1) |
| reason | TEXT | | Explanation for recommendation |
| factors | JSONB | | Contributing factors (genre_match, mood_match, etc.) |
| shown_at | TIMESTAMP | | When recommendation was shown |
| clicked | BOOLEAN | DEFAULT FALSE | Whether user clicked |
| dismissed | BOOLEAN | DEFAULT FALSE | Whether user dismissed |
| created_at | TIMESTAMP | DEFAULT NOW() | Record creation timestamp |

**Indexes:**
- `idx_recommendations_user_id` on `user_id`
- `idx_recommendations_book_id` on `book_id`
- `idx_recommendations_score` on `score`

## Data Types

### JSON Fields

**context (reading_sessions):**
```json
{
  "location": "home",
  "co_read_books": [1, 2, 3],
  "session_notes": "Reading in the garden"
}
```

**tags (books):**
```json
["fiction", "mystery", "bestseller"]
```

**factors (recommendations):**
```json
{
  "genre_match": 0.85,
  "author_match": 0.60,
  "mood_match": 0.75,
  "time_match": 0.50
}
```

## Relationships

1. **User → Reading Sessions**: One-to-Many
   - A user can have many reading sessions
   - Cascade delete: When user is deleted, sessions are deleted

2. **Book → Reading Sessions**: One-to-Many
   - A book can be read in many sessions
   - Cascade delete: When book is deleted, sessions are deleted

3. **User → Book Preferences**: One-to-Many
   - A user can have preferences for many books
   - Unique constraint: One preference per user-book pair

4. **User → External Accounts**: One-to-Many
   - A user can connect multiple platforms
   - Unique constraint: One account per user-platform pair

5. **User → Recommendations**: One-to-Many
   - A user can receive many recommendations

## My Books Data Model

"My Books" displays books that have either:
- A `BookPreference` record (status, rating, tags, etc.)
- OR a `ReadingSession` record (you logged reading for it)

### Database Models (SQLAlchemy)

#### Book Model
```python
class Book(Base):
    __tablename__ = "books"
    
    id: int (Primary Key)
    isbn: str (indexed)
    title: str (required, indexed)
    author: str (indexed)
    publisher: str
    publication_date: datetime
    genre: str (indexed)
    tags: JSON (array of tags)
    description: Text
    cover_image_url: str
    page_count: int
    language: str (default: "en")
    created_at: datetime
    
    # Relationships
    reading_sessions: List[ReadingSession]
    preferences: List[BookPreference]
```

#### BookPreference Model
```python
class BookPreference(Base):
    __tablename__ = "book_preferences"
    
    id: int (Primary Key)
    user_id: int (Foreign Key → users.id)
    book_id: int (Foreign Key → books.id)
    
    rating: int (1-5 stars)
    review: Text
    status: str ("want_to_read", "currently_reading", "read", "abandoned")
    favorite: bool (default: False)
    tags: JSON (user-defined tags array)
    
    created_at: datetime
    updated_at: datetime
    
    # Relationships
    user: User
    book: Book
```

#### ReadingSession Model
```python
class ReadingSession(Base):
    __tablename__ = "reading_sessions"
    
    id: int (Primary Key)
    user_id: int (Foreign Key → users.id)
    book_id: int (Foreign Key → books.id)
    
    # Event tracking
    action: str ("taken" or "returned")
    timestamp: datetime
    
    # Reading metadata
    duration_minutes: float
    mood: str ("relaxed", "focused", "curious", etc.)
    location: str (e.g., "Home", "Library", "Cafe")
    notes: Text
    
    # Reading metrics
    pages_read: int
    reading_pace: float (pages per minute)
    
    created_at: datetime
    
    # Relationships
    user: User
    book: Book
```

## API Schemas (Pydantic)

### BookResponse
```python
{
    "id": int,
    "title": str,
    "author": str | None,
    "isbn": str | None,
    "genre": str | None,
    "cover_image_url": str | None,
    "description": str | None,
    "page_count": int | None,
    "tags": List[str] | None,
    "created_at": datetime
}
```

### BookPreferenceResponse
```python
{
    "id": int,
    "book_id": int,
    "rating": int | None (1-5),
    "review": str | None,
    "status": str | None ("want_to_read", "currently_reading", "read", "abandoned"),
    "favorite": bool,
    "tags": List[str] | None,
    "book": BookResponse | None
}
```

## Frontend TypeScript Interfaces

### Book
```typescript
interface Book {
  id: number
  title: string
  author?: string
  isbn?: string
  genre?: string
  cover_image_url?: string
  description?: string
  page_count?: number
}
```

### BookPreference
```typescript
interface BookPreference {
  id: number
  book_id: number
  rating?: number
  review?: string
  status?: string  // "read", "want_to_read", "currently_reading", "abandoned"
  favorite: boolean
  tags?: string[]
  book?: Book
}
```

## Data Flow for My Books Page

### 1. Fetch Preferences
```
GET /api/v1/preferences
→ Returns: List[BookPreferenceResponse]
→ Contains: book_id, status, rating, tags, favorite
```

### 2. Fetch Book IDs with Sessions
```
GET /api/v1/reading-sessions/book-ids
→ Returns: { "book_ids": [1, 2, 3, ...] }
→ Contains: Unique book IDs that have reading sessions
```

### 3. Combine Book IDs
```typescript
bookIdsWithPreferences = Set(preferences.map(p => p.book_id))
bookIdsWithSessions = Set(sessionsData.book_ids)
myBookIds = Set([...bookIdsWithPreferences, ...bookIdsWithSessions])
```

### 4. Fetch Books in Bulk
```
GET /api/v1/books/bulk?ids=1,2,3,4,5
→ Returns: List[BookResponse]
→ Contains: Full book details for all "My Books"
```

### 5. Display Logic
```typescript
// For each book:
const preference = preferenceMap.get(book.id)
const hasSession = bookIdsWithSessions.has(book.id)

// Status determination:
const status = 
  preference?.status ||                    // Use preference status if exists
  (hasSession ? 'currently_reading' : 'want_to_read')  // Default based on session
```

## Status Values

- `want_to_read` - Book is in reading list
- `currently_reading` - Currently reading this book
- `read` - Finished reading
- `abandoned` - Stopped reading
- `null` - No status (but has reading session)

## Tags

- **Status Tags**: Automatically created from `status` field
  - "Want to Read", "Currently Reading", "Read", "Abandoned"
- **Custom Tags**: User-defined tags stored in `tags` JSON array
  - Can be added/removed independently

## Query Patterns

### Common Queries

**Get user's reading history:**
```sql
SELECT rs.*, b.title, b.author
FROM reading_sessions rs
JOIN books b ON rs.book_id = b.id
WHERE rs.user_id = ?
ORDER BY rs.timestamp DESC
LIMIT 50;
```

**Get reading statistics:**
```sql
SELECT 
  COUNT(*) as total_sessions,
  SUM(duration_minutes) as total_duration,
  AVG(duration_minutes) as avg_duration,
  SUM(pages_read) as total_pages
FROM reading_sessions
WHERE user_id = ?;
```

**Get recommendations:**
```sql
SELECT r.*, b.title, b.author, b.cover_image_url
FROM recommendations r
JOIN books b ON r.book_id = b.id
WHERE r.user_id = ? 
  AND r.dismissed = FALSE
ORDER BY r.score DESC
LIMIT 10;
```

## Migration Strategy

Database migrations are managed using Alembic. To create a new migration:

```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

