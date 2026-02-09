"""
Reading List Service Tests

Tests verify:
1. All service methods (add, assign, get, list, update, delete)
2. Encryption round-trip for notes
3. Audit log generation per PHI operation
4. Authorization checks (client isolation, therapist ownership)
5. Pipeline context generation format
6. Soft delete behavior
7. PHI boundary enforcement (no notes in context output)
"""

import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, call
from uuid import uuid4

os.environ["AWS_REGION"] = "us-east-1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.reading_item import (
    AddedByRole,
    ReadingItem,
    ReadingItemAssign,
    ReadingItemCreate,
    ReadingItemUpdate,
    ReadingStatus,
)
from src.services.encryption import DevEncryptor
from src.services.reading_list import ReadingListError, ReadingListService

# Import all models to register with Base.metadata
import src.models  # noqa: F401


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def engine():
    """In-memory SQLite engine with all tables created."""
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture()
def sf(engine):
    """Session factory bound to the in-memory engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def encryptor():
    """Dev encryptor for testing."""
    return DevEncryptor()


@pytest.fixture()
def mock_audit():
    """Mock audit service."""
    from src.services.audit import AuditService
    mock = MagicMock(spec=AuditService)
    return mock


@pytest.fixture()
def therapist_id():
    return uuid4()


@pytest.fixture()
def client_id():
    return uuid4()


@pytest.fixture()
def other_client_id():
    return uuid4()


@pytest.fixture()
def other_therapist_id():
    return uuid4()


@pytest.fixture()
def setup_data(sf, therapist_id, client_id, other_client_id, other_therapist_id):
    """Create therapist, client, and another client in the DB."""
    from src.models.therapist import Therapist
    from src.models.client import Client

    session = sf()
    # Therapist 1
    session.add(Therapist(
        id=therapist_id,
        cognito_sub=f"cognito-{therapist_id}",
        email_encrypted=b"therapist@test.com",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    # Therapist 2
    session.add(Therapist(
        id=other_therapist_id,
        cognito_sub=f"cognito-{other_therapist_id}",
        email_encrypted=b"other-therapist@test.com",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    # Client 1 (owned by therapist 1)
    session.add(Client(
        id=client_id,
        therapist_id=therapist_id,
        name_encrypted=b"client-name",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    # Client 2 (owned by therapist 2)
    session.add(Client(
        id=other_client_id,
        therapist_id=other_therapist_id,
        name_encrypted=b"other-client-name",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    ))
    session.commit()
    session.close()


@pytest.fixture()
def service(sf, encryptor, mock_audit):
    """Create ReadingListService with test dependencies."""
    return ReadingListService(
        session_factory=sf,
        encryptor=encryptor,
        audit_service=mock_audit,
    )


# =============================================================================
# Add Item Tests
# =============================================================================

class TestAddItem:
    """Tests for add_item."""

    def test_add_item_as_client(self, service, setup_data, client_id):
        """Client adds an article to their reading list."""
        data = ReadingItemCreate(
            url="https://www.psychologytoday.com/article/123",
            title="What Are You Designed to Do?",
            source="Psychology Today",
            notes="This resonated with my career exploration.",
            discuss_in_session=True,
        )
        result = service.add_item(
            user_id=str(client_id),
            user_role="client",
            client_id=str(client_id),
            data=data,
        )
        assert result.title == "What Are You Designed to Do?"
        assert result.source == "Psychology Today"
        assert result.discuss_in_session is True
        assert result.is_assignment is False
        assert result.has_notes is True
        assert result.status == ReadingStatus.UNREAD

    def test_add_item_generates_audit_log(self, service, setup_data, client_id, mock_audit):
        """Adding an item generates a PHI create audit entry."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Test",
            notes="Some notes",
        )
        service.add_item(str(client_id), "client", str(client_id), data)

        mock_audit.log_phi_modification.assert_called_once()
        call_kwargs = mock_audit.log_phi_modification.call_args
        assert call_kwargs.kwargs["action"] == "create"
        assert call_kwargs.kwargs["resource_type"] == "reading_item"

    def test_add_item_without_notes(self, service, setup_data, client_id):
        """Adding an item without notes sets has_notes=False."""
        data = ReadingItemCreate(url="https://example.com", title="No Notes")
        result = service.add_item(str(client_id), "client", str(client_id), data)
        assert result.has_notes is False

    def test_add_item_as_therapist(self, service, setup_data, therapist_id, client_id):
        """Therapist adds an item to their client's list."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Therapist Added",
        )
        result = service.add_item(
            user_id=str(therapist_id),
            user_role="therapist",
            client_id=str(client_id),
            data=data,
        )
        assert result.added_by_role == AddedByRole.THERAPIST

    def test_client_cannot_add_to_other_client(self, service, setup_data, client_id, other_client_id):
        """Client A cannot add items to Client B's list."""
        data = ReadingItemCreate(url="https://example.com", title="Sneaky")
        with pytest.raises(ReadingListError, match="Access denied"):
            service.add_item(str(client_id), "client", str(other_client_id), data)

    def test_therapist_cannot_add_to_unowned_client(self, service, setup_data, therapist_id, other_client_id):
        """Therapist cannot add items for a client they don't own."""
        data = ReadingItemCreate(url="https://example.com", title="Wrong Client")
        with pytest.raises(ReadingListError, match="Access denied"):
            service.add_item(str(therapist_id), "therapist", str(other_client_id), data)

    def test_no_session_factory_raises(self, encryptor, mock_audit):
        """Service without session factory raises error."""
        svc = ReadingListService(session_factory=None, encryptor=encryptor, audit_service=mock_audit)
        data = ReadingItemCreate(url="https://example.com", title="Test")
        with pytest.raises(ReadingListError, match="database session"):
            svc.add_item("user", "client", "client", data)


# =============================================================================
# Assign Item Tests
# =============================================================================

class TestAssignItem:
    """Tests for assign_item."""

    def test_therapist_assigns_reading(self, service, setup_data, therapist_id, client_id):
        """Therapist assigns a book to their client."""
        data = ReadingItemAssign(
            url="https://example.com/mindset",
            title="Mindset: The New Psychology of Success",
            source="book",
            assignment_notes="Read chapters 1-3 before our next session.",
        )
        result = service.assign_item(str(therapist_id), str(client_id), data)

        assert result.is_assignment is True
        assert result.added_by_role == AddedByRole.THERAPIST
        assert result.discuss_in_session is True  # assignments auto-flagged
        assert result.has_assignment_notes is True
        assert result.status == ReadingStatus.UNREAD

    def test_assign_generates_audit_log(self, service, setup_data, therapist_id, client_id, mock_audit):
        """Assigning generates a PHI create audit entry."""
        data = ReadingItemAssign(url="https://example.com", title="Test")
        service.assign_item(str(therapist_id), str(client_id), data)

        mock_audit.log_phi_modification.assert_called_once()
        details = mock_audit.log_phi_modification.call_args.kwargs["details"]
        assert details["is_assignment"] is True


# =============================================================================
# Get Item Tests (with decrypted notes)
# =============================================================================

class TestGetItem:
    """Tests for get_item."""

    def test_get_item_decrypts_notes(self, service, setup_data, client_id):
        """Getting an item decrypts client notes."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Test Article",
            notes="My personal reflection about this reading.",
        )
        created = service.add_item(str(client_id), "client", str(client_id), data)

        detail = service.get_item(str(client_id), "client", str(client_id), str(created.id))

        assert detail.notes == "My personal reflection about this reading."

    def test_get_item_decrypts_assignment_notes(self, service, setup_data, therapist_id, client_id):
        """Getting an assigned item decrypts therapist notes."""
        data = ReadingItemAssign(
            url="https://example.com",
            title="Assigned Book",
            assignment_notes="Focus on chapter about grief.",
        )
        created = service.assign_item(str(therapist_id), str(client_id), data)

        detail = service.get_item(str(therapist_id), "therapist", str(client_id), str(created.id))

        assert detail.assignment_notes == "Focus on chapter about grief."

    def test_get_item_generates_audit_log(self, service, setup_data, client_id, mock_audit):
        """Getting an item generates a PHI access audit entry."""
        data = ReadingItemCreate(url="https://example.com", title="Test")
        created = service.add_item(str(client_id), "client", str(client_id), data)
        mock_audit.reset_mock()

        service.get_item(str(client_id), "client", str(client_id), str(created.id))

        mock_audit.log_phi_access.assert_called_once()
        details = mock_audit.log_phi_access.call_args.kwargs["details"]
        assert details["decrypted_notes"] is True

    def test_get_nonexistent_item_raises(self, service, setup_data, client_id):
        """Getting a nonexistent item raises error."""
        with pytest.raises(ReadingListError, match="not found"):
            service.get_item(str(client_id), "client", str(client_id), str(uuid4()))

    def test_get_soft_deleted_item_raises(self, service, setup_data, client_id):
        """Getting a soft-deleted item raises not found."""
        data = ReadingItemCreate(url="https://example.com", title="Deleted")
        created = service.add_item(str(client_id), "client", str(client_id), data)
        service.delete_item(str(client_id), "client", str(client_id), str(created.id))

        with pytest.raises(ReadingListError, match="not found"):
            service.get_item(str(client_id), "client", str(client_id), str(created.id))


# =============================================================================
# List Items Tests
# =============================================================================

class TestListItems:
    """Tests for list_items."""

    def test_list_items_for_client(self, service, setup_data, client_id):
        """List all items for a client."""
        for i in range(3):
            data = ReadingItemCreate(url=f"https://example.com/{i}", title=f"Article {i}")
            service.add_item(str(client_id), "client", str(client_id), data)

        items = service.list_items(str(client_id), "client", str(client_id))
        assert len(items) == 3

    def test_list_items_excludes_soft_deleted(self, service, setup_data, client_id):
        """Soft-deleted items are excluded from list."""
        data1 = ReadingItemCreate(url="https://example.com/1", title="Keep")
        data2 = ReadingItemCreate(url="https://example.com/2", title="Delete")
        service.add_item(str(client_id), "client", str(client_id), data1)
        created2 = service.add_item(str(client_id), "client", str(client_id), data2)
        service.delete_item(str(client_id), "client", str(client_id), str(created2.id))

        items = service.list_items(str(client_id), "client", str(client_id))
        assert len(items) == 1
        assert items[0].title == "Keep"

    def test_list_items_filter_by_status(self, service, setup_data, client_id):
        """Filter items by status."""
        data = ReadingItemCreate(url="https://example.com/1", title="Unread")
        service.add_item(str(client_id), "client", str(client_id), data)

        data2 = ReadingItemCreate(url="https://example.com/2", title="Reading")
        created2 = service.add_item(str(client_id), "client", str(client_id), data2)
        service.update_item(
            str(client_id), "client", str(client_id), str(created2.id),
            ReadingItemUpdate(status=ReadingStatus.READING),
        )

        items = service.list_items(str(client_id), "client", str(client_id), status=ReadingStatus.UNREAD)
        assert len(items) == 1
        assert items[0].title == "Unread"

    def test_list_items_discuss_only(self, service, setup_data, client_id):
        """Filter items flagged for discussion."""
        data1 = ReadingItemCreate(url="https://example.com/1", title="Discuss", discuss_in_session=True)
        data2 = ReadingItemCreate(url="https://example.com/2", title="No Discuss", discuss_in_session=False)
        service.add_item(str(client_id), "client", str(client_id), data1)
        service.add_item(str(client_id), "client", str(client_id), data2)

        items = service.list_items(str(client_id), "client", str(client_id), discuss_only=True)
        assert len(items) == 1
        assert items[0].title == "Discuss"

    def test_list_items_assignments_only(self, service, setup_data, therapist_id, client_id):
        """Filter for therapist-assigned items only."""
        data1 = ReadingItemCreate(url="https://example.com/1", title="Client Added")
        service.add_item(str(client_id), "client", str(client_id), data1)

        data2 = ReadingItemAssign(url="https://example.com/2", title="Therapist Assigned")
        service.assign_item(str(therapist_id), str(client_id), data2)

        items = service.list_items(str(therapist_id), "therapist", str(client_id), assignments_only=True)
        assert len(items) == 1
        assert items[0].title == "Therapist Assigned"

    def test_list_does_not_decrypt_notes(self, service, setup_data, client_id):
        """List endpoint returns has_notes but NOT decrypted content."""
        data = ReadingItemCreate(url="https://example.com", title="With Notes", notes="Secret thoughts")
        service.add_item(str(client_id), "client", str(client_id), data)

        items = service.list_items(str(client_id), "client", str(client_id))
        assert len(items) == 1
        assert items[0].has_notes is True
        # ReadingItemRead doesn't have notes/assignment_notes fields
        assert not hasattr(items[0], "notes") or getattr(items[0], "notes", None) is None

    def test_list_empty_without_session_factory(self, encryptor, mock_audit):
        """Service without session factory returns empty list."""
        svc = ReadingListService(session_factory=None, encryptor=encryptor, audit_service=mock_audit)
        items = svc.list_items("user", "client", "client")
        assert items == []


# =============================================================================
# Update Item Tests
# =============================================================================

class TestUpdateItem:
    """Tests for update_item."""

    def test_update_status(self, service, setup_data, client_id):
        """Update reading status."""
        data = ReadingItemCreate(url="https://example.com", title="Test")
        created = service.add_item(str(client_id), "client", str(client_id), data)

        result = service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(status=ReadingStatus.READING),
        )
        assert result.status == ReadingStatus.READING

    def test_update_sets_completed_at(self, service, setup_data, client_id):
        """Setting status to COMPLETED auto-sets completed_at."""
        data = ReadingItemCreate(url="https://example.com", title="Test")
        created = service.add_item(str(client_id), "client", str(client_id), data)

        result = service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(status=ReadingStatus.COMPLETED),
        )
        assert result.status == ReadingStatus.COMPLETED
        assert result.completed_at is not None

    def test_update_notes_re_encrypts(self, service, setup_data, client_id):
        """Updating notes re-encrypts them."""
        data = ReadingItemCreate(url="https://example.com", title="Test", notes="Original")
        created = service.add_item(str(client_id), "client", str(client_id), data)

        service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(notes="Updated reflection"),
        )

        detail = service.get_item(str(client_id), "client", str(client_id), str(created.id))
        assert detail.notes == "Updated reflection"

    def test_update_discuss_flag(self, service, setup_data, client_id):
        """Toggle discuss_in_session flag."""
        data = ReadingItemCreate(url="https://example.com", title="Test", discuss_in_session=False)
        created = service.add_item(str(client_id), "client", str(client_id), data)

        result = service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(discuss_in_session=True),
        )
        assert result.discuss_in_session is True

    def test_update_generates_audit_log(self, service, setup_data, client_id, mock_audit):
        """Updating generates a PHI update audit entry."""
        data = ReadingItemCreate(url="https://example.com", title="Test")
        created = service.add_item(str(client_id), "client", str(client_id), data)
        mock_audit.reset_mock()

        service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(status=ReadingStatus.READING),
        )

        mock_audit.log_phi_modification.assert_called_once()
        assert mock_audit.log_phi_modification.call_args.kwargs["action"] == "update"


# =============================================================================
# Delete Item Tests
# =============================================================================

class TestDeleteItem:
    """Tests for delete_item (soft delete)."""

    def test_soft_delete_sets_deleted_at(self, service, sf, setup_data, client_id):
        """Soft delete sets deleted_at but keeps record."""
        data = ReadingItemCreate(url="https://example.com", title="To Delete")
        created = service.add_item(str(client_id), "client", str(client_id), data)

        service.delete_item(str(client_id), "client", str(client_id), str(created.id))

        # Verify still in DB
        session = sf()
        item = session.query(ReadingItem).filter(ReadingItem.id == created.id).first()
        assert item is not None
        assert item.deleted_at is not None
        session.close()

    def test_delete_generates_audit_log(self, service, setup_data, client_id, mock_audit):
        """Delete generates a PHI delete audit entry."""
        data = ReadingItemCreate(url="https://example.com", title="Test")
        created = service.add_item(str(client_id), "client", str(client_id), data)
        mock_audit.reset_mock()

        service.delete_item(str(client_id), "client", str(client_id), str(created.id))

        mock_audit.log_phi_modification.assert_called_once()
        call_kwargs = mock_audit.log_phi_modification.call_args.kwargs
        assert call_kwargs["action"] == "delete"
        assert call_kwargs["details"]["soft_delete"] is True

    def test_delete_nonexistent_raises(self, service, setup_data, client_id):
        """Deleting a nonexistent item raises error."""
        with pytest.raises(ReadingListError, match="not found"):
            service.delete_item(str(client_id), "client", str(client_id), str(uuid4()))


# =============================================================================
# Pipeline Context Tests
# =============================================================================

class TestGetSessionReadingContext:
    """Tests for get_session_reading_context."""

    def test_context_with_flagged_items(self, service, setup_data, therapist_id, client_id):
        """Generate context text for flagged items."""
        # Client item with notes
        service.add_item(
            str(client_id), "client", str(client_id),
            ReadingItemCreate(
                url="https://example.com/1",
                title="What Are You Designed to Do?",
                source="Psychology Today",
                notes="This resonated.",
                discuss_in_session=True,
            ),
        )
        # Client item without notes
        service.add_item(
            str(client_id), "client", str(client_id),
            ReadingItemCreate(
                url="https://example.com/2",
                title="Understanding Growth Mindset",
                source="Psychology Today",
                discuss_in_session=True,
            ),
        )
        # Therapist assignment
        service.assign_item(
            str(therapist_id), str(client_id),
            ReadingItemAssign(
                url="https://example.com/3",
                title="Mindset: The New Psychology of Success",
                source="book",
            ),
        )

        context = service.get_session_reading_context(str(client_id))

        assert context is not None
        assert "3 article(s)" in context
        assert '"What Are You Designed to Do?"' in context
        assert "client added personal notes" in context
        assert '"Understanding Growth Mindset"' in context
        assert "no notes" in context
        assert "[Therapist-assigned]" in context
        assert '"Mindset: The New Psychology of Success"' in context

    def test_context_excludes_discussed_items(self, service, setup_data, client_id):
        """Items with status=discussed are excluded from context."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Already Discussed",
            discuss_in_session=True,
        )
        created = service.add_item(str(client_id), "client", str(client_id), data)
        service.update_item(
            str(client_id), "client", str(client_id), str(created.id),
            ReadingItemUpdate(status=ReadingStatus.DISCUSSED),
        )

        context = service.get_session_reading_context(str(client_id))
        assert context is None

    def test_context_excludes_soft_deleted(self, service, setup_data, client_id):
        """Soft-deleted items are excluded from context."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Deleted",
            discuss_in_session=True,
        )
        created = service.add_item(str(client_id), "client", str(client_id), data)
        service.delete_item(str(client_id), "client", str(client_id), str(created.id))

        context = service.get_session_reading_context(str(client_id))
        assert context is None

    def test_context_returns_none_when_no_items(self, service, setup_data, client_id):
        """No flagged items returns None."""
        context = service.get_session_reading_context(str(client_id))
        assert context is None

    def test_context_does_not_contain_encrypted_notes(self, service, setup_data, client_id):
        """HIPAA: Context output must NOT contain encrypted note content."""
        service.add_item(
            str(client_id), "client", str(client_id),
            ReadingItemCreate(
                url="https://example.com",
                title="Test",
                notes="My deepest psychological reflection about my mother.",
                discuss_in_session=True,
            ),
        )

        context = service.get_session_reading_context(str(client_id))
        assert "My deepest psychological reflection" not in context
        assert "client added personal notes" in context

    def test_context_returns_none_without_session_factory(self, encryptor, mock_audit):
        """Service without session factory returns None."""
        svc = ReadingListService(session_factory=None, encryptor=encryptor, audit_service=mock_audit)
        context = svc.get_session_reading_context("some-client")
        assert context is None


# =============================================================================
# Encryption Round-Trip Tests
# =============================================================================

class TestEncryptionRoundTrip:
    """HIPAA: Verify encryption is actually applied to PHI fields."""

    def test_notes_encrypted_in_db(self, service, sf, setup_data, client_id):
        """Raw DB query shows encrypted bytes, not plaintext."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Encrypted Test",
            notes="This is my personal reflection.",
        )
        created = service.add_item(str(client_id), "client", str(client_id), data)

        # Direct DB query
        session = sf()
        item = session.query(ReadingItem).filter(ReadingItem.id == created.id).first()
        assert item.notes_encrypted is not None
        assert isinstance(item.notes_encrypted, bytes)
        # Encrypted bytes should NOT contain the plaintext
        assert b"This is my personal reflection" not in item.notes_encrypted
        session.close()

    def test_assignment_notes_encrypted_in_db(self, service, sf, setup_data, therapist_id, client_id):
        """Assignment notes are also encrypted at rest."""
        data = ReadingItemAssign(
            url="https://example.com",
            title="Assigned",
            assignment_notes="Read this about grief - relates to your mother's passing.",
        )
        created = service.assign_item(str(therapist_id), str(client_id), data)

        session = sf()
        item = session.query(ReadingItem).filter(ReadingItem.id == created.id).first()
        assert item.assignment_notes_encrypted is not None
        assert isinstance(item.assignment_notes_encrypted, bytes)
        assert b"grief" not in item.assignment_notes_encrypted
        session.close()

    def test_encryption_decryption_round_trip(self, service, setup_data, client_id):
        """Write encrypted notes, read back decrypted."""
        original_notes = "I noticed my tendency to intellectualize during our session."
        data = ReadingItemCreate(
            url="https://example.com",
            title="Round Trip Test",
            notes=original_notes,
        )
        created = service.add_item(str(client_id), "client", str(client_id), data)

        detail = service.get_item(str(client_id), "client", str(client_id), str(created.id))
        assert detail.notes == original_notes


# =============================================================================
# Authorization Tests
# =============================================================================

class TestAuthorization:
    """HIPAA: Client isolation and therapist ownership checks."""

    def test_client_isolation_list(self, service, setup_data, client_id, other_client_id):
        """Client A cannot list Client B's reading items."""
        # Add items for both clients
        service.add_item(
            str(client_id), "client", str(client_id),
            ReadingItemCreate(url="https://example.com/a", title="Client A Article"),
        )

        with pytest.raises(ReadingListError, match="Access denied"):
            service.list_items(str(client_id), "client", str(other_client_id))

    def test_client_isolation_get(self, service, setup_data, client_id, other_client_id):
        """Client A cannot get Client B's reading item details."""
        created = service.add_item(
            str(client_id), "client", str(client_id),
            ReadingItemCreate(url="https://example.com", title="Client A Only"),
        )

        with pytest.raises(ReadingListError, match="Access denied"):
            service.get_item(str(other_client_id), "client", str(client_id), str(created.id))

    def test_therapist_ownership_required(self, service, setup_data, therapist_id, other_client_id):
        """Therapist can only access their own client's items."""
        with pytest.raises(ReadingListError, match="Access denied"):
            service.list_items(str(therapist_id), "therapist", str(other_client_id))

    def test_invalid_role_rejected(self, service, setup_data, client_id):
        """Invalid user role is rejected."""
        with pytest.raises(ReadingListError, match="Invalid user role"):
            service.list_items(str(client_id), "admin", str(client_id))

    def test_nonexistent_client_rejected(self, service, setup_data):
        """Accessing items for nonexistent client raises error."""
        with pytest.raises(ReadingListError, match="not found"):
            service.list_items(str(uuid4()), "client", str(uuid4()))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
