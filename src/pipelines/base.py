"""
Pipeline base utilities for common operations.

Provides helper functions shared across all pipeline modules:
- Updating pipeline stage and status
- Marking pipelines as failed or completed
- Consistent timestamp and error handling
"""

from datetime import datetime
from uuid import UUID

import structlog

from src.models.pipeline_run import PipelineRun, PipelineStatus

logger = structlog.get_logger(__name__)


def _to_uuid(value: str | UUID) -> UUID:
    """Convert a string or UUID to a UUID object."""
    if isinstance(value, UUID):
        return value
    return UUID(value)


def update_pipeline_stage(
    session_factory,
    pipeline_id: str,
    stage: str,
    status: PipelineStatus | None = None,
) -> None:
    """Update the current stage (and optionally status) of a pipeline run.

    Args:
        session_factory: SQLAlchemy session factory.
        pipeline_id: UUID string of the pipeline run.
        stage: Name of the stage the pipeline is entering.
        status: Optional new status. If ``None``, status is unchanged.
    """
    session = session_factory()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == _to_uuid(pipeline_id)).first()
        if run is None:
            logger.warning("pipeline_run_not_found", pipeline_id=pipeline_id)
            return
        run.current_stage = stage
        if status is not None:
            run.status = status.value
        # Set started_at on first processing update
        if run.started_at is None and (status == PipelineStatus.PROCESSING or stage):
            run.started_at = datetime.utcnow()
        session.commit()
        logger.info(
            "pipeline_stage_updated",
            pipeline_id=pipeline_id,
            stage=stage,
            status=status.value if status else run.status,
        )
    except Exception:
        session.rollback()
        logger.error("pipeline_stage_update_failed", pipeline_id=pipeline_id, stage=stage)
        raise
    finally:
        session.close()


def fail_pipeline(
    session_factory,
    pipeline_id: str,
    error_message: str,
) -> None:
    """Mark a pipeline run as FAILED with an error message.

    Args:
        session_factory: SQLAlchemy session factory.
        pipeline_id: UUID string of the pipeline run.
        error_message: Human-readable error description.
    """
    session = session_factory()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == _to_uuid(pipeline_id)).first()
        if run is None:
            logger.warning("pipeline_run_not_found", pipeline_id=pipeline_id)
            return
        run.status = PipelineStatus.FAILED.value
        run.error_message = error_message
        run.completed_at = datetime.utcnow()
        session.commit()
        logger.error(
            "pipeline_failed",
            pipeline_id=pipeline_id,
            error_message=error_message,
        )
    except Exception:
        session.rollback()
        logger.error("pipeline_fail_update_failed", pipeline_id=pipeline_id)
        raise
    finally:
        session.close()


def complete_pipeline(
    session_factory,
    pipeline_id: str,
) -> None:
    """Mark a pipeline run as COMPLETED with a completion timestamp.

    Args:
        session_factory: SQLAlchemy session factory.
        pipeline_id: UUID string of the pipeline run.
    """
    session = session_factory()
    try:
        run = session.query(PipelineRun).filter(PipelineRun.id == _to_uuid(pipeline_id)).first()
        if run is None:
            logger.warning("pipeline_run_not_found", pipeline_id=pipeline_id)
            return
        run.status = PipelineStatus.COMPLETED.value
        run.completed_at = datetime.utcnow()
        session.commit()
        logger.info("pipeline_completed", pipeline_id=pipeline_id)
    except Exception:
        session.rollback()
        logger.error("pipeline_complete_update_failed", pipeline_id=pipeline_id)
        raise
    finally:
        session.close()
