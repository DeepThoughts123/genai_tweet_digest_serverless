"""
Pytest configuration for GenAI Tweet Digest tests.
"""

import pytest
import sys
import os

# Ensure project root and src directory are importable
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Also add src explicitly for convenience
src_dir = os.path.join(root_dir, 'src')
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up the test environment."""
    # Ensure src directory is in path
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    yield
    
    # Cleanup after tests
    pass 