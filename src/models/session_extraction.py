"""
SessionExtraction model - Stores framework extraction results from post-session processing.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, JSONType


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class SessionExtraction(Base):
    """SQLAlchemy model for session_extractions table.

    Stores the framework extraction output from post-session processing.
    """

    __tablename__ = "session_extractions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, unique=True)
    frameworks_discussed = Column(JSONType, nullable=False, default=list)
    modalities_used = Column(JSONType, nullable=False, default=list)
    homework_assigned = Column(JSONType, nullable=False, default=list)
    breakthroughs = Column(JSONType, nullable=False, default=list)
    progress_indicators = Column(JSONType, nullable=False, default=list)
    areas_for_next_session = Column(JSONType, nullable=False, default=list)
    session_summary = Column(JSONType, nullable=True)  # Store as text in JSON for consistency
    extraction_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", backref="extraction")

    def __repr__(self) -> str:
        return f"<SessionExtraction(id={self.id}, session_id={self.session_id})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SessionExtractionBase(BaseModel):
    """Base schema for session extraction data."""
    session_id: UUID = Field(..., description="ID of the session")


class SessionExtractionCreate(SessionExtractionBase):
    """Schema for creating a new session extraction."""
    frameworks_discussed: list[str] = Field(default_factory=list)
    modalities_used: list[str] = Field(default_factory=list)
    homework_assigned: list[dict[str, Any]] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)
    progress_indicators: list[str] = Field(default_factory=list)
    areas_for_next_session: list[str] = Field(default_factory=list)
    session_summary: Optional[str] = None
    extraction_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class SessionExtractionRead(SessionExtractionBase):
    """Schema for reading session extraction data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    frameworks_discussed: list[str] = []
    modalities_used: list[str] = []
    homework_assigned: list[dict[str, Any]] = []
    breakthroughs: list[str] = []
    progress_indicators: list[str] = []
    areas_for_next_session: list[str] = []
    session_summary: Optional[str] = None
    extraction_confidence: Optional[float] = None
    created_at: datetime
