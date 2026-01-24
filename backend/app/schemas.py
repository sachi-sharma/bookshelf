from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Book Schemas
class BookBase(BaseModel):
    isbn: Optional[str] = None
    title: str
    author: Optional[str] = None
    publisher: Optional[str] = None
    publication_date: Optional[datetime] = None
    genre: Optional[str] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    cover_image_url: Optional[str] = None
    page_count: Optional[int] = None
    language: str = "en"
    
    @field_validator('publication_date', mode='before')
    @classmethod
    def parse_publication_date(cls, v):
        """Parse publication_date from various formats"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, date):
            return datetime.combine(v, datetime.min.time())
        if isinstance(v, str):
            # Try to parse various date formats
            try:
                # Try ISO format with time
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                try:
                    # Try date-only format (YYYY-MM-DD)
                    date_obj = datetime.strptime(v, '%Y-%m-%d')
                    return date_obj
                except ValueError:
                    try:
                        # Try year-only format (YYYY)
                        if len(v) == 4 and v.isdigit():
                            return datetime(int(v), 1, 1)
                    except (ValueError, TypeError):
                        pass
            # If all parsing fails, return None
            return None
        return v


class BookCreate(BookBase):
    pass


class BookResponse(BookBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


# Reading Session Schemas
class ReadingSessionBase(BaseModel):
    book_id: int
    action: str  # "taken" or "returned"
    duration_minutes: Optional[float] = None
    mood: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None  # "want_to_read", "currently_reading", "read", "abandoned"
    tags: Optional[List[str]] = None  # User-defined tags array
    pages_read: Optional[int] = None
    reading_pace: Optional[float] = None


class ReadingSessionCreate(ReadingSessionBase):
    pass


class ReadingSessionResponse(ReadingSessionBase):
    id: int
    user_id: int
    timestamp: datetime
    created_at: datetime
    book: Optional[BookResponse] = None
    
    class Config:
        from_attributes = True


# Book Preference Schemas
class BookPreferenceBase(BaseModel):
    book_id: int
    rating: Optional[int] = None
    review: Optional[str] = None
    status: Optional[str] = None
    favorite: bool = False
    tags: Optional[List[str]] = None


class BookPreferenceCreate(BaseModel):
    # book_id is not required here because it comes from the URL path parameter
    rating: Optional[int] = None
    review: Optional[str] = None
    status: Optional[str] = None
    favorite: bool = False
    tags: Optional[List[str]] = None


class BookPreferenceResponse(BookPreferenceBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# External Account Schemas
class ExternalAccountBase(BaseModel):
    platform: str
    platform_user_id: str
    sync_enabled: bool = True


class ExternalAccountCreate(BaseModel):
    # platform is not required here because it comes from the URL path parameter
    platform_user_id: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    sync_enabled: bool = True


class ExternalAccountResponse(ExternalAccountBase):
    id: int
    user_id: int
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Recommendation Schemas
class RecommendationBase(BaseModel):
    book_id: int
    score: float
    reason: Optional[str] = None
    factors: Optional[Dict[str, Any]] = None


class RecommendationResponse(RecommendationBase):
    id: int
    user_id: int
    shown_at: Optional[datetime] = None
    clicked: bool = False
    dismissed: bool = False
    created_at: datetime
    book: Optional[BookResponse] = None
    
    class Config:
        from_attributes = True


# Agent Suggestion Schemas
class AgentSuggestionBase(BaseModel):
    decision_type: str
    reason: str
    supporting_data: Optional[Dict[str, Any]] = None
    book_id: Optional[int] = None
    suggestion_text: Optional[str] = None


class AgentSuggestionCreate(AgentSuggestionBase):
    pass


class AgentSuggestionResponse(AgentSuggestionBase):
    id: int
    user_id: int
    acknowledged: bool = False
    acted_upon: bool = False
    created_at: datetime
    book: Optional[BookResponse] = None
    
    class Config:
        from_attributes = True


# Reading History Query
class ReadingHistoryQuery(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    book_id: Optional[int] = None
    mood: Optional[str] = None
    limit: int = 50
    offset: int = 0


# Pagination
class PaginationParams(BaseModel):
    """Pagination parameters"""
    page: int = 1
    page_size: int = 50
    
    @property
    def offset(self) -> int:
        """Calculate offset from page and page_size"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit (same as page_size)"""
        return self.page_size


# Chat Agent Schemas
class ChatRequest(BaseModel):
    """Request for chat agent"""
    context_type: str  # "dashboard_summary" | "recommendation_explanation" | "book_reflection"
    context_data: Dict[str, Any]  # Pre-assembled context from services
    user_question: Optional[str] = None  # Optional free-text question


class ChatResponse(BaseModel):
    """Response from chat agent"""
    response: str  # Natural language explanation
    primary_insight: Optional[str] = None
    context_type: Optional[str] = None
    insights: List[str]  # Short bullet insights
    follow_up_prompts: List[str]  # Optional suggested questions


class ReflectionRequest(BaseModel):
    """Request for reflection agent"""
    context_type: str  # "finished_unrated", "paused_book", "re_read"
    context_data: Dict[str, Any]


class ReflectionResponse(BaseModel):
    """Response from reflection agent"""
    primary_prompt: str
    secondary_prompt: Optional[str] = None
    tone: str  # "gentle" | "reflective"

