"""
Pytest configuration and fixtures for Rung tests.
"""

import os
import sys
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Change to project root for tests that reference relative paths
@pytest.fixture(autouse=True)
def change_to_project_root():
    """Change to project root directory for all tests."""
    original_dir = os.getcwd()
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)
    yield
    os.chdir(original_dir)
