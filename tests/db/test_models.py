"""
Database Model Tests for Phase 1D

Tests verify:
1. All 10 tables can be created
2. CRUD operations work correctly
3. Foreign key constraints are enforced
4. ENUM types work correctly
5. JSONB fields work correctly
6. Unique constraints are enforced
7. Check constraints are enforced
8. Pydantic schemas validate correctly
"""

import os
import pytest
from datetime import datetime, timezone
from uuid import uuid4

# Set test database before importing models
os.environ["DATABASE_URL"] = "sqlite:///./test_rung.db"

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base, init_db, drop_db
from src.models.therapist import Therapist, TherapistCreate, TherapistRead, TherapistUpdate
from src.models.client import Client, ClientCreate, ClientRead, ClientUpdate, ConsentStatus
from src.models.session import Session as TherapySession, SessionCreate, SessionRead, SessionType, SessionStatus
from src.models.agent import Agent, AgentCreate, AgentRead, AgentName
from src.models.clinical_brief import ClinicalBrief, ClinicalBriefCreate, ClinicalBriefRead
from src.models.client_guide import ClientGuide, ClientGuideCreate, ClientGuideRead
from src.models.development_plan import DevelopmentPlan, DevelopmentPlanCreate, DevelopmentPlanRead
from src.models.couple_link import CoupleLink, CoupleLinkCreate, CoupleLinkRead, CoupleStatus
from src.models.framework_merge import FrameworkMerge, FrameworkMergeCreate, FrameworkMergeRead
from src.models.audit_log import AuditLog, AuditLogCreate, AuditLogRead, AuditEventType, AuditAction


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create a fresh database for each test."""
    from sqlalchemy import event

    engine = create_engine(
        "sqlite:///./test_rung.db",
        connect_args={"check_same_thread": False}
    )

    # Enable foreign key enforcement in SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def session(engine):
    """Create a database session for testing."""
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def therapist(session) -> Therapist:
    """Create a test therapist."""
    therapist = Therapist(
        cognito_sub="auth0|test123",
        email_encrypted=b"encrypted_email_data",
        practice_name="Test Practice"
    )
    session.add(therapist)
    session.commit()
    session.refresh(therapist)
    return therapist


@pytest.fixture
def client(session, therapist) -> Client:
    """Create a test client."""
    client = Client(
        therapist_id=therapist.id,
        name_encrypted=b"encrypted_name_data",
        contact_encrypted=b"encrypted_contact_data",
        consent_status=ConsentStatus.ACTIVE,
        consent_date=datetime.now(timezone.utc)
    )
    session.add(client)
    session.commit()
    session.refresh(client)
    return client


@pytest.fixture
def therapy_session(session, client) -> TherapySession:
    """Create a test therapy session."""
    therapy_session = TherapySession(
        client_id=client.id,
        session_type=SessionType.INDIVIDUAL,
        session_date=datetime.now(timezone.utc),
        status=SessionStatus.SCHEDULED
    )
    session.add(therapy_session)
    session.commit()
    session.refresh(therapy_session)
    return therapy_session


@pytest.fixture
def agent(session, client) -> Agent:
    """Create a test agent."""
    agent = Agent(
        name=AgentName.RUNG,
        client_id=client.id,
        system_prompt="Test system prompt"
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


# =============================================================================
# Table Creation Tests
# =============================================================================

class TestTableCreation:
    """Test that all tables can be created."""

    def test_tables_created(self, engine):
        """Verify all 10 tables exist."""
        tables = Base.metadata.tables.keys()
        expected_tables = [
            "therapists",
            "clients",
            "sessions",
            "agents",
            "clinical_briefs",
            "client_guides",
            "development_plans",
            "couple_links",
            "framework_merges",
            "audit_logs"
        ]
        for table in expected_tables:
            assert table in tables, f"Table {table} should exist"


# =============================================================================
# Therapist Tests
# =============================================================================

class TestTherapist:
    """Test Therapist model CRUD operations."""

    def test_create_therapist(self, session):
        """Test creating a therapist."""
        therapist = Therapist(
            cognito_sub="auth0|unique123",
            email_encrypted=b"encrypted_data",
            practice_name="Test Practice"
        )
        session.add(therapist)
        session.commit()

        assert therapist.id is not None
        assert therapist.cognito_sub == "auth0|unique123"
        assert therapist.created_at is not None

    def test_read_therapist(self, session, therapist):
        """Test reading a therapist."""
        result = session.query(Therapist).filter_by(id=therapist.id).first()
        assert result is not None
        assert result.cognito_sub == therapist.cognito_sub

    def test_update_therapist(self, session, therapist):
        """Test updating a therapist."""
        therapist.practice_name = "Updated Practice"
        session.commit()
        session.refresh(therapist)

        assert therapist.practice_name == "Updated Practice"
        assert therapist.updated_at >= therapist.created_at

    def test_delete_therapist(self, session, therapist):
        """Test deleting a therapist (without clients)."""
        therapist_id = therapist.id
        session.delete(therapist)
        session.commit()

        result = session.query(Therapist).filter_by(id=therapist_id).first()
        assert result is None

    def test_unique_cognito_sub(self, session, therapist):
        """Test that cognito_sub must be unique."""
        duplicate = Therapist(
            cognito_sub=therapist.cognito_sub,  # Same as existing
            email_encrypted=b"other_email"
        )
        session.add(duplicate)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()
        session.rollback()

    def test_pydantic_therapist_create(self):
        """Test TherapistCreate schema."""
        data = TherapistCreate(
            cognito_sub="auth0|test",
            email="test@example.com",
            practice_name="Test"
        )
        assert data.cognito_sub == "auth0|test"
        assert data.email == "test@example.com"


# =============================================================================
# Client Tests
# =============================================================================

class TestClient:
    """Test Client model CRUD operations."""

    def test_create_client(self, session, therapist):
        """Test creating a client."""
        client = Client(
            therapist_id=therapist.id,
            name_encrypted=b"encrypted_name",
            consent_status=ConsentStatus.PENDING
        )
        session.add(client)
        session.commit()

        assert client.id is not None
        assert client.therapist_id == therapist.id

    def test_client_requires_therapist(self, session):
        """Test that client requires valid therapist."""
        client = Client(
            therapist_id=uuid4(),  # Non-existent therapist
            name_encrypted=b"encrypted_name"
        )
        session.add(client)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_consent_status_enum(self, session, therapist):
        """Test consent status enum values."""
        for status in ConsentStatus:
            client = Client(
                therapist_id=therapist.id,
                name_encrypted=b"encrypted_name",
                consent_status=status,
                consent_date=datetime.now(timezone.utc) if status == ConsentStatus.ACTIVE else None
            )
            session.add(client)

        session.commit()
        clients = session.query(Client).filter_by(therapist_id=therapist.id).all()
        assert len(clients) == 3

    def test_pydantic_client_create(self, therapist):
        """Test ClientCreate schema."""
        data = ClientCreate(
            therapist_id=therapist.id,
            name="Test Client",
            consent_status=ConsentStatus.PENDING
        )
        assert data.name == "Test Client"


# =============================================================================
# Session Tests
# =============================================================================

class TestSession:
    """Test Session model CRUD operations."""

    def test_create_session(self, session, client):
        """Test creating a therapy session."""
        therapy_session = TherapySession(
            client_id=client.id,
            session_type=SessionType.INDIVIDUAL,
            session_date=datetime.now(timezone.utc),
            status=SessionStatus.SCHEDULED
        )
        session.add(therapy_session)
        session.commit()

        assert therapy_session.id is not None

    def test_session_type_enum(self, session, client):
        """Test session type enum values."""
        for session_type in SessionType:
            therapy_session = TherapySession(
                client_id=client.id,
                session_type=session_type,
                session_date=datetime.now(timezone.utc)
            )
            session.add(therapy_session)

        session.commit()

    def test_session_status_enum(self, session, client):
        """Test session status enum values."""
        for status in SessionStatus:
            therapy_session = TherapySession(
                client_id=client.id,
                session_date=datetime.now(timezone.utc),
                status=status
            )
            session.add(therapy_session)

        session.commit()


# =============================================================================
# Agent Tests
# =============================================================================

class TestAgent:
    """Test Agent model CRUD operations."""

    def test_create_agent(self, session, client):
        """Test creating an agent."""
        agent = Agent(
            name=AgentName.RUNG,
            client_id=client.id,
            system_prompt="Test prompt"
        )
        session.add(agent)
        session.commit()

        assert agent.id is not None
        assert agent.name == AgentName.RUNG

    def test_unique_agent_per_client(self, session, client):
        """Test that each client can have only one agent of each type."""
        agent1 = Agent(name=AgentName.RUNG, client_id=client.id)
        session.add(agent1)
        session.commit()

        agent2 = Agent(name=AgentName.RUNG, client_id=client.id)  # Duplicate
        session.add(agent2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()

    def test_both_agents_per_client(self, session, client):
        """Test that client can have both Rung and Beth agents."""
        rung = Agent(name=AgentName.RUNG, client_id=client.id)
        beth = Agent(name=AgentName.BETH, client_id=client.id)
        session.add_all([rung, beth])
        session.commit()

        agents = session.query(Agent).filter_by(client_id=client.id).all()
        assert len(agents) == 2


# =============================================================================
# Clinical Brief Tests
# =============================================================================

class TestClinicalBrief:
    """Test ClinicalBrief model CRUD operations."""

    def test_create_clinical_brief(self, session, therapy_session, agent):
        """Test creating a clinical brief."""
        brief = ClinicalBrief(
            session_id=therapy_session.id,
            agent_id=agent.id,
            content_encrypted=b"encrypted_content",
            frameworks_identified=[{"name": "attachment", "confidence": 0.8}],
            risk_flags=[{"level": "low", "description": "test"}],
            research_citations=[]
        )
        session.add(brief)
        session.commit()

        assert brief.id is not None
        assert len(brief.frameworks_identified) == 1

    def test_jsonb_frameworks(self, session, therapy_session, agent):
        """Test JSONB frameworks field."""
        frameworks = [
            {"name": "attachment", "confidence": 0.8, "evidence": "test"},
            {"name": "defense", "confidence": 0.7, "evidence": "test2"}
        ]
        brief = ClinicalBrief(
            session_id=therapy_session.id,
            agent_id=agent.id,
            content_encrypted=b"content",
            frameworks_identified=frameworks
        )
        session.add(brief)
        session.commit()
        session.refresh(brief)

        assert len(brief.frameworks_identified) == 2
        assert brief.frameworks_identified[0]["name"] == "attachment"


# =============================================================================
# Client Guide Tests
# =============================================================================

class TestClientGuide:
    """Test ClientGuide model CRUD operations."""

    def test_create_client_guide(self, session, therapy_session, client):
        """Test creating a client guide."""
        beth_agent = Agent(name=AgentName.BETH, client_id=client.id)
        session.add(beth_agent)
        session.commit()

        guide = ClientGuide(
            session_id=therapy_session.id,
            agent_id=beth_agent.id,
            content_encrypted=b"encrypted_guide",
            key_points=["point1", "point2"],
            exercises_suggested=[{"name": "breathing", "frequency": "daily"}]
        )
        session.add(guide)
        session.commit()

        assert guide.id is not None
        assert len(guide.key_points) == 2


# =============================================================================
# Development Plan Tests
# =============================================================================

class TestDevelopmentPlan:
    """Test DevelopmentPlan model CRUD operations."""

    def test_create_development_plan(self, session, client):
        """Test creating a development plan."""
        plan = DevelopmentPlan(
            client_id=client.id,
            sprint_number=1,
            goals=[{"goal": "test", "metric": "count", "target": "5"}],
            exercises=[{"name": "exercise1"}],
            progress={"week1": "good"}
        )
        session.add(plan)
        session.commit()

        assert plan.id is not None
        assert plan.sprint_number == 1

    def test_unique_sprint_per_client(self, session, client):
        """Test that each client can have only one plan per sprint."""
        plan1 = DevelopmentPlan(client_id=client.id, sprint_number=1)
        session.add(plan1)
        session.commit()

        plan2 = DevelopmentPlan(client_id=client.id, sprint_number=1)  # Duplicate
        session.add(plan2)
        with pytest.raises(Exception):
            session.commit()
        session.rollback()


# =============================================================================
# Couple Link Tests
# =============================================================================

class TestCoupleLink:
    """Test CoupleLink model CRUD operations."""

    def test_create_couple_link(self, session, therapist):
        """Test creating a couple link."""
        # Create two clients
        client_a = Client(
            therapist_id=therapist.id,
            name_encrypted=b"partner_a",
            consent_status=ConsentStatus.ACTIVE,
            consent_date=datetime.now(timezone.utc)
        )
        client_b = Client(
            therapist_id=therapist.id,
            name_encrypted=b"partner_b",
            consent_status=ConsentStatus.ACTIVE,
            consent_date=datetime.now(timezone.utc)
        )
        session.add_all([client_a, client_b])
        session.commit()

        # Ensure ordering (a < b)
        if client_a.id > client_b.id:
            client_a, client_b = client_b, client_a

        link = CoupleLink(
            partner_a_id=client_a.id,
            partner_b_id=client_b.id,
            therapist_id=therapist.id,
            status=CoupleStatus.ACTIVE
        )
        session.add(link)
        session.commit()

        assert link.id is not None

    def test_pydantic_couple_link_auto_swap(self, therapist):
        """Test that Pydantic schema auto-swaps partner IDs."""
        id1 = uuid4()
        id2 = uuid4()

        # Ensure id1 > id2 for test
        if id1 < id2:
            id1, id2 = id2, id1

        data = CoupleLinkCreate(
            partner_a_id=id1,  # Larger ID
            partner_b_id=id2,  # Smaller ID
            therapist_id=therapist.id
        )

        # Should be swapped so partner_a < partner_b
        assert data.partner_a_id < data.partner_b_id


# =============================================================================
# Framework Merge Tests
# =============================================================================

class TestFrameworkMerge:
    """Test FrameworkMerge model CRUD operations."""

    def test_create_framework_merge(self, session, therapist, therapy_session):
        """Test creating a framework merge."""
        # Create couple link first
        client_a = Client(
            therapist_id=therapist.id,
            name_encrypted=b"partner_a",
            consent_status=ConsentStatus.ACTIVE,
            consent_date=datetime.now(timezone.utc)
        )
        client_b = Client(
            therapist_id=therapist.id,
            name_encrypted=b"partner_b",
            consent_status=ConsentStatus.ACTIVE,
            consent_date=datetime.now(timezone.utc)
        )
        session.add_all([client_a, client_b])
        session.commit()

        if client_a.id > client_b.id:
            client_a, client_b = client_b, client_a

        link = CoupleLink(
            partner_a_id=client_a.id,
            partner_b_id=client_b.id,
            therapist_id=therapist.id
        )
        session.add(link)
        session.commit()

        merge = FrameworkMerge(
            couple_link_id=link.id,
            session_id=therapy_session.id,
            partner_a_frameworks=["attachment", "communication"],
            partner_b_frameworks=["intimacy", "trust"],
            merged_insights=[{"theme": "connection", "suggestion": "explore"}]
        )
        session.add(merge)
        session.commit()

        assert merge.id is not None
        assert len(merge.partner_a_frameworks) == 2


# =============================================================================
# Audit Log Tests
# =============================================================================

class TestAuditLog:
    """Test AuditLog model CRUD operations."""

    def test_create_audit_log(self, session):
        """Test creating an audit log entry."""
        log = AuditLog(
            event_type=AuditEventType.PHI_ACCESS,
            user_id=uuid4(),
            resource_type="client",
            resource_id=uuid4(),
            action=AuditAction.READ,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            details={"reason": "therapy session prep"}
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.event_type == AuditEventType.PHI_ACCESS

    def test_audit_log_system_event(self, session):
        """Test audit log for system events (no user_id)."""
        log = AuditLog(
            event_type=AuditEventType.SYSTEM_BACKUP,
            resource_type="database",
            action="backup",
            details={"backup_type": "full"}
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.user_id is None

    def test_audit_log_details_jsonb(self, session):
        """Test JSONB details field."""
        details = {
            "reason": "audit",
            "fields_accessed": ["name", "email"],
            "duration_ms": 150
        }
        log = AuditLog(
            event_type="test",
            resource_type="test",
            action="test",
            details=details
        )
        session.add(log)
        session.commit()
        session.refresh(log)

        assert log.details["reason"] == "audit"
        assert len(log.details["fields_accessed"]) == 2


# =============================================================================
# Relationship Tests
# =============================================================================

class TestRelationships:
    """Test model relationships."""

    def test_therapist_clients_relationship(self, session, therapist, client):
        """Test therapist -> clients relationship."""
        session.refresh(therapist)
        assert len(therapist.clients) >= 1
        assert client in therapist.clients

    def test_client_sessions_relationship(self, session, client, therapy_session):
        """Test client -> sessions relationship."""
        session.refresh(client)
        assert len(client.sessions) >= 1
        assert therapy_session in client.sessions

    def test_session_clinical_briefs_relationship(self, session, therapy_session, agent):
        """Test session -> clinical_briefs relationship."""
        brief = ClinicalBrief(
            session_id=therapy_session.id,
            agent_id=agent.id,
            content_encrypted=b"content"
        )
        session.add(brief)
        session.commit()
        session.refresh(therapy_session)

        assert len(therapy_session.clinical_briefs) == 1


# =============================================================================
# Pydantic Schema Tests
# =============================================================================

class TestPydanticSchemas:
    """Test Pydantic schema validation."""

    def test_therapist_schema_validation(self):
        """Test TherapistCreate validation."""
        # Valid
        data = TherapistCreate(cognito_sub="test", email="test@example.com")
        assert data.cognito_sub == "test"

    def test_client_schema_validation(self):
        """Test ClientCreate validation."""
        data = ClientCreate(
            therapist_id=uuid4(),
            name="Test Client",
            consent_status=ConsentStatus.PENDING
        )
        assert data.consent_status == ConsentStatus.PENDING

    def test_session_schema_validation(self):
        """Test SessionCreate validation."""
        data = SessionCreate(
            client_id=uuid4(),
            session_date=datetime.now(timezone.utc),
            session_type=SessionType.INDIVIDUAL,
            status=SessionStatus.SCHEDULED
        )
        assert data.session_type == SessionType.INDIVIDUAL

    def test_clinical_brief_schema(self):
        """Test ClinicalBriefCreate validation."""
        data = ClinicalBriefCreate(
            session_id=uuid4(),
            agent_id=uuid4(),
            content="Test content",
            frameworks_identified=[{"name": "test", "confidence": 0.8, "evidence": "test"}]
        )
        assert len(data.frameworks_identified) == 1

    def test_audit_log_schema(self):
        """Test AuditLogCreate validation."""
        data = AuditLogCreate(
            event_type="test_event",
            resource_type="test_resource",
            action="test_action",
            details={"key": "value"}
        )
        assert data.event_type == "test_event"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
