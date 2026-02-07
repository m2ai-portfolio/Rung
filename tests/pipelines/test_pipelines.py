"""
Tests for pipeline orchestration modules.

Tests base helpers with an in-memory SQLite DB and each pipeline
with mocked services. Verifies:
- Pipeline stages execute in correct order
- Pipeline status updates correctly
- Failure handling sets FAILED status with error message
"""

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.pipeline_run import PipelineRun, PipelineStatus, PipelineType

# Import all models so Base.metadata knows about every table (ForeignKey targets)
import src.models  # noqa: F401  -- triggers __init__ which registers all ORM models

from src.pipelines.base import complete_pipeline, fail_pipeline, update_pipeline_stage


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
def pipeline_run(sf) -> str:
    """Create a pending pipeline run and return its ID as a string."""
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


def _load_run(sf, pipeline_id: str) -> PipelineRun:
    """Helper to reload a PipelineRun from the DB."""
    from uuid import UUID as _UUID

    pid = _UUID(pipeline_id) if isinstance(pipeline_id, str) else pipeline_id
    session = sf()
    try:
        return session.query(PipelineRun).filter(PipelineRun.id == pid).first()
    finally:
        session.close()


# =============================================================================
# Tests: base.py helpers
# =============================================================================

class TestUpdatePipelineStage:
    """Tests for update_pipeline_stage."""

    def test_updates_stage_and_status(self, sf, pipeline_run):
        update_pipeline_stage(sf, pipeline_run, "fetch_transcript", PipelineStatus.PROCESSING)
        run = _load_run(sf, pipeline_run)
        assert run.current_stage == "fetch_transcript"
        assert run.status == PipelineStatus.PROCESSING.value
        assert run.started_at is not None

    def test_updates_stage_without_status(self, sf, pipeline_run):
        update_pipeline_stage(sf, pipeline_run, "analysis")
        run = _load_run(sf, pipeline_run)
        assert run.current_stage == "analysis"
        assert run.status == PipelineStatus.PENDING.value

    def test_sets_started_at_only_once(self, sf, pipeline_run):
        update_pipeline_stage(sf, pipeline_run, "step_1", PipelineStatus.PROCESSING)
        first = _load_run(sf, pipeline_run).started_at

        update_pipeline_stage(sf, pipeline_run, "step_2")
        second = _load_run(sf, pipeline_run).started_at

        assert first == second

    def test_missing_pipeline_does_not_raise(self, sf):
        # Should not raise, just log a warning
        update_pipeline_stage(sf, str(uuid4()), "anything")


class TestFailPipeline:
    """Tests for fail_pipeline."""

    def test_sets_failed_status_and_message(self, sf, pipeline_run):
        fail_pipeline(sf, pipeline_run, "Something went wrong")
        run = _load_run(sf, pipeline_run)
        assert run.status == PipelineStatus.FAILED.value
        assert run.error_message == "Something went wrong"
        assert run.completed_at is not None

    def test_missing_pipeline_does_not_raise(self, sf):
        fail_pipeline(sf, str(uuid4()), "no-op")


class TestCompletePipeline:
    """Tests for complete_pipeline."""

    def test_sets_completed_status(self, sf, pipeline_run):
        complete_pipeline(sf, pipeline_run)
        run = _load_run(sf, pipeline_run)
        assert run.status == PipelineStatus.COMPLETED.value
        assert run.completed_at is not None

    def test_missing_pipeline_does_not_raise(self, sf):
        complete_pipeline(sf, str(uuid4()))


# =============================================================================
# Helpers for pipeline tests
# =============================================================================

def _make_session_row(
    session_id: str,
    client_id: str,
    transcript_s3_key: str | None = "sessions/test/transcript.json",
    notes_encrypted: bytes | None = None,
):
    """Create a mock Session ORM object."""
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.client_id = client_id
    mock_session.transcript_s3_key = transcript_s3_key
    mock_session.notes_encrypted = notes_encrypted
    return mock_session


def _mock_rung_output():
    """Return a minimal RungAnalysisOutput-like mock."""
    from src.agents.schemas.rung_output import RungAnalysisOutput

    return RungAnalysisOutput(
        frameworks_identified=[],
        defense_mechanisms=[],
        risk_flags=[],
        key_themes=["communication"],
        suggested_exploration=["boundaries"],
        session_questions=["How are you feeling?"],
    )


def _mock_beth_output():
    """Return a minimal BethOutput-like mock."""
    mock = MagicMock()
    mock.tone_check_passed = True
    mock.session_prep = "Welcome to your session."
    mock.discussion_points = []
    mock.reflection_questions = []
    mock.exercises = []
    return mock


def _mock_abstraction_result():
    """Return a minimal AbstractionResult-like mock."""
    from src.agents.schemas.beth_output import AbstractedRungOutput, BethInput

    mock_result = MagicMock()
    mock_result.is_safe_for_beth = True
    mock_result.clinical_terms_stripped = []
    return mock_result


def _mock_research_batch():
    """Return a minimal ResearchBatch-like mock."""
    mock = MagicMock()
    mock.successful_queries = 2
    mock.failed_queries = 0
    mock.results = []
    return mock


def _mock_extraction_output():
    """Return a minimal FrameworkExtractionOutput-like mock."""
    from src.services.framework_extractor import FrameworkExtractionOutput

    return FrameworkExtractionOutput(
        frameworks_discussed=["CBT", "attachment theory"],
        modalities_used=["CBT"],
        homework_assigned=[],
        breakthroughs=["insight about patterns"],
        progress_indicators=["increased awareness"],
        areas_for_next_session=["boundaries"],
        session_summary="Good session with CBT focus.",
    )


def _mock_sprint_plan():
    """Return a minimal SprintPlan-like mock."""
    mock = MagicMock()
    mock.goals = [MagicMock()]
    mock.exercises = [MagicMock()]
    return mock


# =============================================================================
# Tests: pre_session pipeline
# =============================================================================

class TestPreSessionPipeline:
    """Tests for run_pre_session_pipeline."""

    @pytest.fixture()
    def pre_run(self, sf) -> str:
        """Create a pre-session pipeline run."""
        session = sf()
        run_id = uuid4()
        run = PipelineRun(
            id=run_id,
            pipeline_type=PipelineType.PRE_SESSION.value,
            status=PipelineStatus.PENDING.value,
            session_id=uuid4(),
        )
        session.add(run)
        session.commit()
        session.close()
        return str(run_id)

    @pytest.mark.asyncio
    async def test_successful_pipeline(self, sf, pre_run):
        """Full happy-path run with all services mocked."""
        session_id = str(uuid4())
        client_id = str(uuid4())

        # Mock session query
        mock_session_row = _make_session_row(session_id, client_id)

        # Mock services
        ts = MagicMock()
        transcript_result = MagicMock()
        transcript_result.transcript = "I've been feeling stressed about work."
        ts.get_transcript.return_value = transcript_result

        rung = MagicMock()
        rung_output = _mock_rung_output()
        rung.analyze.return_value = rung_output

        research = MagicMock()
        research.research_from_rung_output.return_value = _mock_research_batch()

        abstraction = MagicMock()
        abstraction.abstract.return_value = _mock_abstraction_result()
        beth_input = MagicMock()
        abstraction.to_beth_input.return_value = beth_input

        beth = MagicMock()
        beth.generate.return_value = _mock_beth_output()

        audit = MagicMock()

        from src.pipelines.pre_session import run_pre_session_pipeline

        def custom_sf():
            s = sf()
            original_query = s.query

            def patched_query(model):
                from src.models.pipeline_run import PipelineRun as PR
                if model is PR or (hasattr(model, "__tablename__") and model.__tablename__ == "pipeline_runs"):
                    return original_query(model)
                # For Session model queries, return mock
                mock_q = MagicMock()
                mock_q.filter.return_value.first.return_value = mock_session_row
                return mock_q

            s.query = patched_query
            return s

        await run_pre_session_pipeline(
            session_id=session_id,
            pipeline_id=pre_run,
            session_factory=custom_sf,
            transcription_service=ts,
            rung_agent=rung,
            research_service=research,
            abstraction_layer=abstraction,
            beth_agent=beth,
            audit_service=audit,
        )

        # Verify pipeline completed
        run = _load_run(sf, pre_run)
        assert run.status == PipelineStatus.COMPLETED.value
        assert run.completed_at is not None

        # Verify services were called
        ts.get_transcript.assert_called_once()
        rung.analyze.assert_called_once()
        research.research_from_rung_output.assert_called_once()
        abstraction.abstract.assert_called_once()
        beth.generate.assert_called_once()
        assert audit.log_agent_invocation.call_count == 2  # rung + beth

    @pytest.mark.asyncio
    async def test_failure_sets_failed_status(self, sf, pre_run):
        """Pipeline failure records error in PipelineRun."""
        session_id = str(uuid4())

        # Mock session query to return None (session not found)
        mock_session_row = None

        ts = MagicMock()
        rung = MagicMock()
        research = MagicMock()
        abstraction = MagicMock()
        beth = MagicMock()
        audit = MagicMock()

        from src.pipelines.pre_session import run_pre_session_pipeline

        def custom_sf():
            s = sf()
            original_query = s.query

            def patched_query(model):
                from src.models.pipeline_run import PipelineRun as PR
                if model is PR or (hasattr(model, "__tablename__") and model.__tablename__ == "pipeline_runs"):
                    return original_query(model)
                mock_q = MagicMock()
                mock_q.filter.return_value.first.return_value = mock_session_row
                return mock_q

            s.query = patched_query
            return s

        await run_pre_session_pipeline(
            session_id=session_id,
            pipeline_id=pre_run,
            session_factory=custom_sf,
            transcription_service=ts,
            rung_agent=rung,
            research_service=research,
            abstraction_layer=abstraction,
            beth_agent=beth,
            audit_service=audit,
        )

        run = _load_run(sf, pre_run)
        assert run.status == PipelineStatus.FAILED.value
        assert "Session not found" in run.error_message


# =============================================================================
# Tests: post_session pipeline
# =============================================================================

class TestPostSessionPipeline:
    """Tests for run_post_session_pipeline."""

    @pytest.fixture()
    def post_run(self, sf) -> str:
        """Create a post-session pipeline run."""
        session = sf()
        run_id = uuid4()
        run = PipelineRun(
            id=run_id,
            pipeline_type=PipelineType.POST_SESSION.value,
            status=PipelineStatus.PENDING.value,
            session_id=uuid4(),
        )
        session.add(run)
        session.commit()
        session.close()
        return str(run_id)

    @pytest.mark.asyncio
    async def test_successful_pipeline(self, sf, post_run):
        """Full happy-path run with all services mocked."""
        session_id = str(uuid4())
        client_id = str(uuid4())

        # Mock encrypted notes
        notes_encrypted = b"encrypted-content"

        mock_session_row = _make_session_row(
            session_id, client_id, notes_encrypted=notes_encrypted
        )

        # Mock services
        enc = MagicMock()
        enc.decrypt.return_value = "Session notes about CBT and attachment."

        extractor = MagicMock()
        extraction = _mock_extraction_output()
        extractor.extract.return_value = extraction

        planner = MagicMock()
        planner.create_sprint_plan.return_value = _mock_sprint_plan()

        perceptor = MagicMock()
        processor = MagicMock()

        from src.pipelines.post_session import run_post_session_pipeline

        def custom_sf():
            s = sf()
            original_query = s.query

            def patched_query(model):
                from src.models.pipeline_run import PipelineRun as PR
                if model is PR or (hasattr(model, "__tablename__") and model.__tablename__ == "pipeline_runs"):
                    return original_query(model)
                mock_q = MagicMock()
                mock_q.filter.return_value.first.return_value = mock_session_row
                return mock_q

            s.query = patched_query
            return s

        await run_post_session_pipeline(
            session_id=session_id,
            pipeline_id=post_run,
            session_factory=custom_sf,
            encryptor=enc,
            framework_extractor=extractor,
            sprint_planner=planner,
            perceptor_client=perceptor,
            notes_processor=processor,
        )

        # Verify completion
        run = _load_run(sf, post_run)
        assert run.status == PipelineStatus.COMPLETED.value
        assert run.completed_at is not None

        # Verify services called
        enc.decrypt.assert_called_once()
        extractor.extract.assert_called_once()
        planner.create_sprint_plan.assert_called_once()
        perceptor.save_session_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_notes_fails_pipeline(self, sf, post_run):
        """Pipeline fails when session has no notes."""
        session_id = str(uuid4())
        client_id = str(uuid4())

        # No notes
        mock_session_row = _make_session_row(
            session_id, client_id, notes_encrypted=None
        )

        enc = MagicMock()
        extractor = MagicMock()
        planner = MagicMock()
        perceptor = MagicMock()
        processor = MagicMock()

        from src.pipelines.post_session import run_post_session_pipeline

        def custom_sf():
            s = sf()
            original_query = s.query

            def patched_query(model):
                from src.models.pipeline_run import PipelineRun as PR
                if model is PR or (hasattr(model, "__tablename__") and model.__tablename__ == "pipeline_runs"):
                    return original_query(model)
                mock_q = MagicMock()
                mock_q.filter.return_value.first.return_value = mock_session_row
                return mock_q

            s.query = patched_query
            return s

        await run_post_session_pipeline(
            session_id=session_id,
            pipeline_id=post_run,
            session_factory=custom_sf,
            encryptor=enc,
            framework_extractor=extractor,
            sprint_planner=planner,
            perceptor_client=perceptor,
            notes_processor=processor,
        )

        run = _load_run(sf, post_run)
        assert run.status == PipelineStatus.FAILED.value
        assert "no notes" in run.error_message.lower()


# =============================================================================
# Tests: couples_merge pipeline
# =============================================================================

class TestCouplesMergePipeline:
    """Tests for run_couples_merge_pipeline."""

    @pytest.fixture()
    def merge_run(self, sf) -> str:
        """Create a couples-merge pipeline run."""
        session = sf()
        run_id = uuid4()
        run = PipelineRun(
            id=run_id,
            pipeline_type=PipelineType.COUPLES_MERGE.value,
            status=PipelineStatus.PENDING.value,
            couple_link_id=uuid4(),
        )
        session.add(run)
        session.commit()
        session.close()
        return str(run_id)

    @pytest.mark.asyncio
    async def test_successful_pipeline(self, sf, merge_run):
        """Full happy-path couples merge with mocked services."""
        partner_a_id = str(uuid4())
        partner_b_id = str(uuid4())
        therapist_id = str(uuid4())
        couple_link_id = str(uuid4())

        # Mock couple link
        from src.services.couple_manager import CoupleLink, CoupleLinkStatus

        link = CoupleLink(
            id=couple_link_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            therapist_id=therapist_id,
            status=CoupleLinkStatus.ACTIVE,
        )

        cm = MagicMock()
        cm.get_link.return_value = link
        cm.validate_merge_authorization.return_value = True

        # Mock isolation
        from src.services.isolation_layer import IsolatedFrameworks

        isolated_a = IsolatedFrameworks(
            frameworks_identified=["cbt"],
            theme_categories=["communication"],
        )
        isolated_b = IsolatedFrameworks(
            frameworks_identified=["eft"],
            theme_categories=["communication", "trust"],
        )

        isolation = MagicMock()

        # Mock topic matcher
        from src.services.topic_matcher import TopicMatchResult

        match_result = TopicMatchResult(
            overlapping_themes=[],
            complementary_patterns=[],
            potential_conflicts=[],
            suggested_focus_areas=["Building shared communication"],
            match_summary="1 shared theme.",
        )
        matcher = MagicMock()
        matcher.match.return_value = match_result

        # Mock merge engine
        from src.services.merge_engine import MergedFrameworks

        merged = MergedFrameworks(
            couple_link_id=couple_link_id,
            session_id=couple_link_id,
            partner_a_frameworks=["cbt"],
            partner_b_frameworks=["eft"],
            overlapping_themes=["communication"],
            complementary_patterns=[],
            potential_conflicts=[],
            suggested_focus_areas=["Building shared communication"],
            couples_exercises=["Active listening practice"],
            match_summary="1 shared theme.",
        )
        engine = MagicMock()
        engine.merge.return_value = merged

        audit = MagicMock()

        # Build analyses
        partner_a_analysis = _mock_rung_output()
        partner_b_analysis = _mock_rung_output()

        from src.pipelines.couples_merge import run_couples_merge_pipeline

        await run_couples_merge_pipeline(
            couple_link_id=couple_link_id,
            pipeline_id=merge_run,
            session_factory=sf,
            couple_manager=cm,
            isolation_layer=isolation,
            topic_matcher=matcher,
            merge_engine=engine,
            audit_service=audit,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        run = _load_run(sf, merge_run)
        assert run.status == PipelineStatus.COMPLETED.value
        assert run.completed_at is not None

        # Verify services called
        cm.get_link.assert_called_once_with(couple_link_id)
        engine.merge.assert_called_once()
        audit.log_couples_merge.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_link_fails_pipeline(self, sf, merge_run):
        """Pipeline fails when couple link is not found."""
        couple_link_id = str(uuid4())

        from src.services.couple_manager import CoupleManagerError

        cm = MagicMock()
        cm.get_link.side_effect = CoupleManagerError("Link not found")

        audit = MagicMock()

        from src.pipelines.couples_merge import run_couples_merge_pipeline

        await run_couples_merge_pipeline(
            couple_link_id=couple_link_id,
            pipeline_id=merge_run,
            session_factory=sf,
            couple_manager=cm,
            audit_service=audit,
            partner_a_analysis=_mock_rung_output(),
            partner_b_analysis=_mock_rung_output(),
        )

        run = _load_run(sf, merge_run)
        assert run.status == PipelineStatus.FAILED.value
        assert "not found" in run.error_message.lower()

    @pytest.mark.asyncio
    async def test_inactive_link_fails_pipeline(self, sf, merge_run):
        """Pipeline fails when couple link is not active."""
        couple_link_id = str(uuid4())

        from src.services.couple_manager import CoupleLink, CoupleLinkStatus

        link = CoupleLink(
            id=couple_link_id,
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=str(uuid4()),
            status=CoupleLinkStatus.PAUSED,
        )
        cm = MagicMock()
        cm.get_link.return_value = link

        audit = MagicMock()

        from src.pipelines.couples_merge import run_couples_merge_pipeline

        await run_couples_merge_pipeline(
            couple_link_id=couple_link_id,
            pipeline_id=merge_run,
            session_factory=sf,
            couple_manager=cm,
            audit_service=audit,
            partner_a_analysis=_mock_rung_output(),
            partner_b_analysis=_mock_rung_output(),
        )

        run = _load_run(sf, merge_run)
        assert run.status == PipelineStatus.FAILED.value
        assert "not active" in run.error_message.lower()

    @pytest.mark.asyncio
    async def test_missing_analyses_fails_pipeline(self, sf, merge_run):
        """Pipeline fails when partner analyses are not provided."""
        couple_link_id = str(uuid4())

        from src.services.couple_manager import CoupleLink, CoupleLinkStatus

        link = CoupleLink(
            id=couple_link_id,
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=str(uuid4()),
            status=CoupleLinkStatus.ACTIVE,
        )
        cm = MagicMock()
        cm.get_link.return_value = link

        audit = MagicMock()

        from src.pipelines.couples_merge import run_couples_merge_pipeline

        await run_couples_merge_pipeline(
            couple_link_id=couple_link_id,
            pipeline_id=merge_run,
            session_factory=sf,
            couple_manager=cm,
            audit_service=audit,
            partner_a_analysis=None,
            partner_b_analysis=None,
        )

        run = _load_run(sf, merge_run)
        assert run.status == PipelineStatus.FAILED.value
        assert "must be provided" in run.error_message.lower()


# =============================================================================
# Tests: stage ordering verification
# =============================================================================

class TestStageOrdering:
    """Verify that pipeline stages execute in documented order."""

    @pytest.mark.asyncio
    async def test_pre_session_stage_order(self, sf):
        """Pre-session pipeline updates stages in the correct sequence."""
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

        stages_seen = []
        original_update = update_pipeline_stage

        def tracking_update(session_factory, pipeline_id, stage, status=None):
            stages_seen.append(stage)
            original_update(session_factory, pipeline_id, stage, status)

        session_id = str(uuid4())
        client_id = str(uuid4())
        mock_session_row = _make_session_row(session_id, client_id)

        ts = MagicMock()
        tr = MagicMock()
        tr.transcript = "Test transcript."
        ts.get_transcript.return_value = tr

        rung = MagicMock()
        rung.analyze.return_value = _mock_rung_output()

        research = MagicMock()
        research.research_from_rung_output.return_value = _mock_research_batch()

        abstraction = MagicMock()
        abstraction.abstract.return_value = _mock_abstraction_result()
        abstraction.to_beth_input.return_value = MagicMock()

        beth = MagicMock()
        beth.generate.return_value = _mock_beth_output()

        audit = MagicMock()

        def custom_sf():
            s = sf()
            original_query = s.query

            def patched_query(model):
                from src.models.pipeline_run import PipelineRun as PR
                if model is PR or (hasattr(model, "__tablename__") and model.__tablename__ == "pipeline_runs"):
                    return original_query(model)
                mock_q = MagicMock()
                mock_q.filter.return_value.first.return_value = mock_session_row
                return mock_q

            s.query = patched_query
            return s

        with patch("src.pipelines.pre_session.update_pipeline_stage", side_effect=tracking_update):
            from src.pipelines.pre_session import run_pre_session_pipeline

            await run_pre_session_pipeline(
                session_id=session_id,
                pipeline_id=str(run_id),
                session_factory=custom_sf,
                transcription_service=ts,
                rung_agent=rung,
                research_service=research,
                abstraction_layer=abstraction,
                beth_agent=beth,
                audit_service=audit,
            )

        expected_stages = [
            "fetch_transcript",
            "rung_analysis",
            "research",
            "abstraction",
            "beth_generation",
            "store_results",
        ]
        assert stages_seen == expected_stages

    @pytest.mark.asyncio
    async def test_couples_merge_stage_order(self, sf):
        """Couples merge pipeline updates stages in the correct sequence."""
        session = sf()
        run_id = uuid4()
        run = PipelineRun(
            id=run_id,
            pipeline_type=PipelineType.COUPLES_MERGE.value,
            status=PipelineStatus.PENDING.value,
        )
        session.add(run)
        session.commit()
        session.close()

        stages_seen = []
        original_update = update_pipeline_stage

        def tracking_update(session_factory, pipeline_id, stage, status=None):
            stages_seen.append(stage)
            original_update(session_factory, pipeline_id, stage, status)

        couple_link_id = str(uuid4())

        from src.services.couple_manager import CoupleLink, CoupleLinkStatus

        link = CoupleLink(
            id=couple_link_id,
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
            therapist_id=str(uuid4()),
            status=CoupleLinkStatus.ACTIVE,
        )

        cm = MagicMock()
        cm.get_link.return_value = link
        cm.validate_merge_authorization.return_value = True

        from src.services.merge_engine import MergedFrameworks

        merged = MergedFrameworks(
            couple_link_id=couple_link_id,
            session_id=couple_link_id,
            partner_a_frameworks=["cbt"],
            partner_b_frameworks=["eft"],
            overlapping_themes=[],
            complementary_patterns=[],
            potential_conflicts=[],
            suggested_focus_areas=[],
            couples_exercises=[],
            match_summary="Test.",
        )

        engine = MagicMock()
        engine.merge.return_value = merged

        from src.services.isolation_layer import IsolatedFrameworks

        isolation = MagicMock()

        from src.services.topic_matcher import TopicMatchResult

        matcher = MagicMock()
        matcher.match.return_value = TopicMatchResult()

        audit = MagicMock()

        with patch("src.pipelines.couples_merge.update_pipeline_stage", side_effect=tracking_update):
            from src.pipelines.couples_merge import run_couples_merge_pipeline

            await run_couples_merge_pipeline(
                couple_link_id=couple_link_id,
                pipeline_id=str(run_id),
                session_factory=sf,
                couple_manager=cm,
                isolation_layer=isolation,
                topic_matcher=matcher,
                merge_engine=engine,
                audit_service=audit,
                partner_a_analysis=_mock_rung_output(),
                partner_b_analysis=_mock_rung_output(),
            )

        expected_stages = [
            "validate_link",
            "fetch_analyses",
            "merge",
            "audit",
            "store_results",
        ]
        assert stages_seen == expected_stages
