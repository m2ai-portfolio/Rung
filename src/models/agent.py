"""
Agent model - AI agents (Rung for therapist, Beth for client).
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from src.models.base import Base


# =============================================================================
# Enums
# =============================================================================

class AgentName(str, Enum):
    """Agent type identifier."""
    RUNG = "rung"  # Clinical agent for therapist
    BETH = "beth"  # Client-facing agent


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class Agent(Base):
    """SQLAlchemy model for agents table."""

    __tablename__ = "agents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(SQLEnum(AgentName), nullable=False)
    client_id = Column(PG_UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("client_id", "name", name="unique_agent_per_client"),
    )

    # Relationships
    client = relationship("Client", back_populates="agents")
    clinical_briefs = relationship("ClinicalBrief", back_populates="agent")
    client_guides = relationship("ClientGuide", back_populates="agent")

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name}, client_id={self.client_id})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class AgentBase(BaseModel):
    """Base schema for agent data."""
    name: AgentName = Field(..., description="Agent type (rung or beth)")
    client_id: UUID = Field(..., description="ID of the associated client")


class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    system_prompt: Optional[str] = Field(None, description="Custom system prompt for the agent")


class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    system_prompt: Optional[str] = Field(None, description="Custom system prompt for the agent")


class AgentRead(AgentBase):
    """Schema for reading agent data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    system_prompt: Optional[str] = None
    created_at: datetime
    updated_at: datetime
