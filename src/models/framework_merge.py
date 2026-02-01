"""
FrameworkMerge model - Merged framework analysis for couples sessions.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, JSONType


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class FrameworkMerge(Base):
    """SQLAlchemy model for framework_merges table."""

    __tablename__ = "framework_merges"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    couple_link_id = Column(PG_UUID(as_uuid=True), ForeignKey("couple_links.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    partner_a_frameworks = Column(JSONType, nullable=False, default=list)  # Abstracted only
    partner_b_frameworks = Column(JSONType, nullable=False, default=list)  # Abstracted only
    merged_insights = Column(JSONType, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    couple_link = relationship("CoupleLink", back_populates="framework_merges")
    session = relationship("Session", back_populates="framework_merges")

    def __repr__(self) -> str:
        return f"<FrameworkMerge(id={self.id}, couple_link_id={self.couple_link_id})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class FrameworkMergeBase(BaseModel):
    """Base schema for framework merge data."""
    couple_link_id: UUID = Field(..., description="ID of the couple link")
    session_id: UUID = Field(..., description="ID of the couples session")


class FrameworkMergeCreate(FrameworkMergeBase):
    """Schema for creating a new framework merge."""
    partner_a_frameworks: list[str] = Field(
        default_factory=list,
        description="Abstracted framework names for partner A (NO specific content)"
    )
    partner_b_frameworks: list[str] = Field(
        default_factory=list,
        description="Abstracted framework names for partner B (NO specific content)"
    )
    merged_insights: list[dict[str, Any]] = Field(default_factory=list)


class FrameworkMergeRead(FrameworkMergeBase):
    """Schema for reading framework merge data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_a_frameworks: list[str] = []
    partner_b_frameworks: list[str] = []
    merged_insights: list[dict[str, Any]] = []
    created_at: datetime
