# Features Guide

Complete guide to all Smart Bookshelf features.

## Smart Recommendations

### Quick Recommendation

**"What Should I Read Right Now?"**

Get instant, contextual recommendations based on your current situation.

**How to use:**
1. Go to the Home page (default landing page)
2. You'll see a recommendation at the top with a detailed explanation
3. Click the refresh button (↻) to get a new recommendation
4. Recommendations are automatically personalized based on:
   - Current time of day, day of week, and season
   - Your recent reading patterns (last 30 days weighted more heavily)
   - Books you've enjoyed and their genres/authors
   - Your reading velocity patterns
   - Seasonal reading preferences
5. Each recommendation includes:
   - Book title and author
   - Detailed explanation (3-5 sentences) explaining why it's perfect for you right now
   - Connection to your reading history and patterns

**What it considers:**
- Current time of day (morning, afternoon, evening, night)
- Day of week (Monday-Sunday patterns)
- Month/season (seasonal reading preferences)
- Your mood and location
- Available reading time
- Books in your physical shelf
- Your reading history and patterns

### Recommendation System

The recommendation system uses advanced temporal analysis:

**Temporal Factors:**
- **Time of Day**: Morning, afternoon, evening, night patterns
- **Day of Week**: Monday-Sunday reading preferences
- **Season**: Spring, summer, fall, winter patterns
- **Recent Trends**: Last 30 days weighted more heavily than all-time patterns
- **Reading Velocity**: Pages per minute at different times of day

**Personalization:**
- Matches your favorite genres and authors
- Connects to books you've enjoyed
- Considers your reading patterns and statuses
- Avoids recommending books you've already read

## Reading Tracking

### Log Reading Sessions

Track when you read, what you read, and how you felt.

**How to use:**
1. Go to "Log" page
2. Select a book (or add new one if it doesn't exist)
3. Add details:
   - **Duration**: Minutes spent reading (required)
   - **Mood**: relaxed, focused, curious, stressed, excited, calm (optional)
4. Click "Log Session"

**Why it matters:**
- Helps system learn your reading patterns
- Tracks what books are in your physical shelf
- Builds reading statistics
- Improves recommendations

## Book Management

### View Your Books

View and manage all your books on the Home page.

**How to use:**
1. Go to the Home page (default landing page)
2. View books organized by status:
   - **Reading**: Books you're currently reading
   - **Paused**: Books you've paused
   - **Finished**: Books you've completed
   - **Want to Read**: Books you want to read
3. Use filters to show specific statuses
4. Click on any book to see details
5. Change book status using the status button on each book card

### Add Books

Add books to your collection when logging reading sessions.

**How to use:**
1. Go to "Log" page
2. Search for a book:
   - Type a book title in the search bar
   - Select from local search results or external APIs (Google Books, Open Library)
   - Book details are auto-filled from external APIs
3. Or add manually by entering title and author
4. Books are automatically added when you log a reading session

## Integrations

### External Book Search

Search for books using external APIs.

**Available sources:**
- Google Books (requires API key, optional)
- Open Library (free, no key needed)

**How to use:**
1. Go to "Log" page
2. Use search bar to find books
3. Select source (Google Books or Open Library)
4. View results with covers and details
5. Click to add book

## Home Page

Your reading companion - a quiet space for your books.

**Features:**
- **Recommendations**: See personalized book recommendations at the top with detailed explanations
- **Book Organization**: View books by status (Reading, Paused, Finished, Want to Read)
- **Status Management**: Change book status directly from book cards
- **Filters**: Filter books by status (All, Reading, Paused, Finished, Want to Read)
- **Grid Layout**: Responsive grid layout for easy browsing
- **Refresh Recommendations**: Click refresh button to get new recommendations based on latest patterns

## Tips for Best Experience

### For Better Recommendations

1. **Log regularly**: More data = better recommendations
2. **Be specific**: Include mood when logging sessions
3. **Update status**: Keep book statuses current (Reading, Paused, Finished)
4. **Refresh recommendations**: Click refresh to get new suggestions based on latest patterns

### For Better Statistics

1. **Log duration**: Track how long you read (required field)
2. **Be consistent**: Log every reading session
3. **Add context**: Include mood when available

### For Better Organization

1. **Set status**: Mark books as Reading, Paused, Finished, or Want to Read
2. **Use filters**: Filter books by status on the Home page
3. **Keep status current**: Update book status as you progress

## Privacy & Data

- All data stored locally (SQLite) or your database
- No data shared with third parties
- LLM providers only receive reading patterns (no personal info)
- You control all data

