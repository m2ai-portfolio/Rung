"""
Centralized Audit Service

Provides structured audit logging for HIPAA compliance.
All PHI access must be logged with who, what, when, where.
"""

from typing import Any, Callable, Optional
from uuid import UUID, uuid4

import structlog

from src.models.audit_log import AuditLog, AuditEventType, AuditAction


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    """Convert a string to a UUID object, or return None."""
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(value)

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Centralized audit logging service for HIPAA compliance.

    Provides structured logging of all PHI access, modifications,
    agent invocations, couples merges, and auth events. Persists
    to the database when a session factory is available, and always
    emits structlog events for CloudWatch ingestion.

    Args:
        session_factory: Optional SQLAlchemy session factory for DB persistence.
            When None, audit entries are logged via structlog only.
    """

    def __init__(self, session_factory: Optional[Callable] = None) -> None:
        self._session_factory = session_factory

    def _create_entry(
        self,
        event_type: str,
        user_id: Optional[str],
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """
        Create an AuditLog entry, persist to DB if possible, and emit structlog event.

        Args:
            event_type: Category of audit event (e.g. phi_access, auth_event).
            user_id: ID of the user performing the action.
            resource_type: Type of resource being accessed/modified.
            resource_id: ID of the specific resource.
            action: Action performed (create, read, update, delete, etc.).
            details: Additional context as a JSON-serializable dict.
            ip_address: Client IP address for the request.

        Returns:
            The created AuditLog ORM instance.
        """
        entry = AuditLog(
            id=uuid4(),
            event_type=event_type,
            user_id=_to_uuid(user_id),
            resource_type=resource_type,
            resource_id=_to_uuid(resource_id),
            action=action,
            ip_address=ip_address,
            details=details or {},
        )

        # Persist to database when session factory is available
        if self._session_factory is not None:
            session = self._session_factory()
            try:
                session.add(entry)
                session.commit()
                session.refresh(entry)
            except Exception:
                session.rollback()
                logger.error(
                    "audit_persist_failed",
                    event_type=event_type,
                    action=action,
                    resource_type=resource_type,
                )
                raise
            finally:
                session.close()

        # Always emit structured log for CloudWatch
        logger.info(
            "audit_event",
            event_type=event_type,
            user_id=str(user_id) if user_id else None,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id else None,
            action=action,
            ip_address=ip_address,
            details=details or {},
        )

        return entry

    def log_phi_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """Log a PHI access event (read/view/download/export)."""
        return self._create_entry(
            event_type=AuditEventType.PHI_ACCESS,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
        )

    def log_phi_modification(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """Log a PHI modification event (create/update/delete)."""
        return self._create_entry(
            event_type=AuditEventType.PHI_UPDATE,
            user_id=user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details,
            ip_address=ip_address,
        )

    def log_agent_invocation(
        self,
        user_id: str,
        agent_name: str,
        client_id: str,
        session_id: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """Log an agent invocation event (Rung or Beth agent call)."""
        combined_details = {
            "agent_name": agent_name,
            "client_id": client_id,
            "session_id": session_id,
            **(details or {}),
        }
        return self._create_entry(
            event_type=AuditEventType.AGENT_INVOCATION,
            user_id=user_id,
            resource_type="agent",
            resource_id=None,
            action=AuditAction.INVOKE,
            details=combined_details,
            ip_address=ip_address,
        )

    def log_couples_merge(
        self,
        therapist_id: str,
        couple_link_id: str,
        partner_a_id: str,
        partner_b_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """Log a couples merge event."""
        combined_details = {
            "couple_link_id": couple_link_id,
            "partner_a_id": partner_a_id,
            "partner_b_id": partner_b_id,
            **(details or {}),
        }
        return self._create_entry(
            event_type="couples_merge",
            user_id=therapist_id,
            resource_type="couple_link",
            resource_id=None,
            action=action,
            details=combined_details,
            ip_address=ip_address,
        )

    def log_auth_event(
        self,
        user_id: str,
        action: str,
        details: Optional[dict[str, Any]] = None,
        ip_address: str = "unknown",
    ) -> AuditLog:
        """Log an authentication/authorization event."""
        return self._create_entry(
            event_type="auth_event",
            user_id=user_id,
            resource_type="auth",
            resource_id=None,
            action=action,
            details=details,
            ip_address=ip_address,
        )

    def get_audit_trail(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        """
        Query audit entries with optional filters.

        Args:
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            user_id: Filter by user ID.
            limit: Maximum number of entries to return.

        Returns:
            List of matching AuditLog entries, newest first.

        Raises:
            RuntimeError: If no session factory is configured.
        """
        if self._session_factory is None:
            return []

        session = self._session_factory()
        try:
            query = session.query(AuditLog)

            if resource_type is not None:
                query = query.filter(AuditLog.resource_type == resource_type)
            if resource_id is not None:
                query = query.filter(AuditLog.resource_id == _to_uuid(resource_id))
            if user_id is not None:
                query = query.filter(AuditLog.user_id == _to_uuid(user_id))

            query = query.order_by(AuditLog.created_at.desc()).limit(limit)
            return query.all()
        finally:
            session.close()
