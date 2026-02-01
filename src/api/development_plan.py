"""
Development Plan API Endpoints

Provides endpoints for development sprint planning:
- Get current sprint plan
- Generate new sprint plan
- Get sprint history
- Assess progress
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel, Field

from src.services.sprint_planner import (
    SprintPlanner,
    SprintPlan,
    SMARTGoal,
    Exercise,
    SprintPlannerError,
)
from src.services.framework_extractor import FrameworkExtractionOutput
from src.services.perceptor_client import PerceptorClient, PerceptorClientError


router = APIRouter(prefix="/clients/{client_id}", tags=["development-plan"])


# =============================================================================
# Request/Response Models
# =============================================================================

class GoalResponse(BaseModel):
    """A SMART goal in the response."""
    goal: str
    metric: str
    target: str
    timeframe: str = "1-2 weeks"


class ExerciseResponse(BaseModel):
    """An exercise in the response."""
    name: str
    frequency: str
    description: str
    framework: Optional[str] = None


class SprintPlanResponse(BaseModel):
    """Response with sprint plan details."""
    id: str
    client_id: str
    session_id: str
    sprint_number: int
    duration_days: int
    goals: list[GoalResponse]
    exercises: list[ExerciseResponse]
    reflection_prompts: list[str]
    progress_from_last_sprint: Optional[str] = None
    frameworks_addressed: list[str]
    created_at: str


class SprintHistoryResponse(BaseModel):
    """Response with sprint history."""
    client_id: str
    total_sprints: int
    sprints: list[SprintPlanResponse]


class ProgressAssessmentResponse(BaseModel):
    """Response with progress assessment."""
    sprint_id: str
    goals_count: int
    exercises_count: int
    continued_themes: list[str]
    new_themes: list[str]
    breakthroughs_reported: int
    progress_indicators: int
    progress_score: int
    summary: str


class GenerateSprintRequest(BaseModel):
    """Request to generate a new sprint plan."""
    session_id: str = Field(..., description="Session ID to base plan on")
    frameworks_discussed: list[str] = Field(default_factory=list)
    modalities_used: list[str] = Field(default_factory=list)
    breakthroughs: list[str] = Field(default_factory=list)
    progress_indicators: list[str] = Field(default_factory=list)
    areas_for_next_session: list[str] = Field(default_factory=list)
    session_summary: Optional[str] = None
    use_quick_plan: bool = Field(
        default=False,
        description="Use quick planning (no AI call)"
    )


class GenerateSprintResponse(BaseModel):
    """Response from sprint generation."""
    sprint: SprintPlanResponse
    archived_to_perceptor: bool
    message: str


# =============================================================================
# Module-level services (for dependency injection)
# =============================================================================

_sprint_planner: Optional[SprintPlanner] = None
_perceptor_client: Optional[PerceptorClient] = None


def get_sprint_planner() -> SprintPlanner:
    """Get or create sprint planner."""
    global _sprint_planner
    if _sprint_planner is None:
        _sprint_planner = SprintPlanner()
    return _sprint_planner


def set_sprint_planner(planner: SprintPlanner) -> None:
    """Set sprint planner (for testing)."""
    global _sprint_planner
    _sprint_planner = planner


def get_perceptor_client() -> PerceptorClient:
    """Get or create Perceptor client."""
    global _perceptor_client
    if _perceptor_client is None:
        _perceptor_client = PerceptorClient()
    return _perceptor_client


def set_perceptor_client(client: PerceptorClient) -> None:
    """Set Perceptor client (for testing)."""
    global _perceptor_client
    _perceptor_client = client


# =============================================================================
# Helper Functions
# =============================================================================

def _sprint_to_response(sprint: SprintPlan) -> SprintPlanResponse:
    """Convert SprintPlan to response model."""
    return SprintPlanResponse(
        id=sprint.id,
        client_id=sprint.client_id,
        session_id=sprint.session_id,
        sprint_number=sprint.sprint_number,
        duration_days=sprint.duration_days,
        goals=[
            GoalResponse(
                goal=g.goal,
                metric=g.metric,
                target=g.target,
                timeframe=g.timeframe,
            )
            for g in sprint.goals
        ],
        exercises=[
            ExerciseResponse(
                name=e.name,
                frequency=e.frequency,
                description=e.description,
                framework=e.framework,
            )
            for e in sprint.exercises
        ],
        reflection_prompts=sprint.reflection_prompts,
        progress_from_last_sprint=sprint.progress_from_last_sprint,
        frameworks_addressed=sprint.frameworks_addressed,
        created_at=sprint.created_at,
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/development-plan/current", response_model=SprintPlanResponse)
async def get_current_sprint(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> SprintPlanResponse:
    """
    Get the current active sprint plan for a client.

    SECURITY: Both therapists and clients can access.
    """
    perceptor = get_perceptor_client()

    try:
        # Get most recent sprint from Perceptor
        contexts = perceptor.list_contexts(
            tags=["sprint-plan", f"client:{str(client_id)}"],
            limit=1,
        )

        if not contexts:
            raise HTTPException(
                status_code=404,
                detail="No active sprint plan found for this client"
            )

        # Load full context
        context = perceptor.load_context(contexts[0].id)

        # Parse sprint from content (stored as JSON in content field)
        import json
        sprint_data = json.loads(context.content)
        sprint = SprintPlan(**sprint_data)

        return _sprint_to_response(sprint)

    except PerceptorClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/development-plan/generate", response_model=GenerateSprintResponse)
async def generate_sprint_plan(
    client_id: UUID,
    request: GenerateSprintRequest,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> GenerateSprintResponse:
    """
    Generate a new sprint plan based on session extraction.

    SECURITY: Only therapists can generate sprint plans.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can generate sprint plans"
        )

    planner = get_sprint_planner()
    perceptor = get_perceptor_client()

    # Build extraction output
    extraction = FrameworkExtractionOutput(
        frameworks_discussed=request.frameworks_discussed,
        modalities_used=request.modalities_used,
        breakthroughs=request.breakthroughs,
        progress_indicators=request.progress_indicators,
        areas_for_next_session=request.areas_for_next_session,
        session_summary=request.session_summary,
    )

    # Get sprint number from history
    try:
        existing = perceptor.list_contexts(
            tags=["sprint-plan", f"client:{str(client_id)}"],
            limit=100,
        )
        sprint_number = len(existing) + 1
    except PerceptorClientError:
        sprint_number = 1

    # Generate sprint plan
    try:
        if request.use_quick_plan:
            sprint = planner.create_quick_plan(
                client_id=str(client_id),
                session_id=request.session_id,
                extraction=extraction,
                sprint_number=sprint_number,
            )
        else:
            sprint = planner.create_sprint_plan(
                client_id=str(client_id),
                session_id=request.session_id,
                extraction=extraction,
                sprint_number=sprint_number,
            )
    except SprintPlannerError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Archive to Perceptor
    archived = False
    try:
        import json
        perceptor.save_context(
            title=f"Sprint Plan #{sprint_number} - {sprint.created_at[:10]}",
            content=json.dumps(sprint.model_dump()),
            summary=f"Development sprint with {len(sprint.goals)} goals and {len(sprint.exercises)} exercises",
            tags=["sprint-plan", "development"],
            client_id=str(client_id),
            session_id=request.session_id,
            agent="rung",
            stage="post-session",
        )
        archived = True
    except PerceptorClientError:
        pass  # Non-critical failure

    return GenerateSprintResponse(
        sprint=_sprint_to_response(sprint),
        archived_to_perceptor=archived,
        message=f"Sprint #{sprint_number} generated successfully",
    )


@router.get("/development-plan/history", response_model=SprintHistoryResponse)
async def get_sprint_history(
    client_id: UUID,
    limit: int = 10,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> SprintHistoryResponse:
    """
    Get sprint plan history for a client.

    SECURITY: Only therapists can access full history.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Sprint history is only accessible to therapists"
        )

    perceptor = get_perceptor_client()

    try:
        contexts = perceptor.list_contexts(
            tags=["sprint-plan", f"client:{str(client_id)}"],
            limit=limit,
        )

        sprints = []
        for ctx_summary in contexts:
            try:
                context = perceptor.load_context(ctx_summary.id)
                import json
                sprint_data = json.loads(context.content)
                sprint = SprintPlan(**sprint_data)
                sprints.append(_sprint_to_response(sprint))
            except Exception:
                continue  # Skip invalid entries

        return SprintHistoryResponse(
            client_id=str(client_id),
            total_sprints=len(sprints),
            sprints=sprints,
        )

    except PerceptorClientError as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/development-plan/{sprint_id}/progress",
    response_model=ProgressAssessmentResponse
)
async def assess_sprint_progress(
    client_id: UUID,
    sprint_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ProgressAssessmentResponse:
    """
    Assess progress on a specific sprint.

    SECURITY: Only therapists can access progress assessment.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Progress assessment is only accessible to therapists"
        )

    # This would typically load from database and compare
    # For now, return a placeholder assessment
    return ProgressAssessmentResponse(
        sprint_id=sprint_id,
        goals_count=3,
        exercises_count=4,
        continued_themes=["attachment", "communication"],
        new_themes=["mindfulness"],
        breakthroughs_reported=1,
        progress_indicators=2,
        progress_score=65,
        summary="Steady progress with 1 breakthrough achieved. Continued work on attachment and communication patterns.",
    )


@router.get("/longitudinal-patterns")
async def get_longitudinal_patterns(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> dict:
    """
    Get longitudinal pattern analysis for a client.

    SECURITY: Only therapists can access pattern analysis.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Pattern analysis is only accessible to therapists"
        )

    perceptor = get_perceptor_client()

    try:
        patterns = perceptor.get_longitudinal_patterns(str(client_id))
        return patterns
    except PerceptorClientError as e:
        raise HTTPException(status_code=500, detail=str(e))
