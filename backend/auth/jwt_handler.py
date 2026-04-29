"""
backend/auth/jwt_handler.py

Create and verify JWT tokens using python-jose.
Secret key + algorithm come from environment variables.
"""

from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import HTTPException, status
import os

# ---------------------------------------------------------------------------
# Config — override via .env
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_change_in_production")
ALGORITHM  = os.getenv("ALGORITHM",  "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


# ---------------------------------------------------------------------------
# Create token
# ---------------------------------------------------------------------------
def create_access_token(username: str, user_id: int) -> str:
    """Return a signed JWT containing username + user_id."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub":     username,
        "user_id": user_id,
        "exp":     expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Verify token
# ---------------------------------------------------------------------------
def verify_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.
    Returns the payload dict on success.
    Raises HTTP 401 on any failure (expired, tampered, malformed).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id:  int = payload.get("user_id")
        if username is None or user_id is None:
            raise credentials_exception
        return {"sub": username, "user_id": user_id}
    except JWTError:
        raise credentials_exception