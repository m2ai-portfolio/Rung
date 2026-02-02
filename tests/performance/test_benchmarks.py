"""
Performance benchmarks for Rung system components.

Tests validate:
- P95 latency < 5s for all workflows
- Isolation layer processing < 100ms
- Merge operations < 1s
- Memory usage < 512MB per operation

Run: pytest tests/performance/test_benchmarks.py -v --benchmark-enable
"""

import asyncio
import gc
import os
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

# Set test environment
os.environ["AWS_REGION"] = "us-east-1"

from src.services.isolation_layer import IsolationLayer, IsolatedFrameworks
from src.services.merge_engine import MergeEngine, MergedFrameworks
from src.services.couple_manager import CoupleManager, CoupleLink
from src.agents.schemas.rung_output import (
    RungAnalysisOutput,
    FrameworkIdentified,
    DefenseMechanism,
)


# Performance thresholds
ISOLATION_LATENCY_MS = 100  # Max 100ms for isolation layer
MERGE_LATENCY_MS = 1000  # Max 1s for merge operations
MAX_MEMORY_MB = 512  # Max 512MB per operation
P95_LATENCY_S = 5  # P95 latency target


def generate_rung_analysis(size: str = "normal") -> RungAnalysisOutput:
    """Generate RungAnalysisOutput of varying sizes."""
    sizes = {
        "small": {"frameworks": 2, "defenses": 1, "themes": 2},
        "normal": {"frameworks": 5, "defenses": 3, "themes": 5},
        "large": {"frameworks": 10, "defenses": 5, "themes": 10},
        "xlarge": {"frameworks": 20, "defenses": 10, "themes": 20},
    }
    config = sizes.get(size, sizes["normal"])

    frameworks = [
        FrameworkIdentified(
            name=f"attachment-{i}",
            confidence=0.8,
            evidence=f"Evidence for attachment pattern {i} observed in session",
            category="attachment",
        )
        for i in range(config["frameworks"])
    ]

    defenses = [
        DefenseMechanism(
            type=f"intellectualization",
            indicators=[f"Indicator {j}" for j in range(3)],
            context="Session discussion",
        )
        for i in range(config["defenses"])
    ]

    return RungAnalysisOutput(
        frameworks_identified=frameworks,
        defense_mechanisms=defenses,
        risk_flags=[],
        key_themes=[f"theme_{i}" for i in range(config["themes"])],
        suggested_exploration=["attachment patterns", "communication styles"],
        session_questions=["How do you feel about..."],
        analysis_confidence=0.85,
    )


def generate_partner_analyses() -> tuple:
    """Generate partner analysis data for merge testing."""
    # RungAnalysisOutput doesn't have client_id/session_id fields
    # These are passed separately to the merge function
    partner_a = generate_rung_analysis("normal")
    partner_b = generate_rung_analysis("normal")
    return partner_a, partner_b


class PerformanceMetrics:
    """Helper class for tracking performance metrics."""

    def __init__(self):
        self.latencies: List[float] = []
        self.memory_usage: List[float] = []
        self.start_memory: int = 0

    def start_memory_tracking(self):
        """Start tracking memory allocation."""
        gc.collect()
        tracemalloc.start()
        self.start_memory = tracemalloc.get_traced_memory()[0]

    def stop_memory_tracking(self) -> float:
        """Stop tracking and return memory delta in MB."""
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        delta_mb = (peak - self.start_memory) / (1024 * 1024)
        self.memory_usage.append(delta_mb)
        return delta_mb

    def record_latency(self, latency_ms: float):
        """Record a latency measurement."""
        self.latencies.append(latency_ms)

    def p95_latency(self) -> float:
        """Calculate P95 latency."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        idx = int(len(sorted_latencies) * 0.95)
        return sorted_latencies[min(idx, len(sorted_latencies) - 1)]

    def avg_latency(self) -> float:
        """Calculate average latency."""
        return sum(self.latencies) / len(self.latencies) if self.latencies else 0.0

    def max_memory(self) -> float:
        """Get maximum memory usage in MB."""
        return max(self.memory_usage) if self.memory_usage else 0.0


class TestIsolationLayerPerformance:
    """Performance tests for the isolation layer."""

    @pytest.fixture
    def isolation_layer(self):
        """Create isolation layer instance."""
        return IsolationLayer(strict_mode=True)

    @pytest.fixture
    def metrics(self):
        """Create metrics tracker."""
        return PerformanceMetrics()

    def test_isolation_latency_small_data(self, isolation_layer, metrics):
        """Test isolation layer latency with small data."""
        analysis = generate_rung_analysis("small")
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            result = isolation_layer.isolate(analysis)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        assert p95 < ISOLATION_LATENCY_MS, f"P95 latency {p95:.2f}ms exceeds {ISOLATION_LATENCY_MS}ms threshold"

    def test_isolation_latency_normal_data(self, isolation_layer, metrics):
        """Test isolation layer latency with normal data."""
        analysis = generate_rung_analysis("normal")
        iterations = 100

        for _ in range(iterations):
            start = time.perf_counter()
            result = isolation_layer.isolate(analysis)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        assert p95 < ISOLATION_LATENCY_MS, f"P95 latency {p95:.2f}ms exceeds {ISOLATION_LATENCY_MS}ms threshold"

    def test_isolation_latency_large_data(self, isolation_layer, metrics):
        """Test isolation layer latency with large data."""
        analysis = generate_rung_analysis("large")
        iterations = 50

        for _ in range(iterations):
            start = time.perf_counter()
            result = isolation_layer.isolate(analysis)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        # Allow 2x threshold for large data
        p95 = metrics.p95_latency()
        assert p95 < ISOLATION_LATENCY_MS * 2, f"P95 latency {p95:.2f}ms exceeds threshold for large data"

    def test_isolation_memory_usage(self, isolation_layer, metrics):
        """Test isolation layer memory usage."""
        analysis = generate_rung_analysis("xlarge")
        iterations = 10

        for _ in range(iterations):
            metrics.start_memory_tracking()
            result = isolation_layer.isolate(analysis)
            mem_mb = metrics.stop_memory_tracking()

        max_mem = metrics.max_memory()
        assert max_mem < MAX_MEMORY_MB, f"Max memory {max_mem:.2f}MB exceeds {MAX_MEMORY_MB}MB threshold"

    def test_isolation_concurrent_processing(self, isolation_layer, metrics):
        """Test isolation layer under concurrent load."""
        analysis = generate_rung_analysis("normal")
        concurrent_tasks = 20

        def process_data():
            start = time.perf_counter()
            result = isolation_layer.isolate(analysis)
            return (time.perf_counter() - start) * 1000

        with ThreadPoolExecutor(max_workers=concurrent_tasks) as executor:
            futures = [executor.submit(process_data) for _ in range(concurrent_tasks)]
            latencies = [f.result() for f in futures]

        for lat in latencies:
            metrics.record_latency(lat)

        p95 = metrics.p95_latency()
        # Allow 3x threshold for concurrent processing
        assert p95 < ISOLATION_LATENCY_MS * 3, f"Concurrent P95 latency {p95:.2f}ms exceeds threshold"


class TestMergeEnginePerformance:
    """Performance tests for the merge engine."""

    @pytest.fixture
    def couple_manager(self):
        """Create couple manager with test data."""
        manager = CoupleManager(storage={})
        return manager

    @pytest.fixture
    def merge_engine(self, couple_manager):
        """Create merge engine instance."""
        isolation = IsolationLayer(strict_mode=True)
        return MergeEngine(
            couple_manager=couple_manager,
            isolation_layer=isolation,
        )

    @pytest.fixture
    def metrics(self):
        """Create metrics tracker."""
        return PerformanceMetrics()

    def test_merge_latency_basic(self, merge_engine, couple_manager, metrics):
        """Test basic merge operation latency."""
        partner_a, partner_b = generate_partner_analyses()
        iterations = 50

        for i in range(iterations):
            # Create a fresh link for each iteration with valid UUIDs
            therapist_id = str(uuid4())
            link = couple_manager.create_link(
                therapist_id=therapist_id,
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )

            start = time.perf_counter()
            result = merge_engine.merge(
                couple_link_id=link.id,
                session_id=str(uuid4()),
                therapist_id=therapist_id,
                partner_a_analysis=partner_a,
                partner_b_analysis=partner_b,
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        assert p95 < MERGE_LATENCY_MS, f"P95 latency {p95:.2f}ms exceeds {MERGE_LATENCY_MS}ms threshold"

    def test_merge_memory_usage(self, merge_engine, couple_manager, metrics):
        """Test merge engine memory usage."""
        partner_a, partner_b = generate_partner_analyses()
        iterations = 10

        for i in range(iterations):
            therapist_id = str(uuid4())
            link = couple_manager.create_link(
                therapist_id=therapist_id,
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )

            metrics.start_memory_tracking()
            result = merge_engine.merge(
                couple_link_id=link.id,
                session_id=str(uuid4()),
                therapist_id=therapist_id,
                partner_a_analysis=partner_a,
                partner_b_analysis=partner_b,
            )
            mem_mb = metrics.stop_memory_tracking()

        max_mem = metrics.max_memory()
        assert max_mem < MAX_MEMORY_MB, f"Max memory {max_mem:.2f}MB exceeds {MAX_MEMORY_MB}MB threshold"


class TestCoupleManagerPerformance:
    """Performance tests for couple manager operations."""

    @pytest.fixture
    def manager(self):
        """Create couple manager instance."""
        return CoupleManager(storage={})

    @pytest.fixture
    def metrics(self):
        """Create metrics tracker."""
        return PerformanceMetrics()

    def test_link_creation_latency(self, manager, metrics):
        """Test couple link creation latency."""
        iterations = 100

        for i in range(iterations):
            start = time.perf_counter()
            link = manager.create_link(
                therapist_id=str(uuid4()),
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        # Link creation should be very fast (< 10ms)
        assert p95 < 10, f"P95 latency {p95:.2f}ms exceeds 10ms threshold"

    def test_link_retrieval_latency(self, manager, metrics):
        """Test couple link retrieval latency."""
        # Create many links first
        link_ids = []
        for i in range(100):
            link = manager.create_link(
                therapist_id=str(uuid4()),
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )
            link_ids.append(link.id)

        # Test retrieval
        iterations = 200
        for _ in range(iterations):
            link_id = link_ids[_ % len(link_ids)]
            start = time.perf_counter()
            link = manager.get_link(link_id)
            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        # Retrieval should be very fast (< 5ms)
        assert p95 < 5, f"P95 latency {p95:.2f}ms exceeds 5ms threshold"


class TestEndToEndWorkflowPerformance:
    """End-to-end workflow performance tests."""

    @pytest.fixture
    def metrics(self):
        """Create metrics tracker."""
        return PerformanceMetrics()

    def test_pre_session_workflow_latency(self, metrics):
        """Test complete pre-session workflow latency."""
        # Simulate pre-session workflow without external services
        iterations = 20

        for _ in range(iterations):
            start = time.perf_counter()

            # Simulate steps: transcription → analysis → isolation → brief generation
            time.sleep(0.001)  # Simulated transcription
            isolation = IsolationLayer(strict_mode=True)
            analysis = generate_rung_analysis("normal")
            result = isolation.isolate(analysis)
            time.sleep(0.001)  # Simulated brief generation

            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        # Internal processing should be < 500ms (external services add latency)
        assert p95 < 500, f"Pre-session workflow P95 {p95:.2f}ms exceeds 500ms threshold"

    def test_post_session_workflow_latency(self, metrics):
        """Test complete post-session workflow latency."""
        iterations = 20

        for _ in range(iterations):
            start = time.perf_counter()

            # Simulate steps: notes processing → analysis → plan generation
            time.sleep(0.001)  # Simulated processing
            isolation = IsolationLayer(strict_mode=True)
            analysis = generate_rung_analysis("normal")
            result = isolation.isolate(analysis)
            time.sleep(0.001)  # Simulated plan generation

            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        assert p95 < 500, f"Post-session workflow P95 {p95:.2f}ms exceeds 500ms threshold"

    def test_couples_merge_workflow_latency(self, metrics):
        """Test complete couples merge workflow latency."""
        iterations = 20

        for i in range(iterations):
            start = time.perf_counter()

            # Simulate full couples merge
            manager = CoupleManager(storage={})
            therapist_id = str(uuid4())
            link = manager.create_link(
                therapist_id=therapist_id,
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )

            isolation = IsolationLayer(strict_mode=True)
            merge_engine = MergeEngine(
                couple_manager=manager,
                isolation_layer=isolation,
            )

            partner_a, partner_b = generate_partner_analyses()
            result = merge_engine.merge(
                couple_link_id=link.id,
                session_id=str(uuid4()),
                therapist_id=therapist_id,
                partner_a_analysis=partner_a,
                partner_b_analysis=partner_b,
            )

            latency_ms = (time.perf_counter() - start) * 1000
            metrics.record_latency(latency_ms)

        p95 = metrics.p95_latency()
        assert p95 < MERGE_LATENCY_MS, f"Couples merge workflow P95 {p95:.2f}ms exceeds {MERGE_LATENCY_MS}ms"


class TestThroughputBenchmarks:
    """Throughput benchmark tests."""

    def test_isolation_throughput(self):
        """Measure isolation layer throughput."""
        isolation = IsolationLayer(strict_mode=True)
        analysis = generate_rung_analysis("normal")
        duration_seconds = 5
        operations = 0

        start = time.perf_counter()
        while (time.perf_counter() - start) < duration_seconds:
            isolation.isolate(analysis)
            operations += 1

        throughput = operations / duration_seconds
        # Should process at least 100 operations per second
        assert throughput >= 100, f"Throughput {throughput:.2f} ops/s below 100 ops/s target"

    def test_merge_throughput(self):
        """Measure merge engine throughput."""
        manager = CoupleManager(storage={})
        isolation = IsolationLayer(strict_mode=True)
        merge_engine = MergeEngine(
            couple_manager=manager,
            isolation_layer=isolation,
        )
        partner_a, partner_b = generate_partner_analyses()
        duration_seconds = 5
        operations = 0

        start = time.perf_counter()
        while (time.perf_counter() - start) < duration_seconds:
            therapist_id = str(uuid4())
            link = manager.create_link(
                therapist_id=therapist_id,
                partner_a_id=str(uuid4()),
                partner_b_id=str(uuid4()),
            )
            merge_engine.merge(
                couple_link_id=link.id,
                session_id=str(uuid4()),
                therapist_id=therapist_id,
                partner_a_analysis=partner_a,
                partner_b_analysis=partner_b,
            )
            operations += 1

        throughput = operations / duration_seconds
        # Should process at least 10 merges per second
        assert throughput >= 10, f"Merge throughput {throughput:.2f} ops/s below 10 ops/s target"


# Pytest benchmark integration (requires pytest-benchmark)
@pytest.fixture
def benchmark_data():
    """Provide data for benchmark tests."""
    return {
        "small": generate_rung_analysis("small"),
        "normal": generate_rung_analysis("normal"),
        "large": generate_rung_analysis("large"),
        "partners": generate_partner_analyses(),
    }


def test_benchmark_isolation_small(benchmark, benchmark_data):
    """Benchmark isolation with small data."""
    isolation = IsolationLayer(strict_mode=True)
    benchmark(isolation.isolate, benchmark_data["small"])


def test_benchmark_isolation_normal(benchmark, benchmark_data):
    """Benchmark isolation with normal data."""
    isolation = IsolationLayer(strict_mode=True)
    benchmark(isolation.isolate, benchmark_data["normal"])


def test_benchmark_isolation_large(benchmark, benchmark_data):
    """Benchmark isolation with large data."""
    isolation = IsolationLayer(strict_mode=True)
    benchmark(isolation.isolate, benchmark_data["large"])


def test_benchmark_merge(benchmark, benchmark_data):
    """Benchmark merge operation."""
    manager = CoupleManager(storage={})
    isolation = IsolationLayer(strict_mode=True)
    merge_engine = MergeEngine(
        couple_manager=manager,
        isolation_layer=isolation,
    )
    partners = benchmark_data["partners"]

    def do_merge():
        therapist_id = str(uuid4())
        link = manager.create_link(
            therapist_id=therapist_id,
            partner_a_id=str(uuid4()),
            partner_b_id=str(uuid4()),
        )
        return merge_engine.merge(
            couple_link_id=link.id,
            session_id=str(uuid4()),
            therapist_id=therapist_id,
            partner_a_analysis=partners[0],
            partner_b_analysis=partners[1],
        )

    benchmark(do_merge)
