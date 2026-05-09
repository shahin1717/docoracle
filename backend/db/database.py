# backend/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.config import settings

# ── Engine ────────────────────────────────────────────────────────────────────
# check_same_thread=False is required for SQLite + FastAPI (multi-threaded)
engine = create_engine(
    settings.app_db_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug,        # logs all SQL when DEBUG=true
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ── Base class for all ORM models ─────────────────────────────────────────────
Base = declarative_base()


# ── Dependency — use this in every FastAPI route ──────────────────────────────
def get_db():
    """Yields a DB session and guarantees it closes after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once on app startup."""
    # import models here so Base knows about them before create_all
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)