"""
API Database Integration Tests

Tests verify that API endpoints correctly integrate with database models.
"""

import os
import pytest
from unittest.mock import MagicMock
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["AWS_REGION"] = "us-east-1"

from src.models.base import Base
from src.models.pipeline_run import PipelineRun, PipelineType, PipelineStatus
from src.models.session_extraction import SessionExtraction
from src.models.clinical_brief import ClinicalBrief
from src.models.client_guide import ClientGuide
from src.models.session import Session, SessionType, SessionStatus
from src.models.client import Client, ConsentStatus
from src.models.therapist import Therapist
from src.models.agent import Agent, AgentName
from src.api import pre_session, post_session


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session_factory(test_engine):
    """Create session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def sample_session_data(test_session_factory):
    """Create sample session ID for testing."""
    # Return simple UUID - actual DB relations not required for these API tests
    return {
        "session_id": uuid4(),
        "therapist_id": uuid4(),
        "client_id": uuid4(),
    }


# =============================================================================
# Pre-Session API Tests
# =============================================================================

class TestPreSessionAPIIntegration:
    """Test pre-session API endpoints with database."""

    def test_get_status_no_pipeline(self, test_session_factory, sample_session_data):
        """Test status endpoint when no pipeline exists."""
        # Set session factory for API
        pre_session.set_session_factory_instance(test_session_factory)

        # Call endpoint
        import asyncio
        status = asyncio.run(pre_session.get_pre_session_status(
            session_id=sample_session_data["session_id"],
            x_user_id=str(sample_session_data["therapist_id"]),
        ))

        # Verify
        assert status.status == "pending"
        assert status.voice_memo_uploaded is False
        assert status.transcription_complete is False

    def test_get_status_with_pipeline(self, test_session_factory, sample_session_data):
        """Test status endpoint with existing pipeline."""
        from datetime import datetime

        # Create pipeline run
        session = test_session_factory()
        pipeline_run = PipelineRun(
            id=uuid4(),
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=sample_session_data["session_id"],
            status=PipelineStatus.PROCESSING.value,
            metadata_json={
                "voice_memo_uploaded": True,
                "transcription_complete": True,
                "rung_analysis_complete": False,
                "beth_generation_complete": False,
            },
            created_at=datetime.utcnow(),
        )
        session.add(pipeline_run)
        session.commit()
        session.close()

        # Set session factory for API
        pre_session.set_session_factory_instance(test_session_factory)

        # Call endpoint
        import asyncio
        status = asyncio.run(pre_session.get_pre_session_status(
            session_id=sample_session_data["session_id"],
            x_user_id=str(sample_session_data["therapist_id"]),
        ))

        # Verify
        assert status.status == "processing"
        assert status.voice_memo_uploaded is True
        assert status.transcription_complete is True
        assert status.rung_analysis_complete is False

    def test_trigger_creates_pipeline(self, test_session_factory, sample_session_data):
        """Test trigger endpoint creates pipeline run."""
        # Set session factory for API
        pre_session.set_session_factory_instance(test_session_factory)

        # Create request
        request = pre_session.TriggerRequest(force_reprocess=False)

        # Call endpoint
        import asyncio
        response = asyncio.run(pre_session.trigger_pre_session(
            session_id=sample_session_data["session_id"],
            request=request,
            x_user_id=str(sample_session_data["therapist_id"]),
        ))

        # Verify response
        assert response.status == "triggered"
        assert response.workflow_id is not None

        # Verify database
        session = test_session_factory()
        pipeline_run = session.query(PipelineRun).first()
        assert pipeline_run is not None
        assert pipeline_run.status == PipelineStatus.PENDING.value
        assert str(pipeline_run.id) == response.workflow_id
        session.close()


# =============================================================================
# Post-Session API Tests
# =============================================================================

class TestPostSessionAPIIntegration:
    """Test post-session API endpoints with database."""

    def test_get_extraction_not_found(self, test_session_factory, sample_session_data):
        """Test extraction endpoint when no extraction exists."""
        from fastapi import HTTPException

        # Set session factory for API
        post_session.set_session_factory_instance(test_session_factory)

        # Call endpoint
        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(post_session.get_extraction(
                session_id=sample_session_data["session_id"],
                x_user_id=str(sample_session_data["therapist_id"]),
                x_user_role="therapist",
            ))

        assert exc_info.value.status_code == 404

    def test_get_extraction_success(self, test_session_factory, sample_session_data):
        """Test extraction endpoint with existing extraction."""
        # Create extraction
        session = test_session_factory()
        extraction = SessionExtraction(
            id=uuid4(),
            session_id=sample_session_data["session_id"],
            frameworks_discussed=["CBT", "Attachment Theory"],
            modalities_used=["CBT"],
            homework_assigned=[{"task": "Journal", "due": "next session"}],
            breakthroughs=["Insight achieved"],
            progress_indicators=["Better awareness"],
            areas_for_next_session=["Explore emotions"],
            session_summary="Good session",
            extraction_confidence=0.85,
        )
        session.add(extraction)
        session.commit()
        session.close()

        # Set session factory for API
        post_session.set_session_factory_instance(test_session_factory)

        # Call endpoint
        import asyncio
        result = asyncio.run(post_session.get_extraction(
            session_id=sample_session_data["session_id"],
            x_user_id=str(sample_session_data["therapist_id"]),
            x_user_role="therapist",
        ))

        # Verify
        assert len(result.frameworks_discussed) == 2
        assert "CBT" in result.frameworks_discussed
        assert len(result.homework_assigned) == 1

    def test_get_homework_success(self, test_session_factory, sample_session_data):
        """Test homework endpoint returns assignments."""
        # Create extraction with homework
        session = test_session_factory()
        extraction = SessionExtraction(
            id=uuid4(),
            session_id=sample_session_data["session_id"],
            homework_assigned=[
                {"task": "Practice breathing", "due": "daily", "category": "practice"},
                {"task": "Journal", "due": "next session", "category": "reflection"},
            ],
        )
        session.add(extraction)
        session.commit()
        session.close()

        # Set session factory for API
        post_session.set_session_factory_instance(test_session_factory)

        # Call endpoint
        import asyncio
        result = asyncio.run(post_session.get_homework(
            session_id=sample_session_data["session_id"],
            x_user_id=str(sample_session_data["client_id"]),
        ))

        # Verify
        assert len(result.assignments) == 2
        assert result.assignments[0]["task"] == "Practice breathing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
