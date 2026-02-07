"""
Post-session pipeline -- replaces n8n/workflows/post_session.json.

Orchestrates the post-session processing flow:
1. Encrypt therapist session notes
2. Extract frameworks, modalities, homework from notes
3. Generate a development sprint plan
4. Archive session context to Perceptor
5. Store extraction results and sprint plan in pipeline metadata

All external service calls are wrapped for testability and failure handling.
"""

import asyncio
from typing import Optional
from uuid import UUID

import structlog

from src.models.pipeline_run import PipelineStatus
from src.pipelines.base import complete_pipeline, fail_pipeline, update_pipeline_stage
from src.services.encryption import get_encryptor, DevEncryptor, FieldEncryptor
from src.services.framework_extractor import FrameworkExtractor
from src.services.notes_processor import NotesProcessor
from src.services.perceptor_client import PerceptorClient
from src.services.sprint_planner import SprintPlanner

logger = structlog.get_logger(__name__)


async def run_post_session_pipeline(
    session_id: str,
    pipeline_id: str,
    session_factory,
    *,
    encryptor: Optional[DevEncryptor | FieldEncryptor] = None,
    framework_extractor: Optional[FrameworkExtractor] = None,
    sprint_planner: Optional[SprintPlanner] = None,
    perceptor_client: Optional[PerceptorClient] = None,
    notes_processor: Optional[NotesProcessor] = None,
) -> None:
    """Execute the post-session processing pipeline.

    Designed to run as a background task. Updates the PipelineRun row
    at every stage for progress tracking.

    Args:
        session_id: UUID string of the therapy session.
        pipeline_id: UUID string of the pipeline run.
        session_factory: SQLAlchemy session factory.
        encryptor: Override for tests -- encryption service.
        framework_extractor: Override for tests -- extracts frameworks from notes.
        sprint_planner: Override for tests -- generates sprint plans.
        perceptor_client: Override for tests -- archives to Perceptor.
        notes_processor: Override for tests -- processes therapist notes.
    """
    enc = encryptor or get_encryptor()
    extractor = framework_extractor or FrameworkExtractor()
    planner = sprint_planner or SprintPlanner()
    perceptor = perceptor_client or PerceptorClient()
    processor = notes_processor or NotesProcessor(
        framework_extractor=extractor, encryptor=enc
    )

    try:
        # ------------------------------------------------------------------ #
        # Load session data
        # ------------------------------------------------------------------ #
        db_session = session_factory()
        try:
            from src.models.session import Session

            session_row = (
                db_session.query(Session).filter(Session.id == UUID(session_id)).first()
            )
            if session_row is None:
                raise ValueError(f"Session not found: {session_id}")

            client_id = str(session_row.client_id)
            notes_encrypted = session_row.notes_encrypted
        finally:
            db_session.close()

        if notes_encrypted is None:
            raise ValueError(
                f"Session {session_id} has no notes. "
                "Submit therapist notes before running post-session pipeline."
            )

        # ------------------------------------------------------------------ #
        # Stage 1: encrypt_notes
        # ------------------------------------------------------------------ #
        update_pipeline_stage(
            session_factory, pipeline_id, "encrypt_notes", PipelineStatus.PROCESSING
        )

        # Notes are already stored encrypted in the DB. This stage verifies
        # the encryption is intact and re-encrypts if needed for archival.
        # For the pipeline, we decrypt to work with plaintext for extraction.
        context = {"session_id": session_id, "client_id": client_id}
        try:
            notes_plaintext = enc.decrypt(notes_encrypted, context)
        except Exception:
            # If decryption fails with context, try without (legacy data)
            notes_plaintext = enc.decrypt(notes_encrypted, {})

        logger.info(
            "notes_decrypted",
            session_id=session_id,
            length=len(notes_plaintext),
        )

        # ------------------------------------------------------------------ #
        # Stage 2: extract_frameworks
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "extract_frameworks")

        extraction = await asyncio.to_thread(extractor.extract, notes_plaintext)

        logger.info(
            "frameworks_extracted",
            session_id=session_id,
            frameworks=len(extraction.frameworks_discussed),
            modalities=len(extraction.modalities_used),
            homework=len(extraction.homework_assigned),
        )

        # ------------------------------------------------------------------ #
        # Stage 3: generate_sprint
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "generate_sprint")

        sprint_plan = await asyncio.to_thread(
            planner.create_sprint_plan,
            client_id=client_id,
            session_id=session_id,
            extraction=extraction,
            sprint_number=1,  # TODO: look up actual sprint number from DB
        )

        logger.info(
            "sprint_generated",
            session_id=session_id,
            goals=len(sprint_plan.goals),
            exercises=len(sprint_plan.exercises),
        )

        # ------------------------------------------------------------------ #
        # Stage 4: archive
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "archive")

        # Build content summary for Perceptor (no raw PHI -- frameworks only)
        insights = extraction.breakthroughs + extraction.progress_indicators
        summary = extraction.session_summary or "Post-session analysis complete."

        await asyncio.to_thread(
            perceptor.save_session_context,
            session_id=session_id,
            client_id=client_id,
            agent="rung",
            stage="post-session",
            frameworks=extraction.frameworks_discussed,
            insights=insights,
            summary=summary,
        )

        logger.info("session_archived", session_id=session_id)

        # ------------------------------------------------------------------ #
        # Stage 5: store_results
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "store_results")

        db_session = session_factory()
        try:
            from src.models.pipeline_run import PipelineRun

            run = (
                db_session.query(PipelineRun)
                .filter(PipelineRun.id == UUID(pipeline_id))
                .first()
            )
            if run:
                run.metadata_json = {
                    "frameworks_discussed": extraction.frameworks_discussed,
                    "modalities_used": extraction.modalities_used,
                    "homework_count": len(extraction.homework_assigned),
                    "breakthroughs_count": len(extraction.breakthroughs),
                    "sprint_goals_count": len(sprint_plan.goals),
                    "sprint_exercises_count": len(sprint_plan.exercises),
                }
                db_session.commit()
        finally:
            db_session.close()

        # ------------------------------------------------------------------ #
        # Done
        # ------------------------------------------------------------------ #
        complete_pipeline(session_factory, pipeline_id)

        logger.info("post_session_pipeline_complete", session_id=session_id)

    except Exception as exc:
        logger.error(
            "post_session_pipeline_failed",
            session_id=session_id,
            error=str(exc),
        )
        fail_pipeline(session_factory, pipeline_id, str(exc))
