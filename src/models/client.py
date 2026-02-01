"""
Client model - Therapy clients with encrypted PHI.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# Enums
# =============================================================================

class ConsentStatus(str, Enum):
    """Client consent status for data processing."""
    PENDING = "pending"
    ACTIVE = "active"
    REVOKED = "revoked"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class Client(Base):
    """SQLAlchemy model for clients table."""

    __tablename__ = "clients"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    therapist_id = Column(PG_UUID(as_uuid=True), ForeignKey("therapists.id", ondelete="RESTRICT"), nullable=False)
    name_encrypted = Column(LargeBinary, nullable=False)  # PHI
    contact_encrypted = Column(LargeBinary, nullable=True)  # PHI
    consent_status = Column(SQLEnum(ConsentStatus), nullable=False, default=ConsentStatus.PENDING)
    consent_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint(
            "consent_status != 'active' OR consent_date IS NOT NULL",
            name="consent_date_required_when_active"
        ),
    )

    # Relationships
    therapist = relationship("Therapist", back_populates="clients")
    sessions = relationship("Session", back_populates="client")
    agents = relationship("Agent", back_populates="client")
    development_plans = relationship("DevelopmentPlan", back_populates="client")

    def __repr__(self) -> str:
        return f"<Client(id={self.id}, therapist_id={self.therapist_id}, consent_status={self.consent_status})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ClientBase(BaseModel):
    """Base schema for client data."""
    therapist_id: UUID = Field(..., description="ID of the therapist")
    consent_status: ConsentStatus = Field(ConsentStatus.PENDING, description="Consent status")


class ClientCreate(ClientBase):
    """Schema for creating a new client."""
    name: str = Field(..., description="Client name (will be encrypted)")
    contact: Optional[str] = Field(None, description="Contact info (will be encrypted)")


class ClientUpdate(BaseModel):
    """Schema for updating a client."""
    name: Optional[str] = Field(None, description="Client name (will be encrypted)")
    contact: Optional[str] = Field(None, description="Contact info (will be encrypted)")
    consent_status: Optional[ConsentStatus] = None
    consent_date: Optional[datetime] = None


class ClientRead(ClientBase):
    """Schema for reading client data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: Optional[str] = Field(None, description="Decrypted name (if authorized)")
    contact: Optional[str] = Field(None, description="Decrypted contact (if authorized)")
    consent_date: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
