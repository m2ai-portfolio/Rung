"""
Reading List Pipeline Integration Tests

Tests verify:
1. RungAnalysisRequest includes reading_context field
2. Rung agent _build_user_message includes reading context
3. Pre-session pipeline loads reading context
4. Pipeline continues when reading service fails (resilience)
5. Pipeline unchanged when no reading items exist
"""

import os
import json
import asyncio
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

os.environ["AWS_REGION"] = "us-east-1"

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.pipeline_run import PipelineRun, PipelineStatus, PipelineType

# Import all models to register with Base.metadata
import src.models  # noqa: F401

from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    RungAnalysisRequest,
)
from src.agents.rung import RungAgent
from src.services.reading_list import ReadingListService


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
def sample_reading_context():
    """Sample reading context text."""
    return (
        'Client has flagged 2 article(s) for session discussion:\n'
        '1. "What Are You Designed to Do?" (Psychology Today) - client added personal notes\n'
        '2. [Therapist-assigned] "Mindset: The New Psychology of Success" (book) - no notes'
    )


# =============================================================================
# RungAnalysisRequest Schema Tests
# =============================================================================

class TestRungAnalysisRequestSchema:
    """Test that RungAnalysisRequest includes reading_context field."""

    def test_reading_context_field_exists(self):
        """RungAnalysisRequest has optional reading_context field."""
        request = RungAnalysisRequest(
            session_id="sess-1",
            client_id="client-1",
            transcript="Hello",
        )
        assert request.reading_context is None

    def test_reading_context_field_populated(self, sample_reading_context):
        """RungAnalysisRequest accepts reading_context."""
        request = RungAnalysisRequest(
            session_id="sess-1",
            client_id="client-1",
            transcript="Hello",
            reading_context=sample_reading_context,
        )
        assert "flagged 2 article" in request.reading_context


# =============================================================================
# Rung Agent Message Building Tests
# =============================================================================

class TestRungAgentReadingContext:
    """Test that Rung agent includes reading context in user message."""

    def test_message_includes_reading_context(self, sample_reading_context):
        """_build_user_message includes reading context when provided."""
        agent = RungAgent.__new__(RungAgent)
        request = RungAnalysisRequest(
            session_id="sess-1",
            client_id="client-1",
            transcript="I've been reading about growth mindset.",
            reading_context=sample_reading_context,
        )

        message = agent._build_user_message(request)

        assert "Reading material flagged by client for session discussion:" in message
        assert '"What Are You Designed to Do?"' in message
        assert "[Therapist-assigned]" in message

    def test_message_without_reading_context(self):
        """_build_user_message works without reading context."""
        agent = RungAgent.__new__(RungAgent)
        request = RungAnalysisRequest(
            session_id="sess-1",
            client_id="client-1",
            transcript="Just a regular transcript.",
        )

        message = agent._build_user_message(request)

        assert "Reading material flagged" not in message
        assert "Just a regular transcript." in message

    def test_reading_context_appears_after_historical(self, sample_reading_context):
        """Reading context section appears after historical context."""
        agent = RungAgent.__new__(RungAgent)
        request = RungAnalysisRequest(
            session_id="sess-1",
            client_id="client-1",
            transcript="Transcript text.",
            historical_context="Previous session notes here.",
            reading_context=sample_reading_context,
        )

        message = agent._build_user_message(request)

        hist_pos = message.index("Historical context")
        reading_pos = message.index("Reading material flagged")
        assert reading_pos > hist_pos


# =============================================================================
# Pre-Session Pipeline Integration Tests
# =============================================================================

class TestPreSessionPipelineReadingContext:
    """Test pre-session pipeline with reading context integration."""

    @pytest.fixture()
    def pipeline_run(self, sf) -> str:
        """Create a pending pipeline run."""
        session = sf()
        run_id = uuid4()
        run = PipelineRun(
            id=run_id,
            pipeline_type=PipelineType.PRE_SESSION.value,
            status=PipelineStatus.PENDING.value,
        )
        session.add(run)
        session.commit()
        session.close()
        return str(run_id)

    @pytest.fixture()
    def session_row(self, sf) -> str:
        """Create a session with a transcript key."""
        from src.models.session import Session
        from src.models.therapist import Therapist
        from src.models.client import Client

        session = sf()
        therapist_id = uuid4()
        client_id = uuid4()
        session_id = uuid4()

        session.add(Therapist(
            id=therapist_id,
            cognito_sub=f"cognito-{therapist_id}",
            email_encrypted=b"test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        session.add(Client(
            id=client_id,
            therapist_id=therapist_id,
            name_encrypted=b"test",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        session.add(Session(
            id=session_id,
            client_id=client_id,
            session_date=datetime.utcnow(),
            transcript_s3_key="transcripts/test.txt",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        ))
        session.commit()
        session.close()
        return str(session_id), str(client_id)

    @pytest.mark.asyncio
    async def test_pipeline_passes_reading_context_to_rung(
        self, sf, pipeline_run, session_row, sample_reading_context
    ):
        """Pipeline passes reading context to RungAnalysisRequest."""
        from src.pipelines.pre_session import run_pre_session_pipeline

        session_id, client_id = session_row

        # Mock transcript service
        mock_ts = MagicMock()
        transcript_result = MagicMock()
        transcript_result.transcript = "I've been thinking about growth mindset."
        mock_ts.get_transcript.return_value = transcript_result

        # Mock Rung agent - capture the request
        mock_rung = MagicMock()
        captured_request = []

        def capture_analyze(request):
            captured_request.append(request)
            return RungAnalysisOutput(
                frameworks_identified=[],
                defense_mechanisms=[],
                risk_flags=[],
                key_themes=["growth"],
            )

        mock_rung.analyze.side_effect = capture_analyze

        # Mock research service
        mock_research = MagicMock()
        mock_research_result = MagicMock()
        mock_research_result.successful_queries = 0
        mock_research.research_from_rung_output.return_value = mock_research_result

        # Mock abstraction layer
        mock_abstraction = MagicMock()
        mock_abstraction_result = MagicMock()
        mock_abstraction_result.is_safe_for_beth = True
        mock_abstraction_result.clinical_terms_stripped = []
        mock_abstraction.abstract.return_value = mock_abstraction_result
        mock_abstraction.to_beth_input.return_value = MagicMock()

        # Mock Beth agent
        mock_beth = MagicMock()
        mock_beth_output = MagicMock()
        mock_beth_output.tone_check_passed = True
        mock_beth.generate.return_value = mock_beth_output

        # Mock audit
        mock_audit = MagicMock()

        # Mock reading list service
        mock_reading = MagicMock(spec=ReadingListService)
        mock_reading.get_session_reading_context.return_value = sample_reading_context

        await run_pre_session_pipeline(
            session_id=session_id,
            pipeline_id=pipeline_run,
            session_factory=sf,
            transcription_service=mock_ts,
            rung_agent=mock_rung,
            research_service=mock_research,
            abstraction_layer=mock_abstraction,
            beth_agent=mock_beth,
            audit_service=mock_audit,
            reading_list_service=mock_reading,
        )

        # Verify reading context was passed to Rung analysis request
        assert len(captured_request) == 1
        assert captured_request[0].reading_context == sample_reading_context

    @pytest.mark.asyncio
    async def test_pipeline_resilience_reading_service_failure(
        self, sf, pipeline_run, session_row
    ):
        """Pipeline continues when reading service fails."""
        from src.pipelines.pre_session import run_pre_session_pipeline

        session_id, client_id = session_row

        # Mock transcript service
        mock_ts = MagicMock()
        transcript_result = MagicMock()
        transcript_result.transcript = "Regular transcript."
        mock_ts.get_transcript.return_value = transcript_result

        # Mock Rung agent - capture request to check reading_context
        captured_request = []
        mock_rung = MagicMock()

        def capture_analyze(request):
            captured_request.append(request)
            return RungAnalysisOutput(
                frameworks_identified=[],
                defense_mechanisms=[],
                risk_flags=[],
                key_themes=["default"],
            )

        mock_rung.analyze.side_effect = capture_analyze

        # Mock other services
        mock_research = MagicMock()
        mock_research_result = MagicMock()
        mock_research_result.successful_queries = 0
        mock_research.research_from_rung_output.return_value = mock_research_result

        mock_abstraction = MagicMock()
        mock_abstraction_result = MagicMock()
        mock_abstraction_result.is_safe_for_beth = True
        mock_abstraction_result.clinical_terms_stripped = []
        mock_abstraction.abstract.return_value = mock_abstraction_result
        mock_abstraction.to_beth_input.return_value = MagicMock()

        mock_beth = MagicMock()
        mock_beth_output = MagicMock()
        mock_beth_output.tone_check_passed = True
        mock_beth.generate.return_value = mock_beth_output

        mock_audit = MagicMock()

        # Reading service FAILS
        mock_reading = MagicMock(spec=ReadingListService)
        mock_reading.get_session_reading_context.side_effect = Exception("DB connection failed")

        await run_pre_session_pipeline(
            session_id=session_id,
            pipeline_id=pipeline_run,
            session_factory=sf,
            transcription_service=mock_ts,
            rung_agent=mock_rung,
            research_service=mock_research,
            abstraction_layer=mock_abstraction,
            beth_agent=mock_beth,
            audit_service=mock_audit,
            reading_list_service=mock_reading,
        )

        # Pipeline should still complete - reading context should be None
        assert len(captured_request) == 1
        assert captured_request[0].reading_context is None

        # Pipeline should be marked complete (not failed)
        from uuid import UUID as _UUID
        _pid = _UUID(pipeline_run) if isinstance(pipeline_run, str) else pipeline_run
        db = sf()
        run = db.query(PipelineRun).filter(PipelineRun.id == _pid).first()
        assert run.status == PipelineStatus.COMPLETED.value
        db.close()

    @pytest.mark.asyncio
    async def test_pipeline_no_reading_items(
        self, sf, pipeline_run, session_row
    ):
        """Pipeline works unchanged when no reading items exist."""
        from src.pipelines.pre_session import run_pre_session_pipeline

        session_id, client_id = session_row

        mock_ts = MagicMock()
        transcript_result = MagicMock()
        transcript_result.transcript = "No reading items."
        mock_ts.get_transcript.return_value = transcript_result

        captured_request = []
        mock_rung = MagicMock()

        def capture_analyze(request):
            captured_request.append(request)
            return RungAnalysisOutput(
                frameworks_identified=[],
                defense_mechanisms=[],
                risk_flags=[],
                key_themes=[],
            )

        mock_rung.analyze.side_effect = capture_analyze

        mock_research = MagicMock()
        mock_research_result = MagicMock()
        mock_research_result.successful_queries = 0
        mock_research.research_from_rung_output.return_value = mock_research_result

        mock_abstraction = MagicMock()
        mock_abstraction_result = MagicMock()
        mock_abstraction_result.is_safe_for_beth = True
        mock_abstraction_result.clinical_terms_stripped = []
        mock_abstraction.abstract.return_value = mock_abstraction_result
        mock_abstraction.to_beth_input.return_value = MagicMock()

        mock_beth = MagicMock()
        mock_beth_output = MagicMock()
        mock_beth_output.tone_check_passed = True
        mock_beth.generate.return_value = mock_beth_output

        mock_audit = MagicMock()

        # Reading service returns None (no items)
        mock_reading = MagicMock(spec=ReadingListService)
        mock_reading.get_session_reading_context.return_value = None

        await run_pre_session_pipeline(
            session_id=session_id,
            pipeline_id=pipeline_run,
            session_factory=sf,
            transcription_service=mock_ts,
            rung_agent=mock_rung,
            research_service=mock_research,
            abstraction_layer=mock_abstraction,
            beth_agent=mock_beth,
            audit_service=mock_audit,
            reading_list_service=mock_reading,
        )

        # No reading context passed to Rung
        assert len(captured_request) == 1
        assert captured_request[0].reading_context is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
