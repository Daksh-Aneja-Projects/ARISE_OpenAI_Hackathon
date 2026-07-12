"""
Bid and BidManifest models.
The BidManifest is the central state object persisting across the entire bid lifecycle.
"""

import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Enum, DateTime, JSON, Float, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class BidStatus(str, enum.Enum):
    """Bid pipeline stages."""

    CREATED = "created"
    INTAKE_PROCESSING = "intake_processing"
    INTAKE_REVIEW = "intake_review"
    BID_NO_BID = "bid_no_bid"
    SCOPE_BUILDING = "scope_building"
    SCOPE_REVIEW = "scope_review"
    SOLUTION_DESIGN = "solution_design"
    SOLUTION_REVIEW = "solution_review"
    STRATEGY_ALIGNMENT = "strategy_alignment"
    COMMERCIAL_MODELING = "commercial_modeling"
    COMMERCIAL_APPROVAL = "commercial_approval"
    COMPLIANCE_REVIEW = "compliance_review"
    LEGAL_SIGN_OFF = "legal_sign_off"
    OUTPUT_GENERATION = "output_generation"
    QA_REVIEW = "qa_review"
    FINAL_REVIEW = "final_review"
    SUBMITTED = "submitted"
    WON = "won"
    LOST = "lost"
    ABANDONED = "abandoned"
    NO_BID = "no_bid"


class ContractType(str, enum.Enum):
    """Engagement contract types."""

    AMS = "ams"
    IMPLEMENTATION = "implementation"
    HYBRID = "hybrid"
    EXTEND_OPERATE = "extend_operate"
    ADVISORY = "advisory"
    STAFF_AUG = "staff_aug"


class DeadlineRisk(str, enum.Enum):
    """Submission deadline risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Bid(Base):
    """
    Core bid entity. Each bid has a unique BidManifest (JSON) that
    serves as the single source of truth for all agents.
    """

    __tablename__ = "bids"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bid_reference: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)

    # Client info
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_industry: Mapped[str] = mapped_column(String(100), nullable=True)
    client_geography: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array

    # RFP info
    contract_type: Mapped[str] = mapped_column(String(50), nullable=True)
    products: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array
    employee_population: Mapped[int] = mapped_column(Integer, nullable=True)

    # Dates
    rfp_received_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submission_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Status
    status: Mapped[str] = mapped_column(String(30), default="created", nullable=False)
    deadline_risk: Mapped[str] = mapped_column(String(20), default="low", nullable=True)

    # Scoring
    win_probability: Mapped[float] = mapped_column(Float, nullable=True)
    strategic_value: Mapped[str] = mapped_column(String(50), nullable=True)
    bid_recommendation: Mapped[str] = mapped_column(String(50), nullable=True)
    estimated_tcv: Mapped[float] = mapped_column(Float, nullable=True)

    # The full BidManifest — single source of truth
    manifest: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    # Ownership
    created_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    bid_lead_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Agent outputs stored as JSON — all 15 agents have dedicated columns
    intake_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    data_analyst_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    client_intel_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    bid_no_bid_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    scope_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    solution_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    automation_ai_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    competitive_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    commercial_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    compliance_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    proposal_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    output_generator_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    discovery_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    qa_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    feedback_output: Mapped[dict] = mapped_column(JSON, nullable=True)
    transition_change_output: Mapped[dict] = mapped_column(JSON, nullable=True)

    # Generated document paths
    output_word_path: Mapped[str] = mapped_column(String(500), nullable=True)
    output_ppt_path: Mapped[str] = mapped_column(String(500), nullable=True)
    output_excel_path: Mapped[str] = mapped_column(String(500), nullable=True)


class BidDocument(Base):
    """Documents uploaded for a specific bid."""

    __tablename__ = "bid_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bids.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    document_type: Mapped[str] = mapped_column(
        String(100), nullable=True
    )  # rfp, ticket_dump, etc.
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class GeneratedDocument(Base):
    """Generated response documents (SOW, PPT, Excel) for a specific bid."""

    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bids.id"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # e.g., bid_response, presentation, commercial_model
    file_format: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # e.g., docx, pptx, xlsx
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    generated_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class PipelineRun(Base):
    """Persisted state of a pipeline execution."""

    __tablename__ = "pipeline_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    bid_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("bids.id"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(50), default="running")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_by: Mapped[str] = mapped_column(String(255), nullable=True)
    current_stage_index: Mapped[int] = mapped_column(Integer, default=0)
    current_stage_name: Mapped[str] = mapped_column(String(255), nullable=True)
    total_stages: Mapped[int] = mapped_column(Integer, default=0)
    completed_stages: Mapped[int] = mapped_column(Integer, default=0)
    failed_stage: Mapped[str] = mapped_column(String(255), nullable=True)
    error: Mapped[str] = mapped_column(Text, nullable=True)
    stages: Mapped[dict] = mapped_column(JSON, default=list)
