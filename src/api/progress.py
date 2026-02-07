"""
Progress Analytics API Endpoints

Provides endpoints for tracking and viewing client progress:
- Get progress summary (session engagement trends)
- Get framework usage trends
- Get comprehensive analytics summary
"""

from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from src.services.progress_analytics import ProgressAnalytics


router = APIRouter(prefix="/clients/{client_id}/progress", tags=["progress"])


# =============================================================================
# Response Models
# =============================================================================

class ProgressMetricResponse(BaseModel):
    """A single progress metric in the response."""
    id: str
    client_id: str
    session_id: Optional[str] = None
    metric_type: str
    value: float
    metadata_json: Optional[dict[str, Any]] = None
    measured_at: str
    created_at: str


class ProgressSummaryResponse(BaseModel):
    """Response with session progress summary."""
    client_id: str
    total_sessions: int
    recent_sessions: int
    engagement_trend: str
    metrics: list[dict[str, Any]] = Field(default_factory=list)


class FrameworkTrendsResponse(BaseModel):
    """Response with framework usage trends."""
    client_id: str
    frameworks: dict[str, int] = Field(default_factory=dict)
    primary_framework: Optional[str] = None
    framework_diversity: float = 0.0
    recent_frameworks: list[str] = Field(default_factory=list)


class SprintCompletionResponse(BaseModel):
    """Response with sprint completion data."""
    client_id: str
    total_sprints: int
    completed_sprints: int
    completion_rate: float
    current_sprint_progress: float
    trend: str


class AnalyticsSummaryResponse(BaseModel):
    """Response with full analytics summary."""
    client_id: str
    session_progress: dict[str, Any]
    framework_trends: dict[str, Any]
    sprint_completion: dict[str, Any]
    overall_trajectory: str
    generated_at: str


# =============================================================================
# Module-level service (for dependency injection)
# =============================================================================

_analytics_service: Optional[ProgressAnalytics] = None


def get_analytics_service() -> ProgressAnalytics:
    """Get or create analytics service."""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = ProgressAnalytics()
    return _analytics_service


def set_analytics_service(service: ProgressAnalytics) -> None:
    """Set analytics service (for testing)."""
    global _analytics_service
    _analytics_service = service


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ProgressSummaryResponse:
    """
    Get session-over-session progress summary for a client.

    SECURITY: Only therapists can access progress data.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access progress data"
        )

    service = get_analytics_service()

    try:
        result = service.calculate_session_progress(str(client_id))

        # Convert ProgressMetricRead objects to dicts for JSON serialization
        metrics = []
        for m in result.get("metrics", []):
            if hasattr(m, "model_dump"):
                metrics.append(m.model_dump(mode="json"))
            else:
                metrics.append(m)

        return ProgressSummaryResponse(
            client_id=result["client_id"],
            total_sessions=result["total_sessions"],
            recent_sessions=result["recent_sessions"],
            engagement_trend=result["engagement_trend"],
            metrics=metrics,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends", response_model=FrameworkTrendsResponse)
async def get_framework_trends(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> FrameworkTrendsResponse:
    """
    Get framework usage trends for a client.

    SECURITY: Only therapists can access framework trend data.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access framework trends"
        )

    service = get_analytics_service()

    try:
        result = service.calculate_framework_trends(str(client_id))

        return FrameworkTrendsResponse(
            client_id=result["client_id"],
            frameworks=result["frameworks"],
            primary_framework=result["primary_framework"],
            framework_diversity=result["framework_diversity"],
            recent_frameworks=result["recent_frameworks"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary", response_model=AnalyticsSummaryResponse)
async def get_analytics_summary(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> AnalyticsSummaryResponse:
    """
    Get full analytics summary for a client.

    Combines session progress, framework trends, and sprint completion
    into a comprehensive view with an overall trajectory assessment.

    SECURITY: Only therapists can access analytics summaries.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access analytics summaries"
        )

    service = get_analytics_service()

    try:
        result = service.generate_analytics_summary(str(client_id))

        return AnalyticsSummaryResponse(
            client_id=result["client_id"],
            session_progress=result["session_progress"],
            framework_trends=result["framework_trends"],
            sprint_completion=result["sprint_completion"],
            overall_trajectory=result["overall_trajectory"],
            generated_at=result["generated_at"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
