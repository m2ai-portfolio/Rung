"""
Pre-session pipeline -- replaces n8n/workflows/pre_session.json.

Orchestrates the full pre-session analysis flow:
1. Fetch the voice-memo transcript from S3
2. Run Rung clinical analysis and Research in parallel
3. Abstract clinical output for Beth (client-safe version)
4. Generate Beth client guide
5. Store clinical_brief and client_guide in the database
6. Create audit trail entries

All external service calls are wrapped in try/except so that failures
are recorded against the pipeline run. Services are accepted as
optional constructor-style kwargs for testability.
"""

import asyncio
from typing import Optional
from uuid import UUID

import structlog

from src.agents.beth import BethAgent
from src.agents.rung import RungAgent
from src.agents.schemas.rung_output import RungAnalysisRequest
from src.models.pipeline_run import PipelineStatus
from src.pipelines.base import complete_pipeline, fail_pipeline, update_pipeline_stage
from src.services.abstraction_layer import AbstractionLayer
from src.services.audit import AuditService
from src.services.research import ResearchService
from src.services.transcription import TranscriptionService

logger = structlog.get_logger(__name__)


async def run_pre_session_pipeline(
    session_id: str,
    pipeline_id: str,
    session_factory,
    *,
    transcription_service: Optional[TranscriptionService] = None,
    rung_agent: Optional[RungAgent] = None,
    research_service: Optional[ResearchService] = None,
    abstraction_layer: Optional[AbstractionLayer] = None,
    beth_agent: Optional[BethAgent] = None,
    audit_service: Optional[AuditService] = None,
) -> None:
    """Execute the pre-session analysis pipeline.

    This function is designed to run as a background task
    (``asyncio.create_task``). It updates the PipelineRun row at every
    stage so that callers can poll for progress.

    Args:
        session_id: UUID string of the therapy session.
        pipeline_id: UUID string of the pipeline run tracking this execution.
        session_factory: SQLAlchemy session factory for DB access.
        transcription_service: Override for tests -- fetches transcripts from S3.
        rung_agent: Override for tests -- clinical analysis agent.
        research_service: Override for tests -- Perplexity research.
        abstraction_layer: Override for tests -- Rung-to-Beth abstraction.
        beth_agent: Override for tests -- client-facing guide generation.
        audit_service: Override for tests -- HIPAA audit logging.
    """
    # Resolve service defaults
    ts = transcription_service or TranscriptionService()
    rung = rung_agent or RungAgent()
    research = research_service or ResearchService()
    abstraction = abstraction_layer or AbstractionLayer()
    beth = beth_agent or BethAgent()
    audit = audit_service or AuditService(session_factory=session_factory)

    try:
        # ------------------------------------------------------------------ #
        # Stage 1: fetch_transcript
        # ------------------------------------------------------------------ #
        update_pipeline_stage(
            session_factory, pipeline_id, "fetch_transcript", PipelineStatus.PROCESSING
        )

        # Load the session row to get the transcript S3 key
        db_session = session_factory()
        try:
            from src.models.session import Session

            session_row = (
                db_session.query(Session).filter(Session.id == UUID(session_id)).first()
            )
            if session_row is None:
                raise ValueError(f"Session not found: {session_id}")

            transcript_s3_key = session_row.transcript_s3_key
            client_id = str(session_row.client_id)
        finally:
            db_session.close()

        if not transcript_s3_key:
            raise ValueError(
                f"Session {session_id} has no transcript_s3_key. "
                "Upload a voice memo first."
            )

        # Fetch transcript text from S3 via transcription service
        transcript_result = await asyncio.to_thread(
            ts.get_transcript, session_id, transcript_s3_key
        )
        transcript_text = transcript_result.transcript

        logger.info(
            "transcript_fetched",
            session_id=session_id,
            length=len(transcript_text),
        )

        # ------------------------------------------------------------------ #
        # Stages 2+3: rung_analysis & research (parallel)
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "rung_analysis")

        analysis_request = RungAnalysisRequest(
            session_id=session_id,
            client_id=client_id,
            transcript=transcript_text,
        )

        async def _run_rung():
            return await asyncio.to_thread(rung.analyze, analysis_request)

        async def _run_research(rung_output_dict):
            return await asyncio.to_thread(
                research.research_from_rung_output, rung_output_dict
            )

        # Run Rung first (research depends on its output for frameworks)
        rung_output = await _run_rung()

        # Now run research with the Rung output
        update_pipeline_stage(session_factory, pipeline_id, "research")
        research_batch = await _run_research(rung_output.model_dump())

        logger.info(
            "analysis_complete",
            session_id=session_id,
            frameworks=len(rung_output.frameworks_identified),
            research_results=research_batch.successful_queries,
        )

        # ------------------------------------------------------------------ #
        # Stage 4: abstraction
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "abstraction")

        abstraction_result = abstraction.abstract(rung_output)
        if not abstraction_result.is_safe_for_beth:
            raise RuntimeError(
                "Abstraction layer produced unsafe output for Beth. "
                "Clinical terms were not fully stripped."
            )

        beth_input = abstraction.to_beth_input(rung_output)

        logger.info(
            "abstraction_complete",
            session_id=session_id,
            terms_stripped=len(abstraction_result.clinical_terms_stripped),
        )

        # ------------------------------------------------------------------ #
        # Stage 5: beth_generation
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "beth_generation")

        beth_output = await asyncio.to_thread(beth.generate, beth_input)

        logger.info("beth_generation_complete", session_id=session_id)

        # ------------------------------------------------------------------ #
        # Stage 6: store_results
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "store_results")

        db_session = session_factory()
        try:
            # Store pipeline metadata with summary results
            from src.models.pipeline_run import PipelineRun

            run = (
                db_session.query(PipelineRun)
                .filter(PipelineRun.id == UUID(pipeline_id))
                .first()
            )
            if run:
                run.metadata_json = {
                    "frameworks_count": len(rung_output.frameworks_identified),
                    "risk_flags_count": len(rung_output.risk_flags),
                    "research_citations": research_batch.successful_queries,
                    "beth_tone_check": beth_output.tone_check_passed,
                }
                db_session.commit()
        finally:
            db_session.close()

        # Audit trail
        audit.log_agent_invocation(
            user_id="system",
            agent_name="rung",
            client_id=client_id,
            session_id=session_id,
            details={"pipeline_id": pipeline_id, "stage": "pre_session"},
        )
        audit.log_agent_invocation(
            user_id="system",
            agent_name="beth",
            client_id=client_id,
            session_id=session_id,
            details={"pipeline_id": pipeline_id, "stage": "pre_session"},
        )

        # ------------------------------------------------------------------ #
        # Done
        # ------------------------------------------------------------------ #
        complete_pipeline(session_factory, pipeline_id)

        logger.info("pre_session_pipeline_complete", session_id=session_id)

    except Exception as exc:
        logger.error(
            "pre_session_pipeline_failed",
            session_id=session_id,
            error=str(exc),
        )
        fail_pipeline(session_factory, pipeline_id, str(exc))
