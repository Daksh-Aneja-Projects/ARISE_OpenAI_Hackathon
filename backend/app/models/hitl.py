"""
HITL (Human-in-the-Loop) gate models.
Every gate is blocking — pipeline cannot proceed without recorded approval.
Decisions are immutable and carry named accountability.
"""

import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum, DateTime, Text, ForeignKey, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class HITLGateType(str, enum.Enum):
    """Gate types matching PRD HITL gate specifications."""

    BID_INITIATION = "bid_initiation"
    INTAKE_REVIEW = "intake_review"
    BID_NO_BID = "bid_no_bid"
    SCOPE_REVIEW = "scope_review"
    SOLUTION_REVIEW = "solution_review"
    STRATEGY_ALIGNMENT = "strategy_alignment"
    COMMERCIAL_APPROVAL = "commercial_approval"
    LEGAL_COMPLIANCE = "legal_compliance"
    CLARIFICATION_SUBMISSION = "clarification_submission"
    FINAL_REVIEW = "final_review"


class HITLDecisionType(str, enum.Enum):
    """Decision types available at each gate."""

    APPROVED = "approved"
    APPROVED_WITH_COMMENTS = "approved_with_comments"
    REQUEST_CHANGES = "request_changes"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class HITLGateStatus(str, enum.Enum):
    """Gate lifecycle status."""

    PENDING = "pending"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    EXPIRED = "expired"


# SLA definitions per gate type (in hours)
GATE_SLA_HOURS = {
    HITLGateType.BID_INITIATION: 4,
    HITLGateType.INTAKE_REVIEW: 8,
    HITLGateType.BID_NO_BID: 24,
    HITLGateType.SCOPE_REVIEW: 24,
    HITLGateType.SOLUTION_REVIEW: 24,
    HITLGateType.STRATEGY_ALIGNMENT: 8,
    HITLGateType.COMMERCIAL_APPROVAL: 24,
    HITLGateType.LEGAL_COMPLIANCE: 48,
    HITLGateType.CLARIFICATION_SUBMISSION: 4,
    HITLGateType.FINAL_REVIEW: 8,
}

# Escalation paths per gate type
GATE_ESCALATION = {
    HITLGateType.BID_INITIATION: "practice_director",
    HITLGateType.INTAKE_REVIEW: "practice_director",
    HITLGateType.BID_NO_BID: "evp",
    HITLGateType.SCOPE_REVIEW: "solution_director",
    HITLGateType.SOLUTION_REVIEW: "practice_director",
    HITLGateType.STRATEGY_ALIGNMENT: "evp",
    HITLGateType.COMMERCIAL_APPROVAL: "practice_director",
    HITLGateType.LEGAL_COMPLIANCE: "practice_director",
    HITLGateType.CLARIFICATION_SUBMISSION: "solutioning_lead",
    HITLGateType.FINAL_REVIEW: "practice_director",
}


class HITLGate(Base):
    """
    A HITL review gate instance for a specific bid.
    Gates are blocking — the pipeline cannot proceed without approval.
    """

    __tablename__ = "hitl_gates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bids.id"), nullable=False
    )
    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)

    # Reviewer assignment
    assigned_reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    backup_reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # Agent output summary for the reviewer
    agent_summary: Mapped[str] = mapped_column(Text, nullable=True)
    agent_data: Mapped[dict] = mapped_column(JSON, nullable=True)

    # SLA tracking
    sla_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    sla_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Resolution
    decision: Mapped[str] = mapped_column(String(20), nullable=True)
    decided_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    comments: Mapped[str] = mapped_column(Text, nullable=True)

    # No gate can be modified after decision — immutable audit trail
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)


class HITLDecision(Base):
    """
    Immutable audit record for every HITL decision.
    Cannot be edited or deleted post-submission.
    """

    __tablename__ = "hitl_decisions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    gate_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("hitl_gates.id"), nullable=False
    )
    bid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bids.id"), nullable=False
    )
    gate_type: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # Required — empty rejected
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
