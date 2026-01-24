# Getting Started

Complete guide to setting up and using Smart Bookshelf.

## Installation

### Step 1: Clone and Navigate

```bash
cd bookshelf
```

### Step 2: Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create database (SQLite by default)
python -c "from app.database import engine, Base; from app import models; Base.metadata.create_all(bind=engine)"
```

### Step 3: Configure (Optional)

Create `backend/.env` file:

```env
# Database (optional - SQLite is default)
DATABASE_URL=sqlite:///./bookshelf.db

# LLM Provider (choose one)
LLM_PROVIDER=groq
GROQ_API_KEY=your_key_here

# Or use OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_key_here
```

**Get Free API Keys:**
- Groq: https://console.groq.com (free, fast)
- Hugging Face: https://huggingface.co (free)
- Together AI: https://api.together.xyz (free tier)

### Step 4: Start Backend

```bash
uvicorn app.main:app --reload
```

Backend runs at: http://localhost:8000

### Step 5: Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

## First Steps

### 1. Log Your First Reading Session

1. Go to the "Log" page
2. Search for a book or add a new one:
   - Type a book title in the search bar
   - Select from search results or external APIs (Google Books, Open Library)
   - Or add manually by entering title and author
3. Enter required details:
   - **Duration**: Minutes spent reading (required)
   - **Mood**: Optional (relaxed, focused, curious, stressed, excited, calm)
4. Click "Log Session"

### 2. View Your Library

1. Go to the "Home" page (default landing page)
2. View your books organized by status:
   - **Reading**: Books you're currently reading
   - **Paused**: Books you've paused
   - **Finished**: Books you've completed
   - **Want to Read**: Books you want to read
3. Use filters to show specific statuses
4. Change book status using the status button on each book card

### 3. Get Your First Recommendation

1. Go to the "Home" page
2. You'll see a personalized recommendation at the top
3. Click the refresh button (↻) to get a new recommendation
4. Recommendations are automatically generated based on your reading patterns

## Understanding Recommendations

The system learns from:
- **What you read**: Books, genres, authors
- **When you read**: Time of day, day of week, month
- **Where you read**: Location patterns
- **How you feel**: Mood patterns
- **How long you read**: Reading pace and duration

The more you use it, the better it gets!

## Tips for Better Recommendations

1. **Log regularly**: The more reading sessions you log, the better the system understands you
2. **Add mood**: Include mood when logging sessions to help the system learn your patterns
3. **Update status**: Keep book statuses current (Reading, Paused, Finished, Want to Read)
4. **Be consistent**: Log every reading session to build accurate patterns

## Next Steps

- Read [Features Guide](FEATURES.md) to learn about all features
- Check [API Reference](API.md) for developers
- See [Architecture](ARCHITECTURE.md) for system design

