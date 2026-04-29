"""
backend/auth/router.py

Routes:
    POST /auth/register  — create account, return JWT
    POST /auth/login     — verify credentials, return JWT
    GET  /auth/me        — return current user info (protected)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import bcrypt

from backend.db.database import get_db
from backend.db.models import User
from backend.auth.models import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    UserResponse,
)
from backend.auth.jwt_handler import create_access_token
from backend.auth.middleware import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # check uniqueness
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = bcrypt.hashpw(body.password.encode(), bcrypt.gensalt()).decode()

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hashed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(username=user.username, user_id=user.id)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()

    if not user or not bcrypt.checkpw(body.password.encode(), user.hashed_password.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    token = create_access_token(username=user.username, user_id=user.id)
    return TokenResponse(access_token=token)


# ---------------------------------------------------------------------------
# GET /auth/me  (protected)
# ---------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    return current_user