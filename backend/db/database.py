"""
backend/db/database.py

SQLAlchemy engine, session factory, and declarative Base.
All DB models import Base from here. All routes/services
use get_db() as a FastAPI dependency to get a session.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

# ---------------------------------------------------------------------------
# PostgreSQL connection — credentials from env or defaults
# ---------------------------------------------------------------------------
DB_USER     = os.getenv("DB_USER",     "shahin_docoracle")
DB_PASSWORD = os.getenv("DB_PASSWORD", "docoracle123")
DB_HOST     = os.getenv("DB_HOST",     "localhost")
DB_PORT     = os.getenv("DB_PORT",     "5432")
DB_NAME     = os.getenv("DB_NAME",     "shahin_docoracle")

DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    echo=False,          # set True to log SQL for debugging
    pool_pre_ping=True,  # test connections before using them
)

# ---------------------------------------------------------------------------
# Session factory
# autocommit=False  — we commit explicitly (safer, easier to roll back)
# autoflush=False   — don't flush before every query automatically
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative base — all ORM models inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# Usage in a route:  db: Session = Depends(get_db)
# ---------------------------------------------------------------------------
def get_db():
    """Yield a DB session, always closing it when the request is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Utility — called once at app startup to create all tables
# ---------------------------------------------------------------------------
def init_db():
    """Create all tables defined on Base. Safe to call multiple times."""
    # models must be imported before this runs so SQLAlchemy sees them
    from backend.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)