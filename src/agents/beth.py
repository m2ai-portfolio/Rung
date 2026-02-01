"""
Beth Client Communication Agent

Client-facing session preparation agent that creates accessible,
friendly session preparation guides.

CRITICAL: Beth NEVER receives raw Rung output. All input must pass
through the abstraction layer first.

This agent:
1. Receives abstracted themes (no clinical terminology)
2. Creates warm, conversational session prep guides
3. Suggests reflection questions in accessible language
4. Recommends optional exercises
"""

import os
import re
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from src.services.bedrock_client import BedrockClient, BedrockClientError
from src.agents.schemas.beth_output import BethOutput, BethInput


class BethAgentError(Exception):
    """Custom exception for Beth agent errors."""
    pass


class ClinicalTermError(BethAgentError):
    """Exception when clinical terminology is detected in output."""
    pass


class BethAgent:
    """
    Beth client communication agent.

    Creates client-friendly session preparation guides using
    accessible, warm language. No clinical terminology allowed.

    Attributes:
        bedrock_client: Client for AWS Bedrock Claude API
        system_prompt: The loaded system prompt for Beth
    """

    # Temperature for friendly, varied responses
    DEFAULT_TEMPERATURE = 0.7
    DEFAULT_MAX_TOKENS = 2048

    # Terms that should NEVER appear in Beth's output
    FORBIDDEN_TERMS = [
        "attachment", "avoidant", "anxious", "disorganized", "secure attachment",
        "defense mechanism", "intellectualization", "projection", "denial",
        "rationalization", "displacement", "regression", "repression",
        "transference", "countertransference", "cognitive distortion",
        "stonewalling", "criticism pattern", "contempt", "gottman",
        "trauma", "ptsd", "disorder", "diagnosis", "pathology",
        "maladaptive", "dysfunction", "symptom", "clinical",
        "therapeutic intervention", "modality", "framework",
    ]

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize Beth agent.

        Args:
            bedrock_client: Optional pre-configured Bedrock client
            temperature: Sampling temperature for Claude
            max_tokens: Maximum response tokens
        """
        self.bedrock_client = bedrock_client or BedrockClient(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._system_prompt: Optional[str] = None

    @property
    def system_prompt(self) -> str:
        """Load and cache the system prompt."""
        if self._system_prompt is None:
            self._system_prompt = self._load_system_prompt()
        return self._system_prompt

    def _load_system_prompt(self) -> str:
        """Load the system prompt from file."""
        possible_paths = [
            Path(__file__).parent / "prompts" / "beth_system.txt",
            Path("src/agents/prompts/beth_system.txt"),
            Path(os.environ.get("BETH_PROMPTS_PATH", "")) / "beth_system.txt",
        ]

        for path in possible_paths:
            if path.exists():
                return path.read_text(encoding="utf-8")

        raise BethAgentError(
            "Could not load Beth system prompt. "
            f"Searched paths: {[str(p) for p in possible_paths]}"
        )

    def generate(self, beth_input: BethInput) -> BethOutput:
        """
        Generate client-friendly session preparation.

        Args:
            beth_input: Abstracted input from abstraction layer

        Returns:
            BethOutput with session prep, questions, and exercises

        Raises:
            BethAgentError: If generation fails
            ClinicalTermError: If output contains clinical terms
        """
        # Build user message
        user_message = self._build_user_message(beth_input)

        try:
            # Call Bedrock
            parsed_json, response = self.bedrock_client.invoke_with_json_output(
                system_prompt=self.system_prompt,
                user_message=user_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse output
            output = self._parse_output(parsed_json)

            # Verify no clinical terms
            self._verify_output(output)

            return output

        except BedrockClientError as e:
            raise BethAgentError(f"Bedrock API call failed: {str(e)}") from e
        except ValidationError as e:
            raise BethAgentError(f"Output validation failed: {str(e)}") from e

    def generate_from_themes(
        self,
        themes: list[str],
        session_focus: str = "",
        client_name: Optional[str] = None,
    ) -> BethOutput:
        """
        Convenience method to generate from themes directly.

        Args:
            themes: List of generalized themes
            session_focus: Optional session focus
            client_name: Optional client first name

        Returns:
            BethOutput with session preparation
        """
        beth_input = BethInput(
            themes=themes,
            exploration_areas=[],
            session_focus=session_focus,
            client_name=client_name,
        )
        return self.generate(beth_input)

    def _build_user_message(self, beth_input: BethInput) -> str:
        """Build the user message for generation."""
        parts = ["Please create a session preparation guide."]

        if beth_input.client_name:
            parts.append(f"\nClient's first name: {beth_input.client_name}")

        if beth_input.session_number:
            parts.append(f"This is session #{beth_input.session_number}.")

        if beth_input.themes:
            parts.append("\nThemes to consider (in accessible language):")
            for theme in beth_input.themes:
                parts.append(f"- {theme}")

        if beth_input.exploration_areas:
            parts.append("\nAreas they might want to explore:")
            for area in beth_input.exploration_areas:
                parts.append(f"- {area}")

        if beth_input.session_focus:
            parts.append(f"\nSuggested focus: {beth_input.session_focus}")

        parts.append("\nRemember: Keep everything warm, casual, and completely free of clinical terminology.")

        return "\n".join(parts)

    def _parse_output(self, data: dict) -> BethOutput:
        """Parse the JSON output from Claude."""
        return BethOutput(
            session_prep=data.get("session_prep", ""),
            discussion_points=data.get("discussion_points", []),
            reflection_questions=data.get("reflection_questions", []),
            exercises=data.get("exercises", []),
            tone_check_passed=True,  # Will be updated by verification
        )

    def _verify_output(self, output: BethOutput) -> None:
        """
        Verify output contains no clinical terminology.

        Args:
            output: The generated BethOutput

        Raises:
            ClinicalTermError: If clinical terms are found
        """
        # Combine all text
        all_text = " ".join([
            output.session_prep,
            *output.discussion_points,
            *output.reflection_questions,
            *output.exercises,
        ]).lower()

        # Check for forbidden terms
        found_terms = []
        for term in self.FORBIDDEN_TERMS:
            if term.lower() in all_text:
                found_terms.append(term)

        if found_terms:
            output.tone_check_passed = False
            raise ClinicalTermError(
                f"Beth output contains clinical terminology: {', '.join(found_terms)}"
            )

        output.tone_check_passed = True

    def check_output_safety(self, output: BethOutput) -> tuple[bool, list[str]]:
        """
        Check if output is safe without raising exception.

        Args:
            output: The BethOutput to check

        Returns:
            Tuple of (is_safe, list of found clinical terms)
        """
        all_text = " ".join([
            output.session_prep,
            *output.discussion_points,
            *output.reflection_questions,
            *output.exercises,
        ]).lower()

        found_terms = []
        for term in self.FORBIDDEN_TERMS:
            if term.lower() in all_text:
                found_terms.append(term)

        return len(found_terms) == 0, found_terms
