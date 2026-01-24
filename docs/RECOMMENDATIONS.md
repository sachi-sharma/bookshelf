# LLM-Based Recommendations

## Overview

The Smart Bookshelf app uses **LLM (Large Language Model)** to generate personalized book recommendations based on your reading preferences, patterns, and temporal context. The system learns from your actual reading history to provide contextually relevant recommendations.

## How It Works

1. **Collects Your Reading Data:**
   - Books you've read and rated
   - Favorite genres and authors
   - Reading sessions with timestamps
   - Reading moods and patterns
   - Current mood (if specified)

2. **Analyzes Temporal Patterns:**
   - **Time of Day**: What genres/authors you read during morning, afternoon, evening, night
   - **Day of Week**: Your reading preferences for different days
   - **Month/Season**: Seasonal reading patterns
   - All patterns are **inferred from your actual reading history**, not hardcoded

3. **Sends to LLM:**
   - Your reading profile and inferred patterns
   - Current temporal context (month, day, time)
   - List of books you've already read (to avoid)
   - LLM analyzes and recommends NEW books that match your patterns

4. **Returns Recommendations:**
   - Personalized book recommendations (not from a predefined list)
   - Books are created in the database if they don't exist
   - Explanation for each recommendation
   - Score (0.0-1.0) indicating match quality

## Algorithm Architecture

```
┌─────────────────────────────────────────────────────────┐
│              User Reading History                        │
│  - Books read                                            │
│  - Ratings and reviews                                   │
│  - Reading sessions                                      │
│  - Mood patterns                                         │
│  - Time patterns                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Pattern Analysis
                     ▼
┌─────────────────────────────────────────────────────────┐
│            Pattern Extraction                            │
│  - Preferred genres                                     │
│  - Favorite authors                                     │
│  - Mood preferences                                     │
│  - Time-of-day patterns                                 │
│  - Reading pace                                         │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ LLM Processing
                     ▼
┌─────────────────────────────────────────────────────────┐
│            LLM Recommendation                            │
│  - Analyzes patterns                                    │
│  - Generates book recommendations                        │
│  - Provides explanations                                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Scoring & Ranking
                     ▼
┌─────────────────────────────────────────────────────────┐
│            Top N Recommendations                        │
│  - Sorted by score                                      │
│  - Explanation generation                                │
│  - Factor breakdown                                     │
└─────────────────────────────────────────────────────────┘
```

## Key Features

### Temporal Context Awareness

The system considers:
- **Current Time**: What time of day you're requesting recommendations
- **Current Month**: Seasonal reading preferences
- **Current Day**: Day-of-week patterns
- **Historical Patterns**: What you actually read at similar times

**Example:**
- If you request recommendations on a Tuesday evening in December
- System checks: "What genres/authors do you typically read on Tuesday evenings?"
- System checks: "What genres/authors do you typically read in December?"
- Recommends books matching those patterns

### Pattern Inference (Not Hardcoded)

The system **learns from your reading history**:
- Analyzes your actual reading sessions
- Identifies top genres/authors/moods for each time period
- Only uses patterns when sufficient data exists
- Falls back to overall preferences if no pattern detected

### No Predefined Book List

- LLM recommends **real, published books** based on your preferences
- Books are created in the database if they don't exist
- Recommendations are not limited to books already in your database

## Setup

### Option 1: OpenAI (Paid)

1. **Get OpenAI API Key:**
   - Go to https://platform.openai.com/api-keys
   - Create a new API key
   - Copy the key

2. **Add to .env file:**
   ```bash
   LLM_PROVIDER=openai
   LLM_MODEL=gpt-4o-mini
   OPENAI_API_KEY=sk-your-api-key-here
   ```

### Option 2: Groq (FREE - Recommended!)

1. **Get Groq API Key:**
   - Go to https://console.groq.com
   - Sign up (free)
   - Create an API key

2. **Add to .env file:**
   ```bash
   LLM_PROVIDER=groq
   LLM_MODEL=llama-3.1-8b-instant
   GROQ_API_KEY=your-groq-api-key
   ```

### Option 3: Hugging Face (FREE)

1. **Get Hugging Face API Key (optional):**
   - Go to https://huggingface.co/settings/tokens
   - Create a token (optional for public models)

2. **Add to .env file:**
   ```bash
   LLM_PROVIDER=huggingface
   LLM_MODEL=meta-llama/Meta-Llama-3-8B-Instruct
   HUGGINGFACE_API_KEY=your-token (optional)
   ```

### Option 4: Together AI (FREE)

1. **Get Together AI API Key:**
   - Go to https://api.together.xyz/settings/api-keys
   - Create an API key

2. **Add to .env file:**
   ```bash
   LLM_PROVIDER=together
   LLM_MODEL=meta-llama/Llama-3-8b-chat-hf
   TOGETHER_API_KEY=your-together-api-key
   ```

## Temporal Pattern Analysis

The system analyzes your reading sessions to infer preferences:

### By Time of Day
- **Morning** (5:00-12:00): What genres/authors/moods you read
- **Afternoon** (12:00-17:00): What genres/authors/moods you read
- **Evening** (17:00-21:00): What genres/authors/moods you read
- **Night** (21:00-5:00): What genres/authors/moods you read

### By Month/Season
- Tracks what you read in each month
- Identifies seasonal patterns (summer reads, winter reads, etc.)

### By Day of Week
- Tracks what you read on different days
- Identifies weekday vs weekend patterns

## Pattern Analysis Details

### Genre Preferences

Extract preferred genres from user's reading history:

```python
genre_counts = {}
for preference in user_preferences:
    if preference.book.genre:
        genre_counts[preference.book.genre] += 1

# Normalize to weights
preferred_genres = normalize(genre_counts)
```

**Example:**
- User has read: 10 Fantasy, 5 Mystery, 3 Sci-Fi
- Weights: Fantasy=0.56, Mystery=0.28, Sci-Fi=0.16

### Author Preferences

Identify favorite authors based on high ratings:

```python
author_scores = {}
for preference in user_preferences:
    if preference.rating >= 4:  # 4+ stars
        author_scores[preference.book.author] += preference.rating

favorite_authors = top_n(author_scores, n=5)
```

### Mood Patterns

Analyze mood distribution across reading sessions:

```python
mood_counts = {}
for session in reading_sessions:
    if session.mood:
        mood_counts[session.mood] += 1

# Identify dominant moods
dominant_moods = top_n(mood_counts, n=3)
```

**Example:**
- User reads: 40% relaxed, 30% focused, 20% curious, 10% stressed
- When user selects "relaxed" mood, boost books that match relaxed reading patterns

### Reading Pace

Calculate average reading speed:

```python
paces = [s.reading_pace for s in sessions if s.reading_pace]
average_pace = mean(paces)  # pages per minute

# Use to recommend books of appropriate length
if average_pace > 1.0:
    # Fast reader - can handle longer books
    prefer_longer_books = True
```

## Example Recommendation Flow

1. **User requests recommendations** on Tuesday evening, December 15th, 7:00 PM

2. **System analyzes:**
   - Current context: Tuesday, December, Evening
   - Historical patterns:
     - "You typically read Fantasy and Mystery genres on Tuesday evenings"
     - "You typically read Fantasy and Sci-Fi in December"
     - "You often read books by J.K. Rowling and Brandon Sanderson in the evening"

3. **LLM receives:**
   - Your reading profile
   - Inferred patterns for Tuesday evening + December
   - List of books you've read (to avoid)

4. **LLM recommends:**
   - Books matching your Tuesday evening patterns
   - Books matching your December patterns
   - Books by authors you like in the evening
   - NEW books (not in your database)

5. **System creates books** if they don't exist and returns recommendations

## Cost

### Groq (Recommended - FREE!)
- Free tier available
- Fast responses
- Good quality recommendations

### OpenAI
- GPT-4o-mini: ~$0.15 per 1M input tokens, ~$0.60 per 1M output tokens
- Typical request: ~$0.001-0.01 per request

### Hugging Face
- Free tier available for public models
- May be slower than Groq

### Together AI
- Free tier available
- Good quality models

## Privacy

- Your reading data is sent to the LLM provider
- Data is used only for generating recommendations
- No data is stored by the provider beyond the API call
- See each provider's privacy policy for details

## Error Handling

- If LLM is unavailable: Returns error with helpful message
- If API key is missing: Clear error message
- If authentication fails: Detailed error information
- All errors are logged for debugging

## API Endpoints

### Get Recommendations
```http
GET /api/v1/recommendations?limit=10&current_mood=relaxed
```

### Get Quick Recommendation
```http
GET /api/v1/recommendations/quick?mood=curious&location=home&available_time_minutes=60
```

### Stream Recommendations (with thinking updates)
```http
GET /api/v1/recommendations/stream?limit=10&current_mood=relaxed
```

## Cold Start Problem

For new users with no reading history:

1. **Popular Books**: Recommend trending/popular books
2. **Genre Diversity**: Show books from multiple genres
3. **Quick Onboarding**: Prompt user to rate a few books
4. **External Data**: Use data from connected platforms

```python
def get_popular_books(limit=10):
    # Get books with most reading sessions
    # Or highest average ratings
    return db.query(Book).order_by(Book.popularity_score).limit(limit)
```

## Future Enhancements

### Machine Learning Approach

1. **Collaborative Filtering**
   - Find users with similar reading patterns
   - Recommend books they liked

2. **Deep Learning**
   - Neural collaborative filtering
   - Embedding-based recommendations

3. **Graph-Based**
   - Build book-user graph
   - Use graph algorithms (PageRank, etc.)

### Additional Signals

1. **Book Metadata**
   - Similarity based on description (TF-IDF, embeddings)
   - Tag matching
   - Publication date preferences

2. **Social Signals**
   - Friends' recommendations
   - Community ratings
   - Trending books

3. **Contextual Signals**
   - Weather
   - Location
   - Device type

## Performance Optimization

1. **Caching**
   - Cache user patterns
   - Cache recommendations (TTL: 1 hour)
   - Use Redis for fast lookups

2. **Pre-computation**
   - Pre-compute recommendations daily
   - Store top N for each user

3. **Incremental Updates**
   - Update patterns incrementally
   - Re-score only when patterns change significantly

## Evaluation Metrics

1. **Click-Through Rate (CTR)**
   - Percentage of recommendations clicked

2. **Diversity**
   - Measure genre/author diversity in recommendations

3. **Coverage**
   - Percentage of catalog that can be recommended

4. **User Satisfaction**
   - Explicit feedback (thumbs up/down)
   - Implicit feedback (reading sessions after recommendation)

