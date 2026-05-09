# backend/auth/models.py
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


# ── Register ──────────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email:    EmailStr
    password: str = Field(..., min_length=8, max_length=128)


# ── Login ─────────────────────────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str


# ── Token ─────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"


# ── Current user ──────────────────────────────────────────────────────────────
class UserOut(BaseModel):
    id:              str
    username:        str
    email:           str
    is_active:       bool
    preferred_model: str | None   # None = use server default
    created_at:      datetime

    model_config = {"from_attributes": True}


# ── Update preferences ────────────────────────────────────────────────────────
class UserUpdateRequest(BaseModel):
    preferred_model: str | None = None   # pass None to reset to server default