"""
Topic Matcher Service

Identifies patterns between partners in couples therapy:
- Overlapping themes
- Complementary patterns
- Potential conflict areas
"""

from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

from src.services.isolation_layer import IsolatedFrameworks


class TopicMatch(BaseModel):
    """A matched topic between partners."""
    topic: str = Field(..., description="The matched topic/framework")
    match_type: str = Field(
        ...,
        description="Type: 'overlap', 'complementary', 'conflict'"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence in the match"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the match"
    )


class TopicMatchResult(BaseModel):
    """Result of topic matching between partners."""
    overlapping_themes: list[TopicMatch] = Field(default_factory=list)
    complementary_patterns: list[TopicMatch] = Field(default_factory=list)
    potential_conflicts: list[TopicMatch] = Field(default_factory=list)
    suggested_focus_areas: list[str] = Field(default_factory=list)
    match_summary: str = Field(
        default="",
        description="Summary of the matching analysis"
    )


# =============================================================================
# Pattern Complementarity Definitions
# =============================================================================

# Patterns that often complement each other
COMPLEMENTARY_PATTERNS = {
    ("anxious attachment", "avoidant attachment"): {
        "description": "Classic pursuer-distancer dynamic",
        "focus_area": "Understanding attachment needs and creating safety",
    },
    ("passive", "aggressive"): {
        "description": "Communication style mismatch",
        "focus_area": "Developing assertive communication skills",
    },
    ("avoidant", "confrontational"): {
        "description": "Conflict engagement mismatch",
        "focus_area": "Finding balanced conflict resolution approaches",
    },
    ("intellectualization", "projection"): {
        "description": "Different defensive styles",
        "focus_area": "Emotional awareness and vulnerability",
    },
}

# Patterns that often create conflict
CONFLICT_PATTERNS = {
    ("stonewalling", "criticism"): {
        "description": "Gottman negative cycle",
        "focus_area": "Breaking the criticism-withdrawal cycle",
    },
    ("contempt", "defensiveness"): {
        "description": "Escalating negative cycle",
        "focus_area": "Building fondness and admiration",
    },
    ("demand-withdraw", "mutual avoidance"): {
        "description": "Communication breakdown",
        "focus_area": "Creating safe engagement patterns",
    },
}

# Themes that overlap positively
POSITIVE_OVERLAP_THEMES = {
    "communication",
    "trust",
    "intimacy",
    "connection",
    "commitment",
    "values",
    "goals",
}


class TopicMatcher:
    """
    Identifies patterns and themes between partners.

    Uses isolated framework data (no PHI) to find:
    - Shared themes and frameworks
    - Complementary dynamics
    - Potential conflict areas
    """

    def match(
        self,
        partner_a: IsolatedFrameworks,
        partner_b: IsolatedFrameworks,
    ) -> TopicMatchResult:
        """
        Match topics between partners.

        Args:
            partner_a: Isolated frameworks for partner A
            partner_b: Isolated frameworks for partner B

        Returns:
            TopicMatchResult with matches and suggestions
        """
        result = TopicMatchResult()

        # Find overlapping themes
        result.overlapping_themes = self._find_overlapping_themes(
            partner_a, partner_b
        )

        # Find complementary patterns
        result.complementary_patterns = self._find_complementary_patterns(
            partner_a, partner_b
        )

        # Find potential conflicts
        result.potential_conflicts = self._find_conflict_patterns(
            partner_a, partner_b
        )

        # Generate suggested focus areas
        result.suggested_focus_areas = self._generate_focus_areas(result)

        # Generate summary
        result.match_summary = self._generate_summary(result)

        return result

    def _find_overlapping_themes(
        self,
        partner_a: IsolatedFrameworks,
        partner_b: IsolatedFrameworks,
    ) -> list[TopicMatch]:
        """Find themes that both partners share."""
        matches = []

        # Check theme categories
        a_themes = set(partner_a.theme_categories)
        b_themes = set(partner_b.theme_categories)
        shared_themes = a_themes & b_themes

        for theme in shared_themes:
            is_positive = theme in POSITIVE_OVERLAP_THEMES
            matches.append(TopicMatch(
                topic=theme,
                match_type="overlap",
                confidence=0.9 if is_positive else 0.7,
                description=f"Both partners working on {theme}",
            ))

        # Check attachment patterns
        a_attach = set(partner_a.attachment_patterns)
        b_attach = set(partner_b.attachment_patterns)
        shared_attach = a_attach & b_attach

        for pattern in shared_attach:
            matches.append(TopicMatch(
                topic=pattern,
                match_type="overlap",
                confidence=0.85,
                description=f"Shared attachment pattern: {pattern}",
            ))

        # Check frameworks
        a_frameworks = set(partner_a.frameworks_identified)
        b_frameworks = set(partner_b.frameworks_identified)
        shared_frameworks = a_frameworks & b_frameworks

        for fw in shared_frameworks:
            matches.append(TopicMatch(
                topic=fw,
                match_type="overlap",
                confidence=0.9,
                description=f"Both working with {fw} framework",
            ))

        return matches

    def _find_complementary_patterns(
        self,
        partner_a: IsolatedFrameworks,
        partner_b: IsolatedFrameworks,
    ) -> list[TopicMatch]:
        """Find patterns that complement each other."""
        matches = []

        # Collect all patterns from both partners
        a_patterns = set()
        a_patterns.update(partner_a.attachment_patterns)
        a_patterns.update(partner_a.communication_patterns)
        a_patterns.update(partner_a.defense_patterns)

        b_patterns = set()
        b_patterns.update(partner_b.attachment_patterns)
        b_patterns.update(partner_b.communication_patterns)
        b_patterns.update(partner_b.defense_patterns)

        # Check for known complementary patterns
        for (pattern_1, pattern_2), info in COMPLEMENTARY_PATTERNS.items():
            # Check both directions
            if (pattern_1 in a_patterns and pattern_2 in b_patterns) or \
               (pattern_2 in a_patterns and pattern_1 in b_patterns):
                matches.append(TopicMatch(
                    topic=f"{pattern_1} / {pattern_2}",
                    match_type="complementary",
                    confidence=0.85,
                    description=info["description"],
                ))

        # Classic anxious-avoidant check (special case due to importance)
        anxious_patterns = {"anxious attachment", "anxious-preoccupied", "attachment anxiety"}
        avoidant_patterns = {"avoidant attachment", "dismissive avoidant", "fearful avoidant", "attachment avoidance"}

        a_anxious = bool(a_patterns & anxious_patterns)
        b_anxious = bool(b_patterns & anxious_patterns)
        a_avoidant = bool(a_patterns & avoidant_patterns)
        b_avoidant = bool(b_patterns & avoidant_patterns)

        if (a_anxious and b_avoidant) or (b_anxious and a_avoidant):
            if not any(m.topic == "anxious attachment / avoidant attachment" for m in matches):
                matches.append(TopicMatch(
                    topic="Anxious-Avoidant Dynamic",
                    match_type="complementary",
                    confidence=0.9,
                    description="Classic pursuer-distancer attachment pattern",
                ))

        return matches

    def _find_conflict_patterns(
        self,
        partner_a: IsolatedFrameworks,
        partner_b: IsolatedFrameworks,
    ) -> list[TopicMatch]:
        """Find patterns that may create conflict."""
        matches = []

        # Collect all patterns
        a_patterns = set()
        a_patterns.update(partner_a.communication_patterns)
        a_patterns.update(partner_a.defense_patterns)

        b_patterns = set()
        b_patterns.update(partner_b.communication_patterns)
        b_patterns.update(partner_b.defense_patterns)

        # Check for known conflict patterns
        for (pattern_1, pattern_2), info in CONFLICT_PATTERNS.items():
            if (pattern_1 in a_patterns and pattern_2 in b_patterns) or \
               (pattern_2 in a_patterns and pattern_1 in b_patterns):
                matches.append(TopicMatch(
                    topic=f"{pattern_1} + {pattern_2}",
                    match_type="conflict",
                    confidence=0.8,
                    description=info["description"],
                ))

        # Check Gottman Four Horsemen presence
        four_horsemen = {"criticism", "contempt", "defensiveness", "stonewalling"}
        a_horsemen = a_patterns & four_horsemen
        b_horsemen = b_patterns & four_horsemen

        if len(a_horsemen) >= 2 or len(b_horsemen) >= 2:
            combined = a_horsemen | b_horsemen
            if len(combined) >= 2:
                matches.append(TopicMatch(
                    topic="Gottman Four Horsemen",
                    match_type="conflict",
                    confidence=0.85,
                    description=f"Negative patterns present: {', '.join(combined)}",
                ))

        return matches

    def _generate_focus_areas(
        self,
        result: TopicMatchResult,
    ) -> list[str]:
        """Generate suggested focus areas based on matches."""
        focus_areas = []

        # Add focus areas from complementary patterns
        for match in result.complementary_patterns:
            topic_pair = match.topic.lower()
            for (p1, p2), info in COMPLEMENTARY_PATTERNS.items():
                if p1 in topic_pair or p2 in topic_pair:
                    focus_areas.append(info["focus_area"])
                    break

        # Add focus areas from conflict patterns
        for match in result.potential_conflicts:
            topic_pair = match.topic.lower()
            for (p1, p2), info in CONFLICT_PATTERNS.items():
                if p1 in topic_pair or p2 in topic_pair:
                    focus_areas.append(info["focus_area"])
                    break

        # Add default focus areas for overlapping themes
        for match in result.overlapping_themes:
            if match.topic in POSITIVE_OVERLAP_THEMES:
                focus_areas.append(f"Building shared {match.topic}")

        # Deduplicate
        return list(dict.fromkeys(focus_areas))[:5]  # Max 5 focus areas

    def _generate_summary(self, result: TopicMatchResult) -> str:
        """Generate a summary of the match results."""
        parts = []

        if result.overlapping_themes:
            count = len(result.overlapping_themes)
            parts.append(f"{count} shared theme(s)")

        if result.complementary_patterns:
            count = len(result.complementary_patterns)
            parts.append(f"{count} complementary dynamic(s)")

        if result.potential_conflicts:
            count = len(result.potential_conflicts)
            parts.append(f"{count} potential conflict area(s)")

        if not parts:
            return "No significant patterns identified between partners."

        return f"Analysis identified: {', '.join(parts)}."


def match_couple_topics(
    partner_a_isolated: IsolatedFrameworks,
    partner_b_isolated: IsolatedFrameworks,
) -> TopicMatchResult:
    """
    Convenience function to match topics between partners.

    Args:
        partner_a_isolated: Isolated frameworks for partner A
        partner_b_isolated: Isolated frameworks for partner B

    Returns:
        TopicMatchResult
    """
    matcher = TopicMatcher()
    return matcher.match(partner_a_isolated, partner_b_isolated)
