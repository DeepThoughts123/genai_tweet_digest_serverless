"""
Pytest configuration for GenAI Tweet Digest tests.
"""

import pytest
import sys
import os

# Add src directory to Python path for imports
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(root_dir, 'src')
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