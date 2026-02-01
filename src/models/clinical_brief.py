"""
ClinicalBrief model - Clinical analysis from Rung agent (therapist-facing).
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, JSONType


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class ClinicalBrief(Base):
    """SQLAlchemy model for clinical_briefs table."""

    __tablename__ = "clinical_briefs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    content_encrypted = Column(LargeBinary, nullable=False)  # PHI
    frameworks_identified = Column(JSONType, nullable=False, default=list)
    risk_flags = Column(JSONType, nullable=False, default=list)
    research_citations = Column(JSONType, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="clinical_briefs")
    agent = relationship("Agent", back_populates="clinical_briefs")

    def __repr__(self) -> str:
        return f"<ClinicalBrief(id={self.id}, session_id={self.session_id})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class FrameworkIdentified(BaseModel):
    """Schema for an identified psychological framework."""
    name: str = Field(..., description="Name of the framework")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    evidence: str = Field(..., description="Supporting evidence from session")


class RiskFlag(BaseModel):
    """Schema for a risk indicator."""
    level: str = Field(..., pattern="^(low|medium|high)$", description="Risk level")
    description: str = Field(..., description="Description of the risk")


class ResearchCitation(BaseModel):
    """Schema for a research citation."""
    title: str = Field(..., description="Title of the research")
    source: str = Field(..., description="Source/publication")
    summary: str = Field(..., description="Brief summary")


class ClinicalBriefBase(BaseModel):
    """Base schema for clinical brief data."""
    session_id: UUID = Field(..., description="ID of the session")
    agent_id: UUID = Field(..., description="ID of the Rung agent")


class ClinicalBriefCreate(ClinicalBriefBase):
    """Schema for creating a new clinical brief."""
    content: str = Field(..., description="Clinical analysis content (will be encrypted)")
    frameworks_identified: list[dict[str, Any]] = Field(default_factory=list)
    risk_flags: list[dict[str, Any]] = Field(default_factory=list)
    research_citations: list[dict[str, Any]] = Field(default_factory=list)


class ClinicalBriefRead(ClinicalBriefBase):
    """Schema for reading clinical brief data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: Optional[str] = Field(None, description="Decrypted content (if authorized)")
    frameworks_identified: list[dict[str, Any]] = []
    risk_flags: list[dict[str, Any]] = []
    research_citations: list[dict[str, Any]] = []
    created_at: datetime
