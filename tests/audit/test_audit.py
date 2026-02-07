"""
Tests for the centralized AuditService.

Validates that audit entries are created with correct event types,
persisted to the database when a session factory is available, and
wired correctly into the MergeEngine.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.audit_log import AuditLog, AuditEventType, AuditAction
from src.services.audit import AuditService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def audit_service():
    """AuditService with no DB session (structlog-only mode)."""
    return AuditService()


@pytest.fixture
def db_session_factory():
    """In-memory SQLite session factory with tables created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_audit_service(db_session_factory):
    """AuditService backed by an in-memory SQLite database."""
    return AuditService(session_factory=db_session_factory)


# ---------------------------------------------------------------------------
# Basic creation
# ---------------------------------------------------------------------------

def test_audit_service_creation():
    """AuditService can be instantiated with no arguments."""
    service = AuditService()
    assert service is not None
    assert service._session_factory is None


def test_audit_service_creation_with_factory(db_session_factory):
    """AuditService accepts a session factory."""
    service = AuditService(session_factory=db_session_factory)
    assert service._session_factory is db_session_factory


# ---------------------------------------------------------------------------
# PHI access
# ---------------------------------------------------------------------------

def test_log_phi_access_returns_entry(audit_service):
    """log_phi_access returns an AuditLog instance."""
    entry = audit_service.log_phi_access(
        user_id=str(uuid4()),
        resource_type="client_record",
        resource_id=str(uuid4()),
        action=AuditAction.READ,
    )
    assert isinstance(entry, AuditLog)


def test_log_phi_access_has_correct_event_type(audit_service):
    """log_phi_access sets event_type to phi_access."""
    entry = audit_service.log_phi_access(
        user_id=str(uuid4()),
        resource_type="client_record",
        resource_id=str(uuid4()),
        action=AuditAction.READ,
    )
    assert entry.event_type == AuditEventType.PHI_ACCESS
    assert entry.event_type == "phi_access"


def test_log_phi_access_stores_details(audit_service):
    """log_phi_access forwards arbitrary details."""
    details = {"fields_accessed": ["name", "dob"]}
    entry = audit_service.log_phi_access(
        user_id=str(uuid4()),
        resource_type="client_record",
        resource_id=str(uuid4()),
        action=AuditAction.READ,
        details=details,
        ip_address="192.168.1.10",
    )
    assert entry.details == details
    assert entry.ip_address == "192.168.1.10"


# ---------------------------------------------------------------------------
# PHI modification
# ---------------------------------------------------------------------------

def test_log_phi_modification(audit_service):
    """log_phi_modification sets event_type to phi_update."""
    entry = audit_service.log_phi_modification(
        user_id=str(uuid4()),
        resource_type="session_note",
        resource_id=str(uuid4()),
        action=AuditAction.UPDATE,
    )
    assert entry.event_type == AuditEventType.PHI_UPDATE
    assert entry.action == AuditAction.UPDATE


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------

def test_log_agent_invocation(audit_service):
    """log_agent_invocation sets event_type and embeds agent metadata."""
    client_id = str(uuid4())
    session_id = str(uuid4())

    entry = audit_service.log_agent_invocation(
        user_id=str(uuid4()),
        agent_name="rung",
        client_id=client_id,
        session_id=session_id,
    )
    assert entry.event_type == AuditEventType.AGENT_INVOCATION
    assert entry.action == AuditAction.INVOKE
    assert entry.details["agent_name"] == "rung"
    assert entry.details["client_id"] == client_id
    assert entry.details["session_id"] == session_id


# ---------------------------------------------------------------------------
# Couples merge
# ---------------------------------------------------------------------------

def test_log_couples_merge(audit_service):
    """log_couples_merge sets event_type and embeds partner/couple metadata."""
    partner_a = str(uuid4())
    partner_b = str(uuid4())
    couple_link = str(uuid4())

    entry = audit_service.log_couples_merge(
        therapist_id=str(uuid4()),
        couple_link_id=couple_link,
        partner_a_id=partner_a,
        partner_b_id=partner_b,
        action="merge_completed",
    )
    assert entry.event_type == "couples_merge"
    assert entry.action == "merge_completed"
    assert entry.details["couple_link_id"] == couple_link
    assert entry.details["partner_a_id"] == partner_a
    assert entry.details["partner_b_id"] == partner_b


# ---------------------------------------------------------------------------
# Auth event
# ---------------------------------------------------------------------------

def test_log_auth_event(audit_service):
    """log_auth_event sets event_type to auth_event."""
    entry = audit_service.log_auth_event(
        user_id=str(uuid4()),
        action="login_success",
        details={"method": "mfa"},
        ip_address="10.0.0.1",
    )
    assert entry.event_type == "auth_event"
    assert entry.action == "login_success"
    assert entry.details["method"] == "mfa"
    assert entry.ip_address == "10.0.0.1"


# ---------------------------------------------------------------------------
# Audit trail query
# ---------------------------------------------------------------------------

def test_get_audit_trail_empty(audit_service):
    """get_audit_trail returns empty list when no session factory is set."""
    result = audit_service.get_audit_trail()
    assert result == []


def test_get_audit_trail_empty_with_db(db_audit_service):
    """get_audit_trail returns empty list when no entries exist."""
    result = db_audit_service.get_audit_trail()
    assert result == []


# ---------------------------------------------------------------------------
# Database persistence
# ---------------------------------------------------------------------------

def test_audit_with_db_session(db_audit_service, db_session_factory):
    """Entries are persisted to the database and queryable."""
    user_id = str(uuid4())
    resource_id = str(uuid4())

    # Create an entry via the service
    db_audit_service.log_phi_access(
        user_id=user_id,
        resource_type="client_record",
        resource_id=resource_id,
        action=AuditAction.READ,
        details={"source": "test"},
    )

    # Query directly via a fresh session to verify persistence
    session = db_session_factory()
    try:
        rows = session.query(AuditLog).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.event_type == AuditEventType.PHI_ACCESS
        assert str(row.user_id) == user_id
        assert row.resource_type == "client_record"
        assert str(row.resource_id) == resource_id
        assert row.action == AuditAction.READ
        assert row.details == {"source": "test"}
    finally:
        session.close()


def test_get_audit_trail_filters(db_audit_service):
    """get_audit_trail respects resource_type and user_id filters."""
    user_a = str(uuid4())
    user_b = str(uuid4())

    db_audit_service.log_phi_access(
        user_id=user_a,
        resource_type="client_record",
        resource_id=str(uuid4()),
        action=AuditAction.READ,
    )
    db_audit_service.log_phi_modification(
        user_id=user_b,
        resource_type="session_note",
        resource_id=str(uuid4()),
        action=AuditAction.UPDATE,
    )
    db_audit_service.log_auth_event(
        user_id=user_a,
        action="login_success",
    )

    # Filter by user_id
    trail_a = db_audit_service.get_audit_trail(user_id=user_a)
    assert len(trail_a) == 2

    # Filter by resource_type
    trail_notes = db_audit_service.get_audit_trail(resource_type="session_note")
    assert len(trail_notes) == 1
    assert trail_notes[0].resource_type == "session_note"


# ---------------------------------------------------------------------------
# MergeEngine integration
# ---------------------------------------------------------------------------

def test_merge_engine_uses_audit_service():
    """
    MergeEngine forwards merge audit entries to AuditService
    when one is provided.
    """
    from src.services.merge_engine import MergeEngine, MergeAuditEntry

    # Create a mock AuditService
    mock_audit = MagicMock(spec=AuditService)

    # Create MergeEngine with mocked dependencies so we don't need real
    # couple manager/isolation layer/topic matcher infrastructure.
    mock_couple_manager = MagicMock()
    mock_link = MagicMock()
    mock_link.partner_a_id = str(uuid4())
    mock_link.partner_b_id = str(uuid4())
    mock_couple_manager.get_link.return_value = mock_link
    mock_couple_manager.validate_merge_authorization.return_value = True

    mock_isolation_layer = MagicMock()

    # Build isolated frameworks mocks
    mock_isolated_a = MagicMock()
    mock_isolated_a.attachment_patterns = ["anxious attachment"]
    mock_isolated_a.frameworks_identified = ["CBT"]
    mock_isolated_a.theme_categories = ["communication"]
    mock_isolated_a.defense_patterns = []
    mock_isolated_a.communication_patterns = []

    mock_isolated_b = MagicMock()
    mock_isolated_b.attachment_patterns = ["secure attachment"]
    mock_isolated_b.frameworks_identified = ["ACT"]
    mock_isolated_b.theme_categories = ["trust"]
    mock_isolated_b.defense_patterns = []
    mock_isolated_b.communication_patterns = []

    mock_topic_matcher = MagicMock()
    mock_match_result = MagicMock()
    mock_match_result.overlapping_themes = []
    mock_match_result.complementary_patterns = []
    mock_match_result.potential_conflicts = []
    mock_match_result.suggested_focus_areas = []
    mock_match_result.match_summary = "Test summary"
    mock_topic_matcher.match.return_value = mock_match_result

    engine = MergeEngine(
        couple_manager=mock_couple_manager,
        isolation_layer=mock_isolation_layer,
        topic_matcher=mock_topic_matcher,
        audit_service=mock_audit,
    )

    # Mock the isolation function at module level
    mock_partner_a_analysis = MagicMock()
    mock_partner_b_analysis = MagicMock()

    with patch(
        "src.services.merge_engine.isolate_for_couples_merge",
        return_value=(mock_isolated_a, mock_isolated_b),
    ):
        result = engine.merge(
            couple_link_id=str(uuid4()),
            session_id=str(uuid4()),
            therapist_id=str(uuid4()),
            partner_a_analysis=mock_partner_a_analysis,
            partner_b_analysis=mock_partner_b_analysis,
            ip_address="127.0.0.1",
        )

    # Verify AuditService was called
    mock_audit.log_couples_merge.assert_called_once()

    # Verify the call included the right action (merge_completed on success)
    call_kwargs = mock_audit.log_couples_merge.call_args
    assert call_kwargs.kwargs["action"] == "merge_completed"
    assert call_kwargs.kwargs["ip_address"] == "127.0.0.1"
    assert "partner_a_id" in call_kwargs.kwargs
    assert "partner_b_id" in call_kwargs.kwargs

    # In-memory audit log should also have the entry (backward compat)
    assert len(engine._audit_log) == 1
    assert engine._audit_log[0].action == "merge_completed"
