# Integrations & Sync Agent

## Overview

The Smart Bookshelf application integrates with external reading platforms to search for books and sync user data. This document covers both the integration strategy and the autonomous sync agent system.

## Supported Platforms

### Current Integrations

1. **Open Library** - Free book search API
   - **Type**: Search-only
   - **Authentication**: None required
   - **Features**: Book search, ISBN lookup
   - **Rate Limits**: Generous free tier

2. **Google Books** - Google's book search API
   - **Type**: Search-only
   - **Authentication**: Optional API key (for higher rate limits)
   - **Features**: Book search, ISBN lookup, detailed metadata
   - **Rate Limits**: 1000 requests/day (with API key)

### Planned Integrations

- **StoryGraph** - Reading tracking and analytics (planned)
- **Kindle** - E-book library (planned)
- **Apple Books** - Apple Books library (planned)

## Integration Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                       │
│  "Connect Platform" button                             │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ User connects platform
                     ▼
┌─────────────────────────────────────────────────────────┐
│          External Account Storage                       │
│  - Store platform_user_id                              │
│  - Store sync_enabled flag                             │
│  - Store last_synced_at                                │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Manual Sync (via API)
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Sync Agent                                 │
│  - Autonomous decision making                           │
│  - Automatic retry logic                                │
│  - Error handling and recovery                          │
│  - Data processing                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Uses Integration
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Integration Module                         │
│  - Search books                                         │
│  - Get book by ISBN                                     │
│  - Normalize data to our schema                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Stores in database
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Smart Bookshelf Database                   │
│  - Books                                                │
│  - Ratings/Reviews                                      │
│  - Reading Status                                       │
└─────────────────────────────────────────────────────────┘
```

## Integration Base Interface

All integrations implement the `IntegrationBase` interface:

```python
class IntegrationBase(ABC):
    def authenticate(self) -> bool:
        """Authenticate with the platform"""
        pass
    
    def search_books(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Search for books"""
        pass
    
    def get_book_by_isbn(self, isbn: str) -> Dict[str, Any]:
        """Get book details by ISBN"""
        pass
    
    def sync_books(self) -> List[Dict[str, Any]]:
        """Sync books from the platform (if supported)"""
        pass
    
    def sync_ratings(self) -> List[Dict[str, Any]]:
        """Sync ratings and reviews (if supported)"""
        pass
    
    def sync_reading_status(self) -> List[Dict[str, Any]]:
        """Sync current reading status (if supported)"""
        pass
```

## Sync Agent

The **Sync Agent** (`app/agents/sync_agent.py`) is an autonomous system that handles platform syncing intelligently.

### What is an Agent?

An **agent** is an autonomous system that can:
- **Make decisions** about when to sync
- **Handle errors** automatically with retries
- **Recover from failures** without user intervention
- **Log actions** for debugging and monitoring

### How It Works

#### 1. Decision Making

The agent decides if an account should be synced based on:
- **Last sync time**: Only syncs if last sync was > 24 hours ago
- **Sync enabled**: Respects user's sync preferences
- **Account status**: Checks if account is connected

#### 2. Autonomous Error Handling

The agent automatically:
- **Retries failed syncs** up to 3 times
- **Waits between retries** (60-second delay)
- **Logs all errors** for debugging
- **Continues processing** even if some items fail

#### 3. Data Processing

The agent:
- **Authenticates** with the platform
- **Syncs books** and creates them in the database
- **Syncs ratings** and updates preferences
- **Updates sync timestamp** after successful sync

### Usage

#### Manual Sync (via API)

```python
from app.agents import SyncAgent

# Create agent
agent = SyncAgent(db, user_id=1)

# Sync a specific platform
integration = OpenLibraryIntegration()
result = agent.sync_specific_platform("openlibrary", integration)

# Check result
if result["success"]:
    print(f"Synced {result['books_synced']} books")
else:
    print(f"Errors: {result['errors']}")
```

#### Automatic Sync (Future)

The agent can be extended to run automatically:
- **Background tasks**: Using Celery or similar
- **Scheduled jobs**: Daily sync for all accounts
- **Event-driven**: Sync when new books are added

### Agent Features

1. **Intelligent Retry**: Automatically retries failed operations
2. **Error Recovery**: Handles partial failures gracefully
3. **Logging**: Comprehensive logging for debugging
4. **Flexible**: Works with any integration that implements `IntegrationBase`

### Example Flow

```
1. User clicks "Sync" → API endpoint called
2. Agent created → SyncAgent(db, user_id)
3. Agent checks → should_sync(account) → True
4. Agent syncs → sync_account(account, integration)
   - Authenticates
   - Syncs books (with retry on failure)
   - Syncs ratings (with retry on failure)
   - Updates timestamp
5. Returns result → {success, books_synced, ratings_synced, errors}
```

### Benefits

- **Autonomous**: Handles errors without user intervention
- **Reliable**: Retries ensure syncs complete even with temporary failures
- **Observable**: Comprehensive logging for monitoring
- **Extensible**: Easy to add new platforms or features

## Data Normalization

Each platform has different data formats. We normalize to our schema:

```python
def normalize_book_data(platform_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert platform-specific data to our book schema"""
    return {
        "title": platform_data.get("title", ""),
        "author": platform_data.get("author", ""),
        "isbn": platform_data.get("isbn"),
        "genre": platform_data.get("genre"),
        "description": platform_data.get("description"),
        "cover_image_url": platform_data.get("cover_image_url"),
        "page_count": platform_data.get("page_count"),
        "publication_date": parse_date(platform_data.get("publication_date"))
    }
```

## Sync Strategy

### Manual Sync
- User triggers sync via UI or API
- Immediate execution
- Show progress indicator
- Display results (books synced, ratings synced)

### Automatic Sync (Future)
- Background job (Celery, cron)
- Daily sync for active accounts
- Respect rate limits
- Error handling and retry logic

### Incremental Sync
- Track `last_synced_at` timestamp
- Only fetch new/updated items since last sync
- Reduces API calls and processing time

## Security Considerations

### Token Storage
- **Encrypt access tokens** at rest (future)
- Use environment variables for API keys
- Never log tokens
- Store refresh tokens securely

### API Key Management
- Store API keys in environment variables
- Never commit keys to version control
- Rotate keys periodically
- Use different keys for dev/staging/prod

## Error Handling

### Common Errors

**400 Bad Request:**
- Invalid platform or parameters
- Solution: Check platform name and request format

**404 Not Found:**
- Book not found
- Solution: Verify ISBN or search query

**429 Rate Limited:**
- Too many requests
- Solution: Implement exponential backoff (handled by agent)

**500 Platform Error:**
- Platform API issue
- Solution: Retry with backoff (handled by agent), log error

### Retry Logic

The sync agent automatically handles retries:
- Up to 3 attempts
- 60-second delay between retries
- Logs all errors for debugging

## Testing Strategy

### Mock Integrations
- Create mock integration classes for testing
- Simulate API responses
- Test error scenarios

### Integration Tests
- Use test accounts on each platform
- Test search functionality
- Test error handling

## Future Enhancements

1. **Bidirectional Sync**: Push reading data back to platforms
2. **Real-time Updates**: Webhook support for instant updates
3. **Batch Processing**: Sync multiple platforms in parallel
4. **Conflict Resolution**: Handle conflicting data from multiple sources
5. **Data Deduplication**: Merge duplicate books from different platforms

## Implementation Checklist

- [x] Base integration interface
- [x] Open Library integration
- [x] Google Books integration
- [x] Sync agent for autonomous syncing
- [x] Error handling and retries
- [ ] Token encryption
- [ ] Automatic token refresh
- [ ] Rate limiting
- [ ] Background sync jobs
- [ ] User notification system
- [ ] Integration tests

