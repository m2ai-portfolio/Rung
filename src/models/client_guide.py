"""
ClientGuide model - Session preparation guides from Beth agent (client-facing).
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

class ClientGuide(Base):
    """SQLAlchemy model for client_guides table."""

    __tablename__ = "client_guides"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(PG_UUID(as_uuid=True), ForeignKey("agents.id", ondelete="RESTRICT"), nullable=False)
    content_encrypted = Column(LargeBinary, nullable=False)  # PHI
    key_points = Column(JSONType, nullable=False, default=list)
    exercises_suggested = Column(JSONType, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="client_guides")
    agent = relationship("Agent", back_populates="client_guides")

    def __repr__(self) -> str:
        return f"<ClientGuide(id={self.id}, session_id={self.session_id})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ExerciseSuggested(BaseModel):
    """Schema for a suggested exercise."""
    name: str = Field(..., description="Name of the exercise")
    description: str = Field(..., description="Exercise description")
    frequency: Optional[str] = Field(None, description="Recommended frequency")


class ClientGuideBase(BaseModel):
    """Base schema for client guide data."""
    session_id: UUID = Field(..., description="ID of the session")
    agent_id: UUID = Field(..., description="ID of the Beth agent")


class ClientGuideCreate(ClientGuideBase):
    """Schema for creating a new client guide."""
    content: str = Field(..., description="Guide content (will be encrypted)")
    key_points: list[str] = Field(default_factory=list)
    exercises_suggested: list[dict[str, Any]] = Field(default_factory=list)


class ClientGuideRead(ClientGuideBase):
    """Schema for reading client guide data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: Optional[str] = Field(None, description="Decrypted content (if authorized)")
    key_points: list[str] = []
    exercises_suggested: list[dict[str, Any]] = []
    created_at: datetime
