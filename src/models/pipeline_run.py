"""
PipelineRun model - Tracks async pipeline execution for session processing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base, JSONType


# =============================================================================
# Enums
# =============================================================================

class PipelineType(str, Enum):
    """Type of pipeline execution."""
    PRE_SESSION = "pre_session"
    POST_SESSION = "post_session"
    COUPLES_MERGE = "couples_merge"


class PipelineStatus(str, Enum):
    """Status of a pipeline execution."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class PipelineRun(Base):
    """SQLAlchemy model for pipeline_runs table.

    Tracks the execution state of async pipelines including
    pre-session analysis, post-session synthesis, and couples merge.
    """

    __tablename__ = "pipeline_runs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_type = Column(String(50), nullable=False, index=True)
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True)
    couple_link_id = Column(PG_UUID(as_uuid=True), nullable=True)  # For couples_merge pipelines
    status = Column(String(20), nullable=False, default=PipelineStatus.PENDING.value, index=True)
    current_stage = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    metadata_json = Column(JSONType, nullable=False, default=dict)

    # Relationships
    session = relationship("Session", back_populates="pipeline_runs")

    def __repr__(self) -> str:
        return f"<PipelineRun(id={self.id}, type={self.pipeline_type}, status={self.status})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class PipelineRunBase(BaseModel):
    """Base schema for pipeline run data."""
    pipeline_type: PipelineType = Field(..., description="Type of pipeline")
    session_id: Optional[UUID] = Field(None, description="Associated session ID")
    couple_link_id: Optional[UUID] = Field(None, description="Associated couple link ID (for couples_merge)")


class PipelineRunCreate(PipelineRunBase):
    """Schema for creating a new pipeline run."""
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Additional pipeline metadata")


class PipelineRunUpdate(BaseModel):
    """Schema for updating a pipeline run."""
    status: Optional[PipelineStatus] = None
    current_stage: Optional[str] = Field(None, max_length=100)
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata_json: Optional[dict[str, Any]] = None


class PipelineRunRead(PipelineRunBase):
    """Schema for reading pipeline run data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: PipelineStatus
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    metadata_json: dict[str, Any] = {}
