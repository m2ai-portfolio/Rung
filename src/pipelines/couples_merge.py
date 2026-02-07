"""
Couples merge pipeline -- replaces n8n/workflows/couples_merge.json.

Orchestrates the couples framework merge flow:
1. Validate the couple link exists and is active
2. Fetch both partners' most recent Rung analyses
3. Run MergeEngine (isolation + matching + merge internally)
4. Create audit trail entry
5. Store merged frameworks in pipeline metadata

CRITICAL: MergeEngine invokes IsolationLayer internally before any
cross-client data sharing. This is a HIPAA security boundary.
"""

import asyncio
from typing import Optional
from uuid import UUID

import structlog

from src.agents.schemas.rung_output import RungAnalysisOutput
from src.models.pipeline_run import PipelineStatus
from src.pipelines.base import complete_pipeline, fail_pipeline, update_pipeline_stage
from src.services.audit import AuditService
from src.services.couple_manager import CoupleManager, CoupleManagerError
from src.services.isolation_layer import IsolationLayer
from src.services.merge_engine import MergeEngine
from src.services.topic_matcher import TopicMatcher

logger = structlog.get_logger(__name__)


async def run_couples_merge_pipeline(
    couple_link_id: str,
    pipeline_id: str,
    session_factory,
    *,
    couple_manager: Optional[CoupleManager] = None,
    isolation_layer: Optional[IsolationLayer] = None,
    topic_matcher: Optional[TopicMatcher] = None,
    merge_engine: Optional[MergeEngine] = None,
    audit_service: Optional[AuditService] = None,
    partner_a_analysis: Optional[RungAnalysisOutput] = None,
    partner_b_analysis: Optional[RungAnalysisOutput] = None,
) -> None:
    """Execute the couples merge pipeline.

    Designed to run as a background task. Updates the PipelineRun row
    at every stage for progress tracking.

    Args:
        couple_link_id: UUID string of the couple link.
        pipeline_id: UUID string of the pipeline run.
        session_factory: SQLAlchemy session factory.
        couple_manager: Override for tests -- manages couple links.
        isolation_layer: Override for tests -- strips PHI from analyses.
        topic_matcher: Override for tests -- finds overlapping themes.
        merge_engine: Override for tests -- generates merged output.
        audit_service: Override for tests -- HIPAA audit logging.
        partner_a_analysis: Override for tests -- partner A's RungAnalysisOutput.
        partner_b_analysis: Override for tests -- partner B's RungAnalysisOutput.
    """
    cm = couple_manager or CoupleManager()
    isolation = isolation_layer or IsolationLayer(strict_mode=True)
    matcher = topic_matcher or TopicMatcher()
    audit = audit_service or AuditService(session_factory=session_factory)

    # Build the merge engine with injected dependencies
    engine = merge_engine or MergeEngine(
        couple_manager=cm,
        isolation_layer=isolation,
        topic_matcher=matcher,
        audit_service=audit,
    )

    try:
        # ------------------------------------------------------------------ #
        # Stage 1: validate_link
        # ------------------------------------------------------------------ #
        update_pipeline_stage(
            session_factory, pipeline_id, "validate_link", PipelineStatus.PROCESSING
        )

        try:
            link = cm.get_link(couple_link_id)
        except CoupleManagerError as exc:
            raise ValueError(
                f"Couple link not found or invalid: {couple_link_id}. {exc}"
            ) from exc

        from src.services.couple_manager import CoupleLinkStatus

        if link.status != CoupleLinkStatus.ACTIVE:
            raise ValueError(
                f"Couple link {couple_link_id} is not active "
                f"(status: {link.status.value}). Cannot perform merge."
            )

        partner_a_id = link.partner_a_id
        partner_b_id = link.partner_b_id
        therapist_id = link.therapist_id

        logger.info(
            "couple_link_validated",
            couple_link_id=couple_link_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
        )

        # ------------------------------------------------------------------ #
        # Stage 2: fetch_analyses (parallel)
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "fetch_analyses")

        # In a real deployment, these would be fetched from the database.
        # For now, they must be provided as parameters (the API endpoint
        # passes them in after loading from the most recent pipeline runs).
        if partner_a_analysis is None or partner_b_analysis is None:
            raise ValueError(
                "Both partner_a_analysis and partner_b_analysis must be provided. "
                "The API layer should load the most recent RungAnalysisOutput "
                "for each partner before invoking this pipeline."
            )

        logger.info(
            "analyses_fetched",
            partner_a_frameworks=len(partner_a_analysis.frameworks_identified),
            partner_b_frameworks=len(partner_b_analysis.frameworks_identified),
        )

        # ------------------------------------------------------------------ #
        # Stage 3: merge (isolation + matching + merge)
        #
        # MergeEngine handles isolation internally via
        # isolate_for_couples_merge() -- this is the HIPAA security boundary.
        # Keeping isolation inside MergeEngine ensures it can never be
        # bypassed regardless of how the engine is called.
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "merge")

        merged = await asyncio.to_thread(
            engine.merge,
            couple_link_id=couple_link_id,
            session_id=couple_link_id,  # Use link ID as session context
            therapist_id=therapist_id,
            partner_a_analysis=partner_a_analysis,
            partner_b_analysis=partner_b_analysis,
        )

        logger.info(
            "merge_complete",
            overlapping_themes=len(merged.overlapping_themes),
            complementary_patterns=len(merged.complementary_patterns),
            exercises=len(merged.couples_exercises),
        )

        # ------------------------------------------------------------------ #
        # Stage 4: audit
        # ------------------------------------------------------------------ #
        update_pipeline_stage(session_factory, pipeline_id, "audit")

        audit.log_couples_merge(
            therapist_id=therapist_id,
            couple_link_id=couple_link_id,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            action="merge_completed",
            details={
                "pipeline_id": pipeline_id,
                "overlapping_themes": merged.overlapping_themes,
                "complementary_patterns": merged.complementary_patterns,
                "exercises_count": len(merged.couples_exercises),
            },
        )

        logger.info("audit_entry_created", couple_link_id=couple_link_id)

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
                    "partner_a_frameworks": merged.partner_a_frameworks,
                    "partner_b_frameworks": merged.partner_b_frameworks,
                    "overlapping_themes": merged.overlapping_themes,
                    "complementary_patterns": merged.complementary_patterns,
                    "potential_conflicts": merged.potential_conflicts,
                    "suggested_focus_areas": merged.suggested_focus_areas,
                    "couples_exercises": merged.couples_exercises,
                    "match_summary": merged.match_summary,
                }
                db_session.commit()
        finally:
            db_session.close()

        # ------------------------------------------------------------------ #
        # Done
        # ------------------------------------------------------------------ #
        complete_pipeline(session_factory, pipeline_id)

        logger.info(
            "couples_merge_pipeline_complete",
            couple_link_id=couple_link_id,
        )

    except Exception as exc:
        logger.error(
            "couples_merge_pipeline_failed",
            couple_link_id=couple_link_id,
            error=str(exc),
        )
        fail_pipeline(session_factory, pipeline_id, str(exc))
