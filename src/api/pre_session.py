"""
Pre-Session API Endpoints

Provides endpoints for pre-session workflow status and outputs:
- Clinical Brief (therapist only)
- Client Guide (client only)
- Workflow status
"""

from typing import Callable, Optional
from uuid import UUID, uuid4
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.models.base import get_session_factory
from src.models.pipeline_run import PipelineRun, PipelineType, PipelineStatus
from src.models.clinical_brief import ClinicalBrief as ClinicalBriefModel
from src.models.client_guide import ClientGuide as ClientGuideModel


router = APIRouter(prefix="/sessions/{session_id}/pre-session", tags=["pre-session"])


# =============================================================================
# Request/Response Models
# =============================================================================

class PreSessionStatus(BaseModel):
    """Status of pre-session processing."""
    session_id: str
    status: str = Field(..., description="pending|processing|completed|failed")
    voice_memo_uploaded: bool = False
    transcription_complete: bool = False
    rung_analysis_complete: bool = False
    beth_generation_complete: bool = False
    error_message: Optional[str] = None


class ClinicalBrief(BaseModel):
    """Clinical brief for therapist (Rung output)."""
    session_id: str
    frameworks_identified: list[dict] = Field(default_factory=list)
    defense_mechanisms: list[dict] = Field(default_factory=list)
    risk_flags: list[dict] = Field(default_factory=list)
    key_themes: list[str] = Field(default_factory=list)
    suggested_exploration: list[str] = Field(default_factory=list)
    session_questions: list[str] = Field(default_factory=list)
    research_citations: list[dict] = Field(default_factory=list)
    analysis_confidence: Optional[float] = None


class ClientGuide(BaseModel):
    """Client-friendly session guide (Beth output)."""
    session_id: str
    session_prep: str = ""
    discussion_points: list[str] = Field(default_factory=list)
    reflection_questions: list[str] = Field(default_factory=list)
    exercises: list[str] = Field(default_factory=list)


class TriggerRequest(BaseModel):
    """Request to trigger pre-session processing."""
    force_reprocess: bool = False


class TriggerResponse(BaseModel):
    """Response from trigger endpoint."""
    session_id: str
    workflow_id: str
    status: str
    message: str


# =============================================================================
# Module-level session factory (for dependency injection in tests)
# =============================================================================

_session_factory: Optional[Callable] = None


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

@router.get("/status", response_model=PreSessionStatus)
async def get_pre_session_status(
    session_id: UUID,
    x_user_id: str = Header(...),
) -> PreSessionStatus:
    """
    Get pre-session processing status.

    Returns the current status of voice memo processing,
    transcription, Rung analysis, and Beth generation.
    """
    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for the most recent pre-session pipeline run for this session
        pipeline_run = session.query(PipelineRun).filter(
            PipelineRun.session_id == session_id,
            PipelineRun.pipeline_type == PipelineType.PRE_SESSION.value
        ).order_by(PipelineRun.created_at.desc()).first()

        if pipeline_run is None:
            # No pipeline run exists yet
            return PreSessionStatus(
                session_id=str(session_id),
                status="pending",
                voice_memo_uploaded=False,
                transcription_complete=False,
                rung_analysis_complete=False,
                beth_generation_complete=False,
            )

        # Determine completion flags based on pipeline status and metadata
        metadata = pipeline_run.metadata_json or {}
        voice_memo_uploaded = metadata.get("voice_memo_uploaded", False)
        transcription_complete = metadata.get("transcription_complete", False)
        rung_analysis_complete = metadata.get("rung_analysis_complete", False)
        beth_generation_complete = metadata.get("beth_generation_complete", False)

        return PreSessionStatus(
            session_id=str(session_id),
            status=pipeline_run.status,
            voice_memo_uploaded=voice_memo_uploaded,
            transcription_complete=transcription_complete,
            rung_analysis_complete=rung_analysis_complete,
            beth_generation_complete=beth_generation_complete,
            error_message=pipeline_run.error_message,
        )
    finally:
        session.close()


@router.get("/clinical-brief", response_model=ClinicalBrief)
async def get_clinical_brief(
    session_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ClinicalBrief:
    """
    Get clinical brief for therapist.

    SECURITY: Only accessible by therapist role.
    Contains Rung analysis output with clinical terminology.
    """
    # Verify therapist role
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Clinical brief is only accessible to therapists"
        )

    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for clinical brief for this session
        clinical_brief = session.query(ClinicalBriefModel).filter(
            ClinicalBriefModel.session_id == session_id
        ).first()

        if clinical_brief is None:
            raise HTTPException(
                status_code=404,
                detail="Clinical brief not found for this session"
            )

        # TODO: Decrypt content_encrypted if needed
        # For now, return available structured data
        return ClinicalBrief(
            session_id=str(session_id),
            frameworks_identified=clinical_brief.frameworks_identified or [],
            defense_mechanisms=[],  # Not in current model, would need to be added
            risk_flags=clinical_brief.risk_flags or [],
            key_themes=[],  # Not in current model, could extract from content
            suggested_exploration=[],  # Not in current model
            session_questions=[],  # Not in current model
            research_citations=clinical_brief.research_citations or [],
            analysis_confidence=None,  # Not in current model
        )
    finally:
        session.close()


@router.get("/client-guide", response_model=ClientGuide)
async def get_client_guide(
    session_id: UUID,
    x_user_id: str = Header(...),
) -> ClientGuide:
    """
    Get client-friendly session guide.

    Contains Beth output with accessible language.
    No clinical terminology.
    """
    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Query for client guide for this session
        client_guide = session.query(ClientGuideModel).filter(
            ClientGuideModel.session_id == session_id
        ).first()

        if client_guide is None:
            raise HTTPException(
                status_code=404,
                detail="Client guide not found for this session"
            )

        # TODO: Decrypt content_encrypted if needed
        # For now, return available structured data
        return ClientGuide(
            session_id=str(session_id),
            session_prep="",  # Would need to extract from decrypted content
            discussion_points=client_guide.key_points or [],
            reflection_questions=[],  # Not in current model
            exercises=[ex.get("description", ex.get("name", "")) for ex in (client_guide.exercises_suggested or [])],
        )
    finally:
        session.close()


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pre_session(
    session_id: UUID,
    request: TriggerRequest,
    x_user_id: str = Header(...),
) -> TriggerResponse:
    """
    Trigger pre-session processing workflow.

    Creates a pipeline run record for the pre-session workflow.
    The actual pipeline execution will be handled by a background task.
    """
    SessionFactory = get_session_factory_instance()
    session = SessionFactory()

    try:
        # Check if a pipeline already exists and is running
        existing_run = session.query(PipelineRun).filter(
            PipelineRun.session_id == session_id,
            PipelineRun.pipeline_type == PipelineType.PRE_SESSION.value,
            PipelineRun.status.in_([PipelineStatus.PENDING.value, PipelineStatus.PROCESSING.value])
        ).first()

        if existing_run and not request.force_reprocess:
            raise HTTPException(
                status_code=400,
                detail=f"Pre-session pipeline already running (status: {existing_run.status})"
            )

        # Create new pipeline run record
        pipeline_run = PipelineRun(
            id=uuid4(),
            pipeline_type=PipelineType.PRE_SESSION.value,
            session_id=session_id,
            status=PipelineStatus.PENDING.value,
            metadata_json={
                "triggered_by": x_user_id,
                "force_reprocess": request.force_reprocess,
            },
            created_at=datetime.utcnow(),
        )

        session.add(pipeline_run)
        session.commit()

        workflow_id = str(pipeline_run.id)

        return TriggerResponse(
            session_id=str(session_id),
            workflow_id=workflow_id,
            status="triggered",
            message="Pre-session processing pipeline created",
        )
    finally:
        session.close()


# =============================================================================
# Dual Output Endpoint
# =============================================================================

class DualOutput(BaseModel):
    """Combined output for both therapist and client."""
    session_id: str
    clinical_brief: Optional[ClinicalBrief] = None
    client_guide: Optional[ClientGuide] = None
    status: str


@router.get("/dual-output", response_model=DualOutput)
async def get_dual_output(
    session_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> DualOutput:
    """
    Get both outputs if authorized.

    Therapists can see both clinical brief and client guide.
    Clients can only see client guide.
    """
    session_id_str = str(session_id)

    # Get client guide (always available)
    client_guide = await get_client_guide(session_id, x_user_id)

    # Get clinical brief (therapist only)
    clinical_brief = None
    if x_user_role == "therapist":
        clinical_brief = await get_clinical_brief(
            session_id, x_user_id, x_user_role
        )

    return DualOutput(
        session_id=session_id_str,
        clinical_brief=clinical_brief,
        client_guide=client_guide,
        status="completed",
    )
