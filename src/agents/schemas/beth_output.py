"""
Beth Agent Output Schema

Defines the structured output format for the Beth client-facing agent.
All outputs are validated with Pydantic for type safety.

CRITICAL: Beth output must NEVER contain clinical terminology.
This is client-facing content only.
"""

from typing import Optional
from pydantic import BaseModel, Field


class BethOutput(BaseModel):
    """
    Complete output from Beth client agent.

    This is the primary output schema for client-facing
    session preparation guides. Must use accessible,
    non-clinical language.
    """
    session_prep: str = Field(
        ...,
        description="Conversational preparation guide for the upcoming session"
    )
    discussion_points: list[str] = Field(
        default_factory=list,
        description="Things for the client to consider before the session"
    )
    reflection_questions: list[str] = Field(
        default_factory=list,
        description="Self-reflection prompts for the client"
    )
    exercises: list[str] = Field(
        default_factory=list,
        description="Optional exercises to try before the session"
    )

    # Metadata
    tone_check_passed: bool = Field(
        default=True,
        description="Whether output passed clinical terminology check"
    )


class BethInput(BaseModel):
    """
    Input for Beth agent from abstraction layer.

    CRITICAL: This is NOT raw Rung output. It contains only
    abstracted, generalized themes without clinical terminology.
    """
    themes: list[str] = Field(
        default_factory=list,
        description="Generalized themes only (no clinical terms)"
    )
    exploration_areas: list[str] = Field(
        default_factory=list,
        description="Areas to explore (client-friendly language)"
    )
    session_focus: str = Field(
        default="",
        description="Suggested focus for the upcoming session"
    )

    # Context
    session_number: Optional[int] = Field(
        None,
        description="Session number for continuity"
    )
    client_name: Optional[str] = Field(
        None,
        description="Client first name for personalization"
    )


class AbstractedRungOutput(BaseModel):
    """
    Abstracted version of Rung output for Beth.

    This intermediate format strips all clinical terminology
    and specific framework names before passing to Beth.
    """
    themes: list[str] = Field(
        default_factory=list,
        description="Generalized themes (e.g., 'communication patterns')"
    )
    exploration_areas: list[str] = Field(
        default_factory=list,
        description="Areas to explore in accessible language"
    )
    session_focus: str = Field(
        default="",
        description="Main focus area for the session"
    )

    # What is explicitly EXCLUDED:
    # - Framework names (no "avoidant attachment", just "connection patterns")
    # - Defense mechanism labels (no "intellectualization")
    # - Risk flags (therapist only)
    # - Clinical terminology
    # - Specific quotes from sessions
