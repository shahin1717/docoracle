# backend/auth/router.py
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth.jwt_handler import create_access_token
from backend.auth.middleware import get_current_user
from backend.auth.models import LoginRequest, RegisterRequest, TokenResponse, UserOut
from backend.db.database import get_db
from backend.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


# ── helpers ───────────────────────────────────────────────────────────────────
def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── POST /auth/register ───────────────────────────────────────────────────────
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # duplicate username
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken.",
        )
    # duplicate email
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        username=body.username,
        email=body.email,
        password_hash=_hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(access_token=token)


# ── POST /auth/login ──────────────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == body.username).first()

    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled.",
        )

    token = create_access_token(user_id=user.id, username=user.username)
    return TokenResponse(access_token=token)


# ── GET /auth/me ──────────────────────────────────────────────────────────────
@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)