"""
Pre-Session API Endpoints

Provides endpoints for pre-session workflow status and outputs:
- Clinical Brief (therapist only)
- Client Guide (client only)
- Workflow status
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field


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
    # TODO: Implement database lookup
    # For now, return mock status
    return PreSessionStatus(
        session_id=str(session_id),
        status="pending",
        voice_memo_uploaded=False,
        transcription_complete=False,
        rung_analysis_complete=False,
        beth_generation_complete=False,
    )


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

    # TODO: Implement database lookup and Rung output retrieval
    # For now, return mock data
    return ClinicalBrief(
        session_id=str(session_id),
        frameworks_identified=[],
        defense_mechanisms=[],
        risk_flags=[],
        key_themes=["Processing emotions", "Communication patterns"],
        suggested_exploration=["Attachment history"],
        session_questions=["What comes up when you think about that?"],
        analysis_confidence=0.85,
    )


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
    # TODO: Implement database lookup and Beth output retrieval
    # For now, return mock data
    return ClientGuide(
        session_id=str(session_id),
        session_prep="Your session is coming up! Take a moment to think about what's been on your mind lately.",
        discussion_points=[
            "Any moments this week that stood out to you",
            "How you've been feeling in your relationships",
        ],
        reflection_questions=[
            "What's been taking up most of your mental energy?",
            "Have you noticed any patterns in how you've been feeling?",
        ],
        exercises=[
            "Try journaling for 5 minutes about your week",
            "Take a few deep breaths before your session",
        ],
    )


@router.post("/trigger", response_model=TriggerResponse)
async def trigger_pre_session(
    session_id: UUID,
    request: TriggerRequest,
    x_user_id: str = Header(...),
) -> TriggerResponse:
    """
    Trigger pre-session processing workflow.

    Starts the n8n workflow to process voice memo,
    run Rung analysis, and generate Beth output.
    """
    # TODO: Implement n8n webhook trigger
    # For now, return mock response
    return TriggerResponse(
        session_id=str(session_id),
        workflow_id="mock-workflow-id",
        status="triggered",
        message="Pre-session processing started",
    )


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
