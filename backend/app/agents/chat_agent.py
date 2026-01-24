"""
Chat Agent

A thin intelligence layer that explains existing signals and answers reflective questions.
The agent does NOT query the database directly - it consumes pre-assembled context from services.
"""
import logging
from typing import Dict, Any, List, Optional
from app.agents import BookAgent

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Chat agent that explains signals and answers reflective questions.
    
    The agent operates on pre-assembled context data - it does not query the database.
    This keeps it focused on explanation and reflection, not data gathering.
    """
    
    def __init__(self):
        """Initialize the Chat Agent."""
        pass
    
    def respond(
        self,
        context_type: str,
        context_data: Dict[str, Any],
        user_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response based on context type and data.
        
        Args:
            context_type: One of "dashboard_summary", "recommendation_explanation", "book_reflection"
            context_data: Pre-assembled context from services
            user_question: Optional free-text question from user
            
        Returns:
            Dictionary with:
            - response: Natural language explanation
            - insights: List of short bullet insights
            - follow_up_prompts: List of suggested questions
        """
        if context_type == "dashboard_summary":
            return self._handle_dashboard_summary(context_data, user_question)
        elif context_type == "recommendation_explanation":
            return self._handle_recommendation_explanation(context_data, user_question)
        elif context_type == "book_reflection":
            return self._handle_book_reflection(context_data, user_question)
        else:
            return {
                "response": "I don't recognize that context type.",
                "insights": [],
                "follow_up_prompts": []
            }
    
    def _handle_dashboard_summary(
        self,
        context_data: Dict[str, Any],
        user_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle dashboard summary context.
        
        Returns ONE primary insight based on priority:
        1. Unrated Finished Books (highest priority)
        2. Paused or Stalled Reading
        3. Recent Reading Momentum (last 14 days)
        4. Default qualitative summary
        
        Returns:
            {
                "primary_insight": "string",
                "context_type": "reflection | paused | momentum | default",
                "response": "string" (for backward compatibility),
                "insights": [],
                "follow_up_prompts": []
            }
        """
        stats = context_data.get("reading_statistics", {})
        agent_observations = context_data.get("agent_observations", {})
        recent_activity = context_data.get("recent_activity", {})
        
        total_sessions = stats.get("total_sessions", 0)
        finished_unrated = agent_observations.get("finished_unrated", [])
        paused = agent_observations.get("paused", [])
        stalled = agent_observations.get("stalled", [])
        recent_sessions_14d = recent_activity.get("sessions_count_14d", 0)
        
        # Priority 1: Unrated Finished Books
        if finished_unrated:
            count = len(finished_unrated)
            if count == 1:
                insight = "You've finished a book without rating it — that might be worth revisiting."
            elif count <= 3:
                insight = "You've finished a few books without rating them — that might be worth revisiting."
            else:
                insight = "You've finished several books without rating them — that might be worth revisiting."
            
            return {
                "primary_insight": insight,
                "context_type": "reflection",
                "response": insight,  # Backward compatibility
                "insights": [],
                "follow_up_prompts": ["Help me reflect on my finished books"]
            }
        
        # Priority 2: Paused or Stalled Reading
        paused_or_stalled = paused + stalled
        if paused_or_stalled:
            paused_count = len(paused)
            stalled_count = len(stalled)
            
            if paused_count > 0 and stalled_count > 0:
                insight = "A few books have been paused or sitting idle — perhaps worth picking up again."
            elif paused_count > 0:
                if paused_count == 1:
                    insight = "You have a book on pause — ready to return to it?"
                else:
                    insight = "You have a few books on pause — ready to return to them?"
            else:  # stalled only
                if stalled_count == 1:
                    insight = "A book has been sitting idle — perhaps worth picking up again."
                else:
                    insight = "A few books have been sitting idle — perhaps worth picking up again."
            
            return {
                "primary_insight": insight,
                "context_type": "paused",
                "response": insight,  # Backward compatibility
                "insights": [],
                "follow_up_prompts": ["What should I read next?"]
            }
        
        # Priority 3: Recent Reading Momentum (last 14 days)
        if recent_sessions_14d > 0:
            # Interpret the momentum
            if recent_sessions_14d >= 5:
                insight = "You've been reading actively lately — nice momentum."
            elif recent_sessions_14d >= 2:
                insight = "You've been reading regularly — keep it up."
            else:
                insight = "You've been reading lightly lately."
            
            return {
                "primary_insight": insight,
                "context_type": "momentum",
                "response": insight,  # Backward compatibility
                "insights": [],
                "follow_up_prompts": ["What should I read next?"]
            }
        
        # Priority 4: Default qualitative summary
        if total_sessions == 0:
            insight = "Your reading dashboard is quiet. Start logging sessions to see insights."
        else:
            insight = "You've been reading lightly lately."
        
        return {
            "primary_insight": insight,
            "context_type": "default",
            "response": insight,  # Backward compatibility
            "insights": [],
            "follow_up_prompts": ["What should I read next?"]
        }
    
    def _handle_recommendation_explanation(
        self,
        context_data: Dict[str, Any],
        user_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle recommendation explanation context."""
        recommendation = context_data.get("recommendation", {})
        book = recommendation.get("book", {})
        factors = recommendation.get("factors", {})
        reason = recommendation.get("reason", "")
        
        response_parts = []
        insights = []
        follow_ups = []
        
        book_title = book.get("title", "this book")
        book_author = book.get("author", "")
        
        # Start with the reason if available
        if reason:
            response_parts.append(reason)
        else:
            response_parts.append(f"'{book_title}' was recommended based on your reading patterns.")
        
        # Explain factors
        if factors:
            factor_explanations = []
            
            if factors.get("genre_match"):
                genre = factors.get("genre_match", {}).get("genre", "")
                if genre:
                    factor_explanations.append(f"matches your interest in {genre}")
            
            if factors.get("mood_match"):
                mood = factors.get("mood_match", {}).get("mood", "")
                if mood:
                    factor_explanations.append(f"suits your {mood} reading mood")
            
            if factors.get("author_match"):
                author = factors.get("author_match", {}).get("author", "")
                if author:
                    factor_explanations.append(f"by an author you've enjoyed ({author})")
            
            if factors.get("pace_match"):
                pace_info = factors.get("pace_match", {})
                if pace_info:
                    factor_explanations.append("fits your reading pace")
            
            if factor_explanations:
                insights.extend(factor_explanations)
                response_parts.append(
                    f"This recommendation aligns because it {', '.join(factor_explanations[:2])}."
                )
        
        # Score explanation
        score = recommendation.get("score", 0)
        if score > 0:
            score_percent = int(score * 100)
            if score_percent >= 80:
                insights.append(f"High match score: {score_percent}%")
            elif score_percent >= 60:
                insights.append(f"Good match score: {score_percent}%")
        
        # Handle user question
        if user_question:
            question_lower = user_question.lower()
            if "why" in question_lower or "reason" in question_lower:
                if factors:
                    response_parts.append(
                        "The recommendation considers your past reading patterns, "
                        "preferred genres, and reading context."
                    )
            elif "similar" in question_lower:
                if book_author:
                    response_parts.append(
                        f"If you've enjoyed books by {book_author} before, this might be a good fit."
                    )
        
        response = " ".join(response_parts) if response_parts else f"'{book_title}' is recommended for you."
        
        if not follow_ups:
            follow_ups = [
                "What other books are similar to this?",
                "Why does this match my reading style?"
            ]
        
        return {
            "response": response,
            "insights": insights,
            "follow_up_prompts": follow_ups[:3]
        }
    
    def _handle_book_reflection(
        self,
        context_data: Dict[str, Any],
        user_question: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle book reflection context."""
        book = context_data.get("book", {})
        sessions = context_data.get("sessions", [])
        preference = context_data.get("preference", {})
        reading_stats = context_data.get("reading_stats", {})
        
        response_parts = []
        insights = []
        follow_ups = []
        
        book_title = book.get("title", "this book")
        book_author = book.get("author", "")
        
        # Reading progress
        total_sessions = len(sessions)
        total_pages = sum(s.get("pages_read", 0) for s in sessions)
        book_page_count = book.get("page_count")
        
        if total_sessions > 0:
            response_parts.append(
                f"You've read '{book_title}' in {total_sessions} session{'s' if total_sessions != 1 else ''}."
            )
            
            if book_page_count and total_pages > 0:
                progress = (total_pages / book_page_count) * 100
                insights.append(f"Progress: {progress:.0f}% ({total_pages}/{book_page_count} pages)")
                
                if progress >= 100:
                    response_parts.append("You've finished this book.")
                elif progress >= 50:
                    response_parts.append("You're more than halfway through.")
                elif progress > 0:
                    response_parts.append("You're still in the early stages.")
        
        # Status and rating
        status = preference.get("status")
        rating = preference.get("rating")
        
        if status == "read" and rating:
            response_parts.append(f"You rated it {rating} out of 5 stars.")
            if rating >= 4:
                insights.append("High rating - this was a favorite")
            elif rating <= 2:
                insights.append("Lower rating - this didn't resonate")
        
        elif status == "read" and not rating:
            response_parts.append("You've finished this book but haven't rated it yet.")
            insights.append("Consider reflecting on your experience")
            follow_ups.append("Help me reflect on this book")
        
        elif status == "abandoned":
            response_parts.append("You marked this book as abandoned.")
            insights.append("This book didn't hold your interest")
        
        elif status == "currently_reading":
            response_parts.append("You're currently reading this book.")
        
        # Reading patterns for this book
        if sessions:
            moods = [s.get("mood") for s in sessions if s.get("mood")]
            if moods:
                mood_counts = {}
                for mood in moods:
                    mood_counts[mood] = mood_counts.get(mood, 0) + 1
                top_mood = max(mood_counts.items(), key=lambda x: x[1])
                insights.append(f"Most common mood while reading: {top_mood[0]}")
            
            locations = [s.get("location") for s in sessions if s.get("location")]
            if locations:
                unique_locations = list(set(locations))
                if len(unique_locations) == 1:
                    insights.append(f"Read primarily at: {unique_locations[0]}")
        
        # Handle user question
        if user_question:
            question_lower = user_question.lower()
            if "enjoy" in question_lower or "like" in question_lower:
                if rating:
                    if rating >= 4:
                        response_parts.append("Your rating suggests you really enjoyed this book.")
                    else:
                        response_parts.append("Your rating suggests this book had mixed appeal.")
                else:
                    response_parts.append("Consider rating the book to capture your thoughts.")
            
            elif "finish" in question_lower or "complete" in question_lower:
                if status != "read":
                    if book_page_count and total_pages:
                        remaining = book_page_count - total_pages
                        response_parts.append(f"You have about {remaining} pages left to read.")
                else:
                    response_parts.append("You've already finished this book.")
        
        response = " ".join(response_parts) if response_parts else f"Here's what I know about '{book_title}'."
        
        if not follow_ups:
            follow_ups = [
                "What should I read next?",
                "How does this compare to other books I've read?"
            ]
        
        return {
            "response": response,
            "insights": insights,
            "follow_up_prompts": follow_ups[:3]
        }

