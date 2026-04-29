"""
backend/auth/middleware.py

FastAPI dependency — extracts the current user from the
Authorization: Bearer <token> header.

Usage in any protected route:
    current_user: User = Depends(get_current_user)
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.jwt_handler import verify_access_token

# FastAPI's built-in Bearer token extractor
# tokenUrl is where clients go to get a token (used by OpenAPI docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode the JWT, look up the user in the DB, return the User ORM object.
    Raises HTTP 401 if token is invalid or user not found.
    Raises HTTP 403 if user account is inactive.
    """
    payload = verify_access_token(token)

    user = db.query(User).filter(User.id == payload["user_id"]).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    return user