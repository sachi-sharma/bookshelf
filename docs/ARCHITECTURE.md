# Architecture

High-level overview of Smart Bookshelf system design.

## System Overview

```
┌─────────────────┐
│   Frontend      │  React + TypeScript + Tailwind
│   (Port 5173)   │
└────────┬────────┘
         │
         │ HTTP/REST
         │
┌────────▼────────┐
│   Backend API   │  FastAPI (Python)
│   (Port 8000)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼──────────┐
│  DB   │ │ Integrations│
│SQLite │ │ (Open Library│
│/PG    │ │Google Books)│
└───────┘ └─────────────┘
```

## Backend Structure

```
backend/
├── app/
│   ├── api/              # API endpoints (FastAPI routers)
│   │   ├── books.py
│   │   ├── sessions.py
│   │   ├── recommendations.py
│   │   ├── preferences.py
│   │   ├── integrations.py
│   │   └── users.py
│   ├── agents/           # Autonomous agent systems
│   │   ├── sync_agent.py # Sync agent for platform syncing
│   │   └── __init__.py
│   ├── core/             # Core utilities
│   │   ├── auth.py       # Authentication
│   │   ├── exceptions.py # Custom exceptions
│   │   ├── database.py    # Transaction management
│   │   ├── middleware.py  # Request logging
│   │   └── validation.py # Input validation
│   ├── services/         # Business logic
│   │   ├── book_service.py
│   │   ├── reading_service.py
│   │   ├── llm_recommendation_service.py
│   │   └── recommendation_service.py
│   ├── integrations/     # External API clients
│   │   ├── base.py       # Integration base interface
│   │   ├── google_books.py
│   │   └── openlibrary.py
│   ├── models.py         # Database models (SQLAlchemy)
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # Database connection
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI app
└── alembic/              # Database migrations
```

## Frontend Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   │   ├── Layout.tsx
│   │   └── QuickRecommendation.tsx
│   ├── pages/           # Page components
│   │   ├── Dashboard.tsx
│   │   ├── Recommendations.tsx
│   │   ├── MyBooks.tsx
│   │   ├── LogReading.tsx
│   │   ├── AddBook.tsx
│   │   └── Integrations.tsx
│   ├── services/        # API client
│   │   └── api.ts
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
```

## Data Flow

### Recommendation Flow

1. **User Request** → Frontend calls `/recommendations/quick`
2. **Context Gathering** → Backend collects:
   - Current time, day, month
   - User's mood, location, available time
   - Available books in shelf
   - Reading history and patterns
3. **Pattern Analysis** → Service analyzes:
   - Temporal patterns (time of day, day of week, month)
   - Location patterns
   - Mood patterns
   - Genre/author preferences by context
4. **LLM Call** → Sends context to LLM provider
5. **Response Processing** → Filters and ranks recommendations
6. **Return** → Sends recommendation with explanation

### Reading Session Flow

1. **User Logs Session** → Frontend calls `/reading-sessions`
2. **Validation** → Backend validates data
3. **Database** → Creates session record
4. **Pattern Update** → Updates reading patterns (background)
5. **Response** → Returns created session

### Integration Sync Flow

1. **User Triggers Sync** → Frontend calls `/integrations/{platform}/sync`
2. **Agent Creation** → Backend creates `SyncAgent` instance
3. **Agent Decision** → Agent checks if sync is needed (last sync >24h ago)
4. **Agent Sync** → Agent autonomously:
   - Authenticates with platform
   - Syncs books (with retry on failure)
   - Syncs ratings (with retry on failure)
   - Updates sync timestamp
5. **Response** → Returns sync results with details

## Agent System

The system includes autonomous agents that handle complex operations:

### Sync Agent

The **Sync Agent** (`app/agents/sync_agent.py`) handles platform syncing autonomously:

- **Decision Making**: Decides when to sync based on last sync time
- **Error Handling**: Automatic retries with exponential backoff
- **Data Processing**: Syncs books, ratings, and updates timestamps
- **Logging**: Comprehensive logging for debugging

See [AGENT_SYNC.md](AGENT_SYNC.md) for detailed documentation.

## Database Schema

### Core Tables

- **users**: User accounts
- **books**: Book catalog
- **reading_sessions**: Reading activity logs
- **book_preferences**: User preferences (ratings, status, tags)
- **recommendations**: Generated recommendations
- **external_accounts**: Connected platforms (Open Library, Google Books)

### Key Relationships

- User → Reading Sessions (one-to-many)
- User → Book Preferences (one-to-many)
- User → Recommendations (one-to-many)
- Book → Reading Sessions (one-to-many)
- Book → Preferences (one-to-many)

## Key Technologies

### Backend
- **FastAPI**: Modern Python web framework
- **SQLAlchemy**: ORM for database
- **Pydantic**: Data validation
- **Alembic**: Database migrations
- **JWT**: Authentication

### Frontend
- **React**: UI framework
- **TypeScript**: Type safety
- **Tailwind CSS**: Styling
- **React Query**: Data fetching
- **React Router**: Navigation

### AI/ML
- **LLM Providers**: OpenAI, Groq, Hugging Face, Together AI
- **Pattern Analysis**: Temporal, location, mood patterns
- **Recommendation Engine**: Context-aware suggestions

## Security

- **Authentication**: JWT tokens
- **Password Hashing**: bcrypt
- **Input Validation**: Pydantic schemas
- **Error Handling**: Custom exceptions
- **Request Logging**: Middleware

## Performance

- **Database**: Indexed queries
- **Caching**: React Query for frontend
- **Connection Pooling**: SQLAlchemy
- **Async Operations**: FastAPI async endpoints

## Deployment

### Development
- SQLite database (default)
- Local file storage
- Development server (uvicorn --reload)

### Production
- PostgreSQL database
- Environment variables for config
- Production ASGI server (gunicorn + uvicorn)
- Static file serving

## Extensibility

### Adding New Integrations
1. Create integration class in `app/integrations/`
2. Implement `IntegrationBase` interface
3. Add API endpoint in `app/api/integrations.py`
4. Add frontend UI in `frontend/src/pages/Integrations.tsx`
5. Sync agent automatically handles new integrations

### Adding New LLM Providers
1. Add provider config in `app/config.py`
2. Add provider function in `app/services/llm_recommendation_service.py`
3. Update provider selection logic

### Adding New Agents
1. Create agent class in `app/agents/`
2. Implement autonomous decision-making logic
3. Add error handling and retry logic
4. Integrate with API endpoints

### Adding New Features
1. Create service in `app/services/`
2. Add API endpoint in `app/api/`
3. Add frontend component/page
4. Update database schema if needed
