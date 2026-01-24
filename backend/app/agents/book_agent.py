"""
Autonomous Book Agent

The Book Agent observes reading patterns, infers book states, and makes autonomous
decisions about user's reading behavior. It operates deterministically based on
data patterns without requiring external APIs or cloud services.

Agent Responsibilities:
1. Book State Awareness - Infer current reading states
2. Autonomous Decisions - Identify patterns and opportunities
3. Action Generation - Create suggestions and prompts
4. Explainability - Every decision includes reasoning
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from app import models

logger = logging.getLogger(__name__)


class BookAgent:
    """
    Autonomous agent that observes reading patterns and makes intelligent decisions
    about book states, reading behavior, and opportunities for engagement.
    
    The agent operates deterministically - given the same data, it will make
    the same decisions. This makes it testable and debuggable.
    """
    
    def __init__(self, db: Session, user_id: int):
        """
        Initialize the Book Agent.
        
        Args:
            db: Database session
            user_id: User to observe and make decisions for
        """
        self.db = db
        self.user_id = user_id
        # Use timezone-aware datetime for consistency
        self.now = datetime.now()
        
        # Decision thresholds (configurable)
        self.stalled_days_threshold = 30  # Days without activity to consider stalled
        self.exploration_similarity_threshold = 3  # Number of similar books before suggesting exploration
    
    def run(self) -> Dict[str, Any]:
        """
        Main entry point for the agent. Runs all observation and decision logic.
        
        Returns:
            Dictionary with:
            - observations: What the agent observed
            - decisions: List of decisions made
            - actions_taken: List of actions performed
        """
        logger.info(f"BookAgent: Starting run for user {self.user_id}")
        
        # Phase 1: Observe state
        observations = self._observe_state()
        logger.info(f"BookAgent: Observed {len(observations)} state patterns")
        
        # Phase 2: Make decisions
        decisions = []
        decisions.extend(self._decide_stalled_books(observations))
        decisions.extend(self._decide_unrated_finished(observations))
        decisions.extend(self._decide_exploration_opportunity(observations))
        
        logger.info(f"BookAgent: Made {len(decisions)} decisions")
        
        # Phase 3: Take actions
        actions_taken = []
        for decision in decisions:
            action = self._execute_decision(decision)
            if action:
                actions_taken.append(action)
        
        logger.info(f"BookAgent: Executed {len(actions_taken)} actions")
        
        return {
            "user_id": self.user_id,
            "timestamp": self.now.isoformat(),
            "observations": observations,
            "decisions": decisions,
            "actions_taken": actions_taken,
            "summary": {
                "total_observations": len(observations),
                "total_decisions": len(decisions),
                "total_actions": len(actions_taken)
            }
        }
    
    def _observe_state(self) -> Dict[str, Any]:
        """
        Observe and infer the current state of user's reading.
        
        Returns:
            Dictionary with inferred states:
            - currently_reading: Books currently being read
            - abandoned: Books that appear abandoned
            - finished_unrated: Books finished but not rated
            - available_on_shelf: Books physically available
            - stalled: Books with no activity for threshold days
        """
        observations = {
            "currently_reading": [],
            "abandoned": [],
            "paused": [],
            "finished_unrated": [],
            "available_on_shelf": [],
            "stalled": [],
            "reading_patterns": {}
        }
        
        # Get all books user has interacted with
        all_book_ids = set()
        
        # From preferences
        prefs = self.db.query(models.BookPreference).filter(
            models.BookPreference.user_id == self.user_id
        ).all()
        for pref in prefs:
            all_book_ids.add(pref.book_id)
        
        # From reading sessions
        sessions = self.db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == self.user_id
        ).all()
        for session in sessions:
            all_book_ids.add(session.book_id)
        
        # Analyze each book
        for book_id in all_book_ids:
            book_state = self._analyze_book_state(book_id)
            if book_state:
                state_type = book_state["state"]
                if state_type == "currently_reading":
                    observations["currently_reading"].append(book_state)
                elif state_type == "abandoned":
                    observations["abandoned"].append(book_state)
                elif state_type == "paused":
                    observations["paused"].append(book_state)
                elif state_type == "finished_unrated":
                    observations["finished_unrated"].append(book_state)
                elif state_type == "stalled":
                    observations["stalled"].append(book_state)
        
        # Get available books on shelf
        observations["available_on_shelf"] = self._get_available_books()
        
        # Analyze reading patterns
        observations["reading_patterns"] = self._analyze_reading_patterns()
        
        return observations
    
    def _analyze_book_state(self, book_id: int) -> Optional[Dict[str, Any]]:
        """
        Analyze the state of a specific book for this user.
        
        Returns:
            Dictionary with:
            - book_id
            - state: "currently_reading", "abandoned", "finished_unrated", "stalled", or None
            - evidence: Supporting data
        """
        book = self.db.query(models.Book).filter(models.Book.id == book_id).first()
        if not book:
            return None
        
        # Get preference
        pref = self.db.query(models.BookPreference).filter(
            models.BookPreference.user_id == self.user_id,
            models.BookPreference.book_id == book_id
        ).first()
        
        # Get all sessions for this book
        sessions = self.db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == self.user_id,
            models.ReadingSession.book_id == book_id
        ).order_by(desc(models.ReadingSession.timestamp)).all()
        
        if not sessions:
            return None
        
        latest_session = sessions[0]
        # Handle timezone-aware timestamps
        latest_timestamp = latest_session.timestamp
        if latest_timestamp.tzinfo is not None:
            # Convert to naive datetime for comparison
            latest_timestamp = latest_timestamp.replace(tzinfo=None)
        
        # Ensure now is also naive
        now_naive = self.now.replace(tzinfo=None) if self.now.tzinfo else self.now
        days_since_last_activity = (now_naive - latest_timestamp).days
        
        # Calculate reading progress
        total_pages_read = sum(s.pages_read for s in sessions if s.pages_read)
        progress_percent = None
        if book.page_count and book.page_count > 0:
            progress_percent = (total_pages_read / book.page_count) * 100
        
        evidence = {
            "latest_session": latest_session.timestamp.isoformat(),
            "days_since_last_activity": days_since_last_activity,
            "total_sessions": len(sessions),
            "total_pages_read": total_pages_read,
            "book_page_count": book.page_count,
            "progress_percent": progress_percent,
            "preference_status": pref.status if pref else None,
            "has_rating": pref.rating is not None if pref else False
        }
        
        # Decision logic
        # 1. Check if finished but not rated
        if pref and pref.status == "read" and pref.rating is None:
            return {
                "book_id": book_id,
                "book_title": book.title,
                "state": "finished_unrated",
                "evidence": evidence
            }
        
        # 2. Check if abandoned (explicit status)
        if pref and pref.status == "abandoned":
            return {
                "book_id": book_id,
                "book_title": book.title,
                "state": "abandoned",
                "evidence": evidence
            }
        
        # 2b. Check if paused (explicit status - do NOT apply inactivity heuristics)
        # Explicit user intent (paused shelf) > inferred agent state
        if pref and pref.status == "paused":
            return {
                "book_id": book_id,
                "book_title": book.title,
                "state": "paused",
                "evidence": evidence
            }
        
        # 3. Check if stalled (no activity for threshold days, but not finished)
        # ONLY apply this if status is "currently_reading" or None (not paused)
        # Do NOT apply inactivity-based paused heuristics if status is explicitly paused
        if (days_since_last_activity >= self.stalled_days_threshold and 
            (not pref or pref.status not in ["read", "paused"])):
            # Additional check: has some progress but not finished
            if progress_percent and 5 < progress_percent < 95:
                return {
                    "book_id": book_id,
                    "book_title": book.title,
                    "state": "stalled",
                    "evidence": evidence
                }
        
        # 4. Currently reading (has recent activity or status)
        # Only if status is currently_reading or None (not paused)
        if (days_since_last_activity < self.stalled_days_threshold and 
            (not pref or pref.status in [None, "currently_reading"])):
            return {
                "book_id": book_id,
                "book_title": book.title,
                "state": "currently_reading",
                "evidence": evidence
            }
        
        return None
    
    def _get_available_books(self) -> List[Dict[str, Any]]:
        """
        Get books that are physically available on the shelf.
        A book is available if the most recent action was "taken" (not "returned").
        
        Returns:
            List of book info dictionaries
        """
        # Get all unique books with sessions
        book_ids = self.db.query(models.ReadingSession.book_id).filter(
            models.ReadingSession.user_id == self.user_id
        ).distinct().all()
        
        available = []
        for (book_id,) in book_ids:
            # Get most recent session
            latest = self.db.query(models.ReadingSession).filter(
                models.ReadingSession.user_id == self.user_id,
                models.ReadingSession.book_id == book_id
            ).order_by(desc(models.ReadingSession.timestamp)).first()
            
            if latest and latest.action == "taken":
                book = self.db.query(models.Book).filter(models.Book.id == book_id).first()
                if book:
                    available.append({
                        "book_id": book_id,
                        "book_title": book.title,
                        "last_taken": latest.timestamp.isoformat()
                    })
        
        return available
    
    def _analyze_reading_patterns(self) -> Dict[str, Any]:
        """
        Analyze reading patterns to identify opportunities for exploration.
        
        Returns:
            Dictionary with pattern analysis:
            - genre_distribution: Count of books by genre
            - author_distribution: Count of books by author
            - recent_genres: Genres read in last 30 days
            - recent_authors: Authors read in last 30 days
        """
        thirty_days_ago = self.now - timedelta(days=30)
        
        # Get recent sessions (handle timezone-aware timestamps)
        recent_sessions = self.db.query(models.ReadingSession).filter(
            models.ReadingSession.user_id == self.user_id,
            models.ReadingSession.timestamp >= thirty_days_ago
        ).all()
        
        # Get recent preferences
        recent_prefs = self.db.query(models.BookPreference).filter(
            models.BookPreference.user_id == self.user_id,
            models.BookPreference.created_at >= thirty_days_ago
        ).all()
        
        genre_counts = {}
        author_counts = {}
        
        # Count from sessions
        for session in recent_sessions:
            if session.book and session.book.genre:
                genre_counts[session.book.genre] = genre_counts.get(session.book.genre, 0) + 1
            if session.book and session.book.author:
                author_counts[session.book.author] = author_counts.get(session.book.author, 0) + 1
        
        # Count from preferences
        for pref in recent_prefs:
            if pref.book and pref.book.genre:
                genre_counts[pref.book.genre] = genre_counts.get(pref.book.genre, 0) + 1
            if pref.book and pref.book.author:
                author_counts[pref.book.author] = author_counts.get(pref.book.author, 0) + 1
        
        return {
            "genre_distribution": genre_counts,
            "author_distribution": author_counts,
            "recent_genres": list(genre_counts.keys()),
            "recent_authors": list(author_counts.keys()),
            "total_recent_books": len(set([s.book_id for s in recent_sessions] + [p.book_id for p in recent_prefs]))
        }
    
    def _decide_stalled_books(self, observations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decide if any books should be marked as stalled.
        
        Decision: If a book has been partially read (>5% progress) but untouched
        for 30+ days, suggest marking it as stalled.
        
        Returns:
            List of decision dictionaries
        """
        decisions = []
        
        for stalled_book in observations.get("stalled", []):
            evidence = stalled_book["evidence"]
            days_inactive = evidence["days_since_last_activity"]
            progress = evidence.get("progress_percent", 0)
            
            decision = {
                "decision_type": "stalled_book",
                "book_id": stalled_book["book_id"],
                "book_title": stalled_book["book_title"],
                "reason": (
                    f"'{stalled_book['book_title']}' has been {progress:.0f}% read but "
                    f"untouched for {days_inactive} days. Consider marking as stalled or resuming."
                ),
                "supporting_data": {
                    "days_inactive": days_inactive,
                    "progress_percent": progress,
                    "last_activity": evidence["latest_session"],
                    "total_pages_read": evidence["total_pages_read"],
                    "book_page_count": evidence["book_page_count"]
                },
                "priority": "medium"
            }
            decisions.append(decision)
        
        return decisions
    
    def _decide_unrated_finished(self, observations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decide if any finished books need rating/reflection.
        
        Decision: If a book is marked as "read" but has no rating, suggest reflection.
        
        Returns:
            List of decision dictionaries
        """
        decisions = []
        
        for unrated in observations.get("finished_unrated", []):
            evidence = unrated["evidence"]
            days_since_finished = evidence["days_since_last_activity"]
            
            decision = {
                "decision_type": "unrated_finished",
                "book_id": unrated["book_id"],
                "book_title": unrated["book_title"],
                "reason": (
                    f"You finished '{unrated['book_title']}' but haven't rated it. "
                    f"Take a moment to reflect and rate it."
                ),
                "supporting_data": {
                    "days_since_finished": days_since_finished,
                    "finished_date": evidence["latest_session"],
                    "total_sessions": evidence["total_sessions"]
                },
                "priority": "low"
            }
            decisions.append(decision)
        
        return decisions
    
    def _decide_exploration_opportunity(self, observations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Decide if user should explore different genres/authors.
        
        Decision: If user has read 3+ books from the same genre/author recently,
        suggest exploring something different.
        
        Returns:
            List of decision dictionaries
        """
        decisions = []
        patterns = observations.get("reading_patterns", {})
        
        # Check genre concentration
        genre_dist = patterns.get("genre_distribution", {})
        for genre, count in genre_dist.items():
            if count >= self.exploration_similarity_threshold:
                decision = {
                    "decision_type": "exploration_prompt",
                    "book_id": None,
                    "book_title": None,
                    "reason": (
                        f"You've read {count} {genre} books recently. "
                        f"Consider exploring a different genre for variety."
                    ),
                    "supporting_data": {
                        "concentration_type": "genre",
                        "concentration_value": genre,
                        "count": count,
                        "recent_genres": patterns.get("recent_genres", [])
                    },
                    "priority": "low"
                }
                decisions.append(decision)
                break  # Only suggest one exploration at a time
        
        # Check author concentration
        author_dist = patterns.get("author_distribution", {})
        for author, count in author_dist.items():
            if count >= self.exploration_similarity_threshold:
                decision = {
                    "decision_type": "exploration_prompt",
                    "book_id": None,
                    "book_title": None,
                    "reason": (
                        f"You've read {count} books by {author} recently. "
                        f"Consider exploring a different author for variety."
                    ),
                    "supporting_data": {
                        "concentration_type": "author",
                        "concentration_value": author,
                        "count": count,
                        "recent_authors": patterns.get("recent_authors", [])
                    },
                    "priority": "low"
                }
                decisions.append(decision)
                break  # Only suggest one exploration at a time
        
        return decisions
    
    def _execute_decision(self, decision: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a decision by creating an agent suggestion in the database.
        
        Args:
            decision: Decision dictionary from decision methods
            
        Returns:
            Dictionary with action result, or None if action failed
        """
        try:
            # Check if similar suggestion already exists (avoid duplicates)
            existing = self.db.query(models.AgentSuggestion).filter(
                models.AgentSuggestion.user_id == self.user_id,
                models.AgentSuggestion.decision_type == decision["decision_type"],
                models.AgentSuggestion.book_id == decision.get("book_id"),
                models.AgentSuggestion.acknowledged == False
            ).first()
            
            if existing:
                logger.info(f"BookAgent: Similar suggestion already exists, skipping")
                return None
            
            # Create suggestion
            suggestion = models.AgentSuggestion(
                user_id=self.user_id,
                decision_type=decision["decision_type"],
                reason=decision["reason"],
                supporting_data=decision["supporting_data"],
                book_id=decision.get("book_id"),
                suggestion_text=decision["reason"],
                acknowledged=False,
                acted_upon=False
            )
            
            self.db.add(suggestion)
            self.db.commit()
            self.db.refresh(suggestion)
            
            logger.info(f"BookAgent: Created suggestion {suggestion.id} for decision {decision['decision_type']}")
            
            return {
                "action": "created_suggestion",
                "suggestion_id": suggestion.id,
                "decision_type": decision["decision_type"],
                "book_id": decision.get("book_id")
            }
            
        except Exception as e:
            logger.error(f"BookAgent: Error executing decision: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def get_suggestions(self, acknowledged: Optional[bool] = None) -> List[models.AgentSuggestion]:
        """
        Get agent suggestions for this user.
        
        Args:
            acknowledged: Filter by acknowledged status (None = all)
            
        Returns:
            List of AgentSuggestion objects
        """
        query = self.db.query(models.AgentSuggestion).filter(
            models.AgentSuggestion.user_id == self.user_id
        )
        
        if acknowledged is not None:
            query = query.filter(models.AgentSuggestion.acknowledged == acknowledged)
        
        return query.order_by(desc(models.AgentSuggestion.created_at)).all()
    
    def acknowledge_suggestion(self, suggestion_id: int) -> bool:
        """
        Mark a suggestion as acknowledged.
        
        Args:
            suggestion_id: ID of suggestion to acknowledge
            
        Returns:
            True if successful, False otherwise
        """
        suggestion = self.db.query(models.AgentSuggestion).filter(
            models.AgentSuggestion.id == suggestion_id,
            models.AgentSuggestion.user_id == self.user_id
        ).first()
        
        if suggestion:
            suggestion.acknowledged = True
            self.db.commit()
            return True
        
        return False

