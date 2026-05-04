# backend/auth/jwt_handler.py
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from backend.config import settings


# ── Create ─────────────────────────────────────────────────────────────────────
def create_access_token(user_id: str, username: str) -> str:
    """Sign and return a JWT containing user_id + username."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": user_id,          # subject — our user UUID
        "username": username,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


# ── Verify ─────────────────────────────────────────────────────────────────────
def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Returns the payload dict on success.
    Raises ValueError with a human-readable message on any failure
    (expired, invalid signature, malformed).
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise ValueError("Token is missing subject claim.")
        return payload

    except JWTError as exc:
        raise ValueError(f"Invalid or expired token: {exc}") from exc