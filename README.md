# Smart Bookshelf

A personal reading companion that learns your reading patterns and recommends the perfect book for any moment.

## Features

- **Smart Recommendations** - Get personalized book recommendations based on time of day, mood, and reading history
- **Reading Tracking** - Log reading sessions with mood and duration
- **AI-Powered** - Uses LLM (OpenAI, Groq, Hugging Face, or Together AI) to understand your preferences
- **Pattern Learning** - Learns from your reading history and gets smarter over time

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- PostgreSQL (optional - SQLite works for development)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file (optional - uses SQLite by default)
cp env.example .env

# Create database
python -c "from app.database import engine, Base; from app import models; Base.metadata.create_all(bind=engine)"

# Run server
uvicorn app.main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Configure LLM Provider (Optional)

Edit `backend/.env`:

```env
# Choose one LLM provider
LLM_PROVIDER=groq  # Options: openai, groq, huggingface, together
GROQ_API_KEY=your_key_here  # Get free key at https://console.groq.com
```

**Free Options:**
- **Groq**: Free tier available - fastest option
- **Hugging Face**: Free tier available
- **Together AI**: Free tier available
- **OpenAI**: Paid (but most accurate)

### Access the App

- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- API: http://localhost:8000

## Usage

1. **Get Recommendations**: Visit the Home page to see personalized recommendations
2. **Log Reading**: Go to the Log page to record reading sessions
3. **Manage Books**: View and organize books by status (Reading, Paused, Finished, Want to Read)

## Project Structure

```
bookshelf/
├── backend/              # FastAPI backend
│   ├── app/
│   │   ├── api/         # API endpoints
│   │   ├── core/        # Auth, exceptions, utilities
│   │   ├── services/    # Business logic
│   │   └── integrations/ # External APIs
│   └── requirements.txt
├── frontend/            # React frontend
│   └── src/
│       ├── components/  # Reusable components
│       ├── pages/       # Page components
│       └── services/    # API client
└── docs/                # Documentation
```

## Documentation

See the [docs/](docs/) directory for detailed documentation:
- [Getting Started Guide](docs/GETTING_STARTED.md)
- [Features Guide](docs/FEATURES.md)
- [API Reference](docs/API.md)
- [Architecture](docs/ARCHITECTURE.md)

## Troubleshooting

- **Database Issues**: SQLite works out of the box (default). For PostgreSQL, set `DATABASE_URL` in `.env`
- **LLM Provider Issues**: Check API key is set in `.env` and verify provider name is correct

## License

MIT
