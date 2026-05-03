"""
backend/db/models.py

SQLAlchemy ORM models.

Tables
------
users       — one row per registered user
documents   — one row per uploaded file, FK → users.id

Keep this file purely structural: no business logic, no hashing,
no JWT.  Those live in auth/ and services/.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Integer, String, Text, DateTime, ForeignKey, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.database import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # login credentials
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email:    Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)

    # account state
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # timestamps — stored as UTC
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # one user → many documents
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="owner", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # who owns this document
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # file metadata
    filename:      Mapped[str]  = mapped_column(String(512), nullable=False)
    original_name: Mapped[str]  = mapped_column(String(512), nullable=False)   # user-facing name
    file_type:     Mapped[str]  = mapped_column(String(16),  nullable=False)   # pdf, docx, pptx, md
    file_size:     Mapped[int]  = mapped_column(Integer, nullable=False)        # bytes
    file_path:     Mapped[str]  = mapped_column(Text, nullable=False)           # absolute path on disk

    # ingestion status
    # pending → processing → ready | failed
    status:        Mapped[str]  = mapped_column(String(32), default="pending", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # how many chunks were produced (filled in after ingestion)
    chunk_count:   Mapped[int | None] = mapped_column(Integer, nullable=True)

    # whether a knowledge graph was built for this doc
    has_graph:     Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # timestamps
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # relationship back to owner
    owner: Mapped["User"] = relationship("User", back_populates="documents")

    def __repr__(self) -> str:
        return (
            f"<Document id={self.id} filename={self.filename!r} "
            f"status={self.status!r} user_id={self.user_id}>"
        )