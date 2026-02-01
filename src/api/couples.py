"""
Couples API Endpoints

Provides endpoints for couple linking and management:
- Create couple link
- Get couple link
- Update couple link status
- List therapist's couples
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, Field

from src.services.couple_manager import (
    CoupleManager,
    CoupleLink,
    CoupleLinkStatus,
    CoupleLinkRequest,
    CoupleLinkUpdate,
    CoupleManagerError,
)


router = APIRouter(prefix="/couples", tags=["couples"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateCoupleLinkRequest(BaseModel):
    """Request to create a couple link."""
    partner_a_id: str = Field(..., description="Client ID of partner A")
    partner_b_id: str = Field(..., description="Client ID of partner B")
    notes: Optional[str] = Field(None, description="Optional therapist notes")


class CoupleLinkResponse(BaseModel):
    """Response with couple link details."""
    id: str
    partner_a_id: str
    partner_b_id: str
    therapist_id: str
    status: str
    created_at: str
    updated_at: str
    notes: Optional[str] = None


class UpdateCoupleLinkRequest(BaseModel):
    """Request to update a couple link."""
    status: Optional[str] = Field(
        None,
        description="New status: active, paused, terminated"
    )
    notes: Optional[str] = Field(None, description="Updated notes")


class CoupleListResponse(BaseModel):
    """Response with list of couple links."""
    therapist_id: str
    total: int
    couples: list[CoupleLinkResponse]


# =============================================================================
# Module-level manager (for dependency injection)
# =============================================================================

_couple_manager: Optional[CoupleManager] = None


def get_couple_manager() -> CoupleManager:
    """Get or create couple manager."""
    global _couple_manager
    if _couple_manager is None:
        _couple_manager = CoupleManager()
    return _couple_manager


def set_couple_manager(manager: CoupleManager) -> None:
    """Set couple manager (for testing)."""
    global _couple_manager
    _couple_manager = manager


# =============================================================================
# Helper Functions
# =============================================================================

def _link_to_response(link: CoupleLink) -> CoupleLinkResponse:
    """Convert CoupleLink to response model."""
    return CoupleLinkResponse(
        id=link.id,
        partner_a_id=link.partner_a_id,
        partner_b_id=link.partner_b_id,
        therapist_id=link.therapist_id,
        status=link.status.value,
        created_at=link.created_at,
        updated_at=link.updated_at,
        notes=link.notes,
    )


def _validate_status(status_str: str) -> CoupleLinkStatus:
    """Validate and convert status string."""
    try:
        return CoupleLinkStatus(status_str.lower())
    except ValueError:
        valid = [s.value for s in CoupleLinkStatus]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid}"
        )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", response_model=CoupleLinkResponse)
async def create_couple_link(
    request: CreateCoupleLinkRequest,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Create a couple link between two clients.

    SECURITY: Only therapists can create couple links.
    Both clients must belong to the requesting therapist.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can create couple links"
        )

    manager = get_couple_manager()

    try:
        link = manager.create_link(
            partner_a_id=request.partner_a_id,
            partner_b_id=request.partner_b_id,
            therapist_id=x_user_id,
            notes=request.notes,
        )
        return _link_to_response(link)

    except CoupleManagerError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{link_id}", response_model=CoupleLinkResponse)
async def get_couple_link(
    link_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Get a couple link by ID.

    SECURITY: Only the therapist who created the link can access it.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access couple links"
        )

    manager = get_couple_manager()

    try:
        link = manager.get_link(link_id)

        # Verify authorization
        if link.therapist_id != x_user_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this couple link"
            )

        return _link_to_response(link)

    except CoupleManagerError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{link_id}", response_model=CoupleLinkResponse)
async def update_couple_link(
    link_id: str,
    request: UpdateCoupleLinkRequest,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Update a couple link.

    SECURITY: Only the therapist who created the link can update it.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can update couple links"
        )

    manager = get_couple_manager()

    # Build update
    update = CoupleLinkUpdate()

    if request.status:
        update.status = _validate_status(request.status)

    if request.notes is not None:
        update.notes = request.notes

    try:
        link = manager.update_link(
            link_id=link_id,
            therapist_id=x_user_id,
            update=update,
        )
        return _link_to_response(link)

    except CoupleManagerError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "not authorized" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=CoupleListResponse)
async def list_couple_links(
    status: Optional[str] = None,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleListResponse:
    """
    List all couple links for the requesting therapist.

    SECURITY: Only returns links belonging to the requesting therapist.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can list couple links"
        )

    manager = get_couple_manager()

    # Convert status filter
    status_filter = None
    if status:
        status_filter = _validate_status(status)

    links = manager.get_links_for_therapist(
        therapist_id=x_user_id,
        status=status_filter,
    )

    return CoupleListResponse(
        therapist_id=x_user_id,
        total=len(links),
        couples=[_link_to_response(link) for link in links],
    )


@router.post("/{link_id}/pause", response_model=CoupleLinkResponse)
async def pause_couple_link(
    link_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Pause a couple link.

    SECURITY: Only the therapist who created the link can pause it.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can pause couple links"
        )

    manager = get_couple_manager()

    try:
        link = manager.pause_link(link_id, x_user_id)
        return _link_to_response(link)

    except CoupleManagerError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "not authorized" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{link_id}/reactivate", response_model=CoupleLinkResponse)
async def reactivate_couple_link(
    link_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Reactivate a paused couple link.

    SECURITY: Only the therapist who created the link can reactivate it.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can reactivate couple links"
        )

    manager = get_couple_manager()

    try:
        link = manager.reactivate_link(link_id, x_user_id)
        return _link_to_response(link)

    except CoupleManagerError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "not authorized" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{link_id}/terminate", response_model=CoupleLinkResponse)
async def terminate_couple_link(
    link_id: str,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> CoupleLinkResponse:
    """
    Terminate a couple link.

    SECURITY: Only the therapist who created the link can terminate it.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can terminate couple links"
        )

    manager = get_couple_manager()

    try:
        link = manager.terminate_link(link_id, x_user_id)
        return _link_to_response(link)

    except CoupleManagerError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        if "not authorized" in str(e).lower():
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
