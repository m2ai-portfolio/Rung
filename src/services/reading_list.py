"""
Reading List Service

Manages reading list items for therapy clients. Handles:
- Client adding articles/books with optional notes
- Therapist assigning reading as homework
- Encrypting/decrypting PHI note fields
- Audit logging for all PHI operations
- Generating pre-session pipeline context for flagged items
- Soft delete for HIPAA audit trail preservation

Designed to work with or without a database session factory.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import structlog

from src.models.client import Client
from src.models.reading_item import (
    AddedByRole,
    ReadingItem,
    ReadingItemCreate,
    ReadingItemAssign,
    ReadingItemDetail,
    ReadingItemRead,
    ReadingItemUpdate,
    ReadingStatus,
)
from src.models.audit_log import AuditAction, AuditEventType
from src.services.audit import AuditService
from src.services.encryption import DevEncryptor, Encryptor, get_encryptor

logger = structlog.get_logger(__name__)


class ReadingListError(Exception):
    """Exception for reading list service errors."""
    pass


class ReadingListService:
    """
    Manages reading list items with encryption and audit logging.

    Args:
        session_factory: Optional SQLAlchemy session factory. If None,
            all methods raise ReadingListError.
        encryptor: Optional encryptor for PHI fields. Falls back to
            get_encryptor() if not provided.
        audit_service: Optional audit service for HIPAA logging.
    """

    def __init__(
        self,
        session_factory=None,
        encryptor: Optional[Encryptor] = None,
        audit_service: Optional[AuditService] = None,
    ):
        self._session_factory = session_factory
        self._encryptor = encryptor or get_encryptor()
        self._audit = audit_service or AuditService(session_factory=session_factory)

    def _get_session(self):
        """Get a database session if factory is available."""
        if self._session_factory is None:
            return None
        return self._session_factory()

    @staticmethod
    def _to_uuid(value) -> UUID:
        """Convert a string or UUID to a UUID object."""
        if isinstance(value, UUID):
            return value
        return UUID(str(value))

    def _encryption_context(self, client_id: str) -> dict[str, str]:
        """Build encryption context for PHI fields."""
        return {"client_id": str(client_id), "resource_type": "reading_item"}

    def _verify_client_access(self, db, user_id: str, user_role: str, client_id: str) -> None:
        """Verify user has access to the client's reading items.

        Args:
            db: Database session.
            user_id: UUID string of the requesting user.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.

        Raises:
            ReadingListError: If access is denied.
        """
        _client_id = self._to_uuid(client_id)
        _user_id = self._to_uuid(user_id)

        client = db.query(Client).filter(Client.id == _client_id).first()
        if client is None:
            raise ReadingListError(f"Client not found: {client_id}")

        if user_role == "client":
            # Client can only access their own items
            if client.id != _user_id:
                raise ReadingListError("Access denied: client can only access their own reading items")
        elif user_role == "therapist":
            # Therapist must own the client
            if client.therapist_id != _user_id:
                raise ReadingListError("Access denied: therapist does not own this client")
        else:
            raise ReadingListError(f"Invalid user role: {user_role}")

    def add_item(
        self,
        user_id: str,
        user_role: str,
        client_id: str,
        data: ReadingItemCreate,
    ) -> ReadingItemRead:
        """Add a reading item for a client.

        Args:
            user_id: UUID string of the user adding the item.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.
            data: Reading item creation data.

        Returns:
            ReadingItemRead with the created item (no decrypted notes).

        Raises:
            ReadingListError: If no database session or access denied.
        """
        db = self._get_session()
        if db is None:
            raise ReadingListError("Cannot add items without a database session.")

        try:
            self._verify_client_access(db, user_id, user_role, client_id)

            _client_id = self._to_uuid(client_id)
            _user_id = self._to_uuid(user_id)
            ctx = self._encryption_context(client_id)

            # Encrypt notes if provided
            notes_encrypted = None
            if data.notes:
                notes_encrypted = self._encryptor.encrypt(data.notes, ctx)

            item = ReadingItem(
                id=uuid4(),
                client_id=_client_id,
                added_by_role=AddedByRole(user_role),
                added_by_user_id=_user_id,
                url=data.url,
                title=data.title,
                source=data.source,
                notes_encrypted=notes_encrypted,
                discuss_in_session=data.discuss_in_session,
                is_assignment=False,
                status=ReadingStatus.UNREAD,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            # Audit log
            self._audit.log_phi_modification(
                user_id=user_id,
                resource_type="reading_item",
                resource_id=str(item.id),
                action=AuditAction.CREATE,
                details={
                    "client_id": client_id,
                    "has_notes": data.notes is not None,
                    "discuss_in_session": data.discuss_in_session,
                },
            )

            return self._to_read_schema(item)

        except ReadingListError:
            raise
        except Exception as e:
            db.rollback()
            raise ReadingListError(f"Failed to add reading item: {e}") from e
        finally:
            db.close()

    def assign_item(
        self,
        therapist_id: str,
        client_id: str,
        data: ReadingItemAssign,
    ) -> ReadingItemRead:
        """Therapist assigns reading to a client.

        Args:
            therapist_id: UUID string of the therapist.
            client_id: UUID string of the client.
            data: Assignment data.

        Returns:
            ReadingItemRead with the created assignment.

        Raises:
            ReadingListError: If no database session or access denied.
        """
        db = self._get_session()
        if db is None:
            raise ReadingListError("Cannot assign items without a database session.")

        try:
            self._verify_client_access(db, therapist_id, "therapist", client_id)

            _client_id = self._to_uuid(client_id)
            _therapist_id = self._to_uuid(therapist_id)
            ctx = self._encryption_context(client_id)

            # Encrypt assignment notes if provided
            assignment_notes_encrypted = None
            if data.assignment_notes:
                assignment_notes_encrypted = self._encryptor.encrypt(data.assignment_notes, ctx)

            item = ReadingItem(
                id=uuid4(),
                client_id=_client_id,
                added_by_role=AddedByRole.THERAPIST,
                added_by_user_id=_therapist_id,
                url=data.url,
                title=data.title,
                source=data.source,
                is_assignment=True,
                assignment_notes_encrypted=assignment_notes_encrypted,
                discuss_in_session=True,
                status=ReadingStatus.UNREAD,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            # Audit log
            self._audit.log_phi_modification(
                user_id=therapist_id,
                resource_type="reading_item",
                resource_id=str(item.id),
                action=AuditAction.CREATE,
                details={
                    "client_id": client_id,
                    "is_assignment": True,
                    "has_assignment_notes": data.assignment_notes is not None,
                },
            )

            return self._to_read_schema(item)

        except ReadingListError:
            raise
        except Exception as e:
            db.rollback()
            raise ReadingListError(f"Failed to assign reading item: {e}") from e
        finally:
            db.close()

    def get_item(
        self,
        user_id: str,
        user_role: str,
        client_id: str,
        item_id: str,
    ) -> ReadingItemDetail:
        """Get a single reading item with decrypted notes.

        Args:
            user_id: UUID string of the requesting user.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.
            item_id: UUID string of the reading item.

        Returns:
            ReadingItemDetail with decrypted notes.

        Raises:
            ReadingListError: If not found, access denied, or DB error.
        """
        db = self._get_session()
        if db is None:
            raise ReadingListError("Cannot get items without a database session.")

        try:
            self._verify_client_access(db, user_id, user_role, client_id)

            _client_id = self._to_uuid(client_id)
            _item_id = self._to_uuid(item_id)

            item = (
                db.query(ReadingItem)
                .filter(
                    ReadingItem.id == _item_id,
                    ReadingItem.client_id == _client_id,
                    ReadingItem.deleted_at.is_(None),
                )
                .first()
            )
            if item is None:
                raise ReadingListError(f"Reading item not found: {item_id}")

            ctx = self._encryption_context(client_id)

            # Decrypt notes
            notes = None
            if item.notes_encrypted:
                notes = self._encryptor.decrypt(item.notes_encrypted, ctx)

            assignment_notes = None
            if item.assignment_notes_encrypted:
                assignment_notes = self._encryptor.decrypt(item.assignment_notes_encrypted, ctx)

            # Audit log - PHI access
            self._audit.log_phi_access(
                user_id=user_id,
                resource_type="reading_item",
                resource_id=str(item.id),
                action=AuditAction.READ,
                details={"client_id": client_id, "decrypted_notes": True},
            )

            return self._to_detail_schema(item, notes=notes, assignment_notes=assignment_notes)

        except ReadingListError:
            raise
        except Exception as e:
            raise ReadingListError(f"Failed to get reading item: {e}") from e
        finally:
            db.close()

    def list_items(
        self,
        user_id: str,
        user_role: str,
        client_id: str,
        status: Optional[ReadingStatus] = None,
        discuss_only: bool = False,
        assignments_only: bool = False,
    ) -> list[ReadingItemRead]:
        """List reading items for a client (no decrypted notes).

        Args:
            user_id: UUID string of the requesting user.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.
            status: Optional filter by reading status.
            discuss_only: If True, only items flagged for discussion.
            assignments_only: If True, only therapist-assigned items.

        Returns:
            List of ReadingItemRead (notes NOT decrypted).
        """
        db = self._get_session()
        if db is None:
            return []

        try:
            self._verify_client_access(db, user_id, user_role, client_id)

            _client_id = self._to_uuid(client_id)

            query = (
                db.query(ReadingItem)
                .filter(
                    ReadingItem.client_id == _client_id,
                    ReadingItem.deleted_at.is_(None),
                )
            )

            if status is not None:
                query = query.filter(ReadingItem.status == status)
            if discuss_only:
                query = query.filter(ReadingItem.discuss_in_session.is_(True))
            if assignments_only:
                query = query.filter(ReadingItem.is_assignment.is_(True))

            items = query.order_by(ReadingItem.created_at.desc()).all()

            return [self._to_read_schema(item) for item in items]

        except ReadingListError:
            raise
        except Exception as e:
            raise ReadingListError(f"Failed to list reading items: {e}") from e
        finally:
            db.close()

    def update_item(
        self,
        user_id: str,
        user_role: str,
        client_id: str,
        item_id: str,
        data: ReadingItemUpdate,
    ) -> ReadingItemRead:
        """Update a reading item.

        Args:
            user_id: UUID string of the requesting user.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.
            item_id: UUID string of the reading item.
            data: Fields to update.

        Returns:
            ReadingItemRead with the updated item.

        Raises:
            ReadingListError: If not found, access denied, or DB error.
        """
        db = self._get_session()
        if db is None:
            raise ReadingListError("Cannot update items without a database session.")

        try:
            self._verify_client_access(db, user_id, user_role, client_id)

            _client_id = self._to_uuid(client_id)
            _item_id = self._to_uuid(item_id)

            item = (
                db.query(ReadingItem)
                .filter(
                    ReadingItem.id == _item_id,
                    ReadingItem.client_id == _client_id,
                    ReadingItem.deleted_at.is_(None),
                )
                .first()
            )
            if item is None:
                raise ReadingListError(f"Reading item not found: {item_id}")

            ctx = self._encryption_context(client_id)
            changes = {}

            if data.notes is not None:
                item.notes_encrypted = self._encryptor.encrypt(data.notes, ctx)
                changes["notes_updated"] = True

            if data.discuss_in_session is not None:
                item.discuss_in_session = data.discuss_in_session
                changes["discuss_in_session"] = data.discuss_in_session

            if data.status is not None:
                item.status = data.status
                changes["status"] = data.status.value
                if data.status == ReadingStatus.COMPLETED:
                    item.completed_at = datetime.utcnow()

            if data.session_id is not None:
                item.session_id = data.session_id
                changes["session_id"] = str(data.session_id)

            item.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(item)

            # Audit log
            self._audit.log_phi_modification(
                user_id=user_id,
                resource_type="reading_item",
                resource_id=str(item.id),
                action=AuditAction.UPDATE,
                details={"client_id": client_id, "changes": changes},
            )

            return self._to_read_schema(item)

        except ReadingListError:
            raise
        except Exception as e:
            db.rollback()
            raise ReadingListError(f"Failed to update reading item: {e}") from e
        finally:
            db.close()

    def delete_item(
        self,
        user_id: str,
        user_role: str,
        client_id: str,
        item_id: str,
    ) -> None:
        """Soft delete a reading item.

        Sets deleted_at timestamp. Item remains in DB for audit trail.

        Args:
            user_id: UUID string of the requesting user.
            user_role: 'client' or 'therapist'.
            client_id: UUID string of the client.
            item_id: UUID string of the reading item.

        Raises:
            ReadingListError: If not found, access denied, or DB error.
        """
        db = self._get_session()
        if db is None:
            raise ReadingListError("Cannot delete items without a database session.")

        try:
            self._verify_client_access(db, user_id, user_role, client_id)

            _client_id = self._to_uuid(client_id)
            _item_id = self._to_uuid(item_id)

            item = (
                db.query(ReadingItem)
                .filter(
                    ReadingItem.id == _item_id,
                    ReadingItem.client_id == _client_id,
                    ReadingItem.deleted_at.is_(None),
                )
                .first()
            )
            if item is None:
                raise ReadingListError(f"Reading item not found: {item_id}")

            item.deleted_at = datetime.utcnow()
            item.updated_at = datetime.utcnow()
            db.commit()

            # Audit log
            self._audit.log_phi_modification(
                user_id=user_id,
                resource_type="reading_item",
                resource_id=str(item.id),
                action=AuditAction.DELETE,
                details={"client_id": client_id, "soft_delete": True},
            )

        except ReadingListError:
            raise
        except Exception as e:
            db.rollback()
            raise ReadingListError(f"Failed to delete reading item: {e}") from e
        finally:
            db.close()

    def get_session_reading_context(self, client_id: str) -> Optional[str]:
        """Generate reading context for the pre-session pipeline.

        Returns formatted text of items flagged for discussion. Does NOT
        include encrypted note content -- only indicates presence of notes.

        Args:
            client_id: UUID string of the client.

        Returns:
            Formatted string for pipeline injection, or None if no items.
        """
        db = self._get_session()
        if db is None:
            return None

        try:
            _client_id = self._to_uuid(client_id)

            items = (
                db.query(ReadingItem)
                .filter(
                    ReadingItem.client_id == _client_id,
                    ReadingItem.discuss_in_session.is_(True),
                    ReadingItem.status != ReadingStatus.DISCUSSED,
                    ReadingItem.deleted_at.is_(None),
                )
                .order_by(ReadingItem.created_at.asc())
                .all()
            )

            if not items:
                return None

            lines = [f"Client has flagged {len(items)} article(s) for session discussion:"]
            for i, item in enumerate(items, 1):
                # Build description
                source_part = f" ({item.source})" if item.source else ""
                notes_part = " - client added personal notes" if item.notes_encrypted else " - no notes"
                prefix = "[Therapist-assigned] " if item.is_assignment else ""
                lines.append(f'{i}. {prefix}"{item.title}"{source_part}{notes_part}')

            return "\n".join(lines)

        except Exception as e:
            logger.warning(
                "reading_context_failed",
                client_id=client_id,
                error=str(e),
            )
            return None
        finally:
            db.close()

    # =========================================================================
    # Private helpers
    # =========================================================================

    @staticmethod
    def _to_read_schema(item: ReadingItem) -> ReadingItemRead:
        """Convert a ReadingItem ORM object to ReadingItemRead schema."""
        return ReadingItemRead(
            id=item.id,
            client_id=item.client_id,
            added_by_role=item.added_by_role,
            added_by_user_id=item.added_by_user_id,
            url=item.url,
            title=item.title,
            source=item.source,
            has_notes=item.notes_encrypted is not None,
            discuss_in_session=item.discuss_in_session,
            is_assignment=item.is_assignment,
            has_assignment_notes=item.assignment_notes_encrypted is not None,
            status=item.status,
            session_id=item.session_id,
            completed_at=item.completed_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

    @staticmethod
    def _to_detail_schema(
        item: ReadingItem,
        notes: Optional[str] = None,
        assignment_notes: Optional[str] = None,
    ) -> ReadingItemDetail:
        """Convert a ReadingItem ORM object to ReadingItemDetail schema."""
        return ReadingItemDetail(
            id=item.id,
            client_id=item.client_id,
            added_by_role=item.added_by_role,
            added_by_user_id=item.added_by_user_id,
            url=item.url,
            title=item.title,
            source=item.source,
            has_notes=item.notes_encrypted is not None,
            discuss_in_session=item.discuss_in_session,
            is_assignment=item.is_assignment,
            has_assignment_notes=item.assignment_notes_encrypted is not None,
            status=item.status,
            session_id=item.session_id,
            completed_at=item.completed_at,
            created_at=item.created_at,
            updated_at=item.updated_at,
            notes=notes,
            assignment_notes=assignment_notes,
        )
