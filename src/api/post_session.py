"""
Post-Session API Endpoints

Provides endpoints for post-session notes processing:
- Submit session notes
- Get extraction results
- Trigger post-session workflow
"""

from typing import Callable, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DBSession

from src.models.base import get_session_factory
from src.models.pipeline_run import PipelineRun, PipelineType, PipelineStatus
from src.models.session_extraction import SessionExtraction
from src.services.notes_processor import (
    NotesProcessor,
    NotesInput,
    NotesProcessingResult,
    NotesProcessorError,
)
from src.services.framework_extractor import (
    FrameworkExtractionOutput,
    HomeworkAssignment,
)


router = APIRouter(prefix="/sessions/{session_id}", tags=["post-session"])


# =============================================================================
# Request/Response Models
# =============================================================================

class NotesSubmitRequest(BaseModel):
    """Request to submit session notes."""
    notes: str = Field(..., min_length=10, description="Session notes text")
    encrypt: bool = Field(default=True, description="Whether to encrypt notes")


class NotesSubmitResponse(BaseModel):
    """Response from notes submission."""
    session_id: str
    processing_id: str
    status: str
    message: str


class ExtractionResponse(BaseModel):
    """Response with extraction results."""
    session_id: str
    frameworks_discussed: list[str] = Field(default_factory=list)
    modalities_used: list[str] = Field(default_factory=list)
    homework_assigned: list[dict] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)
    progress_indicators: list[str] = Field(default_factory=list)
    areas_for_next_session: list[str] = Field(default_factory=list)
    session_summary: Optional[str] = None


class PostSessionStatus(BaseModel):
    """Status of post-session processing."""
    session_id: str
    status: str = Field(..., description="pending|processing|completed|failed")
    notes_submitted: bool = False
    extraction_complete: bool = False
    sprint_plan_generated: bool = False
    perceptor_archived: bool = False
    error_message: Optional[str] = None


# =============================================================================
# Module-level dependencies (for dependency injection in tests)
# =============================================================================

_notes_processor: Optional[NotesProcessor] = None
_session_factory: Optional[Callable] = None


def get_notes_processor() -> NotesProcessor:
    """Get or create notes processor."""
    global _notes_processor
    if _notes_processor is None:
        _notes_processor = NotesProcessor()
    return _notes_processor


def set_notes_processor(processor: NotesProcessor) -> None:
    """Set notes processor (for testing)."""
    global _notes_processor
    _notes_processor = processor


def get_session_factory_instance() -> Callable:
    """Get or create session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory()
    return _session_factory


def set_session_factory_instance(factory: Callable) -> None:
    """Set session factory (for testing)."""
    global _session_factory
    _session_factory = factory


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/notes", response_model=NotesSubmitResponse)
async def submit_notes(
    session_id: UUID,
    request: NotesSubmitRequest,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> NotesSubmitResponse:
    """
    Submit session notes for processing.

    Notes will be:
    1. Validated
    2. Encrypted (if requested)
    3. Processed for framework extraction
    4. Stored in database
    5. Trigger post-session workflow

    SECURITY: Only therapists can submit notes.
    """
    # Verify therapist role
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can submit session notes"
        )

    # Validate notes length
    if len(request.notes) < 10:
        raise HTTPException(
            status_code=400,
            detail="Notes must be at least 10 characters"
        )

    # Process notes
    processor = get_notes_processor()

    try:
        input_data = NotesInput(
            session_id=str(session_id),
            notes=request.notes,
            therapist_id=x_user_id,
            encrypt=request.encrypt,
        )

        result = processor.process(input_data)

        return NotesSubmitResponse(
            session_id=str(session_id),
            processing_id=result.processing_id,
            status=result.status,
            message="Notes submitted and processed successfully" if result.status == "completed" else f"Processing failed: {result.error_message}",
        )

    except NotesProcessorError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/extraction", response_model=ExtractionResponse)
async def get_extraction(
    session_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ExtractionResponse:
    """
    Get framework extraction results for a session.

    SECURITY: Only therapists can access extraction results.
    """
    # Verify therapist role
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Extraction results are only accessible to therapists"
        )

    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for extraction data
        extraction = session.query(SessionExtraction).filter(
            SessionExtraction.session_id == session_id
        ).first()

        if extraction is None:
            raise HTTPException(
                status_code=404,
                detail="Extraction results not found for this session"
            )

        return ExtractionResponse(
            session_id=str(session_id),
            frameworks_discussed=extraction.frameworks_discussed or [],
            modalities_used=extraction.modalities_used or [],
            homework_assigned=extraction.homework_assigned or [],
            breakthroughs=extraction.breakthroughs or [],
            progress_indicators=extraction.progress_indicators or [],
            areas_for_next_session=extraction.areas_for_next_session or [],
            session_summary=extraction.session_summary,
        )
    finally:
        session.close()


@router.get("/post-session/status", response_model=PostSessionStatus)
async def get_post_session_status(
    session_id: UUID,
    x_user_id: str = Header(...),
) -> PostSessionStatus:
    """
    Get post-session processing status.

    Returns the current status of notes processing,
    framework extraction, and sprint planning.
    """
    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for the most recent post-session pipeline run for this session
        pipeline_run = session.query(PipelineRun).filter(
            PipelineRun.session_id == session_id,
            PipelineRun.pipeline_type == PipelineType.POST_SESSION.value
        ).order_by(PipelineRun.created_at.desc()).first()

        if pipeline_run is None:
            # No pipeline run exists yet
            return PostSessionStatus(
                session_id=str(session_id),
                status="pending",
                notes_submitted=False,
                extraction_complete=False,
                sprint_plan_generated=False,
                perceptor_archived=False,
            )

        # Determine completion flags based on pipeline status and metadata
        metadata = pipeline_run.metadata_json or {}
        notes_submitted = metadata.get("notes_submitted", False)
        extraction_complete = metadata.get("extraction_complete", False)
        sprint_plan_generated = metadata.get("sprint_plan_generated", False)
        perceptor_archived = metadata.get("perceptor_archived", False)

        return PostSessionStatus(
            session_id=str(session_id),
            status=pipeline_run.status,
            notes_submitted=notes_submitted,
            extraction_complete=extraction_complete,
            sprint_plan_generated=sprint_plan_generated,
            perceptor_archived=perceptor_archived,
            error_message=pipeline_run.error_message,
        )
    finally:
        session.close()


# =============================================================================
# Homework Endpoints
# =============================================================================

class HomeworkListResponse(BaseModel):
    """List of homework assignments."""
    session_id: str
    assignments: list[dict] = Field(default_factory=list)


@router.get("/homework", response_model=HomeworkListResponse)
async def get_homework(
    session_id: UUID,
    x_user_id: str = Header(...),
) -> HomeworkListResponse:
    """
    Get homework assignments from a session.

    Accessible by both therapist and client.
    """
    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for extraction data to get homework
        extraction = session.query(SessionExtraction).filter(
            SessionExtraction.session_id == session_id
        ).first()

        if extraction is None:
            raise HTTPException(
                status_code=404,
                detail="No homework found for this session"
            )

        return HomeworkListResponse(
            session_id=str(session_id),
            assignments=extraction.homework_assigned or [],
        )
    finally:
        session.close()


# =============================================================================
# Progress Endpoints
# =============================================================================

class ProgressResponse(BaseModel):
    """Progress indicators from session."""
    session_id: str
    indicators: list[str] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)


@router.get("/progress", response_model=ProgressResponse)
async def get_progress(
    session_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ProgressResponse:
    """
    Get progress indicators from a session.

    SECURITY: Only therapists can access progress indicators.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Progress indicators are only accessible to therapists"
        )

    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for extraction data to get progress
        extraction = session.query(SessionExtraction).filter(
            SessionExtraction.session_id == session_id
        ).first()

        if extraction is None:
            raise HTTPException(
                status_code=404,
                detail="Progress indicators not found for this session"
            )

        return ProgressResponse(
            session_id=str(session_id),
            indicators=extraction.progress_indicators or [],
            breakthroughs=extraction.breakthroughs or [],
        )
    finally:
        session.close()
