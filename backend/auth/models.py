"""
backend/auth/models.py

Pydantic schemas for auth — request bodies and response shapes.
These are NOT SQLAlchemy models (those live in backend/db/models.py).
"""

from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------
class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 64:
            raise ValueError("Username must be 64 characters or fewer")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


# ---------------------------------------------------------------------------
# Token (returned on login / register)
# ---------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# User info (safe to return to client — no password)
# ---------------------------------------------------------------------------
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}  # allows ORM → Pydantic


# ---------------------------------------------------------------------------
# What gets embedded in the JWT payload
# ---------------------------------------------------------------------------
class TokenPayload(BaseModel):
    sub: str        # username
    user_id: int
    exp: int        # unix timestamp