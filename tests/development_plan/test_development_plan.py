"""
Development Plan Tests for Phase 3B

Tests verify:
1. Perceptor client save/load/search
2. Sprint planner SMART goal generation
3. Development plan API endpoints
4. Longitudinal context retrieval
5. E2E post-session workflow
"""

import json
import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Set test environment variables
os.environ["AWS_REGION"] = "us-east-1"

from src.services.perceptor_client import (
    PerceptorClient,
    PerceptorContext,
    PerceptorSearchResult,
    PerceptorClientError,
)
from src.services.sprint_planner import (
    SprintPlanner,
    SprintPlan,
    SMARTGoal,
    Exercise,
    SprintPlannerError,
    FRAMEWORK_EXERCISES,
)
from src.services.framework_extractor import (
    FrameworkExtractionOutput,
    HomeworkAssignment,
)
from src.services.bedrock_client import BedrockClient, BedrockResponse


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_perceptor_dir():
    """Create a temporary directory for Perceptor storage."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def perceptor_client(temp_perceptor_dir):
    """Create Perceptor client with temp storage."""
    return PerceptorClient(base_path=temp_perceptor_dir)


@pytest.fixture
def sample_extraction():
    """Sample framework extraction output."""
    return FrameworkExtractionOutput(
        frameworks_discussed=["Attachment Theory", "CBT"],
        modalities_used=["CBT", "Mindfulness"],
        homework_assigned=[
            HomeworkAssignment(task="Journal daily", due="next session"),
        ],
        breakthroughs=["Client recognized avoidance pattern"],
        progress_indicators=["Increased emotional awareness"],
        areas_for_next_session=["Explore childhood experiences"],
        session_summary="Productive session focused on attachment patterns.",
        extraction_confidence=0.85,
    )


@pytest.fixture
def sample_sprint_response():
    """Sample sprint planning response from Claude."""
    return {
        "goals": [
            {
                "goal": "Increase awareness of attachment triggers",
                "metric": "Daily journaling completion",
                "target": "5 out of 7 days",
            },
            {
                "goal": "Practice grounding techniques during anxiety",
                "metric": "Self-report of technique usage",
                "target": "Use technique 3 times this week",
            },
        ],
        "exercises": [
            {
                "name": "Attachment Awareness Journal",
                "frequency": "Daily",
                "description": "Record moments when attachment anxiety arises",
                "framework": "Attachment Theory",
            },
            {
                "name": "5-4-3-2-1 Grounding",
                "frequency": "As needed",
                "description": "Use 5 senses to ground during anxiety",
                "framework": "CBT",
            },
        ],
        "reflection_prompts": [
            "What triggered my anxiety this week?",
            "How did I respond differently than before?",
        ],
        "progress_summary": "Building on last sprint's focus on awareness.",
    }


@pytest.fixture
def mock_bedrock_client(sample_sprint_response):
    """Create mock Bedrock client."""
    mock_client = MagicMock(spec=BedrockClient)
    mock_response = BedrockResponse(
        content=json.dumps(sample_sprint_response),
        input_tokens=500,
        output_tokens=600,
        stop_reason="end_turn",
        model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    )
    mock_client.invoke_with_json_output.return_value = (
        sample_sprint_response,
        mock_response,
    )
    return mock_client


# =============================================================================
# Perceptor Client Tests
# =============================================================================

class TestPerceptorClient:
    """Test Perceptor client functionality."""

    def test_client_initialization(self, temp_perceptor_dir):
        """Test client initializes correctly."""
        client = PerceptorClient(base_path=temp_perceptor_dir)
        assert client.base_path == temp_perceptor_dir

        # Verify directories created
        assert os.path.exists(os.path.join(temp_perceptor_dir, "contexts"))
        assert os.path.exists(os.path.join(temp_perceptor_dir, "index.json"))

    def test_save_context(self, perceptor_client):
        """Test saving a context."""
        context = perceptor_client.save_context(
            title="Test Context",
            content="Test content here",
            summary="A test summary",
            tags=["test", "unit-test"],
            client_id="client-123",
            session_id="session-456",
            agent="rung",
            stage="post-session",
        )

        assert isinstance(context, PerceptorContext)
        assert context.title == "Test Context"
        assert "test" in context.tags
        assert "rung" in context.tags
        assert "post-session" in context.tags
        assert "client:client-123" in context.tags

    def test_save_empty_title_raises(self, perceptor_client):
        """Test saving with empty title raises error."""
        with pytest.raises(PerceptorClientError):
            perceptor_client.save_context(
                title="",
                content="Content",
                summary="Summary",
                tags=[],
            )

    def test_save_empty_content_raises(self, perceptor_client):
        """Test saving with empty content raises error."""
        with pytest.raises(PerceptorClientError):
            perceptor_client.save_context(
                title="Title",
                content="",
                summary="Summary",
                tags=[],
            )

    def test_load_context(self, perceptor_client):
        """Test loading a saved context."""
        saved = perceptor_client.save_context(
            title="Load Test",
            content="Content to load",
            summary="Summary",
            tags=["load-test"],
        )

        loaded = perceptor_client.load_context(saved.id)
        assert loaded.id == saved.id
        assert loaded.title == "Load Test"
        assert loaded.content == "Content to load"

    def test_load_nonexistent_raises(self, perceptor_client):
        """Test loading nonexistent context raises error."""
        with pytest.raises(PerceptorClientError):
            perceptor_client.load_context("nonexistent-id")

    def test_list_contexts(self, perceptor_client):
        """Test listing contexts."""
        # Save multiple contexts
        perceptor_client.save_context(
            title="Context 1",
            content="Content 1",
            summary="Summary 1",
            tags=["tag-a"],
        )
        perceptor_client.save_context(
            title="Context 2",
            content="Content 2",
            summary="Summary 2",
            tags=["tag-b"],
        )

        results = perceptor_client.list_contexts()
        assert len(results) == 2

    def test_list_contexts_with_tag_filter(self, perceptor_client):
        """Test listing contexts with tag filter."""
        perceptor_client.save_context(
            title="Tagged",
            content="Content",
            summary="Summary",
            tags=["special-tag"],
        )
        perceptor_client.save_context(
            title="Not Tagged",
            content="Content",
            summary="Summary",
            tags=["other-tag"],
        )

        results = perceptor_client.list_contexts(tags=["special-tag"])
        assert len(results) == 1
        assert results[0].title == "Tagged"

    def test_list_contexts_by_client_id(self, perceptor_client):
        """Test listing contexts by client ID."""
        perceptor_client.save_context(
            title="Client A",
            content="Content",
            summary="Summary",
            tags=[],
            client_id="client-a",
        )
        perceptor_client.save_context(
            title="Client B",
            content="Content",
            summary="Summary",
            tags=[],
            client_id="client-b",
        )

        results = perceptor_client.list_contexts(client_id="client-a")
        assert len(results) == 1
        assert results[0].title == "Client A"

    def test_search_contexts(self, perceptor_client):
        """Test searching contexts."""
        perceptor_client.save_context(
            title="Attachment Theory Discussion",
            content="We discussed attachment patterns in relationships.",
            summary="Session about attachment",
            tags=["attachment"],
        )
        perceptor_client.save_context(
            title="CBT Session",
            content="Focused on cognitive distortions.",
            summary="CBT work",
            tags=["cbt"],
        )

        results = perceptor_client.search_contexts("attachment")
        assert len(results) >= 1
        assert any("attachment" in r.title.lower() for r in results)

    def test_search_empty_query_raises(self, perceptor_client):
        """Test searching with empty query raises error."""
        with pytest.raises(PerceptorClientError):
            perceptor_client.search_contexts("")

    def test_get_client_history(self, perceptor_client):
        """Test getting client history."""
        client_id = str(uuid4())

        perceptor_client.save_context(
            title="Session 1",
            content="First session",
            summary="Summary 1",
            tags=[],
            client_id=client_id,
        )
        perceptor_client.save_context(
            title="Session 2",
            content="Second session",
            summary="Summary 2",
            tags=[],
            client_id=client_id,
        )

        history = perceptor_client.get_client_history(client_id)
        assert len(history) == 2

    def test_save_session_context(self, perceptor_client):
        """Test convenience method for saving session context."""
        context = perceptor_client.save_session_context(
            session_id=str(uuid4()),
            client_id=str(uuid4()),
            agent="rung",
            stage="post-session",
            frameworks=["Attachment Theory", "CBT"],
            insights=["Client showed insight"],
            summary="Good session",
        )

        assert "Rung" in context.title
        assert "post-session" in context.tags
        assert "rung" in context.tags

    def test_get_longitudinal_patterns(self, perceptor_client):
        """Test longitudinal pattern analysis."""
        client_id = str(uuid4())

        # Create multiple sessions with recurring themes
        for i in range(3):
            perceptor_client.save_context(
                title=f"Session {i}",
                content=f"Session content {i}",
                summary=f"Summary {i}",
                tags=["attachment", "anxiety"],
                client_id=client_id,
            )

        patterns = perceptor_client.get_longitudinal_patterns(client_id)

        assert patterns["client_id"] == client_id
        assert patterns["session_count"] == 3
        assert len(patterns["recurring_themes"]) > 0


# =============================================================================
# Sprint Planner Tests
# =============================================================================

class TestSprintPlanner:
    """Test sprint planner functionality."""

    def test_planner_initialization(self, mock_bedrock_client):
        """Test planner initializes correctly."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)
        assert planner.temperature == SprintPlanner.DEFAULT_TEMPERATURE

    def test_create_sprint_plan(self, mock_bedrock_client, sample_extraction):
        """Test creating a sprint plan."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        plan = planner.create_sprint_plan(
            client_id=str(uuid4()),
            session_id=str(uuid4()),
            extraction=sample_extraction,
            sprint_number=1,
        )

        assert isinstance(plan, SprintPlan)
        assert len(plan.goals) >= 1
        assert len(plan.exercises) >= 1
        assert plan.sprint_number == 1

    def test_create_sprint_plan_empty_client_raises(
        self, mock_bedrock_client, sample_extraction
    ):
        """Test creating plan with empty client ID raises error."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        with pytest.raises(SprintPlannerError):
            planner.create_sprint_plan(
                client_id="",
                session_id=str(uuid4()),
                extraction=sample_extraction,
            )

    def test_create_sprint_plan_empty_session_raises(
        self, mock_bedrock_client, sample_extraction
    ):
        """Test creating plan with empty session ID raises error."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        with pytest.raises(SprintPlannerError):
            planner.create_sprint_plan(
                client_id=str(uuid4()),
                session_id="",
                extraction=sample_extraction,
            )

    def test_create_quick_plan(self, mock_bedrock_client, sample_extraction):
        """Test quick plan creation without AI call."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        plan = planner.create_quick_plan(
            client_id=str(uuid4()),
            session_id=str(uuid4()),
            extraction=sample_extraction,
            sprint_number=1,
        )

        assert isinstance(plan, SprintPlan)
        assert len(plan.goals) >= 1
        assert len(plan.exercises) >= 1

        # Verify Bedrock was NOT called
        mock_bedrock_client.invoke_with_json_output.assert_not_called()

    def test_framework_exercises_mapping(self):
        """Test framework to exercise mapping."""
        assert "attachment theory" in FRAMEWORK_EXERCISES
        assert "cbt" in FRAMEWORK_EXERCISES
        assert "dbt" in FRAMEWORK_EXERCISES
        assert "mindfulness" in FRAMEWORK_EXERCISES

    def test_goals_have_smart_structure(
        self, mock_bedrock_client, sample_extraction
    ):
        """Test that goals follow SMART structure."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        plan = planner.create_sprint_plan(
            client_id=str(uuid4()),
            session_id=str(uuid4()),
            extraction=sample_extraction,
        )

        for goal in plan.goals:
            assert goal.goal  # Specific
            assert goal.metric  # Measurable
            assert goal.target  # Achievable/Time-bound

    def test_assess_progress(self, mock_bedrock_client, sample_extraction):
        """Test progress assessment."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)

        # Create a sprint
        sprint = planner.create_quick_plan(
            client_id=str(uuid4()),
            session_id=str(uuid4()),
            extraction=sample_extraction,
        )

        # Create new extraction with progress
        new_extraction = FrameworkExtractionOutput(
            frameworks_discussed=["Attachment Theory", "Mindfulness"],
            breakthroughs=["Major insight achieved"],
            progress_indicators=["Better awareness", "Using techniques"],
        )

        assessment = planner.assess_progress(sprint, new_extraction)

        assert "sprint_id" in assessment
        assert "progress_score" in assessment
        assert "summary" in assessment
        assert assessment["breakthroughs_reported"] == 1


class TestSMARTGoal:
    """Test SMARTGoal model."""

    def test_goal_creation(self):
        """Test SMART goal creation."""
        goal = SMARTGoal(
            goal="Increase self-awareness",
            metric="Daily check-ins",
            target="5 out of 7 days",
        )
        assert goal.goal == "Increase self-awareness"
        assert goal.timeframe == "1-2 weeks"


class TestExercise:
    """Test Exercise model."""

    def test_exercise_creation(self):
        """Test exercise creation."""
        exercise = Exercise(
            name="Journaling",
            frequency="Daily",
            description="Write about feelings",
            framework="CBT",
        )
        assert exercise.name == "Journaling"
        assert exercise.framework == "CBT"

    def test_exercise_optional_framework(self):
        """Test exercise with optional framework."""
        exercise = Exercise(
            name="Breathing",
            frequency="Daily",
            description="Practice deep breathing",
        )
        assert exercise.framework is None


class TestSprintPlan:
    """Test SprintPlan model."""

    def test_sprint_plan_creation(self):
        """Test sprint plan creation."""
        plan = SprintPlan(
            client_id=str(uuid4()),
            session_id=str(uuid4()),
            sprint_number=1,
            goals=[SMARTGoal(goal="Test", metric="Test", target="Test")],
            exercises=[
                Exercise(name="Test", frequency="Daily", description="Test")
            ],
            reflection_prompts=["What did you learn?"],
        )

        assert plan.sprint_number == 1
        assert plan.duration_days == 14
        assert len(plan.goals) == 1


# =============================================================================
# Development Plan API Tests
# =============================================================================

class TestDevelopmentPlanAPI:
    """Test development plan API endpoints."""

    @pytest.fixture(autouse=True)
    def skip_if_no_fastapi(self):
        """Skip API tests if fastapi not installed."""
        pytest.importorskip("fastapi")

    def test_api_module_imports(self):
        """Test API module imports correctly."""
        from src.api.development_plan import (
            router,
            get_sprint_planner,
            set_sprint_planner,
            get_perceptor_client,
            set_perceptor_client,
        )
        assert router is not None

    def test_response_models(self):
        """Test response model imports."""
        from src.api.development_plan import (
            SprintPlanResponse,
            SprintHistoryResponse,
            ProgressAssessmentResponse,
            GenerateSprintRequest,
            GenerateSprintResponse,
        )

        # Test SprintPlanResponse
        response = SprintPlanResponse(
            id="test-id",
            client_id="client-id",
            session_id="session-id",
            sprint_number=1,
            duration_days=14,
            goals=[],
            exercises=[],
            reflection_prompts=[],
            frameworks_addressed=[],
            created_at="2024-01-01T00:00:00",
        )
        assert response.id == "test-id"

    def test_generate_request_model(self):
        """Test generate sprint request model."""
        from src.api.development_plan import GenerateSprintRequest

        request = GenerateSprintRequest(
            session_id=str(uuid4()),
            frameworks_discussed=["CBT"],
            breakthroughs=["Insight"],
        )
        assert len(request.frameworks_discussed) == 1


# =============================================================================
# File Structure Tests
# =============================================================================

class TestFileStructure:
    """Test that all required files exist."""

    def test_perceptor_client_exists(self):
        """Verify perceptor_client.py exists."""
        assert os.path.exists("src/services/perceptor_client.py")

    def test_sprint_planner_exists(self):
        """Verify sprint_planner.py exists."""
        assert os.path.exists("src/services/sprint_planner.py")

    def test_development_plan_api_exists(self):
        """Verify development_plan.py exists."""
        assert os.path.exists("src/api/development_plan.py")

    def test_post_session_workflow_exists(self):
        """Verify post_session.json workflow exists."""
        assert os.path.exists("n8n.deprecated/workflows/post_session.json")


# =============================================================================
# Integration Tests
# =============================================================================

class TestDevelopmentPlanIntegration:
    """Integration tests for development planning."""

    def test_full_planning_workflow(
        self, mock_bedrock_client, sample_extraction, temp_perceptor_dir
    ):
        """Test complete planning workflow."""
        # Create services
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)
        perceptor = PerceptorClient(base_path=temp_perceptor_dir)

        client_id = str(uuid4())
        session_id = str(uuid4())

        # Generate sprint plan
        plan = planner.create_sprint_plan(
            client_id=client_id,
            session_id=session_id,
            extraction=sample_extraction,
            sprint_number=1,
        )

        # Archive to Perceptor
        context = perceptor.save_context(
            title=f"Sprint Plan #{plan.sprint_number}",
            content=json.dumps(plan.model_dump()),
            summary=f"Sprint with {len(plan.goals)} goals",
            tags=["sprint-plan"],
            client_id=client_id,
            session_id=session_id,
            agent="rung",
            stage="post-session",
        )

        # Verify retrieval
        loaded = perceptor.load_context(context.id)
        loaded_plan = SprintPlan(**json.loads(loaded.content))

        assert loaded_plan.sprint_number == plan.sprint_number
        assert len(loaded_plan.goals) == len(plan.goals)

    def test_longitudinal_sprint_tracking(
        self, mock_bedrock_client, sample_extraction, temp_perceptor_dir
    ):
        """Test tracking sprints over time."""
        planner = SprintPlanner(bedrock_client=mock_bedrock_client)
        perceptor = PerceptorClient(base_path=temp_perceptor_dir)

        client_id = str(uuid4())

        # Create multiple sprints
        for i in range(3):
            session_id = str(uuid4())

            plan = planner.create_quick_plan(
                client_id=client_id,
                session_id=session_id,
                extraction=sample_extraction,
                sprint_number=i + 1,
            )

            perceptor.save_context(
                title=f"Sprint Plan #{i + 1}",
                content=json.dumps(plan.model_dump()),
                summary=f"Sprint {i + 1}",
                tags=["sprint-plan"],
                client_id=client_id,
                session_id=session_id,
            )

        # Verify all sprints retrievable
        history = perceptor.list_contexts(
            tags=["sprint-plan"],
            client_id=client_id,
        )

        assert len(history) == 3

    def test_n8n_workflow_valid_json(self):
        """Test n8n workflow is valid JSON."""
        with open("n8n.deprecated/workflows/post_session.json", "r") as f:
            workflow = json.load(f)

        assert "name" in workflow
        assert "nodes" in workflow
        assert "connections" in workflow
        assert workflow["name"] == "Rung Post-Session Workflow"

    def test_n8n_workflow_has_required_nodes(self):
        """Test n8n workflow has required nodes."""
        with open("n8n.deprecated/workflows/post_session.json", "r") as f:
            workflow = json.load(f)

        node_names = [n["name"] for n in workflow["nodes"]]

        required_nodes = [
            "Webhook Trigger",
            "Submit Notes for Processing",
            "Get Framework Extraction",
            "Generate Sprint Plan",
            "Archive to Perceptor",
            "Slack Notification",
        ]

        for required in required_nodes:
            assert required in node_names, f"Missing node: {required}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
