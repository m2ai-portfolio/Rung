"""
Progress Analytics Tests

Tests verify:
1. ProgressMetric model creates with all fields
2. MetricType enum values
3. Pydantic schemas validate correctly
4. ProgressAnalytics service methods work with and without data
5. API endpoints enforce role-based access and return correct responses
"""

import asyncio
import os
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from uuid import UUID, uuid4

# Set test database before importing models
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models.progress_metric import (
    MetricType,
    ProgressMetric,
    ProgressMetricCreate,
    ProgressMetricRead,
)
from src.services.progress_analytics import ProgressAnalytics, ProgressAnalyticsError
from src.api import progress as progress_api


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=OFF")
        cursor.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_session_factory(test_engine):
    """Create session factory for tests."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def analytics(test_session_factory):
    """Create ProgressAnalytics with test DB."""
    return ProgressAnalytics(session_factory=test_session_factory)


@pytest.fixture
def analytics_no_db():
    """Create ProgressAnalytics without DB (empty defaults)."""
    return ProgressAnalytics(session_factory=None)


@pytest.fixture
def client_uuid():
    """Stable client UUID object for direct model tests."""
    return uuid4()


@pytest.fixture
def client_id(client_uuid):
    """Stable client ID as string for service tests."""
    return str(client_uuid)


@pytest.fixture
def session_uuid():
    """Stable session UUID object for direct model tests."""
    return uuid4()


@pytest.fixture
def session_id(session_uuid):
    """Stable session ID as string for service tests."""
    return str(session_uuid)


# =============================================================================
# Model Tests
# =============================================================================

class TestProgressMetricModel:
    """Test ProgressMetric SQLAlchemy model."""

    def test_create_progress_metric(self, test_session_factory, client_uuid, session_uuid):
        """Test creating a ProgressMetric with all fields."""
        db = test_session_factory()
        metric = ProgressMetric(
            id=uuid4(),
            client_id=client_uuid,
            session_id=session_uuid,
            metric_type=MetricType.SESSION_ENGAGEMENT,
            value=0.85,
            metadata_json={"notes": "good engagement"},
            measured_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)

        assert metric.id is not None
        assert metric.client_id == client_uuid
        assert metric.session_id == session_uuid
        assert metric.metric_type == MetricType.SESSION_ENGAGEMENT
        assert metric.value == 0.85
        assert metric.metadata_json["notes"] == "good engagement"
        assert metric.measured_at is not None
        assert metric.created_at is not None
        db.close()

    def test_create_metric_without_session(self, test_session_factory, client_uuid):
        """Test creating a metric without a session_id."""
        db = test_session_factory()
        metric = ProgressMetric(
            id=uuid4(),
            client_id=client_uuid,
            session_id=None,
            metric_type=MetricType.RISK_LEVEL,
            value=0.3,
            measured_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()

        assert metric.session_id is None
        assert metric.metric_type == MetricType.RISK_LEVEL
        db.close()

    def test_create_metric_without_metadata(self, test_session_factory, client_uuid):
        """Test creating a metric without metadata_json."""
        db = test_session_factory()
        metric = ProgressMetric(
            id=uuid4(),
            client_id=client_uuid,
            metric_type=MetricType.HOMEWORK_COMPLETION,
            value=1.0,
            metadata_json=None,
            measured_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )
        db.add(metric)
        db.commit()

        assert metric.metadata_json is None
        db.close()

    def test_repr(self, test_session_factory, client_uuid):
        """Test ProgressMetric __repr__."""
        metric = ProgressMetric(
            id=uuid4(),
            client_id=client_uuid,
            metric_type=MetricType.SESSION_ENGAGEMENT,
            value=0.5,
        )
        assert "ProgressMetric" in repr(metric)
        assert "SESSION_ENGAGEMENT" in repr(metric) or "session_engagement" in repr(metric)


class TestMetricTypeEnum:
    """Test MetricType enum values."""

    def test_all_metric_types_exist(self):
        """Verify all expected metric types."""
        expected = {
            "session_engagement",
            "framework_progress",
            "sprint_completion",
            "risk_level",
            "homework_completion",
        }
        actual = {mt.value for mt in MetricType}
        assert actual == expected

    def test_metric_type_is_str_enum(self):
        """MetricType values should be strings."""
        for mt in MetricType:
            assert isinstance(mt.value, str)


class TestPydanticSchemas:
    """Test Pydantic schema validation."""

    def test_progress_metric_create(self):
        """Test ProgressMetricCreate schema validates correctly."""
        cid = uuid4()
        sid = uuid4()
        data = ProgressMetricCreate(
            client_id=cid,
            session_id=sid,
            metric_type=MetricType.SESSION_ENGAGEMENT,
            value=0.75,
            metadata_json={"framework": "CBT"},
        )
        assert data.client_id == cid
        assert data.session_id == sid
        assert data.metric_type == MetricType.SESSION_ENGAGEMENT
        assert data.value == 0.75
        assert data.metadata_json["framework"] == "CBT"

    def test_progress_metric_create_minimal(self):
        """Test ProgressMetricCreate with only required fields."""
        data = ProgressMetricCreate(
            client_id=uuid4(),
            metric_type=MetricType.RISK_LEVEL,
            value=0.2,
        )
        assert data.session_id is None
        assert data.metadata_json is None

    def test_progress_metric_read(self):
        """Test ProgressMetricRead schema."""
        now = datetime.now(timezone.utc)
        data = ProgressMetricRead(
            id=uuid4(),
            client_id=uuid4(),
            session_id=None,
            metric_type=MetricType.SPRINT_COMPLETION,
            value=0.9,
            metadata_json=None,
            measured_at=now,
            created_at=now,
        )
        assert data.metric_type == MetricType.SPRINT_COMPLETION
        assert data.value == 0.9


# =============================================================================
# Service Tests
# =============================================================================

class TestRecordMetric:
    """Test record_metric method."""

    def test_record_metric_success(self, analytics, client_id, session_id):
        """Test recording a metric stores and returns correct data."""
        result = analytics.record_metric(
            client_id=client_id,
            metric_type=MetricType.SESSION_ENGAGEMENT,
            value=0.8,
            session_id=session_id,
            metadata={"notes": "test"},
        )

        assert isinstance(result, ProgressMetricRead)
        assert str(result.client_id) == client_id
        assert result.metric_type == MetricType.SESSION_ENGAGEMENT
        assert result.value == 0.8
        assert result.metadata_json["notes"] == "test"

    def test_record_metric_no_db_raises(self, analytics_no_db, client_id):
        """Test recording without DB raises ProgressAnalyticsError."""
        with pytest.raises(ProgressAnalyticsError, match="session"):
            analytics_no_db.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.5,
            )


class TestCalculateSessionProgress:
    """Test calculate_session_progress method."""

    def test_no_data_returns_empty_defaults(self, analytics, client_id):
        """Test with no data returns empty/stable defaults."""
        result = analytics.calculate_session_progress(client_id)

        assert result["client_id"] == client_id
        assert result["total_sessions"] == 0
        assert result["recent_sessions"] == 0
        assert result["engagement_trend"] == "stable"
        assert result["metrics"] == []

    def test_no_db_returns_empty_defaults(self, analytics_no_db, client_id):
        """Test without DB session returns empty defaults."""
        result = analytics_no_db.calculate_session_progress(client_id)

        assert result["total_sessions"] == 0
        assert result["engagement_trend"] == "stable"

    def test_with_improving_data(self, analytics, client_id):
        """Test with data showing improving trend."""
        # Record metrics with increasing values (newest last in chronological order)
        base_time = datetime.utcnow()
        for i in range(6):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.3 + (i * 0.1),  # 0.3, 0.4, 0.5, 0.6, 0.7, 0.8
            )

        result = analytics.calculate_session_progress(client_id)

        assert result["total_sessions"] == 6
        assert result["engagement_trend"] == "improving"
        assert len(result["metrics"]) == 6

    def test_with_declining_data(self, analytics, client_id):
        """Test with data showing declining trend."""
        for i in range(6):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.9 - (i * 0.1),  # 0.9, 0.8, 0.7, 0.6, 0.5, 0.4
            )

        result = analytics.calculate_session_progress(client_id)

        assert result["total_sessions"] == 6
        assert result["engagement_trend"] == "declining"

    def test_with_stable_data(self, analytics, client_id):
        """Test with consistent data returns stable trend."""
        for _ in range(4):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.7,
            )

        result = analytics.calculate_session_progress(client_id)

        assert result["engagement_trend"] == "stable"

    def test_limit_parameter(self, analytics, client_id):
        """Test that limit parameter caps the number of metrics returned."""
        for i in range(10):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.5 + (i * 0.01),
            )

        result = analytics.calculate_session_progress(client_id, limit=3)

        assert result["total_sessions"] == 3
        assert len(result["metrics"]) == 3


class TestCalculateFrameworkTrends:
    """Test calculate_framework_trends method."""

    def test_no_data_returns_empty(self, analytics, client_id):
        """Test with no framework data returns empty defaults."""
        result = analytics.calculate_framework_trends(client_id)

        assert result["client_id"] == client_id
        assert result["frameworks"] == {}
        assert result["primary_framework"] is None
        assert result["framework_diversity"] == 0.0

    def test_no_db_returns_empty(self, analytics_no_db, client_id):
        """Test without DB returns empty defaults."""
        result = analytics_no_db.calculate_framework_trends(client_id)
        assert result["frameworks"] == {}

    def test_with_framework_data(self, analytics, client_id):
        """Test with framework data returns correct counts."""
        # Record multiple frameworks
        for _ in range(3):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.FRAMEWORK_PROGRESS,
                value=0.7,
                metadata={"framework": "CBT"},
            )
        for _ in range(2):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.FRAMEWORK_PROGRESS,
                value=0.5,
                metadata={"framework": "EFT"},
            )
        analytics.record_metric(
            client_id=client_id,
            metric_type=MetricType.FRAMEWORK_PROGRESS,
            value=0.3,
            metadata={"framework": "DBT"},
        )

        result = analytics.calculate_framework_trends(client_id)

        assert result["frameworks"]["CBT"] == 3
        assert result["frameworks"]["EFT"] == 2
        assert result["frameworks"]["DBT"] == 1
        assert result["primary_framework"] == "CBT"
        assert result["framework_diversity"] == 0.5  # 3 unique / 6 total
        assert len(result["recent_frameworks"]) <= 5


class TestCalculateSprintCompletion:
    """Test calculate_sprint_completion method."""

    def test_no_data_returns_empty(self, analytics, client_id):
        """Test with no sprint data returns empty defaults."""
        result = analytics.calculate_sprint_completion(client_id)

        assert result["total_sprints"] == 0
        assert result["completed_sprints"] == 0
        assert result["completion_rate"] == 0.0
        assert result["current_sprint_progress"] == 0.0
        assert result["trend"] == "stable"

    def test_no_db_returns_empty(self, analytics_no_db, client_id):
        """Test without DB returns empty defaults."""
        result = analytics_no_db.calculate_sprint_completion(client_id)
        assert result["total_sprints"] == 0
        assert result["trend"] == "stable"

    def test_with_sprint_data(self, analytics, client_id):
        """Test with sprint data returns correct completion rate."""
        # 3 completed (>=0.8) and 1 incomplete
        for val in [0.9, 0.85, 0.8, 0.5]:
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SPRINT_COMPLETION,
                value=val,
            )

        result = analytics.calculate_sprint_completion(client_id)

        assert result["total_sprints"] == 4
        assert result["completed_sprints"] == 3
        assert result["completion_rate"] == 0.75


class TestGenerateAnalyticsSummary:
    """Test generate_analytics_summary method."""

    def test_empty_summary(self, analytics, client_id):
        """Test summary with no data returns stable trajectory."""
        result = analytics.generate_analytics_summary(client_id)

        assert result["client_id"] == client_id
        assert result["overall_trajectory"] == "stable"
        assert "session_progress" in result
        assert "framework_trends" in result
        assert "sprint_completion" in result
        assert "generated_at" in result

    def test_no_db_summary(self, analytics_no_db, client_id):
        """Test summary without DB returns defaults."""
        result = analytics_no_db.generate_analytics_summary(client_id)

        assert result["overall_trajectory"] == "stable"
        assert result["session_progress"]["total_sessions"] == 0

    def test_summary_combines_all_methods(self, analytics, client_id):
        """Test summary calls all sub-methods."""
        # Add some engagement data
        for i in range(4):
            analytics.record_metric(
                client_id=client_id,
                metric_type=MetricType.SESSION_ENGAGEMENT,
                value=0.5 + (i * 0.1),
            )

        # Add framework data
        analytics.record_metric(
            client_id=client_id,
            metric_type=MetricType.FRAMEWORK_PROGRESS,
            value=0.7,
            metadata={"framework": "CBT"},
        )

        # Add sprint data
        analytics.record_metric(
            client_id=client_id,
            metric_type=MetricType.SPRINT_COMPLETION,
            value=0.9,
        )

        result = analytics.generate_analytics_summary(client_id)

        assert result["session_progress"]["total_sessions"] == 4
        assert result["framework_trends"]["primary_framework"] == "CBT"
        assert result["sprint_completion"]["total_sprints"] == 1


# =============================================================================
# Trend Calculation Unit Tests
# =============================================================================

class TestCalculateTrend:
    """Test the _calculate_trend static method directly."""

    def test_single_value_is_stable(self):
        assert ProgressAnalytics._calculate_trend([0.5]) == "stable"

    def test_empty_list_is_stable(self):
        assert ProgressAnalytics._calculate_trend([]) == "stable"

    def test_increasing_values_improving(self):
        # Newest first: [0.9, 0.8, 0.7, 0.3, 0.2, 0.1]
        assert ProgressAnalytics._calculate_trend([0.9, 0.8, 0.7, 0.3, 0.2, 0.1]) == "improving"

    def test_decreasing_values_declining(self):
        # Newest first: [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        assert ProgressAnalytics._calculate_trend([0.1, 0.2, 0.3, 0.7, 0.8, 0.9]) == "declining"

    def test_constant_values_stable(self):
        assert ProgressAnalytics._calculate_trend([0.5, 0.5, 0.5, 0.5]) == "stable"


class TestDeriveTrajectory:
    """Test the _derive_trajectory static method directly."""

    def test_positive_signals(self):
        assert ProgressAnalytics._derive_trajectory("improving", "improving", 0.8) == "positive"

    def test_negative_signals(self):
        assert ProgressAnalytics._derive_trajectory("declining", "declining", 0.1) == "needs_attention"

    def test_mixed_signals_stable(self):
        assert ProgressAnalytics._derive_trajectory("improving", "declining", 0.5) == "stable"

    def test_all_zero_stable(self):
        assert ProgressAnalytics._derive_trajectory("stable", "stable", 0.0) == "stable"


# =============================================================================
# API Tests
# =============================================================================

class TestProgressAPI:
    """Test progress API endpoints."""

    @pytest.fixture(autouse=True)
    def setup_mock_service(self):
        """Set up a mock analytics service for API tests."""
        self.mock_service = MagicMock(spec=ProgressAnalytics)
        progress_api.set_analytics_service(self.mock_service)
        yield
        progress_api.set_analytics_service(None)

    def test_get_progress_summary_therapist(self):
        """GET /clients/{id}/progress returns 200 for therapist."""
        cid = uuid4()
        self.mock_service.calculate_session_progress.return_value = {
            "client_id": str(cid),
            "total_sessions": 5,
            "recent_sessions": 5,
            "engagement_trend": "improving",
            "metrics": [],
        }

        result = asyncio.run(
            progress_api.get_progress_summary(
                client_id=cid,
                x_user_id="therapist-1",
                x_user_role="therapist",
            )
        )

        assert result.total_sessions == 5
        assert result.engagement_trend == "improving"
        self.mock_service.calculate_session_progress.assert_called_once_with(str(cid))

    def test_get_progress_summary_non_therapist_forbidden(self):
        """GET /clients/{id}/progress returns 403 for non-therapist."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                progress_api.get_progress_summary(
                    client_id=uuid4(),
                    x_user_id="client-1",
                    x_user_role="client",
                )
            )

        assert exc_info.value.status_code == 403

    def test_get_framework_trends_therapist(self):
        """GET /clients/{id}/progress/trends returns 200 for therapist."""
        cid = uuid4()
        self.mock_service.calculate_framework_trends.return_value = {
            "client_id": str(cid),
            "frameworks": {"CBT": 5, "EFT": 3},
            "primary_framework": "CBT",
            "framework_diversity": 0.4,
            "recent_frameworks": ["CBT", "EFT"],
        }

        result = asyncio.run(
            progress_api.get_framework_trends(
                client_id=cid,
                x_user_id="therapist-1",
                x_user_role="therapist",
            )
        )

        assert result.frameworks == {"CBT": 5, "EFT": 3}
        assert result.primary_framework == "CBT"
        self.mock_service.calculate_framework_trends.assert_called_once_with(str(cid))

    def test_get_framework_trends_non_therapist_forbidden(self):
        """GET /clients/{id}/progress/trends returns 403 for non-therapist."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                progress_api.get_framework_trends(
                    client_id=uuid4(),
                    x_user_id="client-1",
                    x_user_role="client",
                )
            )

        assert exc_info.value.status_code == 403

    def test_get_analytics_summary_therapist(self):
        """GET /clients/{id}/progress/summary returns 200 for therapist."""
        cid = uuid4()
        self.mock_service.generate_analytics_summary.return_value = {
            "client_id": str(cid),
            "session_progress": {"total_sessions": 3, "engagement_trend": "stable"},
            "framework_trends": {"frameworks": {}, "primary_framework": None},
            "sprint_completion": {"total_sprints": 1, "completion_rate": 0.8},
            "overall_trajectory": "positive",
            "generated_at": "2026-02-06T12:00:00",
        }

        result = asyncio.run(
            progress_api.get_analytics_summary(
                client_id=cid,
                x_user_id="therapist-1",
                x_user_role="therapist",
            )
        )

        assert result.overall_trajectory == "positive"
        assert result.generated_at == "2026-02-06T12:00:00"
        self.mock_service.generate_analytics_summary.assert_called_once_with(str(cid))

    def test_get_analytics_summary_non_therapist_forbidden(self):
        """GET /clients/{id}/progress/summary returns 403 for non-therapist."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(
                progress_api.get_analytics_summary(
                    client_id=uuid4(),
                    x_user_id="client-1",
                    x_user_role="client",
                )
            )

        assert exc_info.value.status_code == 403


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
