"""
AuditLog model - HIPAA-required audit trail for all PHI access.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from src.models.base import Base, JSONType


# =============================================================================
# SQLAlchemy Model
# =============================================================================

class AuditLog(Base):
    """SQLAlchemy model for audit_logs table."""

    __tablename__ = "audit_logs"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(String(100), nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)  # Nullable for system events
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(PG_UUID(as_uuid=True), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(Text, nullable=True)
    details = Column(JSONType, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, action={self.action})>"


# =============================================================================
# Pydantic Schemas
# =============================================================================

class AuditLogBase(BaseModel):
    """Base schema for audit log data."""
    event_type: str = Field(..., max_length=100, description="Category of event")
    resource_type: str = Field(..., max_length=100, description="Type of resource accessed")
    action: str = Field(..., max_length=50, description="Action performed")


class AuditLogCreate(AuditLogBase):
    """Schema for creating a new audit log entry."""
    user_id: Optional[UUID] = Field(None, description="ID of the user (null for system events)")
    resource_id: Optional[UUID] = Field(None, description="ID of the resource")
    ip_address: Optional[str] = Field(None, max_length=45, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional event context")


class AuditLogRead(AuditLogBase):
    """Schema for reading audit log data."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: Optional[UUID] = None
    resource_id: Optional[UUID] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: dict[str, Any] = {}
    created_at: datetime


# =============================================================================
# Audit Event Types (Constants)
# =============================================================================

class AuditEventType:
    """Standard audit event types for HIPAA compliance."""
    # Access events
    PHI_ACCESS = "phi_access"
    PHI_VIEW = "phi_view"
    PHI_DOWNLOAD = "phi_download"
    PHI_EXPORT = "phi_export"

    # Modification events
    PHI_CREATE = "phi_create"
    PHI_UPDATE = "phi_update"
    PHI_DELETE = "phi_delete"

    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"

    # Authorization events
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHANGE = "permission_change"

    # System events
    SYSTEM_BACKUP = "system_backup"
    SYSTEM_RESTORE = "system_restore"
    CONFIG_CHANGE = "config_change"

    # Agent events
    AGENT_INVOCATION = "agent_invocation"
    AGENT_OUTPUT = "agent_output"
    RESEARCH_QUERY = "research_query"


class AuditAction:
    """Standard audit actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    IMPORT = "import"
    INVOKE = "invoke"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"
