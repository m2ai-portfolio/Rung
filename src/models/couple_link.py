"""
CoupleLink model - Links between partners for couples therapy.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import CheckConstraint, Column, DateTime, Enum as SQLEnum, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# Enums
# =============================================================================

class CoupleStatus(str, Enum):
    """Status of a couple link."""
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class CoupleLink(Base):
    """SQLAlchemy model for couple_links table."""

    __tablename__ = "couple_links"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    partner_a_id = Column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    partner_b_id = Column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    therapist_id = Column(PG_UUID(as_uuid=True), ForeignKey("therapists.id", ondelete="RESTRICT"), nullable=False)
    status = Column(SQLEnum(CoupleStatus), nullable=False, default=CoupleStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("partner_a_id < partner_b_id", name="partner_a_less_than_b"),
        CheckConstraint("partner_a_id != partner_b_id", name="different_partners"),
        UniqueConstraint("partner_a_id", "partner_b_id", name="unique_couple"),
    )

    # Relationships
    therapist = relationship("Therapist", back_populates="couple_links")
    framework_merges = relationship("FrameworkMerge", back_populates="couple_link")

    def __repr__(self) -> str:
        return f"<CoupleLink(id={self.id}, status={self.status})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class CoupleLinkBase(BaseModel):
    """Base schema for couple link data."""
    therapist_id: UUID = Field(..., description="ID of the therapist")
    status: CoupleStatus = Field(CoupleStatus.ACTIVE, description="Link status")


class CoupleLinkCreate(CoupleLinkBase):
    """Schema for creating a new couple link."""
    partner_a_id: UUID = Field(..., description="ID of first partner")
    partner_b_id: UUID = Field(..., description="ID of second partner")

    @model_validator(mode="after")
    def validate_partners(self):
        """Ensure partner_a_id < partner_b_id for consistency."""
        if self.partner_a_id == self.partner_b_id:
            raise ValueError("Partners must be different clients")

        # Swap if necessary to maintain ordering
        if self.partner_a_id > self.partner_b_id:
            self.partner_a_id, self.partner_b_id = self.partner_b_id, self.partner_a_id

        return self


class CoupleLinkUpdate(BaseModel):
    """Schema for updating a couple link."""
    status: Optional[CoupleStatus] = None


class CoupleLinkRead(CoupleLinkBase):
    """Schema for reading couple link data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    partner_a_id: UUID
    partner_b_id: UUID
    created_at: datetime
    updated_at: datetime
