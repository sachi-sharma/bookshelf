from sqlalchemy.orm import Session
from app import models, schemas
from typing import List, Optional, Callable
from datetime import datetime, timedelta, timezone
from app.config import settings
import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

try:
    import openai
    # Handle both old (0.x) and new (1.x) API versions
    try:
        from openai import OpenAI
        OPENAI_AVAILABLE = True
        OPENAI_NEW_API = True  # 1.x API
    except ImportError:
        # Try old API (0.x)
        OPENAI_AVAILABLE = True
        OPENAI_NEW_API = False  # 0.x API
        OpenAI = None  # Will use openai.ChatCompletion instead
except ImportError:
    OPENAI_AVAILABLE = False
    OPENAI_NEW_API = False
    logger.warning("OpenAI library not available. Install with: pip install openai")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available. Install with: pip install httpx")


def get_user_reading_preferences(db: Session, user_id: int = 1) -> dict:
    """Get user's reading preferences to feed to LLM"""
    # Get reading sessions
    sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id
    ).all()
    
    # Get book preferences (ratings, reviews)
    preferences = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id
    ).all()
    
    # Get all books user has interacted with - include all with their status
    all_books_with_status = []
    read_books = []  # Only for the "don't recommend" list
    
    for pref in preferences:
        if pref.book:
            book_info = {
                "title": pref.book.title,
                "author": pref.book.author,
                "genre": pref.book.genre,
                "rating": pref.rating,
                "review": pref.review,
                "status": pref.status or "unknown"
            }
            # Add to comprehensive list with status
            all_books_with_status.append(book_info)
            
            # Only add to read_books if actually read (for exclusion list)
            if pref.status == "read":
                read_books.append(book_info)
    
    # Get mood patterns from sessions
    moods = [s.mood for s in sessions if s.mood]
    mood_counts = {}
    for mood in moods:
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
    
    # Get genre preferences
    genre_counts = {}
    for pref in preferences:
        if pref.book and pref.book.genre:
            genre_counts[pref.book.genre] = genre_counts.get(pref.book.genre, 0) + 1
    
    # Get favorite authors (rated 4+ stars)
    favorite_authors = []
    for pref in preferences:
        if pref.book and pref.book.author and pref.rating and pref.rating >= 4:
            favorite_authors.append(pref.book.author)
    
    return {
        "read_books": read_books,  # Only books with status="read" - for exclusion
        "all_books": all_books_with_status,  # All books with their statuses
        "favorite_genres": list(genre_counts.keys()),
        "favorite_authors": list(set(favorite_authors)),
        "mood_patterns": mood_counts,
        "total_books_read": len(read_books),
        "total_sessions": len(sessions)
    }


def generate_llm_recommendations(
    db: Session,
    user_id: int = 1,
    limit: int = 3,  # Default to 3 top recommendations
    current_mood: Optional[str] = None,
    thinking_callback: Optional[Callable[[str], None]] = None
) -> List[schemas.RecommendationResponse]:
    """Generate recommendations using LLM based on reading preferences"""
    
    # Check provider availability
    provider = settings.llm_provider.lower()
    
    if provider == "openai":
        if not OPENAI_AVAILABLE:
            raise ValueError("OpenAI library not available. Install with: pip install openai")
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env file")
    elif provider == "groq":
        if not HTTPX_AVAILABLE:
            raise ValueError("httpx library not available. Install with: pip install httpx")
        if not settings.groq_api_key:
            raise ValueError("Groq API key not configured. Set GROQ_API_KEY in .env file. Get free key at https://console.groq.com")
    elif provider == "huggingface":
        if not HTTPX_AVAILABLE:
            raise ValueError("httpx library not available. Install with: pip install httpx")
        # Hugging Face API key is optional for free tier
    elif provider == "together":
        if not HTTPX_AVAILABLE:
            raise ValueError("httpx library not available. Install with: pip install httpx")
        if not settings.together_api_key:
            raise ValueError("Together AI API key not configured. Set TOGETHER_API_KEY in .env file")
    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'openai', 'groq', 'huggingface', or 'together'")
    
    # Get user's reading preferences
    if thinking_callback:
        thinking_callback("Analyzing your reading preferences...")
    preferences = get_user_reading_preferences(db, user_id)
    
    if thinking_callback:
        book_count = len(preferences['read_books'])
        book_word = "book" if book_count == 1 else "books"
        thinking_callback(f"Found {book_count} {book_word} you've read...")
    
    # Get list of books user has already read (for exclusion check)
    read_books_info = []
    read_preferences = db.query(models.BookPreference).filter(
        models.BookPreference.user_id == user_id,
        models.BookPreference.status == "read"
    ).all()
    for pref in read_preferences:
        if pref.book:
            read_books_info.append({
                "title": pref.book.title.lower().strip(),
                "author": (pref.book.author or "").lower().strip()
            })
    
    # Get reading sessions for additional context
    sessions = db.query(models.ReadingSession).filter(
        models.ReadingSession.user_id == user_id
    ).all()
    
    # Analyze temporal patterns from reading sessions
    # Use local time for current time of day (what time it is for the user right now)
    # Use UTC-aware datetime for comparing with database timestamps (which are timezone-aware)
    now_local = datetime.now()  # Local time for user's current context
    now_utc = datetime.now(timezone.utc)  # UTC for database comparisons
    current_month = now_local.month
    current_day_of_week = now_local.strftime("%A")  # Monday, Tuesday, etc.
    current_hour = now_local.hour
    current_time_of_day = "morning" if 5 <= current_hour < 12 else "afternoon" if 12 <= current_hour < 17 else "evening" if 17 <= current_hour < 21 else "night"
    
    # Analyze reading patterns by time, location, and mood - infer preferences from actual history
    sessions_by_month = defaultdict(int)
    sessions_by_day = defaultdict(int)
    sessions_by_time = defaultdict(int)
    genres_by_time = defaultdict(list)
    genres_by_month = defaultdict(list)
    genres_by_day = defaultdict(list)
    genres_by_location = defaultdict(list)
    authors_by_time = defaultdict(list)
    authors_by_month = defaultdict(list)
    authors_by_day = defaultdict(list)
    authors_by_location = defaultdict(list)
    moods_by_time = defaultdict(list)
    moods_by_month = defaultdict(list)
    moods_by_day = defaultdict(list)
    moods_by_location = defaultdict(list)
    locations_by_time = defaultdict(list)
    locations_by_month = defaultdict(list)
    locations_by_day = defaultdict(list)
    location_counts = defaultdict(int)
    
    for session in sessions:
        if session.timestamp:
            # Month patterns
            session_month = session.timestamp.month
            sessions_by_month[session_month] += 1
            
            # Day of week patterns
            session_day = session.timestamp.strftime("%A")
            sessions_by_day[session_day] += 1
            
            # Time of day patterns
            session_hour = session.timestamp.hour
            if 5 <= session_hour < 12:
                time_key = "morning"
            elif 12 <= session_hour < 17:
                time_key = "afternoon"
            elif 17 <= session_hour < 21:
                time_key = "evening"
            else:
                time_key = "night"
            sessions_by_time[time_key] += 1
            
            # Location patterns
            if session.location:
                location_counts[session.location] += 1
                locations_by_time[time_key].append(session.location)
                locations_by_month[session_month].append(session.location)
                locations_by_day[session_day].append(session.location)
            
            # Collect genre, author, and mood preferences by time, location
            if session.book:
                if session.book.genre:
                    genres_by_time[time_key].append(session.book.genre)
                    genres_by_month[session_month].append(session.book.genre)
                    genres_by_day[session_day].append(session.book.genre)
                    if session.location:
                        genres_by_location[session.location].append(session.book.genre)
                if session.book.author:
                    authors_by_time[time_key].append(session.book.author)
                    authors_by_month[session_month].append(session.book.author)
                    authors_by_day[session_day].append(session.book.author)
                    if session.location:
                        authors_by_location[session.location].append(session.book.author)
            if session.mood:
                moods_by_time[time_key].append(session.mood)
                moods_by_month[session_month].append(session.mood)
                moods_by_day[session_day].append(session.mood)
                if session.location:
                    moods_by_location[session.location].append(session.mood)
    
    # Find most active reading times
    most_active_month = max(sessions_by_month.items(), key=lambda x: x[1])[0] if sessions_by_month else None
    most_active_day = max(sessions_by_day.items(), key=lambda x: x[1])[0] if sessions_by_day else None
    most_active_time = max(sessions_by_time.items(), key=lambda x: x[1])[0] if sessions_by_time else None
    
    # Infer genre preferences by time of day, location from actual history
    def get_top_items(items_list, top_n=3):
        """Get top N most common items from a list"""
        if not items_list:
            return []
        counts = defaultdict(int)
        for item in items_list:
            counts[item] += 1
        return [item for item, count in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]]
    
    # Top locations
    top_locations = get_top_items([loc for loc, count in location_counts.items()], top_n=5)
    
    # Preferences by time of day
    favorite_genres_by_time = {}
    favorite_authors_by_time = {}
    favorite_moods_by_time = {}
    favorite_locations_by_time = {}
    for time_key in ["morning", "afternoon", "evening", "night"]:
        if genres_by_time[time_key]:
            favorite_genres_by_time[time_key] = get_top_items(genres_by_time[time_key])
        if authors_by_time[time_key]:
            favorite_authors_by_time[time_key] = get_top_items(authors_by_time[time_key])
        if moods_by_time[time_key]:
            favorite_moods_by_time[time_key] = get_top_items(moods_by_time[time_key])
        if locations_by_time[time_key]:
            favorite_locations_by_time[time_key] = get_top_items(locations_by_time[time_key])
    
    # Preferences by month/season
    favorite_genres_by_month = {}
    favorite_authors_by_month = {}
    favorite_moods_by_month = {}
    favorite_locations_by_month = {}
    for month in range(1, 13):
        if genres_by_month[month]:
            favorite_genres_by_month[month] = get_top_items(genres_by_month[month])
        if authors_by_month[month]:
            favorite_authors_by_month[month] = get_top_items(authors_by_month[month])
        if moods_by_month[month]:
            favorite_moods_by_month[month] = get_top_items(moods_by_month[month])
        if locations_by_month[month]:
            favorite_locations_by_month[month] = get_top_items(locations_by_month[month])
    
    # Preferences by day of week
    favorite_genres_by_day = {}
    favorite_authors_by_day = {}
    favorite_moods_by_day = {}
    favorite_locations_by_day = {}
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]:
        if genres_by_day[day]:
            favorite_genres_by_day[day] = get_top_items(genres_by_day[day])
        if authors_by_day[day]:
            favorite_authors_by_day[day] = get_top_items(authors_by_day[day])
        if moods_by_day[day]:
            favorite_moods_by_day[day] = get_top_items(moods_by_day[day])
        if locations_by_day[day]:
            favorite_locations_by_day[day] = get_top_items(locations_by_day[day])
    
    # Preferences by location
    favorite_genres_by_location = {}
    favorite_authors_by_location = {}
    favorite_moods_by_location = {}
    for location in top_locations:
        if genres_by_location[location]:
            favorite_genres_by_location[location] = get_top_items(genres_by_location[location])
        if authors_by_location[location]:
            favorite_authors_by_location[location] = get_top_items(authors_by_location[location])
        if moods_by_location[location]:
            favorite_moods_by_location[location] = get_top_items(moods_by_location[location])
    
    # Month name mapping
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    # Season detection
    def get_season(month: int) -> str:
        """Get season from month"""
        if month in [12, 1, 2]:
            return "Winter"
        elif month in [3, 4, 5]:
            return "Spring"
        elif month in [6, 7, 8]:
            return "Summer"
        else:
            return "Fall"
    
    current_season = get_season(current_month)
    
    # Analyze recent trends (last 30 days) vs all-time patterns
    thirty_days_ago = now_utc - timedelta(days=30)
    
    # Normalize timestamps for comparison (handle both timezone-aware and naive)
    def normalize_datetime(dt):
        """Normalize datetime to UTC-aware for comparison"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # Naive datetime - assume UTC
            return dt.replace(tzinfo=timezone.utc)
        # Already timezone-aware - convert to UTC
        return dt.astimezone(timezone.utc)
    
    normalized_thirty_days_ago = normalize_datetime(thirty_days_ago)
    recent_sessions = [
        s for s in sessions 
        if s.timestamp and normalize_datetime(s.timestamp) >= normalized_thirty_days_ago
    ]
    
    # Time-weighted analysis: recent sessions get higher weight
    genres_by_time_weighted = defaultdict(lambda: defaultdict(float))
    authors_by_time_weighted = defaultdict(lambda: defaultdict(float))
    genres_by_month_weighted = defaultdict(lambda: defaultdict(float))
    authors_by_month_weighted = defaultdict(lambda: defaultdict(float))
    
    for session in sessions:
        if session.timestamp and session.book:
            # Calculate weight: more recent = higher weight (exponential decay)
            # Normalize timestamps for comparison
            normalized_session_ts = normalize_datetime(session.timestamp)
            normalized_now = normalize_datetime(now_utc)
            days_ago = (normalized_now - normalized_session_ts).days
            weight = max(0.1, 1.0 / (1.0 + days_ago / 30.0))  # Decay over ~30 days
            
            session_month = session.timestamp.month
            session_hour = session.timestamp.hour
            time_key = "morning" if 5 <= session_hour < 12 else "afternoon" if 12 <= session_hour < 17 else "evening" if 17 <= session_hour < 21 else "night"
            
            if session.book.genre:
                genres_by_time_weighted[time_key][session.book.genre] += weight
                genres_by_month_weighted[session_month][session.book.genre] += weight
            if session.book.author:
                authors_by_time_weighted[time_key][session.book.author] += weight
                authors_by_month_weighted[session_month][session.book.author] += weight
    
    # Get weighted top preferences
    def get_weighted_top_items(weighted_dict, top_n=3):
        """Get top N items by weighted score"""
        if not weighted_dict:
            return []
        return [item for item, score in sorted(weighted_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]]
    
    # Recent vs all-time comparison
    recent_genres_by_time = defaultdict(list)
    recent_authors_by_time = defaultdict(list)
    recent_genres_by_month = defaultdict(list)
    recent_authors_by_month = defaultdict(list)
    
    for session in recent_sessions:
        if session.book and session.timestamp:
            session_month = session.timestamp.month
            session_hour = session.timestamp.hour
            time_key = "morning" if 5 <= session_hour < 12 else "afternoon" if 12 <= session_hour < 17 else "evening" if 17 <= session_hour < 21 else "night"
            
            if session.book.genre:
                recent_genres_by_time[time_key].append(session.book.genre)
                recent_genres_by_month[session_month].append(session.book.genre)
            if session.book.author:
                recent_authors_by_time[time_key].append(session.book.author)
                recent_authors_by_month[session_month].append(session.book.author)
    
    # Reading velocity by time of day (pages per minute)
    reading_velocity_by_time = defaultdict(list)
    for session in sessions:
        if session.timestamp and session.pages_read and session.duration_minutes and session.duration_minutes > 0:
            session_hour = session.timestamp.hour
            time_key = "morning" if 5 <= session_hour < 12 else "afternoon" if 12 <= session_hour < 17 else "evening" if 17 <= session_hour < 21 else "night"
            velocity = session.pages_read / session.duration_minutes
            reading_velocity_by_time[time_key].append(velocity)
    
    avg_velocity_by_time = {}
    for time_key, velocities in reading_velocity_by_time.items():
        if velocities:
            avg_velocity_by_time[time_key] = sum(velocities) / len(velocities)
    
    # Seasonal patterns
    genres_by_season = defaultdict(list)
    authors_by_season = defaultdict(list)
    for session in sessions:
        if session.timestamp and session.book:
            season = get_season(session.timestamp.month)
            if session.book.genre:
                genres_by_season[season].append(session.book.genre)
            if session.book.author:
                authors_by_season[season].append(session.book.author)
    
    favorite_genres_by_season = {}
    favorite_authors_by_season = {}
    for season in ["Spring", "Summer", "Fall", "Winter"]:
        if genres_by_season[season]:
            favorite_genres_by_season[season] = get_top_items(genres_by_season[season])
        if authors_by_season[season]:
            favorite_authors_by_season[season] = get_top_items(authors_by_season[season])
    
    # Create prompt for LLM - recommend NEW books based on reading patterns
    prompt = f"""You are a book recommendation assistant. Based on the user's reading patterns, preferences, and metadata, recommend {limit} NEW books that they haven't read yet.

IMPORTANT: 
- Do NOT recommend books the user has already read (see list below)
- Recommend REAL, EXISTING books that match their reading patterns
- Provide complete book information (title, author, genre, description)
- Base recommendations on their reading patterns, not on a predefined list

User's Reading Profile:
- Total books read: {len(preferences['read_books'])} books
- Favorite genres: {', '.join(preferences['favorite_genres']) if preferences['favorite_genres'] else 'None specified'}
- Favorite authors: {', '.join(preferences['favorite_authors']) if preferences['favorite_authors'] else 'None specified'}
- Reading moods: {', '.join(preferences['mood_patterns'].keys()) if preferences['mood_patterns'] else 'None specified'}
- Current mood: {current_mood if current_mood else 'Not specified'}
- Total reading sessions: {preferences['total_sessions']}

Books they've read (DO NOT recommend these - check titles and authors carefully):
{json.dumps(preferences['read_books'][:20], indent=2) if preferences['read_books'] else 'No books read yet'}

All books in their library with status (for context - understand their reading patterns and statuses):
{json.dumps(preferences.get('all_books', [])[:30], indent=2) if preferences.get('all_books') else 'No books in library'}

Reading patterns from sessions:
- Average session duration: {sum([s.duration_minutes for s in sessions if s.duration_minutes]) / len([s for s in sessions if s.duration_minutes]) if [s for s in sessions if s.duration_minutes] else 0:.1f} minutes
- Common moods: {', '.join(set([s.mood for s in sessions if s.mood])) if sessions else 'None'}
- Total pages read: {sum([s.pages_read for s in sessions if s.pages_read]) if sessions else 0}
- Top reading locations: {', '.join(top_locations) if top_locations else 'None specified'}

TEMPORAL CONTEXT (Inferred from Reading History):
- Current time: {month_names.get(current_month, 'Unknown')} {current_day_of_week} {current_time_of_day} ({current_hour}:00)
- Current season: {current_season}
- Most active reading month: {month_names.get(most_active_month, 'N/A') if most_active_month else 'N/A'}
- Most active reading day: {most_active_day if most_active_day else 'N/A'}
- Most active reading time: {most_active_time if most_active_time else 'N/A'}
- Recent activity (last 30 days): {len(recent_sessions)} sessions (vs {len(sessions)} total)

Inferred Preferences for {current_time_of_day} (from your reading history):
- Favorite genres during {current_time_of_day}: {', '.join(favorite_genres_by_time.get(current_time_of_day, [])) if favorite_genres_by_time.get(current_time_of_day) else 'No pattern detected'}
- Favorite authors during {current_time_of_day}: {', '.join(favorite_authors_by_time.get(current_time_of_day, [])) if favorite_authors_by_time.get(current_time_of_day) else 'No pattern detected'}
- Common moods during {current_time_of_day}: {', '.join(favorite_moods_by_time.get(current_time_of_day, [])) if favorite_moods_by_time.get(current_time_of_day) else 'No pattern detected'}
- Common locations during {current_time_of_day}: {', '.join(favorite_locations_by_time.get(current_time_of_day, [])) if favorite_locations_by_time.get(current_time_of_day) else 'No pattern detected'}

Inferred Preferences for {month_names.get(current_month, 'this month')} (from your reading history):
- Favorite genres in {month_names.get(current_month, 'this month')}: {', '.join(favorite_genres_by_month.get(current_month, [])) if favorite_genres_by_month.get(current_month) else 'No pattern detected'}
- Favorite authors in {month_names.get(current_month, 'this month')}: {', '.join(favorite_authors_by_month.get(current_month, [])) if favorite_authors_by_month.get(current_month) else 'No pattern detected'}
- Common moods in {month_names.get(current_month, 'this month')}: {', '.join(favorite_moods_by_month.get(current_month, [])) if favorite_moods_by_month.get(current_month) else 'No pattern detected'}
- Common locations in {month_names.get(current_month, 'this month')}: {', '.join(favorite_locations_by_month.get(current_month, [])) if favorite_locations_by_month.get(current_month) else 'No pattern detected'}

Inferred Preferences for {current_day_of_week} (from your reading history):
- Favorite genres on {current_day_of_week}: {', '.join(favorite_genres_by_day.get(current_day_of_week, [])) if favorite_genres_by_day.get(current_day_of_week) else 'No pattern detected'}
- Favorite authors on {current_day_of_week}: {', '.join(favorite_authors_by_day.get(current_day_of_week, [])) if favorite_authors_by_day.get(current_day_of_week) else 'No pattern detected'}
- Common moods on {current_day_of_week}: {', '.join(favorite_moods_by_day.get(current_day_of_week, [])) if favorite_moods_by_day.get(current_day_of_week) else 'No pattern detected'}
- Common locations on {current_day_of_week}: {', '.join(favorite_locations_by_day.get(current_day_of_week, [])) if favorite_locations_by_day.get(current_day_of_week) else 'No pattern detected'}

SEASONAL PATTERNS (Inferred from Reading History):
- Favorite genres in {current_season}: {', '.join(favorite_genres_by_season.get(current_season, [])) if favorite_genres_by_season.get(current_season) else 'No seasonal pattern detected'}
- Favorite authors in {current_season}: {', '.join(favorite_authors_by_season.get(current_season, [])) if favorite_authors_by_season.get(current_season) else 'No seasonal pattern detected'}

RECENT TRENDS (Last 30 Days - Weighted More Heavily):
- Recent genres during {current_time_of_day}: {', '.join(get_top_items(recent_genres_by_time.get(current_time_of_day, []))) if recent_genres_by_time.get(current_time_of_day) else 'No recent pattern'}
- Recent authors during {current_time_of_day}: {', '.join(get_top_items(recent_authors_by_time.get(current_time_of_day, []))) if recent_authors_by_time.get(current_time_of_day) else 'No recent pattern'}
- Recent genres in {month_names.get(current_month, 'this month')}: {', '.join(get_top_items(recent_genres_by_month.get(current_month, []))) if recent_genres_by_month.get(current_month) else 'No recent pattern'}
- Recent authors in {month_names.get(current_month, 'this month')}: {', '.join(get_top_items(recent_authors_by_month.get(current_month, []))) if recent_authors_by_month.get(current_month) else 'No recent pattern'}
- Time-weighted top genres for {current_time_of_day}: {', '.join(get_weighted_top_items(genres_by_time_weighted.get(current_time_of_day, {}))) if genres_by_time_weighted.get(current_time_of_day) else 'No weighted pattern'}
- Time-weighted top authors for {current_time_of_day}: {', '.join(get_weighted_top_items(authors_by_time_weighted.get(current_time_of_day, {}))) if authors_by_time_weighted.get(current_time_of_day) else 'No weighted pattern'}

READING VELOCITY PATTERNS:
{chr(10).join([f"- {time_key.capitalize()}: {avg_velocity:.2f} pages/minute (average)" for time_key, avg_velocity in avg_velocity_by_time.items()]) if avg_velocity_by_time else "- No velocity patterns detected"}
{f"- Current time ({current_time_of_day}): Consider that they read at {avg_velocity_by_time.get(current_time_of_day, 0):.2f} pages/minute on average during this time" if avg_velocity_by_time.get(current_time_of_day) else ""}

LOCATION-BASED PATTERNS (Inferred from Reading History):
{chr(10).join([f"- At {loc}: You typically read genres like {', '.join(favorite_genres_by_location.get(loc, []))}, authors like {', '.join(favorite_authors_by_location.get(loc, []))}, and are in moods like {', '.join(favorite_moods_by_location.get(loc, []))}" for loc in top_locations[:3] if favorite_genres_by_location.get(loc) or favorite_authors_by_location.get(loc)]) if top_locations else "- No location patterns detected"}

Based on this COMPREHENSIVE reading profile (considering WHEN, WHERE, MOOD, TIME, SEASON, and RECENT TRENDS), recommend EXACTLY {limit} TOP books that:
1. **Match their favorite genres and authors** (overall preferences)
2. **Are similar in style/tone to books they've enjoyed** (based on ratings and reviews)
3. **Fit their current mood** (if specified: {current_mood})
4. **Match their {current_time_of_day} reading patterns**: {f'Prioritize genres like {", ".join(favorite_genres_by_time.get(current_time_of_day, []))} and authors like {", ".join(favorite_authors_by_time.get(current_time_of_day, []))} (they typically read these during {current_time_of_day})' if favorite_genres_by_time.get(current_time_of_day) or favorite_authors_by_time.get(current_time_of_day) else 'No specific pattern detected for this time of day'}
5. **Match their {month_names.get(current_month, 'this month')} reading patterns**: {f'Prioritize genres like {", ".join(favorite_genres_by_month.get(current_month, []))} and authors like {", ".join(favorite_authors_by_month.get(current_month, []))} (they typically read these in {month_names.get(current_month, "this month")})' if favorite_genres_by_month.get(current_month) or favorite_authors_by_month.get(current_month) else 'No specific monthly pattern detected'}
6. **Match their {current_season} seasonal patterns**: {f'Consider genres like {", ".join(favorite_genres_by_season.get(current_season, []))} and authors like {", ".join(favorite_authors_by_season.get(current_season, []))} (they typically read these in {current_season})' if favorite_genres_by_season.get(current_season) or favorite_authors_by_season.get(current_season) else 'No specific seasonal pattern detected'}
7. **Prioritize RECENT trends** (last 30 days weighted more heavily): {f'Recent preferences show genres like {", ".join(get_top_items(recent_genres_by_time.get(current_time_of_day, [])))} and authors like {", ".join(get_top_items(recent_authors_by_time.get(current_time_of_day, [])))} during {current_time_of_day}' if recent_genres_by_time.get(current_time_of_day) or recent_authors_by_time.get(current_time_of_day) else 'No strong recent trends'}
8. **Match their {current_day_of_week} reading patterns**: {f'Consider genres like {", ".join(favorite_genres_by_day.get(current_day_of_week, []))} and authors like {", ".join(favorite_authors_by_day.get(current_day_of_week, []))} (they typically read these on {current_day_of_week})' if favorite_genres_by_day.get(current_day_of_week) or favorite_authors_by_day.get(current_day_of_week) else 'No specific day pattern detected'}
9. **Consider reading velocity**: {f'They read at {avg_velocity_by_time.get(current_time_of_day, 0):.2f} pages/minute during {current_time_of_day} - consider book length and complexity accordingly' if avg_velocity_by_time.get(current_time_of_day) else 'No velocity data for this time'}
10. **Consider location patterns**: {f'They often read at {", ".join(top_locations[:3])} - consider books suitable for these reading environments' if top_locations else 'No location patterns'}
11. **Are REAL, published books** (not made up - verify titles and authors exist)
12. **Are NOT in the "Books they've read" list above** (check carefully)

CRITICAL: Synthesize ALL factors above (time, location, mood, when they read) to recommend the TOP {limit} most relevant books. Don't just match one factor - consider how all patterns combine to suggest the perfect book for RIGHT NOW. Base recommendations on the ACTUAL patterns shown above, not on general assumptions.

REASONING REQUIREMENTS:
- Your "reason" field is CRITICAL - it's what the user will read to understand why you recommended this book
- Be SPECIFIC: Reference actual books they've read, genres they prefer, patterns you see in their data
- Be PERSONAL: Connect to their unique reading history, not generic statements
- Be TEMPORAL: Explain why this book fits RIGHT NOW (current time, day, month, season, recent trends)
- Be COMPREHENSIVE: Mention 2-4 different factors that influenced your recommendation
- Be CONVINCING: Make them feel like you truly understand their reading preferences
- Avoid vague phrases like "you might like" or "this is a good book" - be specific about WHY

For each recommendation, provide:
- title (required): Full book title
- author (required): Author name
- genre (optional): Book genre
- description (optional): Brief description or why it matches their preferences
- isbn (optional): ISBN if known
- score (required): Recommendation score from 0.0 to 1.0
- reason (required): A DETAILED, PERSONALIZED explanation (3-5 sentences) that:
  * Explains WHY this book is perfect for them RIGHT NOW (consider current time, day, month, season)
  * References SPECIFIC patterns from their reading history (genres, authors, moods, temporal patterns)
  * Connects to books they've enjoyed (similar style, theme, or author)
  * Mentions relevant temporal factors (time of day preferences, seasonal patterns, recent trends)
  * Explains how it fits their current reading context (mood, location patterns, reading velocity)
  * Makes it feel personal and tailored, not generic
  Example format: "Based on your recent interest in [genre] during [time of day] sessions, and your enjoyment of [similar book/author], this book aligns perfectly with your [season] reading patterns. You've been reading [recent trend] lately, and this matches that momentum while introducing [new element]. Given your preference for [pattern] and your current mood of [mood], this feels like the ideal next read."

Return your response as a JSON object with a "recommendations" array:
{{
  "recommendations": [
    {{
      "title": "<book title>",
      "author": "<author name>",
      "genre": "<genre>",
      "description": "<brief description>",
      "isbn": "<isbn if known>",
      "score": <0.0-1.0>,
      "reason": {{
        "primary_signal": "<short identifier the model invents>",
        "explanation": "<1–2 sentences explaining this dominant reason>"
    }}

    }},
    ...
  ]
}}

CRITICAL: 
- Do NOT recommend any books from the "Books they've read" list
- Only recommend REAL, published books
- Return exactly {limit} recommendations
- All book titles and authors must be accurate

REASONING CONSTRAINT (IMPORTANT):

Although many factors are provided above, you must:
- Identify ONE primary reason that most strongly explains why this book is a good recommendation RIGHT NOW
- Base this primary reason ONLY on the actual data provided above (e.g. reading pace, time-of-day habits, mood alignment, genre patterns, location patterns)
- Do NOT invent or assume information not provided in the data above
- Use the "All books in their library with status" section to understand their reading patterns
- Only mention specific books and their statuses if they are explicitly shown in that section
- Do NOT infer or assume book statuses that aren't shown in the data above
- Do NOT make up information about which books are paused, reading, or finished - only use what is explicitly provided with status information
- If a book's status is "unknown" or not shown, do NOT assume its status
- Do NOT list multiple reasons
- Do NOT say "among other reasons" or similar phrases
- Avoid generic preference statements like "you enjoy" or "you like"
- Anchor explanations in observable behavior shown in the data above (e.g. session patterns, time-of-day preferences, mood patterns, genre preferences)

The reason should be something the user can immediately recognize as true based on their actual reading data.
"""

    try:
        if thinking_callback:
            thinking_callback("Connecting to AI recommendation engine...")
        
        provider = settings.llm_provider.lower()
        model = settings.llm_model
        
        if thinking_callback:
            thinking_callback(f"Using {provider} with model {model}...")
            thinking_callback("Analyzing your reading patterns and preferences...")
        
        # Call appropriate provider
        if provider == "openai":
            content = _call_openai(prompt, model, thinking_callback)
        elif provider == "groq":
            content = _call_groq(prompt, model, thinking_callback)
        elif provider == "huggingface":
            content = _call_huggingface(prompt, model, thinking_callback)
        elif provider == "together":
            content = _call_together(prompt, model, thinking_callback)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        # Parse LLM response
        if thinking_callback:
            thinking_callback("AI is generating personalized recommendations...")
        
        # Try to extract JSON from response
        try:
            # If response is wrapped in markdown code blocks, extract it
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            rec_data = json.loads(content)
            
            # Extract recommendations array
            if "recommendations" in rec_data:
                recommendations = rec_data["recommendations"]
            elif isinstance(rec_data, list):
                recommendations = rec_data
            else:
                # Single recommendation object
                recommendations = [rec_data]
            
            if not isinstance(recommendations, list):
                recommendations = [recommendations]
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {content}")
            logger.error(f"Raw LLM response: {content[:500]}")  # Log first 500 chars
            # Don't create fallback recommendations - raise error instead
            raise ValueError(f"LLM returned invalid JSON. Please try again or check your OpenAI API key.")
        
        # Create recommendation objects
        if thinking_callback:
            thinking_callback(f"Processing {len(recommendations)} recommendations...")
        
        saved_recommendations = []
        from app.services import book_service
        
        for rec in recommendations[:limit]:
            title = rec.get("title")
            author = rec.get("author")
            
            if not title or not author:
                logger.warning(f"Skipping recommendation - missing title or author: {rec}")
                continue
            
            # Check if user has already read this book (by title/author matching)
            title_lower = title.lower().strip()
            author_lower = author.lower().strip()
            
            already_read = False
            for read_book in read_books_info:
                if (read_book["title"] == title_lower and 
                    read_book["author"] == author_lower):
                    logger.warning(f"Skipping recommendation - user has already read: {title} by {author}")
                    already_read = True
                    break
            
            if already_read:
                continue
            
            # Find or create the book
            book = None
            
            # Try to find by ISBN first
            if rec.get("isbn"):
                book = book_service.get_book_by_isbn(db, rec.get("isbn"))
            
            # Try to find by title and author
            if not book:
                book = db.query(models.Book).filter(
                    models.Book.title.ilike(f"%{title}%"),
                    models.Book.author.ilike(f"%{author}%")
                ).first()
            
            # Create book if it doesn't exist
            if not book:
                if thinking_callback:
                    thinking_callback(f"Adding new book: {title} by {author}...")
                
                book_data = schemas.BookCreate(
                    title=title,
                    author=author,
                    genre=rec.get("genre"),
                    description=rec.get("description"),
                    isbn=rec.get("isbn")
                )
                book = book_service.create_book(db, book_data)
                logger.info(f"Created new book: {title} by {author} (ID: {book.id})")
            else:
                logger.info(f"Found existing book: {title} by {author} (ID: {book.id})")
            
            # Double-check: Skip if user has read this book (by book_id)
            read_check = db.query(models.BookPreference).filter(
                models.BookPreference.user_id == user_id,
                models.BookPreference.book_id == book.id,
                models.BookPreference.status == "read"
            ).first()
            if read_check:
                logger.warning(f"Skipping recommendation - user has already read book ID {book.id}")
                continue
            
            # Check if recommendation already exists
            existing = db.query(models.Recommendation).filter(
                models.Recommendation.user_id == user_id,
                models.Recommendation.book_id == book.id
            ).first()
            
            # Handle reason field - it might be a dict or a string
            reason_value = rec.get("reason", "Recommended")
            if isinstance(reason_value, dict):
                # If reason is a dict, convert to JSON string
                reason_str = json.dumps(reason_value)
            else:
                # If it's already a string, use it as-is
                reason_str = str(reason_value) if reason_value else "Recommended"
            
            if existing:
                # Update existing recommendation
                existing.score = rec.get("score", 0.5)
                existing.reason = reason_str
                existing.factors = {"llm_recommendation": True, "llm_model": model}
                saved_recommendations.append(existing)
            else:
                # Create new recommendation
                db_rec = models.Recommendation(
                    user_id=user_id,
                    book_id=book.id,
                    score=rec.get("score", 0.5),
                    reason=reason_str,
                    factors={"llm_recommendation": True, "llm_model": model}
                )
                db.add(db_rec)
                saved_recommendations.append(db_rec)
        
        db.commit()
        
        # Refresh to get book relationships - explicitly load book for each recommendation
        from sqlalchemy.orm import joinedload
        
        for rec in saved_recommendations:
            db.refresh(rec)
            # Explicitly load book relationship to ensure it's available
            # This is necessary because lazy loading might not work in async contexts
            if not hasattr(rec, 'book') or rec.book is None:
                book = db.query(models.Book).filter(models.Book.id == rec.book_id).first()
                if book:
                    # Manually set the relationship
                    object.__setattr__(rec, 'book', book)
            
            # Mark as shown if not already set
            if not rec.shown_at:
                rec.shown_at = datetime.now()
                db.commit()
        
        return saved_recommendations
        
    except Exception as e:
        logger.error(f"Error generating LLM recommendations: {e}", exc_info=True)
        # Don't create fallback recommendations - instead raise the error
        # so the user knows something went wrong
        raise ValueError(f"Failed to generate recommendations: {str(e)}")


def _call_openai(prompt: str, model: str, thinking_callback: Optional[Callable[[str], None]] = None) -> str:
    """Call OpenAI API - supports both 0.x and 1.x API versions"""
    import openai as openai_lib
    
    model_name = model or "gpt-4o-mini"
    messages = [
            {"role": "system", "content": "You are a helpful book recommendation assistant. Always return valid JSON with a 'recommendations' array."},
            {"role": "user", "content": prompt}
    ]
    
    if OPENAI_NEW_API and OpenAI:
        # New API (1.x)
        client = OpenAI(api_key=settings.openai_api_key)
        params = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.7,
        }
        # response_format available in 1.x
        try:
            params["response_format"] = {"type": "json_object"}
        except Exception:
            pass
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    else:
        # Old API (0.x) - use openai.ChatCompletion.create directly
        try:
            # Set API key for old API
            openai_lib.api_key = settings.openai_api_key
            response = openai_lib.ChatCompletion.create(
                model=model_name,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content
        except (AttributeError, Exception) as e:
            # Fallback if ChatCompletion doesn't exist or other error
            logger.error(f"Error calling OpenAI API: {e}")
            raise ValueError(f"OpenAI API error: {str(e)}. Please check your API key and openai version.")


def _call_groq(prompt: str, model: str, thinking_callback: Optional[Callable[[str], None]] = None) -> str:
    """Call Groq API (FREE tier available)"""
    if not HTTPX_AVAILABLE:
        raise ValueError("httpx required for Groq. Install with: pip install httpx")
    
    import httpx
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.groq_api_key}",
        "Content-Type": "application/json"
    }
    
    # Groq models: llama-3.1-8b-instant (fast, free), llama-3.1-70b-versatile (better quality)
    payload = {
        "model": model or "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": "You are a helpful book recommendation assistant. Always return valid JSON with a 'recommendations' array."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _call_huggingface(prompt: str, model: str, thinking_callback: Optional[Callable[[str], None]] = None) -> str:
    """Call Hugging Face Inference API (FREE tier available)"""
    if not HTTPX_AVAILABLE:
        raise ValueError("httpx required for Hugging Face. Install with: pip install httpx")
    
    import httpx
    
    # Use a free model like meta-llama/Meta-Llama-3-8B-Instruct
    model_name = model or "meta-llama/Meta-Llama-3-8B-Instruct"
    url = f"https://api-inference.huggingface.co/models/{model_name}"
    
    headers = {}
    if settings.huggingface_api_key:
        headers["Authorization"] = f"Bearer {settings.huggingface_api_key}"
    
    # Hugging Face format
    full_prompt = f"""You are a helpful book recommendation assistant. Always return valid JSON with a 'recommendations' array.

{prompt}

Return only valid JSON:"""
    
    payload = {
        "inputs": full_prompt,
        "parameters": {
            "temperature": 0.7,
            "max_new_tokens": 2000,
            "return_full_text": False
        }
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()
    
    # Hugging Face returns a list with generated text
    if isinstance(data, list) and len(data) > 0:
        return data[0].get("generated_text", "")
    elif isinstance(data, dict) and "generated_text" in data:
        return data["generated_text"]
    else:
        raise ValueError(f"Unexpected Hugging Face response format: {data}")


def _call_together(prompt: str, model: str, thinking_callback: Optional[Callable[[str], None]] = None) -> str:
    """Call Together AI API (FREE tier available)"""
    if not HTTPX_AVAILABLE:
        raise ValueError("httpx required for Together AI. Install with: pip install httpx")
    
    import httpx
    
    url = "https://api.together.xyz/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.together_api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model or "meta-llama/Llama-3-8b-chat-hf",
        "messages": [
            {"role": "system", "content": "You are a helpful book recommendation assistant. Always return valid JSON with a 'recommendations' array."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    response = httpx.post(url, headers=headers, json=payload, timeout=60.0)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

