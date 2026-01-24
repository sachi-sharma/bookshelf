from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings

# SQLite requires check_same_thread=False for async operations
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
elif settings.database_url.startswith("postgresql"):
    # Ensure UTF-8 encoding for PostgreSQL
    connect_args = {"client_encoding": "utf8"}

engine = create_engine(
    settings.database_url, 
    connect_args=connect_args,
    pool_pre_ping=True
)

# Set client encoding for PostgreSQL connections
if settings.database_url.startswith("postgresql"):
    @event.listens_for(engine, "connect")
    def set_encoding(dbapi_conn, connection_record):
        """Set UTF-8 encoding on connection"""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("SET client_encoding TO 'UTF8'")
        except Exception:
            pass  # Ignore if encoding can't be set
        cursor.close()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

