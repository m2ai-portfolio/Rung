"""Pytest configuration for performance tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "benchmark: marks tests that require pytest-benchmark"
    )


def pytest_collection_modifyitems(config, items):
    """Skip benchmark tests if pytest-benchmark not installed."""
    try:
        import pytest_benchmark
    except ImportError:
        skip_benchmark = pytest.mark.skip(reason="pytest-benchmark not installed")
        for item in items:
            if "benchmark" in item.fixturenames:
                item.add_marker(skip_benchmark)
