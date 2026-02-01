"""
Rung Clinical Analysis Agent

Pre-session analysis agent that processes client voice memos and
communications to generate clinical briefs for the therapist.

This agent:
1. Analyzes transcribed voice memos
2. Identifies psychological frameworks and patterns
3. Flags risk indicators
4. Generates structured output for therapist review
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from src.services.bedrock_client import BedrockClient, BedrockClientError
from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    RungAnalysisRequest,
    FrameworkIdentified,
    DefenseMechanism,
    RiskFlag,
    RiskLevel,
)


class RungAgentError(Exception):
    """Custom exception for Rung agent errors."""
    pass


class RungAgent:
    """
    Rung clinical analysis agent.

    Analyzes client communications to identify psychological frameworks,
    defense mechanisms, risk indicators, and areas for therapeutic exploration.

    Attributes:
        bedrock_client: Client for AWS Bedrock Claude API
        system_prompt: The loaded system prompt for Rung
    """

    # Temperature for clinical consistency (lower = more deterministic)
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_MAX_TOKENS = 4096

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize Rung agent.

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
        # Try multiple paths for flexibility in different environments
        possible_paths = [
            Path(__file__).parent / "prompts" / "rung_system.txt",
            Path("src/agents/prompts/rung_system.txt"),
            Path(os.environ.get("RUNG_PROMPTS_PATH", "")) / "rung_system.txt",
        ]

        for path in possible_paths:
            if path.exists():
                return path.read_text(encoding="utf-8")

        raise RungAgentError(
            "Could not load Rung system prompt. "
            f"Searched paths: {[str(p) for p in possible_paths]}"
        )

    def analyze(
        self,
        request: RungAnalysisRequest,
    ) -> RungAnalysisOutput:
        """
        Analyze client communication and generate clinical brief.

        Args:
            request: Analysis request with transcript and metadata

        Returns:
            RungAnalysisOutput with frameworks, risks, and suggestions

        Raises:
            RungAgentError: If analysis fails
        """
        # Build user message
        user_message = self._build_user_message(request)

        try:
            # Call Bedrock
            parsed_json, response = self.bedrock_client.invoke_with_json_output(
                system_prompt=self.system_prompt,
                user_message=user_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            # Parse and validate output
            output = self._parse_output(parsed_json)

            # Add metadata
            output.raw_text_length = len(request.transcript)

            return output

        except BedrockClientError as e:
            raise RungAgentError(f"Bedrock API call failed: {str(e)}") from e
        except ValidationError as e:
            raise RungAgentError(f"Output validation failed: {str(e)}") from e

    def analyze_text(
        self,
        transcript: str,
        session_id: str = "unknown",
        client_id: str = "unknown",
        historical_context: Optional[str] = None,
    ) -> RungAnalysisOutput:
        """
        Convenience method to analyze raw text.

        Args:
            transcript: The text to analyze
            session_id: Optional session identifier
            client_id: Optional client identifier
            historical_context: Optional historical context

        Returns:
            RungAnalysisOutput with analysis results
        """
        request = RungAnalysisRequest(
            session_id=session_id,
            client_id=client_id,
            transcript=transcript,
            historical_context=historical_context,
        )
        return self.analyze(request)

    def _build_user_message(self, request: RungAnalysisRequest) -> str:
        """Build the user message for analysis."""
        parts = [
            "Please analyze the following client communication:",
            "",
            "---BEGIN TRANSCRIPT---",
            request.transcript,
            "---END TRANSCRIPT---",
        ]

        if request.historical_context:
            parts.extend([
                "",
                "Historical context from previous sessions:",
                request.historical_context,
            ])

        if request.session_number:
            parts.extend([
                "",
                f"This is session #{request.session_number} with this client.",
            ])

        parts.extend([
            "",
            "Provide your clinical analysis as structured JSON.",
        ])

        return "\n".join(parts)

    def _parse_output(self, data: dict) -> RungAnalysisOutput:
        """Parse and validate the JSON output from Claude."""
        # Parse frameworks
        frameworks = []
        for f in data.get("frameworks_identified", []):
            frameworks.append(FrameworkIdentified(
                name=f.get("name", ""),
                confidence=float(f.get("confidence", 0.5)),
                evidence=f.get("evidence", ""),
                category=f.get("category"),
            ))

        # Parse defense mechanisms
        defenses = []
        for d in data.get("defense_mechanisms", []):
            defenses.append(DefenseMechanism(
                type=d.get("type", ""),
                indicators=d.get("indicators", []),
                context=d.get("context"),
            ))

        # Parse risk flags
        risks = []
        for r in data.get("risk_flags", []):
            level_str = r.get("level", "low").lower()
            try:
                level = RiskLevel(level_str)
            except ValueError:
                level = RiskLevel.LOW

            risks.append(RiskFlag(
                level=level,
                description=r.get("description", ""),
                recommended_action=r.get("recommended_action"),
            ))

        # Build output
        return RungAnalysisOutput(
            frameworks_identified=frameworks,
            defense_mechanisms=defenses,
            risk_flags=risks,
            key_themes=data.get("key_themes", []),
            suggested_exploration=data.get("suggested_exploration", []),
            session_questions=data.get("session_questions", []),
            analysis_confidence=data.get("analysis_confidence"),
        )

    def detect_frameworks(self, text: str) -> list[FrameworkIdentified]:
        """
        Quick framework detection without full analysis.

        Args:
            text: Text to analyze for frameworks

        Returns:
            List of identified frameworks
        """
        output = self.analyze_text(text)
        return output.frameworks_identified

    def assess_risk(self, text: str) -> list[RiskFlag]:
        """
        Quick risk assessment without full analysis.

        Args:
            text: Text to assess for risk indicators

        Returns:
            List of risk flags
        """
        output = self.analyze_text(text)
        return output.risk_flags

    def has_high_risk(self, text: str) -> bool:
        """
        Check if text contains high-risk indicators.

        Args:
            text: Text to assess

        Returns:
            True if any high-risk flags are present
        """
        risks = self.assess_risk(text)
        return any(r.level == RiskLevel.HIGH for r in risks)
