"""
Reading List API Endpoints

Provides endpoints for managing client reading lists:
- Add reading items (articles, books)
- List and filter reading items
- Get item details with decrypted notes
- Update item status and flags
- Soft delete items
- Therapist assigns reading to client
- Get items flagged for session discussion
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Header, Query
from pydantic import BaseModel, Field

from src.models.reading_item import (
    ReadingItemAssign,
    ReadingItemCreate,
    ReadingItemDetail,
    ReadingItemRead,
    ReadingItemUpdate,
    ReadingStatus,
)
from src.services.reading_list import ReadingListService, ReadingListError


router = APIRouter(prefix="/clients/{client_id}/reading-list", tags=["reading-list"])


# =============================================================================
# Module-level services (for dependency injection)
# =============================================================================

_reading_list_service: Optional[ReadingListService] = None


def get_reading_list_service() -> ReadingListService:
    """Get or create reading list service."""
    global _reading_list_service
    if _reading_list_service is None:
        _reading_list_service = ReadingListService()
    return _reading_list_service


def set_reading_list_service(service: ReadingListService) -> None:
    """Set reading list service (for testing)."""
    global _reading_list_service
    _reading_list_service = service


# =============================================================================
# Response Models
# =============================================================================

class ReadingItemListResponse(BaseModel):
    """Response for listing reading items."""
    items: list[ReadingItemRead]
    count: int


class ForSessionResponse(BaseModel):
    """Response for items flagged for session discussion."""
    items: list[ReadingItemRead]
    count: int
    context_text: Optional[str] = Field(
        None, description="Formatted text for pre-session pipeline"
    )


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/", response_model=ReadingItemRead)
async def add_reading_item(
    client_id: UUID,
    data: ReadingItemCreate,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="client"),
) -> ReadingItemRead:
    """
    Add a reading item to a client's reading list.

    SECURITY: Client can add to own list. Therapist can add to owned client's list.
    """
    service = get_reading_list_service()

    try:
        return service.add_item(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            data=data,
        )
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=ReadingItemListResponse)
async def list_reading_items(
    client_id: UUID,
    status: Optional[ReadingStatus] = Query(None, description="Filter by reading status"),
    discuss_only: bool = Query(False, description="Only items flagged for discussion"),
    assignments_only: bool = Query(False, description="Only therapist-assigned items"),
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="client"),
) -> ReadingItemListResponse:
    """
    List reading items for a client (notes NOT decrypted in list view).

    SECURITY: Client sees own items. Therapist sees owned client's items.
    """
    service = get_reading_list_service()

    try:
        items = service.list_items(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            status=status,
            discuss_only=discuss_only,
            assignments_only=assignments_only,
        )
        return ReadingItemListResponse(items=items, count=len(items))
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/for-session", response_model=ForSessionResponse)
async def get_for_session(
    client_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ForSessionResponse:
    """
    Get reading items flagged for session discussion with pipeline context.

    SECURITY: Only therapists can access the pre-session view.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can access pre-session reading context"
        )

    service = get_reading_list_service()

    try:
        items = service.list_items(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            discuss_only=True,
        )

        context_text = service.get_session_reading_context(str(client_id))

        return ForSessionResponse(
            items=items,
            count=len(items),
            context_text=context_text,
        )
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{item_id}", response_model=ReadingItemDetail)
async def get_reading_item(
    client_id: UUID,
    item_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="client"),
) -> ReadingItemDetail:
    """
    Get a single reading item with decrypted notes.

    SECURITY: Client sees own items. Therapist sees owned client's items.
    """
    service = get_reading_list_service()

    try:
        return service.get_item(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            item_id=str(item_id),
        )
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{item_id}", response_model=ReadingItemRead)
async def update_reading_item(
    client_id: UUID,
    item_id: UUID,
    data: ReadingItemUpdate,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="client"),
) -> ReadingItemRead:
    """
    Update a reading item (notes, status, discuss flag).

    SECURITY: Client can update own items. Therapist can update owned client's items.
    """
    service = get_reading_list_service()

    try:
        return service.update_item(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            item_id=str(item_id),
            data=data,
        )
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{item_id}")
async def delete_reading_item(
    client_id: UUID,
    item_id: UUID,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="client"),
) -> dict:
    """
    Soft delete a reading item (preserved for audit trail).

    SECURITY: Client can delete own items. Therapist can delete owned client's items.
    """
    service = get_reading_list_service()

    try:
        service.delete_item(
            user_id=x_user_id,
            user_role=x_user_role,
            client_id=str(client_id),
            item_id=str(item_id),
        )
        return {"status": "deleted", "item_id": str(item_id)}
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign", response_model=ReadingItemRead)
async def assign_reading(
    client_id: UUID,
    data: ReadingItemAssign,
    x_user_id: str = Header(...),
    x_user_role: str = Header(default="therapist"),
) -> ReadingItemRead:
    """
    Therapist assigns reading to a client as homework.

    SECURITY: Only therapists can assign reading.
    """
    if x_user_role != "therapist":
        raise HTTPException(
            status_code=403,
            detail="Only therapists can assign reading"
        )

    service = get_reading_list_service()

    try:
        return service.assign_item(
            therapist_id=x_user_id,
            client_id=str(client_id),
            data=data,
        )
    except ReadingListError as e:
        if "Access denied" in str(e):
            raise HTTPException(status_code=403, detail=str(e))
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=500, detail=str(e))
