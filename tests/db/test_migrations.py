"""
Alembic migration and new model tests.

Tests verify:
1. Alembic configuration exists and is correct
2. env.py references Base.metadata
3. PipelineRun model CRUD operations work
4. PipelineRun status transitions work
5. Session model has transcript_s3_key column
6. PipelineRun Pydantic schemas validate correctly
"""

import os
import pytest
from datetime import datetime, timezone
from uuid import uuid4

# Set test database before importing models
os.environ["DATABASE_URL"] = "sqlite:///./test_migrations.db"

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session, sessionmaker

from src.models.base import Base
from src.models.therapist import Therapist
from src.models.client import Client, ConsentStatus
from src.models.session import Session as TherapySession, SessionCreate, SessionRead, SessionUpdate, SessionType, SessionStatus
from src.models.pipeline_run import (
    PipelineRun,
    PipelineRunCreate,
    PipelineRunRead,
    PipelineRunUpdate,
    PipelineType,
    PipelineStatus,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def engine():
    """Create a fresh in-memory database for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

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
        cognito_sub="auth0|migration_test",
        email_encrypted=b"encrypted_email_data",
        practice_name="Migration Test Practice",
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
        consent_date=datetime.now(timezone.utc),
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
        status=SessionStatus.SCHEDULED,
    )
    session.add(therapy_session)
    session.commit()
    session.refresh(therapy_session)
    return therapy_session


# =============================================================================
# Alembic Configuration Tests
# =============================================================================

class TestAlembicConfig:
    """Verify Alembic configuration is correct."""

    def test_alembic_config_exists(self):
        """Verify alembic.ini exists at the project root."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        alembic_ini = os.path.join(project_root, "alembic.ini")
        assert os.path.isfile(alembic_ini), f"alembic.ini not found at {alembic_ini}"

    def test_alembic_env_imports_models(self):
        """Verify env.py references Base.metadata for autogenerate support."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        env_py = os.path.join(project_root, "src", "db", "alembic", "env.py")
        assert os.path.isfile(env_py), f"env.py not found at {env_py}"

        with open(env_py, "r") as f:
            content = f.read()

        assert "from src.models.base import Base" in content, (
            "env.py must import Base from src.models.base"
        )
        assert "target_metadata = Base.metadata" in content, (
            "env.py must set target_metadata = Base.metadata"
        )
        # Verify all models are imported
        assert "from src.models.pipeline_run import PipelineRun" in content
        assert "from src.models.therapist import Therapist" in content
        assert "from src.models.session import Session" in content

    def test_alembic_versions_directory_exists(self):
        """Verify the versions directory exists with at least one migration."""
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        versions_dir = os.path.join(project_root, "src", "db", "alembic", "versions")
        assert os.path.isdir(versions_dir), f"versions directory not found at {versions_dir}"

        migration_files = [f for f in os.listdir(versions_dir) if f.endswith(".py") and not f.startswith("__")]
        assert len(migration_files) >= 1, "At least one migration file should exist"


# =============================================================================
# PipelineRun Model Tests
# =============================================================================

class TestPipelineRunModel:
    """Test PipelineRun model CRUD operations."""

    def test_pipeline_run_model_creation(self, session, therapy_session):
        """Create PipelineRun in SQLite, verify all fields are persisted."""
        run = PipelineRun(
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.PENDING.value,
            current_stage="initialization",
            metadata_json={"source": "test", "version": "1.0"},
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        assert run.id is not None
        assert run.pipeline_type == "pre_session"
        assert run.session_id == therapy_session.id
        assert run.status == "pending"
        assert run.current_stage == "initialization"
        assert run.error_message is None
        assert run.started_at is None
        assert run.completed_at is None
        assert run.created_at is not None
        assert run.metadata_json == {"source": "test", "version": "1.0"}

    def test_pipeline_run_without_session(self, session):
        """PipelineRun with no session_id (e.g., standalone pipeline)."""
        run = PipelineRun(
            pipeline_type=PipelineType.COUPLES_MERGE.value,
            couple_link_id=uuid4(),
            status=PipelineStatus.PENDING.value,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        assert run.id is not None
        assert run.session_id is None
        assert run.couple_link_id is not None

    def test_pipeline_run_status_transitions(self, session, therapy_session):
        """Create a pipeline run and transition through statuses."""
        run = PipelineRun(
            pipeline_type=PipelineType.POST_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.PENDING.value,
        )
        session.add(run)
        session.commit()

        # Transition: pending -> processing
        run.status = PipelineStatus.PROCESSING.value
        run.current_stage = "framework_analysis"
        run.started_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
        assert run.status == "processing"
        assert run.started_at is not None

        # Transition: processing -> completed
        run.status = PipelineStatus.COMPLETED.value
        run.current_stage = "done"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
        assert run.status == "completed"
        assert run.completed_at is not None

    def test_pipeline_run_failure(self, session, therapy_session):
        """Test pipeline run failure with error message."""
        run = PipelineRun(
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.PROCESSING.value,
            started_at=datetime.now(timezone.utc),
        )
        session.add(run)
        session.commit()

        # Transition: processing -> failed
        run.status = PipelineStatus.FAILED.value
        run.error_message = "Bedrock API timeout after 30s"
        run.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)

        assert run.status == "failed"
        assert "timeout" in run.error_message

    def test_pipeline_run_metadata_json(self, session, therapy_session):
        """Test that metadata_json stores and retrieves complex data."""
        metadata = {
            "input_tokens": 1500,
            "output_tokens": 800,
            "model": "anthropic.claude-3-5-sonnet",
            "frameworks": ["attachment", "defense"],
        }
        run = PipelineRun(
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.COMPLETED.value,
            metadata_json=metadata,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        assert run.metadata_json["input_tokens"] == 1500
        assert "attachment" in run.metadata_json["frameworks"]

    def test_pipeline_runs_table_in_metadata(self, engine):
        """Verify pipeline_runs table exists in the schema."""
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        assert "pipeline_runs" in tables

    def test_pipeline_run_relationship_to_session(self, session, therapy_session):
        """Verify the PipelineRun -> Session relationship works."""
        run = PipelineRun(
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.PENDING.value,
        )
        session.add(run)
        session.commit()
        session.refresh(run)

        assert run.session is not None
        assert run.session.id == therapy_session.id

    def test_session_pipeline_runs_relationship(self, session, therapy_session):
        """Verify Session -> PipelineRun back-reference works."""
        run1 = PipelineRun(
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.COMPLETED.value,
        )
        run2 = PipelineRun(
            pipeline_type=PipelineType.POST_SESSION.value,
            session_id=therapy_session.id,
            status=PipelineStatus.PENDING.value,
        )
        session.add_all([run1, run2])
        session.commit()
        session.refresh(therapy_session)

        assert len(therapy_session.pipeline_runs) == 2


# =============================================================================
# Session transcript_s3_key Tests
# =============================================================================

class TestSessionTranscriptS3Key:
    """Test that Session model has the transcript_s3_key column."""

    def test_session_has_transcript_s3_key(self, session, client):
        """Verify the transcript_s3_key column exists and can store data."""
        s3_key = "transcripts/2026/02/session-abc123.json"
        therapy_session = TherapySession(
            client_id=client.id,
            session_type=SessionType.INDIVIDUAL,
            session_date=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
            transcript_s3_key=s3_key,
        )
        session.add(therapy_session)
        session.commit()
        session.refresh(therapy_session)

        assert therapy_session.transcript_s3_key == s3_key

    def test_session_transcript_s3_key_nullable(self, session, client):
        """Verify transcript_s3_key is nullable (not all sessions have transcripts)."""
        therapy_session = TherapySession(
            client_id=client.id,
            session_type=SessionType.INDIVIDUAL,
            session_date=datetime.now(timezone.utc),
            status=SessionStatus.SCHEDULED,
        )
        session.add(therapy_session)
        session.commit()
        session.refresh(therapy_session)

        assert therapy_session.transcript_s3_key is None

    def test_session_transcript_s3_key_in_schema(self, engine):
        """Verify transcript_s3_key column exists in sessions table schema."""
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("sessions")}
        assert "transcript_s3_key" in columns


# =============================================================================
# Pydantic Schema Tests
# =============================================================================

class TestPipelineRunPydanticSchemas:
    """Test PipelineRun Pydantic schemas."""

    def test_pipeline_run_create_schema(self):
        """Test PipelineRunCreate validates correctly."""
        data = PipelineRunCreate(
            pipeline_type=PipelineType.PRE_SESSION,
            session_id=uuid4(),
            metadata_json={"key": "value"},
        )
        assert data.pipeline_type == PipelineType.PRE_SESSION
        assert data.session_id is not None
        assert data.metadata_json == {"key": "value"}

    def test_pipeline_run_create_couples_merge(self):
        """Test PipelineRunCreate for couples merge pipeline."""
        couple_id = uuid4()
        data = PipelineRunCreate(
            pipeline_type=PipelineType.COUPLES_MERGE,
            couple_link_id=couple_id,
        )
        assert data.pipeline_type == PipelineType.COUPLES_MERGE
        assert data.couple_link_id == couple_id
        assert data.session_id is None
        assert data.metadata_json == {}

    def test_pipeline_run_update_schema(self):
        """Test PipelineRunUpdate with partial updates."""
        data = PipelineRunUpdate(
            status=PipelineStatus.PROCESSING,
            current_stage="framework_analysis",
        )
        assert data.status == PipelineStatus.PROCESSING
        assert data.current_stage == "framework_analysis"
        assert data.error_message is None
        assert data.completed_at is None

    def test_pipeline_run_update_failure(self):
        """Test PipelineRunUpdate for marking failure."""
        data = PipelineRunUpdate(
            status=PipelineStatus.FAILED,
            error_message="Bedrock invocation error: rate limit exceeded",
            completed_at=datetime.now(timezone.utc),
        )
        assert data.status == PipelineStatus.FAILED
        assert "rate limit" in data.error_message

    def test_pipeline_run_read_schema(self):
        """Test PipelineRunRead with from_attributes."""
        run_id = uuid4()
        session_id = uuid4()
        now = datetime.now(timezone.utc)

        data = PipelineRunRead(
            id=run_id,
            pipeline_type=PipelineType.POST_SESSION,
            session_id=session_id,
            status=PipelineStatus.COMPLETED,
            current_stage="done",
            created_at=now,
            started_at=now,
            completed_at=now,
            metadata_json={"tokens": 500},
        )
        assert data.id == run_id
        assert data.status == PipelineStatus.COMPLETED
        assert data.metadata_json["tokens"] == 500

    def test_pipeline_type_enum_values(self):
        """Verify PipelineType enum has expected values."""
        assert PipelineType.PRE_SESSION.value == "pre_session"
        assert PipelineType.POST_SESSION.value == "post_session"
        assert PipelineType.COUPLES_MERGE.value == "couples_merge"

    def test_pipeline_status_enum_values(self):
        """Verify PipelineStatus enum has expected values."""
        assert PipelineStatus.PENDING.value == "pending"
        assert PipelineStatus.PROCESSING.value == "processing"
        assert PipelineStatus.COMPLETED.value == "completed"
        assert PipelineStatus.FAILED.value == "failed"


class TestSessionPydanticSchemas:
    """Test updated Session Pydantic schemas include transcript_s3_key."""

    def test_session_create_with_transcript_key(self):
        """Test SessionCreate accepts transcript_s3_key."""
        data = SessionCreate(
            client_id=uuid4(),
            session_date=datetime.now(timezone.utc),
            transcript_s3_key="transcripts/2026/02/test.json",
        )
        assert data.transcript_s3_key == "transcripts/2026/02/test.json"

    def test_session_create_without_transcript_key(self):
        """Test SessionCreate works without transcript_s3_key."""
        data = SessionCreate(
            client_id=uuid4(),
            session_date=datetime.now(timezone.utc),
        )
        assert data.transcript_s3_key is None

    def test_session_update_with_transcript_key(self):
        """Test SessionUpdate accepts transcript_s3_key."""
        data = SessionUpdate(
            transcript_s3_key="transcripts/2026/02/updated.json",
        )
        assert data.transcript_s3_key == "transcripts/2026/02/updated.json"

    def test_session_read_includes_transcript_key(self):
        """Test SessionRead includes transcript_s3_key field."""
        data = SessionRead(
            id=uuid4(),
            client_id=uuid4(),
            session_type=SessionType.INDIVIDUAL,
            session_date=datetime.now(timezone.utc),
            status=SessionStatus.COMPLETED,
            transcript_s3_key="transcripts/2026/02/read.json",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert data.transcript_s3_key == "transcripts/2026/02/read.json"
