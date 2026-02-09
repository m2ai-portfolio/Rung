"""
Reading List Model Tests

Tests verify:
1. SQLAlchemy model CRUD operations
2. Foreign key constraints (client_id, session_id)
3. Enum validation (ReadingStatus, AddedByRole)
4. Pydantic schema validation and serialization
5. Soft delete filtering
6. Relationship traversal (client.reading_items)
7. Index creation
"""

import os
import pytest
from datetime import datetime
from uuid import uuid4

os.environ["AWS_REGION"] = "us-east-1"

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.reading_item import (
    AddedByRole,
    ReadingItem,
    ReadingItemAssign,
    ReadingItemCreate,
    ReadingItemDetail,
    ReadingItemRead,
    ReadingItemUpdate,
    ReadingStatus,
)

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
def therapist_id():
    return uuid4()


@pytest.fixture()
def client_id():
    return uuid4()


@pytest.fixture()
def setup_client(sf, therapist_id, client_id):
    """Create a therapist and client in the DB."""
    from src.models.therapist import Therapist
    from src.models.client import Client

    session = sf()
    therapist = Therapist(
        id=therapist_id,
        cognito_sub=f"cognito-{therapist_id}",
        email_encrypted=b"test-encrypted-email",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    client = Client(
        id=client_id,
        therapist_id=therapist_id,
        name_encrypted=b"test-encrypted-name",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(therapist)
    session.add(client)
    session.commit()
    session.close()
    return client_id


# =============================================================================
# SQLAlchemy Model Tests
# =============================================================================

class TestReadingItemModel:
    """Test ReadingItem SQLAlchemy model."""

    def test_create_reading_item(self, sf, setup_client, client_id):
        """Test creating a reading item in the database."""
        session = sf()
        item = ReadingItem(
            id=uuid4(),
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=client_id,
            url="https://www.psychologytoday.com/article/123",
            title="What Are You Designed to Do?",
            source="Psychology Today",
            discuss_in_session=True,
            is_assignment=False,
            status=ReadingStatus.UNREAD,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(item)
        session.commit()

        loaded = session.query(ReadingItem).filter(ReadingItem.id == item.id).first()
        assert loaded is not None
        assert loaded.title == "What Are You Designed to Do?"
        assert loaded.status == ReadingStatus.UNREAD
        assert loaded.added_by_role == AddedByRole.CLIENT
        assert loaded.discuss_in_session is True
        assert loaded.is_assignment is False
        assert loaded.deleted_at is None
        session.close()

    def test_reading_item_with_encrypted_notes(self, sf, setup_client, client_id):
        """Test that encrypted notes are stored as bytes."""
        session = sf()
        item = ReadingItem(
            id=uuid4(),
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=client_id,
            url="https://example.com/article",
            title="Test Article",
            notes_encrypted=b"encrypted-client-notes",
            assignment_notes_encrypted=b"encrypted-therapist-notes",
            discuss_in_session=False,
            is_assignment=True,
            status=ReadingStatus.READING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(item)
        session.commit()

        loaded = session.query(ReadingItem).filter(ReadingItem.id == item.id).first()
        assert loaded.notes_encrypted == b"encrypted-client-notes"
        assert loaded.assignment_notes_encrypted == b"encrypted-therapist-notes"
        session.close()

    def test_soft_delete(self, sf, setup_client, client_id):
        """Test soft delete sets deleted_at but keeps record in DB."""
        session = sf()
        item = ReadingItem(
            id=uuid4(),
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=client_id,
            url="https://example.com/delete-me",
            title="To Delete",
            discuss_in_session=False,
            is_assignment=False,
            status=ReadingStatus.UNREAD,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(item)
        session.commit()

        # Soft delete
        item.deleted_at = datetime.utcnow()
        session.commit()

        # Item still in DB
        all_items = session.query(ReadingItem).all()
        assert len(all_items) == 1
        assert all_items[0].deleted_at is not None

        # Filtered query excludes it
        active_items = (
            session.query(ReadingItem)
            .filter(ReadingItem.deleted_at.is_(None))
            .all()
        )
        assert len(active_items) == 0
        session.close()

    def test_status_transitions(self, sf, setup_client, client_id):
        """Test reading status transitions."""
        session = sf()
        item = ReadingItem(
            id=uuid4(),
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=client_id,
            url="https://example.com",
            title="Status Test",
            discuss_in_session=False,
            is_assignment=False,
            status=ReadingStatus.UNREAD,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(item)
        session.commit()

        # unread -> reading
        item.status = ReadingStatus.READING
        session.commit()
        assert item.status == ReadingStatus.READING

        # reading -> completed
        item.status = ReadingStatus.COMPLETED
        item.completed_at = datetime.utcnow()
        session.commit()
        assert item.status == ReadingStatus.COMPLETED
        assert item.completed_at is not None

        # completed -> discussed
        item.status = ReadingStatus.DISCUSSED
        session.commit()
        assert item.status == ReadingStatus.DISCUSSED
        session.close()

    def test_relationship_client_reading_items(self, sf, setup_client, client_id):
        """Test client.reading_items relationship traversal."""
        from src.models.client import Client

        session = sf()
        for i in range(3):
            session.add(ReadingItem(
                id=uuid4(),
                client_id=client_id,
                added_by_role=AddedByRole.CLIENT,
                added_by_user_id=client_id,
                url=f"https://example.com/{i}",
                title=f"Article {i}",
                discuss_in_session=False,
                is_assignment=False,
                status=ReadingStatus.UNREAD,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ))
        session.commit()

        client = session.query(Client).filter(Client.id == client_id).first()
        assert len(client.reading_items) == 3
        session.close()

    def test_repr(self, sf, setup_client, client_id):
        """Test __repr__ output."""
        item = ReadingItem(
            id=uuid4(),
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=client_id,
            url="https://example.com",
            title="Test",
            discuss_in_session=False,
            is_assignment=False,
            status=ReadingStatus.UNREAD,
        )
        repr_str = repr(item)
        assert "ReadingItem" in repr_str
        assert "Test" in repr_str


class TestReadingItemIndexes:
    """Test that indexes are created correctly."""

    def test_indexes_exist(self, engine):
        """Verify all expected indexes on reading_items table."""
        inspector = inspect(engine)
        indexes = inspector.get_indexes("reading_items")
        index_names = {idx["name"] for idx in indexes}

        assert "ix_reading_items_client_id" in index_names
        assert "ix_reading_items_client_discuss" in index_names
        assert "ix_reading_items_client_status" in index_names


# =============================================================================
# Pydantic Schema Tests
# =============================================================================

class TestReadingItemSchemas:
    """Test Pydantic schema validation."""

    def test_create_schema_valid(self):
        """Test valid ReadingItemCreate."""
        data = ReadingItemCreate(
            url="https://www.psychologytoday.com/article",
            title="Growth Mindset",
            source="Psychology Today",
            notes="This resonated with me.",
            discuss_in_session=True,
        )
        assert data.url == "https://www.psychologytoday.com/article"
        assert data.discuss_in_session is True

    def test_create_schema_minimal(self):
        """Test minimal ReadingItemCreate (only required fields)."""
        data = ReadingItemCreate(
            url="https://example.com",
            title="Test",
        )
        assert data.source is None
        assert data.notes is None
        assert data.discuss_in_session is False

    def test_assign_schema_valid(self):
        """Test valid ReadingItemAssign."""
        data = ReadingItemAssign(
            url="https://example.com/book",
            title="Mindset: The New Psychology of Success",
            source="book",
            assignment_notes="Read chapters 1-3 before next session.",
        )
        assert data.assignment_notes is not None

    def test_update_schema_all_optional(self):
        """Test that all ReadingItemUpdate fields are optional."""
        data = ReadingItemUpdate()
        assert data.notes is None
        assert data.discuss_in_session is None
        assert data.status is None
        assert data.session_id is None

    def test_update_schema_partial(self):
        """Test partial update."""
        data = ReadingItemUpdate(
            status=ReadingStatus.COMPLETED,
            discuss_in_session=True,
        )
        assert data.status == ReadingStatus.COMPLETED
        assert data.notes is None

    def test_read_schema_from_attributes(self):
        """Test ReadingItemRead.model_config from_attributes."""
        now = datetime.utcnow()
        item_id = uuid4()
        client_id = uuid4()
        user_id = uuid4()

        data = ReadingItemRead(
            id=item_id,
            client_id=client_id,
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=user_id,
            url="https://example.com",
            title="Test",
            has_notes=True,
            discuss_in_session=False,
            is_assignment=False,
            has_assignment_notes=False,
            status=ReadingStatus.UNREAD,
            created_at=now,
            updated_at=now,
        )
        assert data.id == item_id
        assert data.has_notes is True
        assert data.has_assignment_notes is False

    def test_detail_schema_includes_notes(self):
        """Test ReadingItemDetail includes decrypted notes fields."""
        now = datetime.utcnow()
        data = ReadingItemDetail(
            id=uuid4(),
            client_id=uuid4(),
            added_by_role=AddedByRole.CLIENT,
            added_by_user_id=uuid4(),
            url="https://example.com",
            title="Test",
            has_notes=True,
            discuss_in_session=False,
            is_assignment=True,
            has_assignment_notes=True,
            status=ReadingStatus.READING,
            created_at=now,
            updated_at=now,
            notes="My personal reflection on this article.",
            assignment_notes="Read this for homework.",
        )
        assert data.notes == "My personal reflection on this article."
        assert data.assignment_notes == "Read this for homework."

    def test_create_schema_url_max_length(self):
        """Test URL max length validation."""
        with pytest.raises(Exception):
            ReadingItemCreate(
                url="x" * 2049,
                title="Test",
            )


class TestEnumValues:
    """Test enum serialization."""

    def test_reading_status_values(self):
        assert ReadingStatus.UNREAD.value == "unread"
        assert ReadingStatus.READING.value == "reading"
        assert ReadingStatus.COMPLETED.value == "completed"
        assert ReadingStatus.DISCUSSED.value == "discussed"

    def test_added_by_role_values(self):
        assert AddedByRole.CLIENT.value == "client"
        assert AddedByRole.THERAPIST.value == "therapist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
