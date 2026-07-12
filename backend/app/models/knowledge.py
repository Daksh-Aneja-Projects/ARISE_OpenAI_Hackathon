"""
Knowledge Base document models.
Supports 14 KB collections with vector embeddings for RAG.
"""

import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String,
    Enum,
    DateTime,
    Text,
    ForeignKey,
    Integer,
    Float,
    JSON,
    Boolean,
)
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class KBCollectionType(str, enum.Enum):
    """KB collection types matching PRD knowledge base schema."""

    RFPS = "rfps"
    SOWS = "sows"
    RATE_CARDS = "rate_cards"
    SCOPE_TEMPLATES = "scope_templates"
    SOLUTION_TEMPLATES = "solution_templates"
    COMMERCIAL_MODELS = "commercial_models"
    CLAUSE_LIBRARY = "clause_library"
    PARTNER_PROFILES = "partner_profiles"
    CLIENT_PROFILES = "client_profiles"
    WIN_LOSS_DATA = "win_loss_data"
    BRAND = "brand"
    TICKET_TAXONOMIES = "ticket_taxonomies"
    ESTIMATING_ACTUALS = "estimating_actuals"


class KBDocument(Base):
    """A document stored in the Knowledge Base."""

    __tablename__ = "kb_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    collection: Mapped[str] = mapped_column(String(50), nullable=False)

    # File info
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Mandatory tagging (per PRD KB-02)
    product: Mapped[str] = mapped_column(String(255), nullable=True)
    engagement_type: Mapped[str] = mapped_column(String(100), nullable=True)
    client_industry: Mapped[str] = mapped_column(String(100), nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=True)  # won/lost/pending

    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_latest: Mapped[bool] = mapped_column(Boolean, default=True)
    previous_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("kb_documents.id"), nullable=True
    )

    # Rate card specific
    effective_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(10), nullable=True)
    approved_by: Mapped[str] = mapped_column(String(255), nullable=True)

    # Content (for text-based documents)
    content_text: Mapped[str] = mapped_column(Text, nullable=True)

    # Metadata
    tags: Mapped[dict] = mapped_column(JSON, default=dict)
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class KBEmbedding(Base):
    """Vector embeddings for RAG search against KB documents."""

    __tablename__ = "kb_embeddings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("kb_documents.id"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Embedding stored as JSON array (will use pgvector when available)
    embedding: Mapped[str] = mapped_column(Text, nullable=True)

    # Metadata for retrieval weighting
    source_document: Mapped[str] = mapped_column(String(500), nullable=True)
    collection: Mapped[str] = mapped_column(String(50), nullable=True)
    outcome: Mapped[str] = mapped_column(
        String(50), nullable=True
    )  # For outcome weighting
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class KBCollection(Base):
    """KB collection metadata and access control."""

    __tablename__ = "kb_collections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    document_count: Mapped[int] = mapped_column(Integer, default=0)
    write_access_roles: Mapped[str] = mapped_column(Text, nullable=True)  # CSV of roles
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
