"""
Merged Frameworks API Endpoints

Provides endpoints for couples merge workflow:
- Trigger merge operation
- Get merged frameworks
- Get merge history
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field

from src.services.merge_engine import (
    MergeEngine,
    MergedFrameworks,
    MergeAuditEntry,
    MergeEngineError,
)
from src.services.couple_manager import CoupleManager
from src.agents.schemas.rung_output import RungAnalysisOutput, FrameworkIdentified


router = APIRouter(prefix="/couples/{link_id}", tags=["merged-frameworks"])


# =============================================================================
# Request/Response Models
# =============================================================================

class MergeRequest(BaseModel):
    """Request to trigger a merge operation."""
    session_id: str = Field(..., description="Session ID triggering the merge")
    partner_a_analysis: dict = Field(
        ...,
        description="Rung analysis output for partner A"
    )
    partner_b_analysis: dict = Field(
        ...,
        description="Rung analysis output for partner B"
    )


class MergedFrameworksResponse(BaseModel):
    """Response with merged framework data."""
    id: str
    couple_link_id: str
    session_id: str
    partner_a_frameworks: list[str]
    partner_b_frameworks: list[str]
    overlapping_themes: list[str]
    complementary_patterns: list[str]
    potential_conflicts: list[str]
    suggested_focus_areas: list[str]
    couples_exercises: list[str]
    match_summary: str
    created_at: str


class MergeHistoryResponse(BaseModel):
    """Response with merge history."""
    couple_link_id: str
    total_merges: int
    merges: list[dict]


class AuditLogResponse(BaseModel):
    """Response with audit log entries."""
    couple_link_id: str
    total_entries: int
    entries: list[dict]


# =============================================================================
# Module-level services (for dependency injection)
# =============================================================================

_merge_engine: Optional[MergeEngine] = None
_merged_frameworks_store: dict[str, list[MergedFrameworks]] = {}


def get_merge_engine() -> MergeEngine:
    """Get or create merge engine."""
    global _merge_engine
    if _merge_engine is None:
        _merge_engine = MergeEngine()
    return _merge_engine


def set_merge_engine(engine: MergeEngine) -> None:
    """Set merge engine (for testing)."""
    global _merge_engine
    _merge_engine = engine


def _store_merged_frameworks(merged: MergedFrameworks) -> None:
    """Store merged frameworks (in-memory for now)."""
    if merged.couple_link_id not in _merged_frameworks_store:
        _merged_frameworks_store[merged.couple_link_id] = []
    _merged_frameworks_store[merged.couple_link_id].append(merged)


def _get_merged_frameworks(
    couple_link_id: str,
    session_id: Optional[str] = None,
) -> list[MergedFrameworks]:
    """Get stored merged frameworks."""
    frameworks = _merged_frameworks_store.get(couple_link_id, [])
    if session_id:
        frameworks = [f for f in frameworks if f.session_id == session_id]
    return frameworks


# =============================================================================
# Helper Functions
# =============================================================================

def _merged_to_response(merged: MergedFrameworks) -> MergedFrameworksResponse:
    """Convert MergedFrameworks to response model."""
    return MergedFrameworksResponse(
        id=merged.id,
        couple_link_id=merged.couple_link_id,
        session_id=merged.session_id,
        partner_a_frameworks=merged.partner_a_frameworks,
        partner_b_frameworks=merged.partner_b_frameworks,
        overlapping_themes=merged.overlapping_themes,
        complementary_patterns=merged.complementary_patterns,
        potential_conflicts=merged.potential_conflicts,
        suggested_focus_areas=merged.suggested_focus_areas,
        couples_exercises=merged.couples_exercises,
        match_summary=merged.match_summary,
        created_at=merged.created_at,
    )


def _parse_rung_analysis(data: dict) -> RungAnalysisOutput:
    """Parse Rung analysis from dict."""
    # Parse frameworks
    frameworks = []
    for fw in data.get("frameworks_identified", []):
        frameworks.append(FrameworkIdentified(
            name=fw.get("name", ""),
            confidence=fw.get("confidence", 0.5),
            evidence=fw.get("evidence", ""),
        ))

    return RungAnalysisOutput(
        frameworks_identified=frameworks,
        defense_mechanisms=data.get("defense_mechanisms", []),
        risk_flags=data.get("risk_flags", []),
        key_themes=data.get("key_themes", []),
        suggested_exploration=data.get("suggested_exploration", []),
        session_questions=data.get("session_questions", []),
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/merge", response_model=MergedFrameworksResponse)
async def trigger_merge(
    link_id: str,
    request: MergeRequest,
    http_request: Request,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> MergedFrameworksResponse:
    """
    Trigger a couples merge operation.

    This endpoint:
    1. Validates therapist authorization
    2. Invokes isolation layer on both analyses
    3. Matches topics between partners
    4. Generates merged insights and exercises
    5. Creates comprehensive audit trail

    SECURITY: Only therapists can trigger merge. Isolation layer is ALWAYS invoked.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can trigger merge operations"
        )

    engine = get_merge_engine()

    # Get client IP for audit
    ip_address = http_request.client.host if http_request.client else "unknown"

    try:
        # Parse Rung analyses
        partner_a = _parse_rung_analysis(request.partner_a_analysis)
        partner_b = _parse_rung_analysis(request.partner_b_analysis)

        # Execute merge
        merged = engine.merge(
            couple_link_id=link_id,
            session_id=request.session_id,
            therapist_id=x_user_id,
            partner_a_analysis=partner_a,
            partner_b_analysis=partner_b,
            ip_address=ip_address,
        )

        # Store result
        _store_merged_frameworks(merged)

        return _merged_to_response(merged)

    except MergeEngineError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/merged-frameworks", response_model=MergedFrameworksResponse)
async def get_merged_frameworks(
    link_id: str,
    session_id: Optional[str] = None,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> MergedFrameworksResponse:
    """
    Get the most recent merged frameworks for a couple.

    SECURITY: Only the therapist who owns the couple link can access.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access merged frameworks"
        )

    engine = get_merge_engine()

    # Verify authorization
    try:
        engine.couple_manager.validate_merge_authorization(link_id, x_user_id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Get stored frameworks
    frameworks = _get_merged_frameworks(link_id, session_id)

    if not frameworks:
        raise HTTPException(
            status_code=404,
            detail="No merged frameworks found for this couple"
        )

    # Return most recent
    most_recent = sorted(
        frameworks,
        key=lambda x: x.created_at,
        reverse=True
    )[0]

    return _merged_to_response(most_recent)


@router.get("/merge-history", response_model=MergeHistoryResponse)
async def get_merge_history(
    link_id: str,
    limit: int = 10,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> MergeHistoryResponse:
    """
    Get merge history for a couple.

    SECURITY: Only the therapist who owns the couple link can access.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access merge history"
        )

    engine = get_merge_engine()

    # Verify authorization
    try:
        engine.couple_manager.validate_merge_authorization(link_id, x_user_id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Get stored frameworks
    frameworks = _get_merged_frameworks(link_id)

    # Sort by date descending
    sorted_frameworks = sorted(
        frameworks,
        key=lambda x: x.created_at,
        reverse=True
    )[:limit]

    return MergeHistoryResponse(
        couple_link_id=link_id,
        total_merges=len(frameworks),
        merges=[
            {
                "id": f.id,
                "session_id": f.session_id,
                "overlapping_themes_count": len(f.overlapping_themes),
                "complementary_patterns_count": len(f.complementary_patterns),
                "exercises_count": len(f.couples_exercises),
                "created_at": f.created_at,
            }
            for f in sorted_frameworks
        ],
    )


@router.get("/audit-log", response_model=AuditLogResponse)
async def get_audit_log(
    link_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> AuditLogResponse:
    """
    Get audit log for a couple's merge operations.

    SECURITY: Only the therapist who owns the couple link can access.
    This endpoint supports compliance and forensic review.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access audit logs"
        )

    engine = get_merge_engine()

    # Verify authorization
    try:
        engine.couple_manager.validate_merge_authorization(link_id, x_user_id)
    except Exception as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Get audit entries
    entries = engine.get_audit_log(link_id)

    return AuditLogResponse(
        couple_link_id=link_id,
        total_entries=len(entries),
        entries=[
            {
                "id": e.id,
                "event_type": e.event_type,
                "action": e.action,
                "session_id": e.session_id,
                "isolation_invoked": e.isolation_invoked,
                "result_summary": e.result_summary,
                "error_message": e.error_message,
                "ip_address": e.ip_address,
                "created_at": e.created_at,
            }
            for e in entries
        ],
    )
