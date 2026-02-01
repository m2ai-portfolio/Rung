"""
Merge Engine Service

Orchestrates the couples merge workflow:
1. Validates merge authorization
2. Fetches partner analyses (isolated)
3. Matches topics between partners
4. Generates merged insights
5. Creates comprehensive audit trail
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.services.isolation_layer import (
    IsolationLayer,
    IsolatedFrameworks,
    isolate_for_couples_merge,
    IsolationViolation,
)
from src.services.topic_matcher import (
    TopicMatcher,
    TopicMatchResult,
    match_couple_topics,
)
from src.services.couple_manager import (
    CoupleManager,
    CoupleLink,
    CoupleManagerError,
)
from src.agents.schemas.rung_output import RungAnalysisOutput


class MergedFrameworks(BaseModel):
    """Output from couples merge operation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    couple_link_id: str = Field(..., description="Couple link ID")
    session_id: str = Field(..., description="Session ID that triggered merge")
    partner_a_frameworks: list[str] = Field(
        default_factory=list,
        description="Partner A framework names only"
    )
    partner_b_frameworks: list[str] = Field(
        default_factory=list,
        description="Partner B framework names only"
    )
    overlapping_themes: list[str] = Field(
        default_factory=list,
        description="Themes shared between partners"
    )
    complementary_patterns: list[str] = Field(
        default_factory=list,
        description="Complementary dynamics identified"
    )
    potential_conflicts: list[str] = Field(
        default_factory=list,
        description="Potential conflict areas"
    )
    suggested_focus_areas: list[str] = Field(
        default_factory=list,
        description="Suggested areas for couples work"
    )
    couples_exercises: list[str] = Field(
        default_factory=list,
        description="Recommended couples exercises"
    )
    match_summary: str = Field(
        default="",
        description="Summary of the match analysis"
    )
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class MergeAuditEntry(BaseModel):
    """Audit log entry for merge operation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: str = Field(default="couples_merge")
    couple_link_id: str
    session_id: str
    therapist_id: str
    action: str = Field(..., description="merge_initiated|merge_completed|merge_failed")
    partner_a_id: str
    partner_b_id: str
    isolation_invoked: bool = Field(default=True)
    frameworks_accessed: dict = Field(
        default_factory=dict,
        description="Record of what data was accessed"
    )
    result_summary: Optional[str] = None
    error_message: Optional[str] = None
    ip_address: str = Field(default="unknown")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )


class MergeEngineError(Exception):
    """Exception for merge engine errors."""
    pass


# Couples exercises based on common patterns
COUPLES_EXERCISES = {
    "anxious-avoidant": [
        "Attachment awareness dialogue",
        "Safe haven practice",
        "Needs expression exercise",
        "Comfort vs. closeness negotiation",
    ],
    "communication": [
        "Active listening practice",
        "Soft start-up exercise",
        "Repair conversation template",
        "Weekly check-in ritual",
    ],
    "conflict": [
        "Time-out protocol",
        "De-escalation breathing",
        "Compromise conversation",
        "Aftermath of conflict discussion",
    ],
    "trust": [
        "Trust-building actions list",
        "Transparency practice",
        "Reliability commitment",
        "Emotional availability check-in",
    ],
    "intimacy": [
        "Love maps questionnaire",
        "Fondness and admiration sharing",
        "Bids for connection practice",
        "Emotional intimacy dialogue",
    ],
}


class MergeEngine:
    """
    Orchestrates couples merge workflow.

    Ensures:
    - Proper authorization before merge
    - Isolation layer is always invoked
    - Complete audit trail
    - No PHI crosses boundaries
    """

    def __init__(
        self,
        couple_manager: Optional[CoupleManager] = None,
        isolation_layer: Optional[IsolationLayer] = None,
        topic_matcher: Optional[TopicMatcher] = None,
    ):
        """
        Initialize merge engine.

        Args:
            couple_manager: Optional pre-configured couple manager
            isolation_layer: Optional pre-configured isolation layer
            topic_matcher: Optional pre-configured topic matcher
        """
        self.couple_manager = couple_manager or CoupleManager()
        self.isolation_layer = isolation_layer or IsolationLayer(strict_mode=True)
        self.topic_matcher = topic_matcher or TopicMatcher()
        self._audit_log: list[MergeAuditEntry] = []

    def merge(
        self,
        couple_link_id: str,
        session_id: str,
        therapist_id: str,
        partner_a_analysis: RungAnalysisOutput,
        partner_b_analysis: RungAnalysisOutput,
        ip_address: str = "unknown",
    ) -> MergedFrameworks:
        """
        Execute couples merge workflow.

        Args:
            couple_link_id: Couple link ID
            session_id: Session ID triggering the merge
            therapist_id: Therapist requesting merge
            partner_a_analysis: Rung analysis for partner A
            partner_b_analysis: Rung analysis for partner B
            ip_address: Request IP for audit

        Returns:
            MergedFrameworks with isolated and matched data

        Raises:
            MergeEngineError: If merge fails
        """
        # Get link for partner IDs
        try:
            link = self.couple_manager.get_link(couple_link_id)
        except CoupleManagerError as e:
            raise MergeEngineError(f"Invalid couple link: {e}")

        # Create initial audit entry
        audit = MergeAuditEntry(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            action="merge_initiated",
            partner_a_id=link.partner_a_id,
            partner_b_id=link.partner_b_id,
            ip_address=ip_address,
        )

        try:
            # Step 1: Validate authorization
            self.couple_manager.validate_merge_authorization(
                couple_link_id, therapist_id
            )

            # Step 2: Isolate frameworks (CRITICAL)
            partner_a_isolated, partner_b_isolated = isolate_for_couples_merge(
                partner_a_analysis,
                partner_b_analysis,
                strict_mode=True,
            )

            audit.isolation_invoked = True
            audit.frameworks_accessed = {
                "partner_a": {
                    "attachment_patterns": partner_a_isolated.attachment_patterns,
                    "frameworks": partner_a_isolated.frameworks_identified,
                    "themes": partner_a_isolated.theme_categories,
                },
                "partner_b": {
                    "attachment_patterns": partner_b_isolated.attachment_patterns,
                    "frameworks": partner_b_isolated.frameworks_identified,
                    "themes": partner_b_isolated.theme_categories,
                },
            }

            # Step 3: Match topics
            match_result = self.topic_matcher.match(
                partner_a_isolated,
                partner_b_isolated,
            )

            # Step 4: Generate exercises based on patterns
            exercises = self._generate_exercises(
                partner_a_isolated,
                partner_b_isolated,
                match_result,
            )

            # Step 5: Build merged output
            merged = MergedFrameworks(
                couple_link_id=couple_link_id,
                session_id=session_id,
                partner_a_frameworks=self._combine_frameworks(partner_a_isolated),
                partner_b_frameworks=self._combine_frameworks(partner_b_isolated),
                overlapping_themes=[
                    m.topic for m in match_result.overlapping_themes
                ],
                complementary_patterns=[
                    m.topic for m in match_result.complementary_patterns
                ],
                potential_conflicts=[
                    m.topic for m in match_result.potential_conflicts
                ],
                suggested_focus_areas=match_result.suggested_focus_areas,
                couples_exercises=exercises,
                match_summary=match_result.match_summary,
            )

            # Update audit for success
            audit.action = "merge_completed"
            audit.result_summary = (
                f"Merged {len(merged.partner_a_frameworks)} + "
                f"{len(merged.partner_b_frameworks)} frameworks. "
                f"Found {len(merged.overlapping_themes)} overlaps, "
                f"{len(merged.complementary_patterns)} complementary patterns."
            )
            self._audit_log.append(audit)

            return merged

        except IsolationViolation as e:
            audit.action = "merge_failed"
            audit.error_message = f"Isolation violation: {str(e)}"
            self._audit_log.append(audit)
            raise MergeEngineError(f"Isolation failed: {e}")

        except CoupleManagerError as e:
            audit.action = "merge_failed"
            audit.error_message = f"Authorization error: {str(e)}"
            self._audit_log.append(audit)
            raise MergeEngineError(f"Authorization failed: {e}")

        except Exception as e:
            audit.action = "merge_failed"
            audit.error_message = str(e)
            self._audit_log.append(audit)
            raise MergeEngineError(f"Merge failed: {e}")

    def _combine_frameworks(
        self,
        isolated: IsolatedFrameworks,
    ) -> list[str]:
        """Combine all framework-related items into a single list."""
        combined = []
        combined.extend(isolated.attachment_patterns)
        combined.extend(isolated.frameworks_identified)
        combined.extend(isolated.defense_patterns)
        combined.extend(isolated.communication_patterns)
        return list(set(combined))

    def _generate_exercises(
        self,
        partner_a: IsolatedFrameworks,
        partner_b: IsolatedFrameworks,
        match_result: TopicMatchResult,
    ) -> list[str]:
        """Generate relevant couples exercises based on patterns."""
        exercises = []

        # Check for anxious-avoidant dynamic
        a_patterns = set(partner_a.attachment_patterns)
        b_patterns = set(partner_b.attachment_patterns)

        anxious_patterns = {"anxious attachment", "anxious-preoccupied", "attachment anxiety"}
        avoidant_patterns = {"avoidant attachment", "dismissive avoidant", "fearful avoidant"}

        if (a_patterns & anxious_patterns and b_patterns & avoidant_patterns) or \
           (b_patterns & anxious_patterns and a_patterns & avoidant_patterns):
            exercises.extend(COUPLES_EXERCISES["anxious-avoidant"][:2])

        # Check for communication themes
        a_themes = set(partner_a.theme_categories)
        b_themes = set(partner_b.theme_categories)
        all_themes = a_themes | b_themes

        if "communication" in all_themes:
            exercises.extend(COUPLES_EXERCISES["communication"][:2])

        if "trust" in all_themes:
            exercises.extend(COUPLES_EXERCISES["trust"][:2])

        if "intimacy" in all_themes:
            exercises.extend(COUPLES_EXERCISES["intimacy"][:2])

        # Add exercises for conflicts
        if match_result.potential_conflicts:
            exercises.extend(COUPLES_EXERCISES["conflict"][:2])

        # Deduplicate and limit
        return list(dict.fromkeys(exercises))[:6]

    def get_audit_log(
        self,
        couple_link_id: Optional[str] = None,
    ) -> list[MergeAuditEntry]:
        """
        Get audit log entries.

        Args:
            couple_link_id: Optional filter by couple link

        Returns:
            List of audit entries
        """
        if couple_link_id:
            return [
                entry for entry in self._audit_log
                if entry.couple_link_id == couple_link_id
            ]
        return self._audit_log.copy()

    def get_merge_history(
        self,
        couple_link_id: str,
    ) -> list[MergeAuditEntry]:
        """
        Get merge history for a couple.

        Args:
            couple_link_id: Couple link ID

        Returns:
            List of audit entries for this couple
        """
        return [
            entry for entry in self._audit_log
            if entry.couple_link_id == couple_link_id
            and entry.action == "merge_completed"
        ]

    def create_audit_entry(
        self,
        couple_link_id: str,
        session_id: str,
        therapist_id: str,
        action: str,
        partner_a_id: str,
        partner_b_id: str,
        result_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        ip_address: str = "unknown",
    ) -> MergeAuditEntry:
        """
        Create a manual audit entry.

        Args:
            couple_link_id: Couple link ID
            session_id: Session ID
            therapist_id: Therapist ID
            action: Action taken
            partner_a_id: Partner A ID
            partner_b_id: Partner B ID
            result_summary: Optional result summary
            error_message: Optional error message
            ip_address: Request IP

        Returns:
            Created audit entry
        """
        entry = MergeAuditEntry(
            couple_link_id=couple_link_id,
            session_id=session_id,
            therapist_id=therapist_id,
            action=action,
            partner_a_id=partner_a_id,
            partner_b_id=partner_b_id,
            result_summary=result_summary,
            error_message=error_message,
            ip_address=ip_address,
        )
        self._audit_log.append(entry)
        return entry
