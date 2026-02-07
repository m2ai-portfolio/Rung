"""
ProgressMetric model - Tracks quantitative progress metrics for clients.

Stores engagement scores, framework progress, sprint completion rates,
risk levels, and homework completion across sessions.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.models.base import Base, JSONType


# =============================================================================
# Enums
# =============================================================================

class MetricType(str, Enum):
    """Type of progress metric being tracked."""
    SESSION_ENGAGEMENT = "session_engagement"
    FRAMEWORK_PROGRESS = "framework_progress"
    SPRINT_COMPLETION = "sprint_completion"
    RISK_LEVEL = "risk_level"
    HOMEWORK_COMPLETION = "homework_completion"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class ProgressMetric(Base):
    """SQLAlchemy model for progress_metrics table.

    Stores individual progress measurements tied to a client and optionally
    a specific session. Each metric has a type, a numeric value, and optional
    JSON metadata for type-specific context (e.g., framework names, sprint IDs).
    """

    __tablename__ = "progress_metrics"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    metric_type = Column(SQLEnum(MetricType), nullable=False)
    value = Column(Float, nullable=False)
    metadata_json = Column(JSONType, nullable=True)
    measured_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_progress_metrics_client_id", "client_id"),
        Index("ix_progress_metrics_metric_type", "metric_type"),
        Index("ix_progress_metrics_client_type", "client_id", "metric_type"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProgressMetric(id={self.id}, client_id={self.client_id}, "
            f"metric_type={self.metric_type}, value={self.value})>"
        )


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ProgressMetricCreate(BaseModel):
    """Schema for creating a new progress metric."""
    client_id: UUID = Field(..., description="ID of the client")
    session_id: Optional[UUID] = Field(None, description="Optional session ID")
    metric_type: MetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Numeric metric value")
    metadata_json: Optional[dict[str, Any]] = Field(
        None, description="Type-specific metadata (e.g., framework names)"
    )


class ProgressMetricRead(BaseModel):
    """Schema for reading progress metric data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    session_id: Optional[UUID] = None
    metric_type: MetricType
    value: float
    metadata_json: Optional[dict[str, Any]] = None
    measured_at: datetime
    created_at: datetime
