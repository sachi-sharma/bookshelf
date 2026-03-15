from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import logging
import sys

from app.config import settings
from app.database import get_db, engine, Base
from app.api import books, sessions, recommendations, integrations, preferences
from app.core.middleware import RequestLoggingMiddleware
from app.core.exceptions import BookshelfException

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Bookshelf API",
    description="API for tracking reading habits and generating book recommendations",
    version="1.0.0"
)

# Request logging middleware (should be first)
app.add_middleware(RequestLoggingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(books.router, prefix="/api/v1", tags=["books"])
app.include_router(sessions.router, prefix="/api/v1", tags=["reading-sessions"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["recommendations"])
app.include_router(integrations.router, prefix="/api/v1", tags=["integrations"])
app.include_router(preferences.router, prefix="/api/v1", tags=["preferences"])


@app.get("/")
async def root():
    return {
        "message": "Smart Bookshelf API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        from sqlalchemy import text
        db = next(get_db())
        db.execute(text("SELECT 1"))
        db.close()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "disconnected",
                "error": str(e) if settings.debug else "Database connection failed"
            }
        )


# Exception handlers
@app.exception_handler(BookshelfException)
async def bookshelf_exception_handler(request: Request, exc: BookshelfException):
    """Handle custom application exceptions"""
    logger.warning(f"BookshelfException: {exc.detail} at {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions"""
    logger.info(f"HTTPException: {exc.status_code} - {exc.detail} at {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc} at {request.url.path}", exc_info=True)
    error_detail = str(exc)
    
    # In production, don't expose full traceback
    if not settings.debug:
        error_detail = "An internal server error occurred"
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": error_detail,
            "type": type(exc).__name__,
            "path": str(request.url.path)
        }
    )

