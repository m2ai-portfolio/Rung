"""
Framework Isolation Layer - CRITICAL SECURITY COMPONENT

Extracts ONLY framework-level data from clinical analysis outputs.
This layer ensures NO PHI or specific content crosses between
individual client contexts in couples therapy.

ALLOWED OUTPUT:
- Pattern category names (e.g., "attachment anxiety")
- Framework references (e.g., "Gottman Four Horsemen")
- Theme categories (e.g., "communication", "intimacy", "trust")
- Modality names (e.g., "CBT", "EFT")

PROHIBITED (MUST BE STRIPPED):
- Direct quotes from sessions
- Specific incidents or events
- Emotional content details
- Dates or timeline specifics
- Names, places, or identifying information
- Numerical details (ages, amounts, durations)
- Any PHI (Protected Health Information)
"""

import re
from typing import Optional
from pydantic import BaseModel, Field

from src.agents.schemas.rung_output import RungAnalysisOutput


class IsolatedFrameworks(BaseModel):
    """
    Isolated framework data safe for cross-client sharing.

    Contains ONLY category-level information with no specific content.
    """
    # Pattern categories (not specific instances)
    attachment_patterns: list[str] = Field(
        default_factory=list,
        description="Attachment pattern categories (e.g., 'anxious attachment')"
    )

    # Framework references only
    frameworks_identified: list[str] = Field(
        default_factory=list,
        description="Framework names (e.g., 'Gottman Four Horsemen')"
    )

    # Theme categories
    theme_categories: list[str] = Field(
        default_factory=list,
        description="Theme categories (e.g., 'communication', 'trust')"
    )

    # Modality names
    modalities: list[str] = Field(
        default_factory=list,
        description="Therapeutic modalities used"
    )

    # Defense mechanism categories (not instances)
    defense_patterns: list[str] = Field(
        default_factory=list,
        description="Defense mechanism categories"
    )

    # Communication pattern categories
    communication_patterns: list[str] = Field(
        default_factory=list,
        description="Communication pattern categories"
    )


class IsolationLayerError(Exception):
    """Exception for isolation layer errors."""
    pass


class IsolationViolation(Exception):
    """Exception raised when PHI is detected in output."""
    pass


# =============================================================================
# Allowed Terms (Whitelist Approach)
# =============================================================================

# Attachment patterns - CATEGORY NAMES ONLY
ALLOWED_ATTACHMENT_PATTERNS = {
    "secure attachment",
    "anxious attachment",
    "avoidant attachment",
    "disorganized attachment",
    "fearful avoidant",
    "dismissive avoidant",
    "anxious-preoccupied",
    "attachment anxiety",
    "attachment avoidance",
}

# Framework references - NAMES ONLY
ALLOWED_FRAMEWORKS = {
    # Gottman
    "gottman method",
    "gottman four horsemen",
    "criticism",
    "contempt",
    "defensiveness",
    "stonewalling",
    "repair attempts",
    "love maps",
    "fondness and admiration",
    "turning toward",
    "positive perspective",
    "manage conflict",
    "make life dreams come true",
    "create shared meaning",

    # EFT
    "emotionally focused therapy",
    "eft",
    "attachment theory",
    "pursue-withdraw cycle",
    "pursuer-distancer",
    "protest polka",
    "freeze and flee",
    "find the raw spots",
    "hold me tight",

    # CBT
    "cognitive behavioral therapy",
    "cbt",
    "cognitive distortions",
    "automatic thoughts",
    "core beliefs",
    "behavioral activation",
    "thought records",

    # DBT
    "dialectical behavior therapy",
    "dbt",
    "mindfulness",
    "distress tolerance",
    "emotion regulation",
    "interpersonal effectiveness",
    "wise mind",
    "radical acceptance",

    # Other frameworks
    "internal family systems",
    "ifs",
    "parts work",
    "psychodynamic",
    "transactional analysis",
    "schema therapy",
    "somatic experiencing",
    "emdr",
    "narrative therapy",
    "solution focused",
}

# Theme categories - GENERIC ONLY
ALLOWED_THEMES = {
    "communication",
    "trust",
    "intimacy",
    "boundaries",
    "conflict",
    "connection",
    "attachment",
    "safety",
    "vulnerability",
    "autonomy",
    "interdependence",
    "respect",
    "appreciation",
    "commitment",
    "values",
    "goals",
    "family of origin",
    "parenting",
    "finances",
    "work-life balance",
    "sexuality",
    "emotional attunement",
    "validation",
    "support",
    "independence",
}

# Defense mechanism categories
ALLOWED_DEFENSES = {
    "denial",
    "projection",
    "rationalization",
    "intellectualization",
    "displacement",
    "regression",
    "repression",
    "sublimation",
    "reaction formation",
    "splitting",
    "passive aggression",
    "avoidance",
    "minimization",
    "externalization",
}

# Communication patterns - CATEGORIES ONLY
ALLOWED_COMMUNICATION_PATTERNS = {
    "passive",
    "aggressive",
    "passive-aggressive",
    "assertive",
    "avoidant",
    "confrontational",
    "placating",
    "blaming",
    "computing",
    "distracting",
    "leveling",
    "demand-withdraw",
    "mutual avoidance",
    "mutual engagement",
}

# Modalities
ALLOWED_MODALITIES = {
    "cbt",
    "dbt",
    "eft",
    "emdr",
    "ifs",
    "mindfulness",
    "psychodynamic",
    "gottman",
    "narrative",
    "solution focused",
    "somatic",
    "art therapy",
    "play therapy",
    "trauma focused",
    "acceptance and commitment therapy",
    "act",
}


# =============================================================================
# PHI Detection Patterns
# =============================================================================

# Patterns that indicate PHI - MUST BE BLOCKED
PHI_PATTERNS = [
    # Quotes and specific statements
    r'"[^"]{10,}"',  # Quoted text longer than 10 chars
    r"'[^']{10,}'",  # Single-quoted text
    r"said\s+that",
    r"told\s+me",
    r"mentioned\s+that",
    r"described\s+how",
    r"reported\s+that",
    r"stated\s+that",

    # Dates and times
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",  # MM/DD/YYYY
    r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
    r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b",
    r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
    r"\blast\s+(week|month|year|night|time)\b",
    r"\b(yesterday|today|tomorrow)\b",
    r"\b\d+\s+(days?|weeks?|months?|years?)\s+ago\b",

    # Names (capitalized words that aren't frameworks)
    r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # Two capitalized words (names)

    # Locations
    r"\b(street|avenue|road|drive|lane|court|blvd|boulevard)\b",
    r"\b(hospital|clinic|school|office|workplace|home)\b",

    # Numbers that could be identifying
    r"\b\d{3,}\b",  # 3+ digit numbers
    r"\$\d+",  # Money amounts
    r"\b\d+\s*%\b",  # Percentages

    # Specific incidents
    r"\b(incident|event|situation|argument|fight|episode)\b",
    r"when\s+(he|she|they|we|I)\s+\w+ed",  # "when he/she did something"
    r"after\s+(he|she|they|we|I)\s+\w+ed",
    r"because\s+(he|she|they|we|I)",

    # Emotional details
    r"\bfelt\s+(so|very|extremely|really)\s+\w+\b",
    r"\bwas\s+(so|very|extremely|really)\s+\w+\b",
    r"\b(crying|screaming|yelling|shouting|sobbing)\b",

    # Family members with context
    r"\b(my|his|her|their)\s+(mother|father|sister|brother|son|daughter|wife|husband|partner)\s+\w+",

    # Session-specific details
    r"in\s+session\s+\d+",
    r"during\s+(the|our)\s+\w+\s+session",
]


class IsolationLayer:
    """
    Extracts framework-level data while stripping all specific content.

    This is a CRITICAL SECURITY COMPONENT that ensures no PHI or
    identifying information crosses between client contexts.

    Uses a WHITELIST approach - only explicitly allowed terms pass through.
    """

    def __init__(self, strict_mode: bool = True):
        """
        Initialize isolation layer.

        Args:
            strict_mode: If True, raises exception on any PHI detection.
                        If False, silently strips PHI (less safe).
        """
        self.strict_mode = strict_mode
        self._phi_patterns = [re.compile(p, re.IGNORECASE) for p in PHI_PATTERNS]

    def isolate(self, analysis: RungAnalysisOutput) -> IsolatedFrameworks:
        """
        Extract isolated framework data from Rung analysis.

        Args:
            analysis: Full Rung analysis output

        Returns:
            IsolatedFrameworks with only safe category-level data

        Raises:
            IsolationViolation: If PHI detected in strict mode
        """
        isolated = IsolatedFrameworks()

        # Extract attachment patterns (categories only)
        isolated.attachment_patterns = self._extract_attachment_patterns(analysis)

        # Extract framework names
        isolated.frameworks_identified = self._extract_frameworks(analysis)

        # Extract theme categories
        isolated.theme_categories = self._extract_themes(analysis)

        # Extract modalities
        isolated.modalities = self._extract_modalities(analysis)

        # Extract defense patterns
        isolated.defense_patterns = self._extract_defenses(analysis)

        # Extract communication patterns
        isolated.communication_patterns = self._extract_communication_patterns(analysis)

        # Final validation - ensure no PHI leaked through
        self._validate_output(isolated)

        return isolated

    def _extract_attachment_patterns(
        self, analysis: RungAnalysisOutput
    ) -> list[str]:
        """Extract only allowed attachment pattern categories."""
        patterns = []

        # Check frameworks for attachment-related patterns
        for fw in analysis.frameworks_identified:
            name_lower = fw.name.lower()

            # Check for full pattern match
            for allowed in ALLOWED_ATTACHMENT_PATTERNS:
                if allowed in name_lower:
                    patterns.append(allowed)
                    break

            # Also check for partial style matches (e.g., "anxious" in name)
            if "anxious" in name_lower and "attachment" in name_lower:
                patterns.append("anxious attachment")
            elif "avoidant" in name_lower and "attachment" in name_lower:
                patterns.append("avoidant attachment")
            elif "disorganized" in name_lower and "attachment" in name_lower:
                patterns.append("disorganized attachment")
            elif "secure" in name_lower and "attachment" in name_lower:
                patterns.append("secure attachment")

        return list(set(patterns))

    def _extract_frameworks(self, analysis: RungAnalysisOutput) -> list[str]:
        """Extract only allowed framework names."""
        frameworks = []

        for fw in analysis.frameworks_identified:
            name_lower = fw.name.lower()

            # Check against whitelist
            for allowed in ALLOWED_FRAMEWORKS:
                if allowed in name_lower or name_lower in allowed:
                    frameworks.append(allowed)
                    break

        return list(set(frameworks))

    def _extract_themes(self, analysis: RungAnalysisOutput) -> list[str]:
        """Extract only allowed theme categories."""
        themes = []

        for theme in analysis.key_themes:
            theme_lower = theme.lower()

            # Check against whitelist
            for allowed in ALLOWED_THEMES:
                if allowed in theme_lower:
                    themes.append(allowed)
                    break

        return list(set(themes))

    def _extract_modalities(self, analysis: RungAnalysisOutput) -> list[str]:
        """Extract only allowed modality names."""
        modalities = []

        # Check session questions for modality mentions
        # In real impl, this would come from the session data

        # Check frameworks for modality associations
        for fw in analysis.frameworks_identified:
            name_lower = fw.name.lower()

            for allowed in ALLOWED_MODALITIES:
                if allowed in name_lower:
                    modalities.append(allowed)
                    break

        return list(set(modalities))

    def _extract_defenses(self, analysis: RungAnalysisOutput) -> list[str]:
        """Extract only allowed defense mechanism categories."""
        defenses = []

        for dm in analysis.defense_mechanisms:
            mechanism_type = dm.type.lower()

            # Check against whitelist
            for allowed in ALLOWED_DEFENSES:
                if allowed in mechanism_type or mechanism_type in allowed:
                    defenses.append(allowed)
                    break

        return list(set(defenses))

    def _extract_communication_patterns(
        self, analysis: RungAnalysisOutput
    ) -> list[str]:
        """Extract only allowed communication pattern categories."""
        patterns = []

        for theme in analysis.key_themes:
            theme_lower = theme.lower()

            for allowed in ALLOWED_COMMUNICATION_PATTERNS:
                if allowed in theme_lower:
                    patterns.append(allowed)
                    break

        return list(set(patterns))

    def _validate_output(self, isolated: IsolatedFrameworks) -> None:
        """
        Final validation to ensure no PHI in output.

        Since we only extract from whitelists, PHI should not be present.
        This is a secondary check for defense in depth.

        Raises:
            IsolationViolation: If any PHI detected
        """
        # Combine all output for validation
        all_content = []
        all_content.extend(isolated.attachment_patterns)
        all_content.extend(isolated.frameworks_identified)
        all_content.extend(isolated.theme_categories)
        all_content.extend(isolated.modalities)
        all_content.extend(isolated.defense_patterns)
        all_content.extend(isolated.communication_patterns)

        # All content should be from whitelists (lowercase)
        # Verify each item is in a whitelist
        all_allowed = (
            ALLOWED_ATTACHMENT_PATTERNS |
            ALLOWED_FRAMEWORKS |
            ALLOWED_THEMES |
            ALLOWED_DEFENSES |
            ALLOWED_COMMUNICATION_PATTERNS |
            ALLOWED_MODALITIES
        )

        for item in all_content:
            if item and item not in all_allowed:
                if self.strict_mode:
                    raise IsolationViolation(
                        f"Non-whitelisted term in output: {item}"
                    )

    def contains_phi(self, text: str) -> bool:
        """
        Check if text contains PHI patterns.

        Args:
            text: Text to check

        Returns:
            True if PHI detected
        """
        if not text:
            return False

        text_lower = text.lower()

        # Build set of all whitelisted terms
        all_allowed = (
            ALLOWED_ATTACHMENT_PATTERNS |
            ALLOWED_FRAMEWORKS |
            ALLOWED_THEMES |
            ALLOWED_DEFENSES |
            ALLOWED_COMMUNICATION_PATTERNS |
            ALLOWED_MODALITIES
        )

        # Check for PHI patterns
        for pattern in self._phi_patterns:
            match = pattern.search(text)
            if match:
                matched_text = match.group().lower()
                # Check if matched text is a whitelisted term
                is_whitelisted = any(
                    allowed in matched_text or matched_text in allowed
                    for allowed in all_allowed
                )
                if not is_whitelisted:
                    return True

        return False

    def sanitize_text(self, text: str) -> str:
        """
        Remove PHI patterns from text.

        WARNING: This is a fallback - prefer using whitelist extraction.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        result = text
        for pattern in self._phi_patterns:
            result = pattern.sub("[REDACTED]", result)

        return result

    def extract_safe_categories(self, text: str) -> list[str]:
        """
        Extract only safe category terms from arbitrary text.

        Uses whitelist approach - only returns terms from allowed sets.

        Args:
            text: Text to extract from

        Returns:
            List of safe category terms found
        """
        if not text:
            return []

        text_lower = text.lower()
        found = []

        # Check all whitelists
        all_allowed = (
            ALLOWED_ATTACHMENT_PATTERNS |
            ALLOWED_FRAMEWORKS |
            ALLOWED_THEMES |
            ALLOWED_DEFENSES |
            ALLOWED_COMMUNICATION_PATTERNS |
            ALLOWED_MODALITIES
        )

        for allowed in all_allowed:
            if allowed in text_lower:
                found.append(allowed)

        return found


def isolate_for_couples_merge(
    partner_a_analysis: RungAnalysisOutput,
    partner_b_analysis: RungAnalysisOutput,
    strict_mode: bool = True,
) -> tuple[IsolatedFrameworks, IsolatedFrameworks]:
    """
    Isolate framework data from both partners for couples merge.

    This is the primary entry point for the couples merge workflow.

    Args:
        partner_a_analysis: Rung analysis for partner A
        partner_b_analysis: Rung analysis for partner B
        strict_mode: If True, raises on any PHI detection

    Returns:
        Tuple of (partner_a_isolated, partner_b_isolated)

    Raises:
        IsolationViolation: If PHI detected in either analysis
    """
    layer = IsolationLayer(strict_mode=strict_mode)

    partner_a_isolated = layer.isolate(partner_a_analysis)
    partner_b_isolated = layer.isolate(partner_b_analysis)

    return partner_a_isolated, partner_b_isolated
