"""
Framework Extractor Service

Extracts psychological frameworks, modalities, homework, and
progress indicators from therapist session notes.

This is used for post-session processing to:
1. Track frameworks discussed in sessions
2. Record homework assignments
3. Note therapeutic modalities used
4. Identify breakthrough moments
5. Track client progress
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from pydantic import BaseModel, Field

from src.services.bedrock_client import BedrockClient, BedrockClientError


class HomeworkAssignment(BaseModel):
    """A homework assignment from the session."""
    task: str = Field(..., description="The homework task")
    due: Optional[str] = Field(None, description="When it's due (e.g., 'next session', '1 week')")
    category: Optional[str] = Field(None, description="Category (reflection, practice, reading)")


class FrameworkExtractionOutput(BaseModel):
    """Output from framework extraction."""
    frameworks_discussed: list[str] = Field(
        default_factory=list,
        description="Psychological frameworks discussed in the session"
    )
    modalities_used: list[str] = Field(
        default_factory=list,
        description="Therapeutic modalities used (CBT, DBT, EFT, etc.)"
    )
    homework_assigned: list[HomeworkAssignment] = Field(
        default_factory=list,
        description="Homework assignments given to the client"
    )
    breakthroughs: list[str] = Field(
        default_factory=list,
        description="Breakthrough moments or insights during the session"
    )
    progress_indicators: list[str] = Field(
        default_factory=list,
        description="Indicators of client progress"
    )
    areas_for_next_session: list[str] = Field(
        default_factory=list,
        description="Topics to explore in the next session"
    )
    session_summary: Optional[str] = Field(
        None,
        description="Brief summary of the session"
    )
    extraction_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence in the extraction"
    )


class FrameworkExtractorError(Exception):
    """Exception for framework extraction errors."""
    pass


# System prompt for framework extraction
EXTRACTION_SYSTEM_PROMPT = """You are a clinical documentation assistant that extracts structured information from therapist session notes.

Your task is to identify and extract:
1. **Frameworks Discussed**: Psychological frameworks mentioned or applied (e.g., attachment theory, Gottman method, cognitive behavioral patterns)
2. **Modalities Used**: Therapeutic approaches used (e.g., CBT, DBT, EFT, EMDR, psychodynamic, mindfulness-based)
3. **Homework Assigned**: Any exercises, reflections, or tasks assigned to the client
4. **Breakthroughs**: Significant insights, realizations, or emotional moments
5. **Progress Indicators**: Signs of improvement, growth, or positive change
6. **Areas for Next Session**: Topics flagged for future exploration

You MUST respond with valid JSON matching this structure:

```json
{
  "frameworks_discussed": ["Framework 1", "Framework 2"],
  "modalities_used": ["CBT", "Mindfulness"],
  "homework_assigned": [
    {"task": "Journal about feelings", "due": "next session", "category": "reflection"}
  ],
  "breakthroughs": ["Client recognized pattern of..."],
  "progress_indicators": ["Client showed increased awareness..."],
  "areas_for_next_session": ["Explore relationship with..."],
  "session_summary": "Brief 2-3 sentence summary",
  "extraction_confidence": 0.85
}
```

Be thorough but accurate. Only extract what is clearly stated or strongly implied in the notes.
"""


class FrameworkExtractor:
    """
    Extracts structured information from session notes.

    Uses Claude to analyze therapist notes and extract:
    - Frameworks and modalities
    - Homework assignments
    - Progress indicators
    - Next session topics
    """

    DEFAULT_TEMPERATURE = 0.2  # Low for consistent extraction
    DEFAULT_MAX_TOKENS = 2048

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize framework extractor.

        Args:
            bedrock_client: Optional pre-configured Bedrock client
            temperature: Sampling temperature
            max_tokens: Maximum response tokens
        """
        self.bedrock_client = bedrock_client or BedrockClient(
            temperature=temperature,
            max_tokens=max_tokens,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens

    def extract(self, notes: str) -> FrameworkExtractionOutput:
        """
        Extract frameworks and other info from session notes.

        Args:
            notes: Therapist session notes text

        Returns:
            FrameworkExtractionOutput with extracted information

        Raises:
            FrameworkExtractorError: If extraction fails
        """
        if not notes or not notes.strip():
            raise FrameworkExtractorError("Notes cannot be empty")

        user_message = f"""Please analyze these session notes and extract structured information:

---BEGIN NOTES---
{notes}
---END NOTES---

Extract frameworks, modalities, homework, breakthroughs, progress indicators, and areas for next session.
Respond with valid JSON only."""

        try:
            parsed_json, response = self.bedrock_client.invoke_with_json_output(
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                user_message=user_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return self._parse_output(parsed_json)

        except BedrockClientError as e:
            raise FrameworkExtractorError(f"Extraction failed: {str(e)}") from e

    def _parse_output(self, data: dict) -> FrameworkExtractionOutput:
        """Parse the JSON output from Claude."""
        # Parse homework assignments
        homework = []
        for hw in data.get("homework_assigned", []):
            if isinstance(hw, dict):
                homework.append(HomeworkAssignment(
                    task=hw.get("task", ""),
                    due=hw.get("due"),
                    category=hw.get("category"),
                ))
            elif isinstance(hw, str):
                homework.append(HomeworkAssignment(task=hw))

        return FrameworkExtractionOutput(
            frameworks_discussed=data.get("frameworks_discussed", []),
            modalities_used=data.get("modalities_used", []),
            homework_assigned=homework,
            breakthroughs=data.get("breakthroughs", []),
            progress_indicators=data.get("progress_indicators", []),
            areas_for_next_session=data.get("areas_for_next_session", []),
            session_summary=data.get("session_summary"),
            extraction_confidence=data.get("extraction_confidence"),
        )

    def extract_frameworks_only(self, notes: str) -> list[str]:
        """
        Quick extraction of just frameworks.

        Args:
            notes: Session notes text

        Returns:
            List of framework names
        """
        output = self.extract(notes)
        return output.frameworks_discussed

    def extract_homework(self, notes: str) -> list[HomeworkAssignment]:
        """
        Quick extraction of just homework assignments.

        Args:
            notes: Session notes text

        Returns:
            List of homework assignments
        """
        output = self.extract(notes)
        return output.homework_assigned
