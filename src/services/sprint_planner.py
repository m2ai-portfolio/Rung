"""
Sprint Planner Service

Generates development plans from framework extraction:
- SMART goal generation
- Exercise recommendations based on frameworks
- 1-2 week sprint planning
- Cumulative progress tracking
"""

import os
from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from src.services.bedrock_client import BedrockClient, BedrockClientError
from src.services.framework_extractor import FrameworkExtractionOutput


class SMARTGoal(BaseModel):
    """A SMART goal for the development plan."""
    goal: str = Field(..., description="The goal statement")
    metric: str = Field(..., description="How progress will be measured")
    target: str = Field(..., description="Specific target to achieve")
    timeframe: str = Field(default="1-2 weeks", description="Timeframe for goal")


class Exercise(BaseModel):
    """A recommended exercise."""
    name: str = Field(..., description="Exercise name")
    frequency: str = Field(..., description="How often to practice")
    description: str = Field(..., description="Exercise description")
    framework: Optional[str] = Field(None, description="Related framework")


class SprintPlan(BaseModel):
    """A development sprint plan."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    client_id: str = Field(..., description="Client ID")
    session_id: str = Field(..., description="Session ID that triggered this plan")
    sprint_number: int = Field(..., description="Sprint number for this client")
    duration_days: int = Field(default=14, description="Sprint duration")
    goals: list[SMARTGoal] = Field(default_factory=list)
    exercises: list[Exercise] = Field(default_factory=list)
    reflection_prompts: list[str] = Field(default_factory=list)
    progress_from_last_sprint: Optional[str] = Field(None)
    frameworks_addressed: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SprintPlannerError(Exception):
    """Exception for sprint planning errors."""
    pass


# Framework to exercise mapping
FRAMEWORK_EXERCISES = {
    "attachment theory": [
        Exercise(
            name="Secure Base Journaling",
            frequency="Daily",
            description="Write about moments when you felt emotionally safe or supported.",
            framework="Attachment Theory"
        ),
        Exercise(
            name="Attachment Awareness Practice",
            frequency="2-3 times per week",
            description="Notice and record your attachment responses in relationships.",
            framework="Attachment Theory"
        ),
    ],
    "cbt": [
        Exercise(
            name="Thought Record",
            frequency="Daily",
            description="Document automatic thoughts, identify cognitive distortions, and reframe.",
            framework="CBT"
        ),
        Exercise(
            name="Behavioral Experiment",
            frequency="Weekly",
            description="Test a negative prediction with a small, safe experiment.",
            framework="CBT"
        ),
    ],
    "dbt": [
        Exercise(
            name="TIPP Skills Practice",
            frequency="As needed",
            description="Practice Temperature, Intense exercise, Paced breathing, Paired muscle relaxation.",
            framework="DBT"
        ),
        Exercise(
            name="Opposite Action",
            frequency="3 times per week",
            description="When experiencing an unhelpful emotion, act opposite to its urge.",
            framework="DBT"
        ),
    ],
    "mindfulness": [
        Exercise(
            name="5-Minute Breathing",
            frequency="Daily",
            description="Practice focused breathing for 5 minutes each morning.",
            framework="Mindfulness"
        ),
        Exercise(
            name="Body Scan",
            frequency="3 times per week",
            description="Complete a 10-minute progressive body scan relaxation.",
            framework="Mindfulness"
        ),
    ],
    "gottman": [
        Exercise(
            name="Daily Appreciation",
            frequency="Daily",
            description="Express one specific appreciation to your partner each day.",
            framework="Gottman Method"
        ),
        Exercise(
            name="Stress-Reducing Conversation",
            frequency="Daily (20 mins)",
            description="Practice active listening about external stressors without problem-solving.",
            framework="Gottman Method"
        ),
    ],
    "eft": [
        Exercise(
            name="Emotion Naming",
            frequency="Daily",
            description="Identify and name primary emotions beneath surface reactions.",
            framework="EFT"
        ),
        Exercise(
            name="Soft Start-Up Practice",
            frequency="As needed",
            description="Begin difficult conversations with 'I feel...' statements.",
            framework="EFT"
        ),
    ],
}

# System prompt for sprint planning
SPRINT_PLANNING_PROMPT = """You are a clinical development planning assistant that creates personalized growth sprints based on therapy session insights.

Your task is to generate a development sprint plan that:
1. Creates 2-4 SMART goals based on the session insights
2. Recommends specific exercises aligned with the frameworks discussed
3. Provides reflection prompts for self-exploration
4. Acknowledges progress from previous sprints (if provided)

Output MUST be valid JSON matching this structure:
```json
{
  "goals": [
    {"goal": "string", "metric": "string", "target": "string"}
  ],
  "exercises": [
    {"name": "string", "frequency": "string", "description": "string", "framework": "string"}
  ],
  "reflection_prompts": ["string"],
  "progress_summary": "string describing progress from last sprint or null"
}
```

Keep goals specific, measurable, and achievable within 1-2 weeks.
Keep language supportive and growth-oriented.
"""


class SprintPlanner:
    """
    Plans development sprints from session framework extraction.

    Generates:
    - SMART goals based on session insights
    - Exercises aligned with therapeutic frameworks
    - Reflection prompts
    - Progress tracking across sprints
    """

    DEFAULT_TEMPERATURE = 0.4
    DEFAULT_MAX_TOKENS = 2048
    DEFAULT_DURATION_DAYS = 14

    def __init__(
        self,
        bedrock_client: Optional[BedrockClient] = None,
        temperature: float = DEFAULT_TEMPERATURE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize sprint planner.

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

    def create_sprint_plan(
        self,
        client_id: str,
        session_id: str,
        extraction: FrameworkExtractionOutput,
        sprint_number: int = 1,
        previous_sprint: Optional[SprintPlan] = None,
        duration_days: int = DEFAULT_DURATION_DAYS,
    ) -> SprintPlan:
        """
        Create a development sprint plan from session extraction.

        Args:
            client_id: Client ID
            session_id: Session ID
            extraction: Framework extraction from session notes
            sprint_number: Sprint number for this client
            previous_sprint: Optional previous sprint for progress tracking
            duration_days: Sprint duration in days

        Returns:
            SprintPlan with goals, exercises, and reflection prompts

        Raises:
            SprintPlannerError: If planning fails
        """
        if not client_id or not client_id.strip():
            raise SprintPlannerError("Client ID cannot be empty")

        if not session_id or not session_id.strip():
            raise SprintPlannerError("Session ID cannot be empty")

        # Build context for Claude
        context_parts = [
            "## Session Insights",
            "",
            "### Frameworks Discussed",
            *[f"- {f}" for f in extraction.frameworks_discussed],
            "",
            "### Modalities Used",
            *[f"- {m}" for m in extraction.modalities_used],
            "",
            "### Breakthroughs",
            *[f"- {b}" for b in extraction.breakthroughs],
            "",
            "### Progress Indicators",
            *[f"- {p}" for p in extraction.progress_indicators],
            "",
            "### Areas for Next Session",
            *[f"- {a}" for a in extraction.areas_for_next_session],
        ]

        if extraction.session_summary:
            context_parts.extend(["", "### Summary", extraction.session_summary])

        if previous_sprint:
            context_parts.extend([
                "",
                "## Previous Sprint Goals",
                *[f"- {g.goal} (target: {g.target})" for g in previous_sprint.goals],
            ])

        user_message = f"""Create a {duration_days}-day development sprint plan based on these session insights:

{chr(10).join(context_parts)}

Generate 2-4 SMART goals, recommend exercises, and provide reflection prompts.
Respond with valid JSON only."""

        try:
            parsed_json, response = self.bedrock_client.invoke_with_json_output(
                system_prompt=SPRINT_PLANNING_PROMPT,
                user_message=user_message,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

            return self._build_sprint_plan(
                parsed_json,
                client_id=client_id,
                session_id=session_id,
                sprint_number=sprint_number,
                duration_days=duration_days,
                extraction=extraction,
            )

        except BedrockClientError as e:
            raise SprintPlannerError(f"Sprint planning failed: {str(e)}") from e

    def _build_sprint_plan(
        self,
        data: dict,
        client_id: str,
        session_id: str,
        sprint_number: int,
        duration_days: int,
        extraction: FrameworkExtractionOutput,
    ) -> SprintPlan:
        """Build SprintPlan from parsed JSON."""
        # Parse goals
        goals = []
        for g in data.get("goals", []):
            if isinstance(g, dict):
                goals.append(SMARTGoal(
                    goal=g.get("goal", ""),
                    metric=g.get("metric", "self-report"),
                    target=g.get("target", "improvement"),
                ))

        # Parse exercises
        exercises = []
        for e in data.get("exercises", []):
            if isinstance(e, dict):
                exercises.append(Exercise(
                    name=e.get("name", ""),
                    frequency=e.get("frequency", "as needed"),
                    description=e.get("description", ""),
                    framework=e.get("framework"),
                ))

        # Add framework-based exercises if not enough
        if len(exercises) < 2:
            exercises.extend(
                self._get_framework_exercises(extraction.frameworks_discussed)
            )

        # Parse reflection prompts
        prompts = data.get("reflection_prompts", [])
        if not prompts:
            prompts = self._generate_default_prompts(extraction)

        return SprintPlan(
            client_id=client_id,
            session_id=session_id,
            sprint_number=sprint_number,
            duration_days=duration_days,
            goals=goals,
            exercises=exercises[:6],  # Limit to 6 exercises
            reflection_prompts=prompts[:5],  # Limit to 5 prompts
            progress_from_last_sprint=data.get("progress_summary"),
            frameworks_addressed=extraction.frameworks_discussed,
        )

    def _get_framework_exercises(
        self,
        frameworks: list[str],
    ) -> list[Exercise]:
        """Get exercises based on frameworks."""
        exercises = []

        for framework in frameworks:
            framework_lower = framework.lower()

            # Check for matches
            for key, exercise_list in FRAMEWORK_EXERCISES.items():
                if key in framework_lower or framework_lower in key:
                    exercises.extend(exercise_list[:2])
                    break

        return exercises[:4]  # Return max 4

    def _generate_default_prompts(
        self,
        extraction: FrameworkExtractionOutput,
    ) -> list[str]:
        """Generate default reflection prompts."""
        prompts = [
            "What patterns did you notice in yourself this week?",
            "What was one moment when you responded differently than usual?",
        ]

        if extraction.breakthroughs:
            prompts.append(
                f"Reflect on your insight about: {extraction.breakthroughs[0]}"
            )

        if extraction.areas_for_next_session:
            prompts.append(
                f"What thoughts or feelings come up when you consider: {extraction.areas_for_next_session[0]}?"
            )

        return prompts

    def create_quick_plan(
        self,
        client_id: str,
        session_id: str,
        extraction: FrameworkExtractionOutput,
        sprint_number: int = 1,
    ) -> SprintPlan:
        """
        Create a quick sprint plan without Claude call.

        Uses predefined exercises based on frameworks.

        Args:
            client_id: Client ID
            session_id: Session ID
            extraction: Framework extraction
            sprint_number: Sprint number

        Returns:
            SprintPlan with framework-based exercises
        """
        if not client_id or not client_id.strip():
            raise SprintPlannerError("Client ID cannot be empty")

        # Get framework exercises
        exercises = self._get_framework_exercises(extraction.frameworks_discussed)

        # Generate goals from extraction
        goals = []

        if extraction.areas_for_next_session:
            for area in extraction.areas_for_next_session[:2]:
                goals.append(SMARTGoal(
                    goal=f"Explore and reflect on {area.lower()}",
                    metric="Journal entries and session discussion",
                    target="Increased awareness and insight",
                ))

        if extraction.breakthroughs:
            goals.append(SMARTGoal(
                goal=f"Build on insight: {extraction.breakthroughs[0]}",
                metric="Application of insight in daily life",
                target="2-3 instances of applying this awareness",
            ))

        # Default goals if none generated
        if not goals:
            goals = [
                SMARTGoal(
                    goal="Increase self-awareness of emotional patterns",
                    metric="Daily check-in completion",
                    target="5 out of 7 days",
                ),
                SMARTGoal(
                    goal="Practice therapeutic techniques learned in session",
                    metric="Exercise completion log",
                    target="Complete assigned exercises 3 times",
                ),
            ]

        # Generate prompts
        prompts = self._generate_default_prompts(extraction)

        return SprintPlan(
            client_id=client_id,
            session_id=session_id,
            sprint_number=sprint_number,
            duration_days=14,
            goals=goals,
            exercises=exercises,
            reflection_prompts=prompts,
            frameworks_addressed=extraction.frameworks_discussed,
        )

    def assess_progress(
        self,
        current_sprint: SprintPlan,
        new_extraction: FrameworkExtractionOutput,
    ) -> dict:
        """
        Assess progress based on new session extraction.

        Args:
            current_sprint: The sprint being assessed
            new_extraction: Extraction from new session

        Returns:
            Progress assessment dictionary
        """
        # Check for framework coverage
        frameworks_from_sprint = set(
            f.lower() for f in current_sprint.frameworks_addressed
        )
        frameworks_discussed = set(
            f.lower() for f in new_extraction.frameworks_discussed
        )

        continued_themes = frameworks_from_sprint & frameworks_discussed
        new_themes = frameworks_discussed - frameworks_from_sprint

        # Build assessment
        assessment = {
            "sprint_id": current_sprint.id,
            "goals_count": len(current_sprint.goals),
            "exercises_count": len(current_sprint.exercises),
            "continued_themes": list(continued_themes),
            "new_themes": list(new_themes),
            "breakthroughs_reported": len(new_extraction.breakthroughs),
            "progress_indicators": len(new_extraction.progress_indicators),
        }

        # Calculate simple progress score
        score = 0
        if new_extraction.breakthroughs:
            score += 30
        if new_extraction.progress_indicators:
            score += 20 * len(new_extraction.progress_indicators)
        if continued_themes:
            score += 10 * len(continued_themes)

        assessment["progress_score"] = min(score, 100)
        assessment["summary"] = self._generate_progress_summary(assessment)

        return assessment

    def _generate_progress_summary(self, assessment: dict) -> str:
        """Generate a human-readable progress summary."""
        parts = []

        if assessment["breakthroughs_reported"] > 0:
            parts.append(
                f"{assessment['breakthroughs_reported']} breakthrough(s) achieved"
            )

        if assessment["progress_indicators"] > 0:
            parts.append(
                f"{assessment['progress_indicators']} progress indicator(s) noted"
            )

        if assessment["continued_themes"]:
            parts.append(
                f"Continued work on: {', '.join(assessment['continued_themes'][:3])}"
            )

        if assessment["new_themes"]:
            parts.append(
                f"New areas explored: {', '.join(assessment['new_themes'][:3])}"
            )

        if not parts:
            return "Steady progress maintained"

        return ". ".join(parts) + "."
