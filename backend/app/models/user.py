"""
User and Role models.
Supports role-based access control per PRD persona definitions.
"""

import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserRole(str, enum.Enum):
    """Platform roles matching PRD persona definitions."""

    BID_MANAGER = "bid_manager"
    SOLUTIONING_LEAD = "solutioning_lead"
    COMMERCIAL_DIRECTOR = "commercial_director"
    LEGAL_COUNSEL = "legal_counsel"
    SOLUTION_DIRECTOR = "solution_director"
    PRACTICE_DIRECTOR = "practice_director"
    EVP = "evp"
    DELIVERY_LEAD = "delivery_lead"
    ADMIN = "admin"


class User(Base):
    """Platform user with role-based access."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, default="bid_manager")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    avatar_url: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    last_login: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=True)
