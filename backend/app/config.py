from pydantic_settings import BaseSettings
from typing import List
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Database
    database_url: str = "sqlite:///./bookshelf.db"  # Default to SQLite for development
    
    # Security
    secret_key: str = "dev-secret-key-change-in-production"  # Default for development only
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._validate_security()
    
    def _validate_security(self):
        """Validate security settings"""
        if not self.debug and self.secret_key == "dev-secret-key-change-in-production":
            logger.warning(
                "⚠️  WARNING: Using default secret key in production! "
                "Set SECRET_KEY environment variable."
            )
        
        if len(self.secret_key) < 32:
            logger.warning(
                "⚠️  WARNING: Secret key is too short. "
                "For production, use a key of at least 32 characters."
            )
    
    # External APIs
    goodreads_api_key: str = ""  # ⚠️ DEPRECATED: Goodreads API no longer issues new keys
    goodreads_api_secret: str = ""  # ⚠️ DEPRECATED
    google_books_api_key: str = ""  # Optional: Get from https://console.cloud.google.com/apis/credentials
    
    # LLM Provider Settings
    llm_provider: str = "groq"  # Options: "openai", "groq" (FREE), "huggingface" (FREE), "together" (FREE)
    llm_model: str = "llama-3.1-8b-instant"  # Default: Groq's free fast model
    openai_api_key: str = ""  # For OpenAI (gpt-4o-mini, etc.)
    groq_api_key: str = ""  # For Groq (FREE tier) - Get from https://console.groq.com
    huggingface_api_key: str = ""  # For Hugging Face Inference API (FREE tier) - Optional
    together_api_key: str = ""  # For Together AI (FREE tier) - Get from https://api.together.xyz
    
    # App Settings
    debug: bool = True
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env (like removed Audible settings)


# Load settings
# Try to load from .env file, but use defaults if not found
settings = Settings()

# Validate critical settings on startup
def validate_settings():
    """Validate critical settings and log warnings"""
    warnings = []
    
    # Check LLM provider configuration
    provider = settings.llm_provider.lower()
    if provider == "openai" and not settings.openai_api_key:
        warnings.append("OpenAI provider selected but OPENAI_API_KEY not set")
    elif provider == "groq" and not settings.groq_api_key:
        warnings.append("Groq provider selected but GROQ_API_KEY not set")
    elif provider == "together" and not settings.together_api_key:
        warnings.append("Together AI provider selected but TOGETHER_API_KEY not set")
    
    # Check database
    if settings.database_url.startswith("sqlite") and not settings.debug:
        warnings.append("Using SQLite in production is not recommended. Use PostgreSQL instead.")
    
    for warning in warnings:
        logger.warning(f"⚠️  {warning}")


# Run validation on import
validate_settings()

