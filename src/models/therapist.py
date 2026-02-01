"""
Therapist model - Licensed therapists using the Rung system.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class Therapist(Base):
    """SQLAlchemy model for therapists table."""

    __tablename__ = "therapists"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    cognito_sub = Column(String(255), unique=True, nullable=False, index=True)
    email_encrypted = Column(LargeBinary, nullable=False)  # PHI
    practice_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clients = relationship("Client", back_populates="therapist")
    couple_links = relationship("CoupleLink", back_populates="therapist")

    def __repr__(self) -> str:
        return f"<Therapist(id={self.id}, cognito_sub={self.cognito_sub})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class TherapistBase(BaseModel):
    """Base schema for therapist data."""
    cognito_sub: str = Field(..., max_length=255, description="Cognito user sub ID")
    practice_name: Optional[str] = Field(None, max_length=255, description="Name of the practice")


class TherapistCreate(TherapistBase):
    """Schema for creating a new therapist."""
    email: str = Field(..., description="Email address (will be encrypted)")


class TherapistUpdate(BaseModel):
    """Schema for updating a therapist."""
    practice_name: Optional[str] = Field(None, max_length=255)
    email: Optional[str] = Field(None, description="Email address (will be encrypted)")


class TherapistRead(TherapistBase):
    """Schema for reading therapist data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: Optional[str] = Field(None, description="Decrypted email (if authorized)")
    created_at: datetime
    updated_at: datetime
