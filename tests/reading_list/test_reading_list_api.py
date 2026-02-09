"""
Reading List API Tests

Tests verify:
1. All endpoint routes and HTTP methods
2. Role-based access control (client vs therapist)
3. Client isolation (client A can't see B's items)
4. Therapist-only /assign endpoint
5. PATCH status transitions
6. Error responses (403, 404, 500)
7. Query parameter filtering
"""

import os
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

os.environ["AWS_REGION"] = "us-east-1"

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.reading_list import set_reading_list_service
from src.models.reading_item import (
    AddedByRole,
    ReadingItemDetail,
    ReadingItemRead,
    ReadingStatus,
)
from src.services.reading_list import ReadingListError, ReadingListService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture()
def mock_service():
    """Mock ReadingListService."""
    mock = MagicMock(spec=ReadingListService)
    set_reading_list_service(mock)
    yield mock
    set_reading_list_service(None)


@pytest.fixture()
def client_id():
    return uuid4()


@pytest.fixture()
def therapist_id():
    return uuid4()


@pytest.fixture()
def item_id():
    return uuid4()


@pytest.fixture()
def sample_read_item(client_id, item_id):
    """Sample ReadingItemRead for mock returns."""
    now = datetime.utcnow()
    return ReadingItemRead(
        id=item_id,
        client_id=client_id,
        added_by_role=AddedByRole.CLIENT,
        added_by_user_id=client_id,
        url="https://www.psychologytoday.com/article/123",
        title="What Are You Designed to Do?",
        source="Psychology Today",
        has_notes=True,
        discuss_in_session=True,
        is_assignment=False,
        has_assignment_notes=False,
        status=ReadingStatus.UNREAD,
        created_at=now,
        updated_at=now,
    )


@pytest.fixture()
def sample_detail_item(client_id, item_id):
    """Sample ReadingItemDetail for mock returns."""
    now = datetime.utcnow()
    return ReadingItemDetail(
        id=item_id,
        client_id=client_id,
        added_by_role=AddedByRole.CLIENT,
        added_by_user_id=client_id,
        url="https://www.psychologytoday.com/article/123",
        title="What Are You Designed to Do?",
        source="Psychology Today",
        has_notes=True,
        discuss_in_session=True,
        is_assignment=False,
        has_assignment_notes=False,
        status=ReadingStatus.UNREAD,
        created_at=now,
        updated_at=now,
        notes="My personal reflection.",
        assignment_notes=None,
    )


# =============================================================================
# POST / - Add Reading Item
# =============================================================================

class TestAddReadingItem:
    """Tests for POST /clients/{client_id}/reading-list/."""

    def test_add_item_success(self, client, mock_service, client_id, sample_read_item):
        """Successfully add a reading item."""
        mock_service.add_item.return_value = sample_read_item

        response = client.post(
            f"/clients/{client_id}/reading-list/",
            json={
                "url": "https://www.psychologytoday.com/article/123",
                "title": "What Are You Designed to Do?",
                "source": "Psychology Today",
                "discuss_in_session": True,
            },
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "What Are You Designed to Do?"
        assert data["discuss_in_session"] is True

    def test_add_item_access_denied(self, client, mock_service, client_id):
        """Access denied returns 403."""
        mock_service.add_item.side_effect = ReadingListError("Access denied: client can only access their own")

        response = client.post(
            f"/clients/{client_id}/reading-list/",
            json={"url": "https://example.com", "title": "Test"},
            headers={"x-user-id": str(uuid4()), "x-user-role": "client"},
        )

        assert response.status_code == 403

    def test_add_item_client_not_found(self, client, mock_service):
        """Client not found returns 404."""
        mock_service.add_item.side_effect = ReadingListError("Client not found: abc")

        response = client.post(
            f"/clients/{uuid4()}/reading-list/",
            json={"url": "https://example.com", "title": "Test"},
            headers={"x-user-id": str(uuid4()), "x-user-role": "client"},
        )

        assert response.status_code == 404


# =============================================================================
# GET / - List Reading Items
# =============================================================================

class TestListReadingItems:
    """Tests for GET /clients/{client_id}/reading-list/."""

    def test_list_items_success(self, client, mock_service, client_id, sample_read_item):
        """Successfully list reading items."""
        mock_service.list_items.return_value = [sample_read_item]

        response = client.get(
            f"/clients/{client_id}/reading-list/",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["items"]) == 1

    def test_list_items_with_filters(self, client, mock_service, client_id):
        """Query parameters are passed to service."""
        mock_service.list_items.return_value = []

        response = client.get(
            f"/clients/{client_id}/reading-list/?status=unread&discuss_only=true&assignments_only=true",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        mock_service.list_items.assert_called_once()
        call_kwargs = mock_service.list_items.call_args
        assert call_kwargs.kwargs["status"] == ReadingStatus.UNREAD
        assert call_kwargs.kwargs["discuss_only"] is True
        assert call_kwargs.kwargs["assignments_only"] is True

    def test_list_items_access_denied(self, client, mock_service, client_id):
        """Access denied returns 403."""
        mock_service.list_items.side_effect = ReadingListError("Access denied: therapist does not own")

        response = client.get(
            f"/clients/{client_id}/reading-list/",
            headers={"x-user-id": str(uuid4()), "x-user-role": "therapist"},
        )

        assert response.status_code == 403


# =============================================================================
# GET /for-session - Pre-Session View
# =============================================================================

class TestForSession:
    """Tests for GET /clients/{client_id}/reading-list/for-session."""

    def test_for_session_therapist_only(self, client, mock_service, client_id):
        """Only therapists can access for-session view."""
        response = client.get(
            f"/clients/{client_id}/reading-list/for-session",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 403

    def test_for_session_success(self, client, mock_service, client_id, therapist_id, sample_read_item):
        """Therapist gets for-session view with context text."""
        mock_service.list_items.return_value = [sample_read_item]
        mock_service.get_session_reading_context.return_value = (
            'Client has flagged 1 article(s) for session discussion:\n'
            '1. "What Are You Designed to Do?" (Psychology Today) - client added personal notes'
        )

        response = client.get(
            f"/clients/{client_id}/reading-list/for-session",
            headers={"x-user-id": str(therapist_id), "x-user-role": "therapist"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert "flagged 1 article" in data["context_text"]


# =============================================================================
# GET /{item_id} - Get Single Item (with notes)
# =============================================================================

class TestGetReadingItem:
    """Tests for GET /clients/{client_id}/reading-list/{item_id}."""

    def test_get_item_success(self, client, mock_service, client_id, item_id, sample_detail_item):
        """Successfully get item with decrypted notes."""
        mock_service.get_item.return_value = sample_detail_item

        response = client.get(
            f"/clients/{client_id}/reading-list/{item_id}",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notes"] == "My personal reflection."

    def test_get_item_not_found(self, client, mock_service, client_id, item_id):
        """Item not found returns 404."""
        mock_service.get_item.side_effect = ReadingListError("Reading item not found: abc")

        response = client.get(
            f"/clients/{client_id}/reading-list/{item_id}",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 404


# =============================================================================
# PATCH /{item_id} - Update Item
# =============================================================================

class TestUpdateReadingItem:
    """Tests for PATCH /clients/{client_id}/reading-list/{item_id}."""

    def test_update_item_success(self, client, mock_service, client_id, item_id, sample_read_item):
        """Successfully update item status."""
        updated = sample_read_item.model_copy(update={"status": ReadingStatus.READING})
        mock_service.update_item.return_value = updated

        response = client.patch(
            f"/clients/{client_id}/reading-list/{item_id}",
            json={"status": "reading"},
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "reading"

    def test_update_item_access_denied(self, client, mock_service, client_id, item_id):
        """Access denied returns 403."""
        mock_service.update_item.side_effect = ReadingListError("Access denied: client can only access their own")

        response = client.patch(
            f"/clients/{client_id}/reading-list/{item_id}",
            json={"status": "reading"},
            headers={"x-user-id": str(uuid4()), "x-user-role": "client"},
        )

        assert response.status_code == 403


# =============================================================================
# DELETE /{item_id} - Soft Delete
# =============================================================================

class TestDeleteReadingItem:
    """Tests for DELETE /clients/{client_id}/reading-list/{item_id}."""

    def test_delete_item_success(self, client, mock_service, client_id, item_id):
        """Successfully soft delete an item."""
        mock_service.delete_item.return_value = None

        response = client.delete(
            f"/clients/{client_id}/reading-list/{item_id}",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_item_not_found(self, client, mock_service, client_id, item_id):
        """Deleting nonexistent item returns 404."""
        mock_service.delete_item.side_effect = ReadingListError("Reading item not found: abc")

        response = client.delete(
            f"/clients/{client_id}/reading-list/{item_id}",
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 404


# =============================================================================
# POST /assign - Therapist Assigns Reading
# =============================================================================

class TestAssignReading:
    """Tests for POST /clients/{client_id}/reading-list/assign."""

    def test_assign_success(self, client, mock_service, client_id, therapist_id, sample_read_item):
        """Therapist successfully assigns reading."""
        assigned = sample_read_item.model_copy(update={
            "is_assignment": True,
            "added_by_role": AddedByRole.THERAPIST,
        })
        mock_service.assign_item.return_value = assigned

        response = client.post(
            f"/clients/{client_id}/reading-list/assign",
            json={
                "url": "https://example.com/book",
                "title": "Mindset",
                "source": "book",
            },
            headers={"x-user-id": str(therapist_id), "x-user-role": "therapist"},
        )

        assert response.status_code == 200
        assert response.json()["is_assignment"] is True

    def test_assign_client_forbidden(self, client, mock_service, client_id):
        """Client cannot use the /assign endpoint."""
        response = client.post(
            f"/clients/{client_id}/reading-list/assign",
            json={"url": "https://example.com", "title": "Sneaky"},
            headers={"x-user-id": str(client_id), "x-user-role": "client"},
        )

        assert response.status_code == 403
        assert "Only therapists" in response.json()["detail"]

    def test_assign_wrong_therapist(self, client, mock_service, client_id, therapist_id):
        """Therapist can't assign to a client they don't own."""
        mock_service.assign_item.side_effect = ReadingListError("Access denied: therapist does not own")

        response = client.post(
            f"/clients/{client_id}/reading-list/assign",
            json={"url": "https://example.com", "title": "Not My Client"},
            headers={"x-user-id": str(therapist_id), "x-user-role": "therapist"},
        )

        assert response.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
