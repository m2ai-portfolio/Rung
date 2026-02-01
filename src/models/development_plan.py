"""
DevelopmentPlan model - Sprint-based development plans for clients.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, JSONType


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class DevelopmentPlan(Base):
    """SQLAlchemy model for development_plans table."""

    __tablename__ = "development_plans"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    sprint_number = Column(Integer, nullable=False, default=1)
    goals = Column(JSONType, nullable=False, default=list)
    exercises = Column(JSONType, nullable=False, default=list)
    progress = Column(JSONType, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "sprint_number", name="unique_sprint_per_client"),
    )

    # Relationships
    client = relationship("Client", back_populates="development_plans")

    def __repr__(self) -> str:
        return f"<DevelopmentPlan(id={self.id}, client_id={self.client_id}, sprint={self.sprint_number})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class Goal(BaseModel):
    """Schema for a development goal."""
    goal: str = Field(..., description="Goal description")
    metric: str = Field(..., description="How to measure progress")
    target: str = Field(..., description="Target to achieve")


class Exercise(BaseModel):
    """Schema for a development exercise."""
    name: str = Field(..., description="Exercise name")
    frequency: str = Field(..., description="Recommended frequency")
    description: str = Field(..., description="Exercise description")


class DevelopmentPlanBase(BaseModel):
    """Base schema for development plan data."""
    client_id: UUID = Field(..., description="ID of the client")
    sprint_number: int = Field(1, ge=1, description="Sprint number")


class DevelopmentPlanCreate(DevelopmentPlanBase):
    """Schema for creating a new development plan."""
    goals: list[dict[str, Any]] = Field(default_factory=list)
    exercises: list[dict[str, Any]] = Field(default_factory=list)
    progress: dict[str, Any] = Field(default_factory=dict)


class DevelopmentPlanUpdate(BaseModel):
    """Schema for updating a development plan."""
    goals: Optional[list[dict[str, Any]]] = None
    exercises: Optional[list[dict[str, Any]]] = None
    progress: Optional[dict[str, Any]] = None


class DevelopmentPlanRead(DevelopmentPlanBase):
    """Schema for reading development plan data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goals: list[dict[str, Any]] = []
    exercises: list[dict[str, Any]] = []
    progress: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
