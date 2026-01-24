from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    reading_sessions = relationship("ReadingSession", back_populates="user")
    book_preferences = relationship("BookPreference", back_populates="user")
    external_accounts = relationship("ExternalAccount", back_populates="user")
    agent_suggestions = relationship("AgentSuggestion", back_populates="user")


class Book(Base):
    __tablename__ = "books"
    
    id = Column(Integer, primary_key=True, index=True)
    isbn = Column(String, index=True)
    title = Column(String, nullable=False, index=True)
    author = Column(String, index=True)
    publisher = Column(String)
    publication_date = Column(DateTime)
    genre = Column(String, index=True)
    tags = Column(JSON)  # Array of tags
    description = Column(Text)
    cover_image_url = Column(String)
    page_count = Column(Integer)
    language = Column(String, default="en")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    reading_sessions = relationship("ReadingSession", back_populates="book")
    preferences = relationship("BookPreference", back_populates="book")


class ReadingSession(Base):
    __tablename__ = "reading_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    
    # Event tracking
    action = Column(String, nullable=False)  # "taken" or "returned"
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Reading metadata
    duration_minutes = Column(Float)  # Duration of reading session
    mood = Column(String)  # e.g., "relaxed", "focused", "curious", "stressed"
    context = Column(JSON)  # {location, co_read_books, session_notes}
    location = Column(String)
    notes = Column(Text)
    
    # Status and tags (same as BookPreference)
    status = Column(String)  # "want_to_read", "currently_reading", "read", "abandoned"
    tags = Column(JSON)  # User-defined tags array
    
    # Reading metrics
    pages_read = Column(Integer)
    reading_pace = Column(Float)  # pages per minute
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="reading_sessions")
    book = relationship("Book", back_populates="reading_sessions")


class BookPreference(Base):
    __tablename__ = "book_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    
    rating = Column(Integer)  # 1-5 stars
    review = Column(Text)
    status = Column(String)  # "want_to_read", "currently_reading", "read", "abandoned"
    favorite = Column(Boolean, default=False)
    tags = Column(JSON)  # User-defined tags
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="book_preferences")
    book = relationship("Book", back_populates="preferences")


class ExternalAccount(Base):
    __tablename__ = "external_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    platform = Column(String, nullable=False)  # "openlibrary", "google_books"
    platform_user_id = Column(String, nullable=False)
    access_token = Column(String)
    refresh_token = Column(String)
    token_expires_at = Column(DateTime)
    sync_enabled = Column(Boolean, default=True)
    last_synced_at = Column(DateTime)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="external_accounts")


class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    
    score = Column(Float, nullable=False)  # Recommendation score (0-1)
    reason = Column(Text)  # Explanation for recommendation
    factors = Column(JSON)  # Contributing factors: {genre_match, mood_match, pace_match, etc.}
    
    shown_at = Column(DateTime(timezone=True))
    clicked = Column(Boolean, default=False)
    dismissed = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    book = relationship("Book", backref="recommendations")


class AgentSuggestion(Base):
    """
    Stores autonomous agent suggestions and decisions.
    Each suggestion represents an agent's observation and recommended action.
    """
    __tablename__ = "agent_suggestions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Decision metadata
    decision_type = Column(String, nullable=False, index=True)  # e.g., "stalled_book", "unrated_finished", "exploration_prompt"
    reason = Column(Text, nullable=False)  # Human-readable explanation
    supporting_data = Column(JSON)  # Structured data supporting the decision
    
    # Action context
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)  # Related book (if applicable)
    suggestion_text = Column(Text)  # The actual suggestion/prompt text
    
    # Status tracking
    acknowledged = Column(Boolean, default=False)  # User has seen/acknowledged
    acted_upon = Column(Boolean, default=False)  # User has acted on the suggestion
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="agent_suggestions")
    book = relationship("Book", backref="agent_suggestions")
