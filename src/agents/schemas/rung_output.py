"""
Rung Agent Output Schema

Defines the structured output format for the Rung clinical analysis agent.
All outputs are validated with Pydantic for type safety.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Risk level classification for clinical flags."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AttachmentStyle(str, Enum):
    """Attachment pattern classifications."""
    SECURE = "secure"
    ANXIOUS = "anxious"
    AVOIDANT = "avoidant"
    DISORGANIZED = "disorganized"


class DefenseMechanismType(str, Enum):
    """Common defense mechanisms in therapy contexts."""
    INTELLECTUALIZATION = "intellectualization"
    PROJECTION = "projection"
    DENIAL = "denial"
    RATIONALIZATION = "rationalization"
    DISPLACEMENT = "displacement"
    REGRESSION = "regression"
    REPRESSION = "repression"
    SUBLIMATION = "sublimation"
    REACTION_FORMATION = "reaction_formation"
    SPLITTING = "splitting"
    PASSIVE_AGGRESSION = "passive_aggression"
    AVOIDANCE = "avoidance"


class CommunicationPattern(str, Enum):
    """Gottman Four Horsemen and related patterns."""
    CRITICISM = "criticism"
    CONTEMPT = "contempt"
    DEFENSIVENESS = "defensiveness"
    STONEWALLING = "stonewalling"
    FLOODING = "flooding"
    REPAIR_ATTEMPT = "repair_attempt"


class RelationshipDynamic(str, Enum):
    """Common relationship dynamic patterns."""
    PURSUER_DISTANCER = "pursuer_distancer"
    PARENT_CHILD = "parent_child"
    ENMESHMENT = "enmeshment"
    DISENGAGEMENT = "disengagement"
    POWER_IMBALANCE = "power_imbalance"
    CODEPENDENCY = "codependency"


class FrameworkIdentified(BaseModel):
    """A psychological framework identified in client input."""
    name: str = Field(
        ...,
        description="Name of the psychological framework or pattern"
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0-1.0) in the identification"
    )
    evidence: str = Field(
        ...,
        description="Specific evidence from the transcript supporting this identification"
    )
    category: Optional[str] = Field(
        None,
        description="Category of framework (attachment, defense, communication, relationship)"
    )


class DefenseMechanism(BaseModel):
    """A defense mechanism detected in client communication."""
    type: str = Field(
        ...,
        description="Type of defense mechanism"
    )
    indicators: list[str] = Field(
        default_factory=list,
        description="Specific phrases or behaviors indicating this mechanism"
    )
    context: Optional[str] = Field(
        None,
        description="Context in which the defense was observed"
    )


class RiskFlag(BaseModel):
    """A clinical risk flag requiring attention."""
    level: RiskLevel = Field(
        ...,
        description="Severity level of the risk"
    )
    description: str = Field(
        ...,
        description="Description of the risk concern"
    )
    recommended_action: Optional[str] = Field(
        None,
        description="Recommended clinical action for this flag"
    )


class RungAnalysisOutput(BaseModel):
    """
    Complete output from Rung clinical analysis agent.

    This is the primary output schema for pre-session analysis
    that will be provided to the therapist as a clinical brief.
    """
    frameworks_identified: list[FrameworkIdentified] = Field(
        default_factory=list,
        description="Psychological frameworks identified in the client input"
    )
    defense_mechanisms: list[DefenseMechanism] = Field(
        default_factory=list,
        description="Defense mechanisms detected in communication patterns"
    )
    risk_flags: list[RiskFlag] = Field(
        default_factory=list,
        description="Clinical risk flags requiring therapist attention"
    )
    key_themes: list[str] = Field(
        default_factory=list,
        description="Primary themes emerging from the client input"
    )
    suggested_exploration: list[str] = Field(
        default_factory=list,
        description="Areas recommended for therapeutic exploration"
    )
    session_questions: list[str] = Field(
        default_factory=list,
        description="Suggested questions for the upcoming session"
    )

    # Metadata
    analysis_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Overall confidence in the analysis"
    )
    raw_text_length: Optional[int] = Field(
        None,
        description="Length of the input text analyzed"
    )


class RungAnalysisRequest(BaseModel):
    """Input request for Rung analysis."""
    session_id: str = Field(
        ...,
        description="UUID of the therapy session"
    )
    client_id: str = Field(
        ...,
        description="UUID of the client"
    )
    transcript: str = Field(
        ...,
        description="Transcribed voice memo or text input from client"
    )
    historical_context: Optional[str] = Field(
        None,
        description="Previous session context from Perceptor (optional)"
    )
    session_number: Optional[int] = Field(
        None,
        description="Session number for longitudinal tracking"
    )
