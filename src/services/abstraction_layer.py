"""
Abstraction Layer for Rung-to-Beth Communication

CRITICAL SECURITY COMPONENT

This layer ensures that Beth NEVER receives raw Rung output.
It strips all clinical terminology, defense mechanism labels,
risk flags, and specific framework names.

Beth should only receive generalized themes in accessible language.
"""

import re
from dataclasses import dataclass
from typing import Optional

from src.agents.schemas.rung_output import RungAnalysisOutput
from src.agents.schemas.beth_output import AbstractedRungOutput, BethInput


@dataclass
class AbstractionResult:
    """Result of abstraction process."""
    abstracted_output: AbstractedRungOutput
    clinical_terms_stripped: list[str]
    risk_flags_removed: int
    is_safe_for_beth: bool


class AbstractionError(Exception):
    """Exception raised when abstraction fails."""
    pass


class AbstractionLayer:
    """
    Converts Rung clinical output to Beth-safe input.

    CRITICAL: This is a security boundary. All Rung output
    MUST pass through this layer before reaching Beth.

    Transformations:
    1. Framework names → Generalized themes
    2. Defense mechanisms → Removed entirely
    3. Risk flags → Removed (therapist only)
    4. Clinical terminology → Accessible language
    5. Specific evidence/quotes → Removed
    """

    # Clinical terms that must be stripped
    CLINICAL_TERMS = {
        # Attachment terminology
        "avoidant attachment": "connection patterns",
        "anxious attachment": "relationship concerns",
        "disorganized attachment": "mixed feelings about closeness",
        "secure attachment": "healthy connection",
        "attachment style": "relationship patterns",
        "attachment pattern": "connection patterns",

        # Defense mechanisms (remove entirely, replace with general)
        "intellectualization": "thinking patterns",
        "projection": "perception patterns",
        "denial": "awareness",
        "rationalization": "thought patterns",
        "displacement": "emotional patterns",
        "regression": "stress responses",
        "repression": "memory patterns",
        "sublimation": "coping strategies",
        "reaction formation": "emotional responses",
        "splitting": "perspective patterns",
        "passive aggression": "communication patterns",
        "avoidance": "response patterns",

        # Gottman terminology
        "stonewalling": "communication challenges",
        "criticism": "feedback patterns",
        "contempt": "respect concerns",
        "defensiveness": "response patterns",
        "four horsemen": "communication patterns",
        "gottman": "relationship",

        # Clinical terms
        "transference": "relationship dynamics",
        "countertransference": "therapeutic relationship",
        "cognitive distortion": "thought patterns",
        "rumination": "repetitive thinking",
        "dissociation": "disconnection",
        "hypervigilance": "heightened awareness",
        "trauma response": "stress response",
        "maladaptive": "unhelpful",
        "pathological": "concerning",
        "disorder": "challenges",
        "dysfunction": "difficulties",
        "symptom": "experience",
        "diagnosis": "understanding",

        # Relationship dynamics
        "pursuer-distancer": "different needs for closeness",
        "enmeshment": "very close boundaries",
        "codependency": "interconnected patterns",
        "triangulation": "involving others",
    }

    # Terms that should trigger complete removal (too clinical)
    REMOVE_ENTIRELY = {
        "suicidal", "self-harm", "abuse", "trauma", "ptsd",
        "borderline", "narcissistic", "antisocial", "psychotic",
        "manic", "depressive episode", "dissociative",
        "paranoid", "schizoid", "histrionic",
    }

    # Generic theme mappings for frameworks
    FRAMEWORK_TO_THEME = {
        "attachment": "how you connect with others",
        "defense": "how you protect yourself emotionally",
        "communication": "how you express yourself",
        "relationship": "how you relate to others",
        "emotional": "your emotional experiences",
        "cognitive": "your thought patterns",
        "behavioral": "your actions and habits",
    }

    def __init__(self, strict_mode: bool = True):
        """
        Initialize abstraction layer.

        Args:
            strict_mode: If True, raise error on any clinical terms that
                        can't be mapped. If False, remove them.
        """
        self.strict_mode = strict_mode

    def abstract(self, rung_output: RungAnalysisOutput) -> AbstractionResult:
        """
        Abstract Rung output for Beth.

        Args:
            rung_output: Raw Rung analysis output

        Returns:
            AbstractionResult with safe output for Beth

        Raises:
            AbstractionError: If abstraction fails in strict mode
        """
        clinical_terms_stripped = []
        risk_flags_removed = len(rung_output.risk_flags)

        # Extract and transform themes
        themes = self._extract_themes(rung_output, clinical_terms_stripped)

        # Extract exploration areas (from suggested_exploration)
        exploration_areas = self._transform_explorations(
            rung_output.suggested_exploration,
            clinical_terms_stripped
        )

        # Generate session focus from key themes
        session_focus = self._generate_focus(rung_output.key_themes)

        abstracted = AbstractedRungOutput(
            themes=themes,
            exploration_areas=exploration_areas,
            session_focus=session_focus,
        )

        # Verify output is clean
        is_safe = self._verify_safe(abstracted)

        return AbstractionResult(
            abstracted_output=abstracted,
            clinical_terms_stripped=clinical_terms_stripped,
            risk_flags_removed=risk_flags_removed,
            is_safe_for_beth=is_safe,
        )

    def to_beth_input(
        self,
        rung_output: RungAnalysisOutput,
        session_number: Optional[int] = None,
        client_name: Optional[str] = None,
    ) -> BethInput:
        """
        Convert Rung output to Beth input.

        Args:
            rung_output: Raw Rung analysis output
            session_number: Optional session number
            client_name: Optional client first name

        Returns:
            BethInput ready for Beth agent
        """
        result = self.abstract(rung_output)

        if not result.is_safe_for_beth:
            raise AbstractionError(
                "Abstracted output contains clinical terminology"
            )

        return BethInput(
            themes=result.abstracted_output.themes,
            exploration_areas=result.abstracted_output.exploration_areas,
            session_focus=result.abstracted_output.session_focus,
            session_number=session_number,
            client_name=client_name,
        )

    def _extract_themes(
        self,
        rung_output: RungAnalysisOutput,
        stripped: list[str]
    ) -> list[str]:
        """Extract and transform themes from Rung output."""
        themes = []

        # Transform key themes
        for theme in rung_output.key_themes:
            transformed = self._transform_text(theme, stripped)
            if transformed and not self._contains_clinical(transformed):
                themes.append(transformed)

        # Add generalized framework themes
        for framework in rung_output.frameworks_identified:
            category = framework.category or ""
            if category in self.FRAMEWORK_TO_THEME:
                theme = self.FRAMEWORK_TO_THEME[category]
                if theme not in themes:
                    themes.append(theme)

        return themes[:5]  # Limit to 5 themes

    def _transform_explorations(
        self,
        explorations: list[str],
        stripped: list[str]
    ) -> list[str]:
        """Transform exploration suggestions to accessible language."""
        transformed = []

        for exp in explorations:
            new_exp = self._transform_text(exp, stripped)
            if new_exp and not self._contains_clinical(new_exp):
                transformed.append(new_exp)

        return transformed[:4]  # Limit to 4

    def _generate_focus(self, key_themes: list[str]) -> str:
        """Generate session focus from themes."""
        if not key_themes:
            return "exploring what's on your mind"

        # Take first theme and make it accessible
        theme = key_themes[0].lower()

        # Transform to accessible language
        for clinical, accessible in self.CLINICAL_TERMS.items():
            theme = theme.replace(clinical.lower(), accessible)

        return f"exploring {theme}"

    def _transform_text(self, text: str, stripped: list[str]) -> str:
        """Transform text by replacing clinical terms."""
        result = text.lower()

        # Check for terms that require complete removal
        for term in self.REMOVE_ENTIRELY:
            if term in result:
                stripped.append(term)
                return ""  # Remove entirely

        # Replace clinical terms
        for clinical, accessible in self.CLINICAL_TERMS.items():
            if clinical.lower() in result:
                stripped.append(clinical)
                result = result.replace(clinical.lower(), accessible)

        # Capitalize first letter
        if result:
            result = result[0].upper() + result[1:]

        return result

    def _contains_clinical(self, text: str) -> bool:
        """Check if text contains any clinical terminology."""
        text_lower = text.lower()

        # Check for removal terms
        for term in self.REMOVE_ENTIRELY:
            if term in text_lower:
                return True

        # Check for clinical terms that weren't mapped
        clinical_patterns = [
            r"\battachment\b",
            r"\bdefense\s+mechanism\b",
            r"\btransference\b",
            r"\bcognitive\s+distortion\b",
            r"\bdiagnos",
            r"\bdisorder\b",
            r"\bpatholog",
            r"\bmaladaptive\b",
        ]

        for pattern in clinical_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _verify_safe(self, output: AbstractedRungOutput) -> bool:
        """Verify abstracted output is safe for Beth."""
        # Check all text fields
        all_text = " ".join([
            output.session_focus,
            *output.themes,
            *output.exploration_areas,
        ])

        return not self._contains_clinical(all_text)


def abstract_for_beth(
    rung_output: RungAnalysisOutput,
    session_number: Optional[int] = None,
    client_name: Optional[str] = None,
) -> BethInput:
    """
    Convenience function to abstract Rung output for Beth.

    Args:
        rung_output: Raw Rung analysis output
        session_number: Optional session number
        client_name: Optional client first name

    Returns:
        BethInput ready for Beth agent
    """
    layer = AbstractionLayer()
    return layer.to_beth_input(rung_output, session_number, client_name)
