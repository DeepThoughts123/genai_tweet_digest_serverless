"""Test configuration."""

# Environment
ENVIRONMENT = "test"
DEBUG = False

# Use in-memory/mock services for testing
USE_LOCALSTACK = True
LOCALSTACK_ENDPOINT = "http://localhost:4566"

# Test data
TEST_OUTPUT_DIR = "outputs/test"
SAMPLE_ACCOUNTS = ["testuser1", "testuser2"]

# Disable external API calls in tests
MOCK_EXTERNAL_APIS = True
