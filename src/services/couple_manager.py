"""
Couple Manager Service

Manages couple links between clients:
- Link creation with validation
- Link status management
- Therapist authorization checks
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class CoupleLinkStatus(str, Enum):
    """Status of a couple link."""
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


class CoupleLink(BaseModel):
    """A link between two clients in couples therapy."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    partner_a_id: str = Field(..., description="Client ID of partner A")
    partner_b_id: str = Field(..., description="Client ID of partner B")
    therapist_id: str = Field(..., description="Shared therapist ID")
    status: CoupleLinkStatus = Field(default=CoupleLinkStatus.ACTIVE)
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    notes: Optional[str] = Field(None, description="Therapist notes about the link")

    @field_validator("partner_a_id", "partner_b_id", "therapist_id")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        """Validate that ID is a valid UUID."""
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID: {v}")
        return v

    def model_post_init(self, __context) -> None:
        """Ensure partner_a_id < partner_b_id to prevent duplicates."""
        if self.partner_a_id > self.partner_b_id:
            # Swap to maintain canonical order
            self.partner_a_id, self.partner_b_id = (
                self.partner_b_id,
                self.partner_a_id,
            )


class CoupleLinkRequest(BaseModel):
    """Request to create a couple link."""
    partner_a_id: str = Field(..., description="Client ID of partner A")
    partner_b_id: str = Field(..., description="Client ID of partner B")
    notes: Optional[str] = Field(None, description="Optional notes")


class CoupleLinkUpdate(BaseModel):
    """Request to update a couple link."""
    status: Optional[CoupleLinkStatus] = None
    notes: Optional[str] = None


class CoupleManagerError(Exception):
    """Exception for couple manager errors."""
    pass


class CoupleManager:
    """
    Manages couple links between clients.

    Enforces:
    - Same therapist requirement
    - Different clients requirement
    - No duplicate links
    - Proper authorization
    """

    def __init__(self, storage: Optional[dict] = None):
        """
        Initialize couple manager.

        Args:
            storage: Optional storage dict (for testing). In production,
                    this would be a database connection.
        """
        # In-memory storage for now; replace with DB in production
        self._links: dict[str, CoupleLink] = storage if storage is not None else {}
        self._clients: dict[str, dict] = {}  # client_id -> {therapist_id, ...}

    def register_client(
        self,
        client_id: str,
        therapist_id: str,
    ) -> None:
        """
        Register a client with their therapist.

        Args:
            client_id: Client ID
            therapist_id: Therapist ID
        """
        try:
            UUID(client_id)
            UUID(therapist_id)
        except ValueError as e:
            raise CoupleManagerError(f"Invalid UUID: {e}")

        self._clients[client_id] = {"therapist_id": therapist_id}

    def create_link(
        self,
        partner_a_id: str,
        partner_b_id: str,
        therapist_id: str,
        notes: Optional[str] = None,
    ) -> CoupleLink:
        """
        Create a couple link between two clients.

        Args:
            partner_a_id: Client ID of partner A
            partner_b_id: Client ID of partner B
            therapist_id: Therapist creating the link
            notes: Optional therapist notes

        Returns:
            Created CoupleLink

        Raises:
            CoupleManagerError: If validation fails
        """
        # Validate UUIDs
        try:
            UUID(partner_a_id)
            UUID(partner_b_id)
            UUID(therapist_id)
        except ValueError as e:
            raise CoupleManagerError(f"Invalid UUID: {e}")

        # Validate different clients
        if partner_a_id == partner_b_id:
            raise CoupleManagerError("Cannot link a client to themselves")

        # Validate same therapist (if clients registered)
        if partner_a_id in self._clients:
            if self._clients[partner_a_id]["therapist_id"] != therapist_id:
                raise CoupleManagerError(
                    "Partner A is not a client of this therapist"
                )

        if partner_b_id in self._clients:
            if self._clients[partner_b_id]["therapist_id"] != therapist_id:
                raise CoupleManagerError(
                    "Partner B is not a client of this therapist"
                )

        # Check for existing link
        existing = self.find_link(partner_a_id, partner_b_id)
        if existing:
            raise CoupleManagerError(
                f"Link already exists: {existing.id}"
            )

        # Create link
        link = CoupleLink(
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            therapist_id=therapist_id,
            notes=notes,
        )

        self._links[link.id] = link
        return link

    def get_link(self, link_id: str) -> CoupleLink:
        """
        Get a couple link by ID.

        Args:
            link_id: Link ID

        Returns:
            CoupleLink

        Raises:
            CoupleManagerError: If link not found
        """
        if link_id not in self._links:
            raise CoupleManagerError(f"Link not found: {link_id}")
        return self._links[link_id]

    def find_link(
        self,
        partner_a_id: str,
        partner_b_id: str,
    ) -> Optional[CoupleLink]:
        """
        Find a link between two specific partners.

        Args:
            partner_a_id: Client ID of partner A
            partner_b_id: Client ID of partner B

        Returns:
            CoupleLink if found, None otherwise
        """
        # Normalize order
        if partner_a_id > partner_b_id:
            partner_a_id, partner_b_id = partner_b_id, partner_a_id

        for link in self._links.values():
            if (link.partner_a_id == partner_a_id and
                link.partner_b_id == partner_b_id):
                return link
        return None

    def update_link(
        self,
        link_id: str,
        therapist_id: str,
        update: CoupleLinkUpdate,
    ) -> CoupleLink:
        """
        Update a couple link.

        Args:
            link_id: Link ID to update
            therapist_id: Therapist making the update (must match)
            update: Update data

        Returns:
            Updated CoupleLink

        Raises:
            CoupleManagerError: If link not found or unauthorized
        """
        link = self.get_link(link_id)

        # Verify therapist authorization
        if link.therapist_id != therapist_id:
            raise CoupleManagerError(
                "Not authorized to update this link"
            )

        # Apply updates
        if update.status is not None:
            link.status = update.status

        if update.notes is not None:
            link.notes = update.notes

        link.updated_at = datetime.utcnow().isoformat()

        return link

    def get_links_for_therapist(
        self,
        therapist_id: str,
        status: Optional[CoupleLinkStatus] = None,
    ) -> list[CoupleLink]:
        """
        Get all links for a therapist.

        Args:
            therapist_id: Therapist ID
            status: Optional status filter

        Returns:
            List of CoupleLinks
        """
        links = [
            link for link in self._links.values()
            if link.therapist_id == therapist_id
        ]

        if status:
            links = [link for link in links if link.status == status]

        return links

    def get_links_for_client(
        self,
        client_id: str,
        status: Optional[CoupleLinkStatus] = None,
    ) -> list[CoupleLink]:
        """
        Get all links involving a specific client.

        Args:
            client_id: Client ID
            status: Optional status filter

        Returns:
            List of CoupleLinks
        """
        links = [
            link for link in self._links.values()
            if client_id in (link.partner_a_id, link.partner_b_id)
        ]

        if status:
            links = [link for link in links if link.status == status]

        return links

    def terminate_link(
        self,
        link_id: str,
        therapist_id: str,
    ) -> CoupleLink:
        """
        Terminate a couple link.

        Args:
            link_id: Link ID to terminate
            therapist_id: Therapist making the termination

        Returns:
            Terminated CoupleLink
        """
        return self.update_link(
            link_id,
            therapist_id,
            CoupleLinkUpdate(status=CoupleLinkStatus.TERMINATED),
        )

    def pause_link(
        self,
        link_id: str,
        therapist_id: str,
    ) -> CoupleLink:
        """
        Pause a couple link.

        Args:
            link_id: Link ID to pause
            therapist_id: Therapist making the pause

        Returns:
            Paused CoupleLink
        """
        return self.update_link(
            link_id,
            therapist_id,
            CoupleLinkUpdate(status=CoupleLinkStatus.PAUSED),
        )

    def reactivate_link(
        self,
        link_id: str,
        therapist_id: str,
    ) -> CoupleLink:
        """
        Reactivate a paused couple link.

        Args:
            link_id: Link ID to reactivate
            therapist_id: Therapist making the reactivation

        Returns:
            Reactivated CoupleLink
        """
        return self.update_link(
            link_id,
            therapist_id,
            CoupleLinkUpdate(status=CoupleLinkStatus.ACTIVE),
        )

    def validate_merge_authorization(
        self,
        link_id: str,
        therapist_id: str,
    ) -> bool:
        """
        Validate that a therapist can perform a merge for a couple.

        Args:
            link_id: Couple link ID
            therapist_id: Therapist requesting merge

        Returns:
            True if authorized

        Raises:
            CoupleManagerError: If not authorized
        """
        link = self.get_link(link_id)

        if link.therapist_id != therapist_id:
            raise CoupleManagerError(
                "Not authorized for this couple link"
            )

        if link.status != CoupleLinkStatus.ACTIVE:
            raise CoupleManagerError(
                f"Link is not active: {link.status.value}"
            )

        return True
