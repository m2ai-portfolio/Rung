"""
Session model - Therapy sessions with encrypted notes.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# Enums
# =============================================================================

class SessionType(str, Enum):
    """Type of therapy session."""
    INDIVIDUAL = "individual"
    COUPLES = "couples"


class SessionStatus(str, Enum):
    """Status of a therapy session."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class Session(Base):
    """SQLAlchemy model for sessions table."""

    __tablename__ = "sessions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    session_type = Column(SQLEnum(SessionType), nullable=False, default=SessionType.INDIVIDUAL)
    session_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(SQLEnum(SessionStatus), nullable=False, default=SessionStatus.SCHEDULED)
    notes_encrypted = Column(LargeBinary, nullable=True)  # PHI
    transcript_s3_key = Column(String, nullable=True)  # S3 key for session transcript
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = relationship("Client", back_populates="sessions")
    clinical_briefs = relationship("ClinicalBrief", back_populates="session")
    client_guides = relationship("ClientGuide", back_populates="session")
    framework_merges = relationship("FrameworkMerge", back_populates="session")
    pipeline_runs = relationship("PipelineRun", back_populates="session")

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, client_id={self.client_id}, status={self.status})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SessionBase(BaseModel):
    """Base schema for session data."""
    client_id: UUID = Field(..., description="ID of the client")
    session_type: SessionType = Field(SessionType.INDIVIDUAL, description="Type of session")
    session_date: datetime = Field(..., description="Scheduled date/time of session")
    status: SessionStatus = Field(SessionStatus.SCHEDULED, description="Session status")


class SessionCreate(SessionBase):
    """Schema for creating a new session."""
    notes: Optional[str] = Field(None, description="Session notes (will be encrypted)")
    transcript_s3_key: Optional[str] = Field(None, description="S3 key for session transcript")


class SessionUpdate(BaseModel):
    """Schema for updating a session."""
    session_type: Optional[SessionType] = None
    session_date: Optional[datetime] = None
    status: Optional[SessionStatus] = None
    notes: Optional[str] = Field(None, description="Session notes (will be encrypted)")
    transcript_s3_key: Optional[str] = Field(None, description="S3 key for session transcript")


class SessionRead(SessionBase):
    """Schema for reading session data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    notes: Optional[str] = Field(None, description="Decrypted notes (if authorized)")
    transcript_s3_key: Optional[str] = Field(None, description="S3 key for session transcript")
    created_at: datetime
    updated_at: datetime
