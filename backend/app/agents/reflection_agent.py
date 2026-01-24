"""
Reflection Agent

Generates short, context-aware reflective prompts to invite user contemplation.
This agent does not act automatically, persist data, or trigger notifications.
It only responds when explicitly invoked.

Philosophy:
- Reflection is an invitation, not a task
- Less is more
- Gentle prompts that respect user agency
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ReflectionAgent:
    """
    Agent that generates reflective prompts based on reading context.
    
    This agent is passive - it only generates prompts when explicitly invoked.
    It does not:
    - Act automatically
    - Persist data
    - Trigger notifications
    - Query the database
    - Call external APIs
    
    It simply returns templated prompts based on context.
    """
    
    @staticmethod
    def generate(
        context_type: str,
        context_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a reflective prompt based on context.
        
        Args:
            context_type: One of "finished_unrated", "paused_book", "re_read"
            context_data: Context-specific data (book info, status, etc.)
            
        Returns:
            {
                "primary_prompt": "string",
                "secondary_prompt": "string | null",
                "tone": "gentle | reflective"
            }
        """
        if context_type == "finished_unrated":
            return ReflectionAgent._generate_finished_unrated_prompt(context_data)
        elif context_type == "paused_book":
            return ReflectionAgent._generate_paused_book_prompt(context_data)
        elif context_type == "re_read":
            return ReflectionAgent._generate_re_read_prompt(context_data)
        else:
            logger.warning(f"Unknown context_type: {context_type}")
            return {
                "primary_prompt": "What stands out to you about this book?",
                "secondary_prompt": None,
                "tone": "gentle"
            }
    
    @staticmethod
    def _generate_finished_unrated_prompt(context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prompt for finished but unrated books.
        
        Context data may include:
        - book_title: str
        - book_author: str (optional)
        """
        book_title = context_data.get("book_title", "this book")
        
        primary = f"What did you appreciate about {book_title}, even if you didn't love it?"
        
        secondary = "What made it worth finishing?"
        
        return {
            "primary_prompt": primary,
            "secondary_prompt": secondary,
            "tone": "reflective"
        }
    
    @staticmethod
    def _generate_paused_book_prompt(context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prompt for paused books.
        
        Context data may include:
        - book_title: str
        - book_author: str (optional)
        - status: str (optional, "paused" or agent-derived)
        - paused_days: int (optional, days since paused)
        """
        book_title = context_data.get("book_title", "this book")
        
        primary = f"Do you want to return to {book_title}, or was it right to pause it?"
        
        secondary = "What made you step away?"
        
        return {
            "primary_prompt": primary,
            "secondary_prompt": secondary,
            "tone": "gentle"
        }
    
    @staticmethod
    def _generate_re_read_prompt(context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate prompt for re-read books.
        
        Context data may include:
        - book_title: str
        - book_author: str (optional)
        - read_count: int (number of times read)
        - last_read_date: str (optional)
        """
        book_title = context_data.get("book_title", "this book")
        read_count = context_data.get("read_count", 2)
        
        if read_count == 2:
            primary = f"What draws you back to {book_title} at this time?"
        else:
            primary = f"You've read {book_title} {read_count} times. What keeps bringing you back?"
        
        secondary = "What feels different this time?"
        
        return {
            "primary_prompt": primary,
            "secondary_prompt": secondary,
            "tone": "reflective"
        }

