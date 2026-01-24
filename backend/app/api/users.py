from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.config import settings
import hashlib
import base64
import logging
import bcrypt

logger = logging.getLogger(__name__)

router = APIRouter()
# Use bcrypt directly instead of passlib to avoid initialization bug detection issues


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash"""
    # Ensure password is within 72 bytes
    password_bytes = plain_password.encode('utf-8')
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
        plain_password = password_bytes.decode('utf-8', errors='ignore')
    
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


def get_password_hash(password: str) -> str:
    # Ensure password is within bcrypt's 72-byte limit
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    
    # Check if this looks like an already-hashed password (bcrypt hashes start with $2b$)
    if password.startswith('$2b$') or password.startswith('$2a$') or password.startswith('$2y$'):
        # Already hashed, return as-is
        return password
    
    # Convert to bytes and check length
    try:
        password_bytes = password.encode('utf-8')
    except (UnicodeEncodeError, AttributeError):
        # If encoding fails, use ASCII with errors='ignore'
        password_bytes = password.encode('ascii', errors='ignore')
    
    # Strictly enforce 72-byte limit - truncate if necessary
    if len(password_bytes) > 72:
        # Truncate to exactly 72 bytes
        password_bytes = password_bytes[:72]
        # Try to decode back to string
        try:
            password = password_bytes.decode('utf-8')
        except UnicodeDecodeError:
            # If UTF-8 decode fails, try removing bytes from the end until it works
            while len(password_bytes) > 0:
                try:
                    password = password_bytes.decode('utf-8')
                    break
                except UnicodeDecodeError:
                    password_bytes = password_bytes[:-1]
            else:
                # If all else fails, use ASCII
                password = password_bytes.decode('ascii', errors='ignore')
    
    # Final safety check - ensure it's definitely under 72 bytes before hashing
    final_bytes = password.encode('utf-8')
    if len(final_bytes) > 72:
        # Last resort: truncate string to 72 characters
        password = password[:72]
        final_bytes = password.encode('utf-8')
        if len(final_bytes) > 72:
            # Truncate bytes directly
            password = final_bytes[:72].decode('utf-8', errors='ignore')
            final_bytes = password.encode('utf-8')
    
    # If password is still too long after truncation, pre-hash with SHA-256
    # This ensures bcrypt always gets input <= 72 bytes
    final_check = password.encode('utf-8')
    if len(final_check) > 72:
        # Pre-hash with SHA-256, then base64 encode (always 44 chars, < 72 bytes)
        sha256_hash = hashlib.sha256(password.encode('utf-8')).digest()
        password = base64.b64encode(sha256_hash).decode('ascii')
        # Now password is exactly 44 characters, well under 72 bytes
        logger.info("Password was too long, pre-hashed with SHA-256 before bcrypt")
    
    # Final safety check
    final_bytes = password.encode('utf-8')
    if len(final_bytes) > 72:
        # Last resort: truncate
        password = password[:72]
        final_bytes = password.encode('utf-8')
    
    # Ensure we're passing a string
    if not isinstance(password, str):
        password = str(password)
    
    # Use bcrypt directly to avoid passlib's bug detection issues
    # Ensure password is definitely under 72 bytes
    password_bytes = password.encode('utf-8')
    if len(password_bytes) > 72:
        # Truncate to 72 bytes
        password_bytes = password_bytes[:72]
        password = password_bytes.decode('utf-8', errors='ignore')
    
    # Hash with bcrypt directly
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


@router.post("/users/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    from app.core.validation import validate_password, validate_email
    from app.core.exceptions import ValidationError
    
    # Validate input
    try:
        validate_email(user.email)
        validate_password(user.password)
    except ValidationError:
        raise
    
    # Check if user exists
    db_user = db.query(models.User).filter(
        (models.User.email == user.email) | (models.User.username == user.username)
    ).first()
    
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.post("/users/login")
def login(form_data: dict, db: Session = Depends(get_db)):
    """Login and get access token"""
    username = form_data.get("username")
    password = form_data.get("password")
    
    user = db.query(models.User).filter(
        (models.User.email == username) | (models.User.username == username)
    ).first()
    
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer", "user_id": user.id}


@router.get("/users/me", response_model=schemas.UserResponse)
def get_current_user_endpoint(
    db: Session = Depends(get_db)
):
    """Get current user"""
    from app.core.auth import get_current_user
    return get_current_user(db=db)

