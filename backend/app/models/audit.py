"""
Immutable audit log model.
Every agent action and HITL decision is logged permanently.
Retained for 7 years minimum per PRD NFR-04.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AuditLog(Base):
    """
    Immutable audit trail. Append-only — no UPDATE or DELETE operations.
    Records agent actions, HITL decisions, KB changes, and system events.
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # What happened
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_detail: Mapped[str] = mapped_column(Text, nullable=False)

    # Context
    bid_id: Mapped[str] = mapped_column(String(36), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=True)
    gate_type: Mapped[str] = mapped_column(String(100), nullable=True)

    # Who
    user_id: Mapped[str] = mapped_column(String(36), nullable=True)
    user_name: Mapped[str] = mapped_column(String(255), nullable=True)

    # Additional data
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)

    # When — immutable
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
