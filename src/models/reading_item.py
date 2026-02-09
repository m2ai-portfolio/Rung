"""
ReadingItem model - Tracks articles and books for therapy session discussion.

Stores reading list items that clients can tag for discussion or therapists
can assign as homework. Integrates with the pre-session pipeline to give
therapists structured context about client reading.

PHI classification:
- url, title, source: NOT PHI (public articles/books)
- notes_encrypted: PHI (client's psychological reflections)
- assignment_notes_encrypted: PHI (therapist instructions may reference treatment)
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Index, LargeBinary, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# Enums
# =============================================================================

class ReadingStatus(str, Enum):
    """Status of a reading list item."""
    UNREAD = "unread"
    READING = "reading"
    COMPLETED = "completed"
    DISCUSSED = "discussed"


class AddedByRole(str, Enum):
    """Role of the user who added the reading item."""
    CLIENT = "client"
    THERAPIST = "therapist"


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class ReadingItem(Base):
    """SQLAlchemy model for reading_items table.

    Stores reading list entries (articles, books) that clients flag for
    therapy session discussion or that therapists assign as homework.
    Notes fields are encrypted at rest as they may contain PHI.
    Supports soft delete for HIPAA audit trail preservation.
    """

    __tablename__ = "reading_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    client_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
    )
    added_by_role = Column(SQLEnum(AddedByRole), nullable=False)
    added_by_user_id = Column(PG_UUID(as_uuid=True), nullable=False)
    url = Column(String(2048), nullable=False)
    title = Column(String(500), nullable=False)
    source = Column(String(255), nullable=True)
    notes_encrypted = Column(LargeBinary, nullable=True)  # PHI - client reflections
    discuss_in_session = Column(Boolean, nullable=False, default=False)
    is_assignment = Column(Boolean, nullable=False, default=False)
    assignment_notes_encrypted = Column(LargeBinary, nullable=True)  # PHI - therapist instructions
    status = Column(SQLEnum(ReadingStatus), nullable=False, default=ReadingStatus.UNREAD)
    session_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_reading_items_client_id", "client_id"),
        Index("ix_reading_items_client_discuss", "client_id", "discuss_in_session"),
        Index("ix_reading_items_client_status", "client_id", "status"),
    )

    # Relationships
    client = relationship("Client", back_populates="reading_items")

    def __repr__(self) -> str:
        return (
            f"<ReadingItem(id={self.id}, client_id={self.client_id}, "
            f"title={self.title!r}, status={self.status})>"
        )


# =============================================================================
# Pydantic Schemas
# =============================================================================

class ReadingItemCreate(BaseModel):
    """Schema for a client adding a reading item."""
    url: str = Field(..., max_length=2048, description="Article or book URL")
    title: str = Field(..., max_length=500, description="Title of the article/book")
    source: Optional[str] = Field(None, max_length=255, description="Source (e.g., 'Psychology Today', 'book')")
    notes: Optional[str] = Field(None, description="Client's personal notes/reflections (will be encrypted)")
    discuss_in_session: bool = Field(False, description="Flag for pre-session pipeline discussion")


class ReadingItemAssign(BaseModel):
    """Schema for a therapist assigning reading to a client."""
    url: str = Field(..., max_length=2048, description="Article or book URL")
    title: str = Field(..., max_length=500, description="Title of the article/book")
    source: Optional[str] = Field(None, max_length=255, description="Source (e.g., 'Psychology Today', 'book')")
    assignment_notes: Optional[str] = Field(None, description="Therapist instructions (will be encrypted)")


class ReadingItemUpdate(BaseModel):
    """Schema for updating a reading item."""
    notes: Optional[str] = Field(None, description="Updated client notes (will be encrypted)")
    discuss_in_session: Optional[bool] = Field(None, description="Flag for session discussion")
    status: Optional[ReadingStatus] = Field(None, description="Updated reading status")
    session_id: Optional[UUID] = Field(None, description="Session where item was discussed")


class ReadingItemRead(BaseModel):
    """Schema for reading item data (list view - no decrypted notes)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    added_by_role: AddedByRole
    added_by_user_id: UUID
    url: str
    title: str
    source: Optional[str] = None
    has_notes: bool = Field(False, description="Whether client notes exist (not decrypted in list)")
    discuss_in_session: bool
    is_assignment: bool
    has_assignment_notes: bool = Field(False, description="Whether therapist notes exist (not decrypted in list)")
    status: ReadingStatus
    session_id: Optional[UUID] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class ReadingItemDetail(ReadingItemRead):
    """Schema for reading item detail view (with decrypted notes)."""
    notes: Optional[str] = Field(None, description="Decrypted client notes")
    assignment_notes: Optional[str] = Field(None, description="Decrypted therapist assignment notes")
