"""
Progress Analytics Service

Calculates and tracks progress analytics for therapy clients:
- Session engagement trends
- Framework usage patterns
- Sprint completion rates
- Comprehensive analytics summaries

Designed to work with or without a database session factory.
When no session_factory is provided, methods return sensible empty defaults.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from src.models.progress_metric import (
    MetricType,
    ProgressMetric,
    ProgressMetricRead,
)


class ProgressAnalyticsError(Exception):
    """Exception for progress analytics errors."""
    pass


class ProgressAnalytics:
    """
    Calculates progress analytics from stored ProgressMetric data.

    Args:
        session_factory: Optional SQLAlchemy session factory. If None,
            all query methods return empty/default responses.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory

    def _get_session(self) -> Optional[Session]:
        """Get a database session if factory is available."""
        if self._session_factory is None:
            return None
        return self._session_factory()

    @staticmethod
    def _to_uuid(value) -> UUID:
        """Convert a string or UUID to a UUID object."""
        if isinstance(value, UUID):
            return value
        return UUID(str(value))

    def record_metric(
        self,
        client_id: str,
        metric_type: MetricType,
        value: float,
        session_id: str = None,
        metadata: dict = None,
    ) -> ProgressMetricRead:
        """Record a new progress metric.

        Args:
            client_id: Client UUID string.
            metric_type: Type of metric being recorded.
            value: Numeric value of the metric.
            session_id: Optional session UUID string.
            metadata: Optional dict with type-specific context.

        Returns:
            ProgressMetricRead with the created metric data.

        Raises:
            ProgressAnalyticsError: If no database session is available
                or the insert fails.
        """
        db = self._get_session()
        if db is None:
            raise ProgressAnalyticsError(
                "Cannot record metrics without a database session. "
                "Provide a session_factory when initializing ProgressAnalytics."
            )

        try:
            # Convert string IDs to UUID objects for PG_UUID columns
            _client_id = UUID(client_id) if isinstance(client_id, str) else client_id
            _session_id = UUID(session_id) if isinstance(session_id, str) else session_id

            metric = ProgressMetric(
                id=uuid4(),
                client_id=_client_id,
                session_id=_session_id,
                metric_type=metric_type,
                value=value,
                metadata_json=metadata,
                measured_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
            )
            db.add(metric)
            db.commit()
            db.refresh(metric)

            return ProgressMetricRead.model_validate(metric)
        except Exception as e:
            db.rollback()
            raise ProgressAnalyticsError(f"Failed to record metric: {e}") from e
        finally:
            db.close()

    def calculate_session_progress(
        self,
        client_id: str,
        limit: int = 10,
    ) -> dict:
        """Calculate session-over-session engagement metrics.

        Queries SESSION_ENGAGEMENT metrics ordered by measured_at DESC,
        then determines trend by comparing the average of the most recent
        half to the older half.

        Args:
            client_id: Client UUID string.
            limit: Max number of recent metrics to consider.

        Returns:
            Dict with client_id, total_sessions, recent_sessions,
            engagement_trend, and metrics list.
        """
        db = self._get_session()
        if db is None:
            return {
                "client_id": client_id,
                "total_sessions": 0,
                "recent_sessions": 0,
                "engagement_trend": "stable",
                "metrics": [],
            }

        try:
            _cid = self._to_uuid(client_id)
            metrics = (
                db.query(ProgressMetric)
                .filter(
                    ProgressMetric.client_id == _cid,
                    ProgressMetric.metric_type == MetricType.SESSION_ENGAGEMENT,
                )
                .order_by(ProgressMetric.measured_at.desc())
                .limit(limit)
                .all()
            )

            if not metrics:
                return {
                    "client_id": client_id,
                    "total_sessions": 0,
                    "recent_sessions": 0,
                    "engagement_trend": "stable",
                    "metrics": [],
                }

            metric_reads = [
                ProgressMetricRead.model_validate(m) for m in metrics
            ]

            # Calculate trend: compare recent half avg to older half avg
            trend = self._calculate_trend([m.value for m in metrics])

            return {
                "client_id": client_id,
                "total_sessions": len(metrics),
                "recent_sessions": min(len(metrics), limit),
                "engagement_trend": trend,
                "metrics": metric_reads,
            }
        finally:
            db.close()

    def calculate_framework_trends(self, client_id: str) -> dict:
        """Track which frameworks have been identified across sessions.

        Queries FRAMEWORK_PROGRESS metrics and counts framework occurrences
        from metadata_json. Calculates diversity as unique_frameworks / total_entries.

        Args:
            client_id: Client UUID string.

        Returns:
            Dict with client_id, frameworks count map, primary_framework,
            framework_diversity, and recent_frameworks list.
        """
        db = self._get_session()
        if db is None:
            return {
                "client_id": client_id,
                "frameworks": {},
                "primary_framework": None,
                "framework_diversity": 0.0,
                "recent_frameworks": [],
            }

        try:
            _cid = self._to_uuid(client_id)
            metrics = (
                db.query(ProgressMetric)
                .filter(
                    ProgressMetric.client_id == _cid,
                    ProgressMetric.metric_type == MetricType.FRAMEWORK_PROGRESS,
                )
                .order_by(ProgressMetric.measured_at.desc())
                .all()
            )

            if not metrics:
                return {
                    "client_id": client_id,
                    "frameworks": {},
                    "primary_framework": None,
                    "framework_diversity": 0.0,
                    "recent_frameworks": [],
                }

            # Count frameworks from metadata_json
            framework_counts: dict[str, int] = {}
            recent_frameworks: list[str] = []

            for metric in metrics:
                framework_name = None
                if metric.metadata_json and isinstance(metric.metadata_json, dict):
                    framework_name = metric.metadata_json.get("framework")

                if framework_name:
                    framework_counts[framework_name] = (
                        framework_counts.get(framework_name, 0) + 1
                    )
                    if len(recent_frameworks) < 5 and framework_name not in recent_frameworks:
                        recent_frameworks.append(framework_name)

            # Primary framework = most frequent
            primary = None
            if framework_counts:
                primary = max(framework_counts, key=framework_counts.get)

            # Diversity = unique frameworks / total entries
            total_entries = len(metrics)
            unique_count = len(framework_counts)
            diversity = unique_count / total_entries if total_entries > 0 else 0.0

            return {
                "client_id": client_id,
                "frameworks": framework_counts,
                "primary_framework": primary,
                "framework_diversity": round(diversity, 3),
                "recent_frameworks": recent_frameworks,
            }
        finally:
            db.close()

    def calculate_sprint_completion(self, client_id: str) -> dict:
        """Track sprint plan completion rates.

        Queries SPRINT_COMPLETION metrics. Values are expected to be
        0.0-1.0 representing completion percentage. A sprint with
        value >= 0.8 is considered "completed".

        Args:
            client_id: Client UUID string.

        Returns:
            Dict with client_id, total_sprints, completed_sprints,
            completion_rate, current_sprint_progress, and trend.
        """
        db = self._get_session()
        if db is None:
            return {
                "client_id": client_id,
                "total_sprints": 0,
                "completed_sprints": 0,
                "completion_rate": 0.0,
                "current_sprint_progress": 0.0,
                "trend": "stable",
            }

        try:
            _cid = self._to_uuid(client_id)
            metrics = (
                db.query(ProgressMetric)
                .filter(
                    ProgressMetric.client_id == _cid,
                    ProgressMetric.metric_type == MetricType.SPRINT_COMPLETION,
                )
                .order_by(ProgressMetric.measured_at.desc())
                .all()
            )

            if not metrics:
                return {
                    "client_id": client_id,
                    "total_sprints": 0,
                    "completed_sprints": 0,
                    "completion_rate": 0.0,
                    "current_sprint_progress": 0.0,
                    "trend": "stable",
                }

            total = len(metrics)
            completed = sum(1 for m in metrics if m.value >= 0.8)
            completion_rate = completed / total if total > 0 else 0.0

            # Current sprint = most recent metric
            current_progress = metrics[0].value

            # Trend from values
            trend = self._calculate_trend([m.value for m in metrics])

            return {
                "client_id": client_id,
                "total_sprints": total,
                "completed_sprints": completed,
                "completion_rate": round(completion_rate, 3),
                "current_sprint_progress": round(current_progress, 3),
                "trend": trend,
            }
        finally:
            db.close()

    def generate_analytics_summary(self, client_id: str) -> dict:
        """Generate comprehensive analytics summary combining all metrics.

        Calls calculate_session_progress, calculate_framework_trends, and
        calculate_sprint_completion, then derives an overall_trajectory
        from the combined signals.

        Args:
            client_id: Client UUID string.

        Returns:
            Dict with session_progress, framework_trends, sprint_completion,
            overall_trajectory, and generated_at timestamp.
        """
        session_progress = self.calculate_session_progress(client_id)
        framework_trends = self.calculate_framework_trends(client_id)
        sprint_completion = self.calculate_sprint_completion(client_id)

        # Derive overall trajectory from combined signals
        trajectory = self._derive_trajectory(
            session_progress["engagement_trend"],
            sprint_completion["trend"],
            sprint_completion["completion_rate"],
        )

        # Serialize metrics in session_progress for JSON compatibility
        serialized_progress = dict(session_progress)
        serialized_progress["metrics"] = [
            m.model_dump(mode="json") if hasattr(m, "model_dump") else m
            for m in session_progress.get("metrics", [])
        ]

        return {
            "client_id": client_id,
            "session_progress": serialized_progress,
            "framework_trends": framework_trends,
            "sprint_completion": sprint_completion,
            "overall_trajectory": trajectory,
            "generated_at": datetime.utcnow().isoformat(),
        }

    # =========================================================================
    # Private helpers
    # =========================================================================

    @staticmethod
    def _calculate_trend(values: list[float]) -> str:
        """Determine trend from a list of values (newest first).

        Compares average of the recent half to the older half.
        Threshold of 10% difference determines improving/declining.

        Args:
            values: List of float values ordered newest-first.

        Returns:
            One of "improving", "stable", or "declining".
        """
        if len(values) < 2:
            return "stable"

        midpoint = len(values) // 2
        # values[0] is newest; recent = first half, older = second half
        recent_avg = sum(values[:midpoint]) / midpoint if midpoint > 0 else 0
        older_avg = sum(values[midpoint:]) / (len(values) - midpoint)

        if older_avg == 0:
            return "stable" if recent_avg == 0 else "improving"

        change_ratio = (recent_avg - older_avg) / abs(older_avg)

        if change_ratio > 0.10:
            return "improving"
        elif change_ratio < -0.10:
            return "declining"
        return "stable"

    @staticmethod
    def _derive_trajectory(
        engagement_trend: str,
        sprint_trend: str,
        completion_rate: float,
    ) -> str:
        """Derive overall trajectory from multiple signals.

        Args:
            engagement_trend: "improving", "stable", or "declining".
            sprint_trend: "improving", "stable", or "declining".
            completion_rate: 0.0-1.0 sprint completion rate.

        Returns:
            One of "positive", "stable", or "needs_attention".
        """
        positive_signals = 0
        negative_signals = 0

        for trend in [engagement_trend, sprint_trend]:
            if trend == "improving":
                positive_signals += 1
            elif trend == "declining":
                negative_signals += 1

        if completion_rate >= 0.7:
            positive_signals += 1
        elif completion_rate < 0.3 and completion_rate > 0:
            negative_signals += 1

        if positive_signals >= 2:
            return "positive"
        elif negative_signals >= 2:
            return "needs_attention"
        return "stable"
