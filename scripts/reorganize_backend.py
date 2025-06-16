#!/usr/bin/env python3
"""
Backend Code Reorganization Script

This script helps migrate the current backend code structure to the new
organized structure following best practices.

Usage:
    python scripts/reorganize_backend.py --dry-run    # Preview changes
    python scripts/reorganize_backend.py --execute   # Execute migration
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple
import argparse
import re

class BackendReorganizer:
    """Handles the backend code reorganization process."""
    
    def __init__(self, project_root: Path, dry_run: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.changes_log = []
        
        # Define the migration mapping
        self.migration_map = {
            # Move main processors to applications/processors/
            "enhanced_optimized_processor.py": "src/applications/processors/enhanced_processor.py",
            "optimized_tweet_processor.py": "src/applications/processors/tweet_processor.py",
            
            # Break down large services in src/shared/ and move to appropriate locations
            "src/shared/tweet_services.py": [
                "src/core/services/tweet_processing.py",
                "src/infrastructure/external/twitter_client.py"
            ],
            "src/shared/twitter_account_discovery_service.py": [
                "src/core/services/account_discovery.py",
                "src/infrastructure/external/twitter_client.py"  # merge
            ],
            "src/shared/visual_tweet_capture_service.py": [
                "src/infrastructure/external/selenium_client.py",
                "src/applications/processors/visual_processor.py"
            ],
            
            # Move classification components
            "src/shared/classification/": "src/core/services/classification/",
            
            # Infrastructure components
            "src/shared/dynamodb_service.py": "src/infrastructure/persistence/dynamodb/subscription_store.py",
            "src/shared/ses_service.py": "src/infrastructure/email/ses_client.py",
            "src/shared/queue.py": "src/infrastructure/messaging/sqs_client.py",
            
            # Configuration
            "src/shared/config.py": "src/shared/config/settings.py",
            "src/shared/env.py": "src/shared/config/environment.py",
            
            # Utilities - keep but organize better
            "src/shared/utils/": "src/shared/utils/",  # Keep as is
            
            # Serverless functions
            "src/lambda_functions/": "src/serverless/functions/",
            "src/fargate/": "src/serverless/containers/",
        }
        
        # Directory structure to create
        self.new_directories = [
            "src/core",
            "src/core/domain",
            "src/core/services",
            "src/core/services/classification",
            "src/core/repositories",
            "src/infrastructure",
            "src/infrastructure/external",
            "src/infrastructure/persistence",
            "src/infrastructure/persistence/dynamodb",
            "src/infrastructure/persistence/s3",
            "src/infrastructure/messaging",
            "src/infrastructure/email",
            "src/applications",
            "src/applications/processors",
            "src/applications/cli",
            "src/applications/workflows",
            "src/serverless",
            "src/serverless/functions",
            "src/serverless/containers",
            "src/shared/config",
            "src/shared/exceptions",
            "src/shared/constants",
            "tests/unit/core",
            "tests/unit/core/domain",
            "tests/unit/core/services",
            "tests/unit/infrastructure",
            "tests/unit/infrastructure/external",
            "tests/unit/infrastructure/persistence",
            "tests/unit/applications",
            "tests/unit/applications/processors",
            "tests/unit/serverless",
            "tests/integration",
            "tests/e2e",
            "tests/fixtures",
            "config",
            "requirements",
            "outputs",
            "outputs/development",
            "outputs/staging",
            "outputs/production",
        ]
        
        # Files to update import statements
        self.files_to_update_imports = []
        
    def execute_migration(self):
        """Execute the complete migration process."""
        print(f"🚀 Starting backend reorganization {'(DRY RUN)' if self.dry_run else '(EXECUTING)'}")
        print(f"Project root: {self.project_root}")
        
        try:
            # Phase 1: Create new directory structure
            self._create_directories()
            
            # Phase 2: Move and reorganize files
            self._move_files()
            
            # Phase 3: Update import statements
            self._update_imports()
            
            # Phase 4: Clean up old structure
            self._cleanup_old_structure()
            
            # Phase 5: Create new configuration files
            self._create_config_files()
            
            # Print summary
            self._print_summary()
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
            
        return True
    
    def _create_directories(self):
        """Create the new directory structure."""
        print("\n📁 Creating new directory structure...")
        
        for directory in self.new_directories:
            dir_path = self.project_root / directory
            
            if not self.dry_run:
                dir_path.mkdir(parents=True, exist_ok=True)
                # Create __init__.py for Python packages
                if directory.startswith('src/') or directory.startswith('tests/'):
                    init_file = dir_path / "__init__.py"
                    if not init_file.exists():
                        init_file.write_text('"""Package initialization."""\n')
            
            self.changes_log.append(f"CREATE DIR: {directory}")
            print(f"  ✅ {directory}")
    
    def _move_files(self):
        """Move files according to the migration map."""
        print("\n📦 Moving and reorganizing files...")
        
        for source, destination in self.migration_map.items():
            source_path = self.project_root / source
            
            if not source_path.exists():
                print(f"  ⚠️  Skipping {source} (not found)")
                continue
            
            if isinstance(destination, list):
                # Split large file into multiple files
                self._split_large_file(source_path, destination)
            else:
                # Simple move
                dest_path = self.project_root / destination
                self._move_single_file(source_path, dest_path)
    
    def _split_large_file(self, source_path: Path, destinations: List[str]):
        """Split a large file into multiple smaller files."""
        print(f"  🔀 Splitting {source_path.name} into {len(destinations)} files")
        
        # This is a placeholder - in practice, you'd need to analyze each file
        # and extract specific classes/functions to appropriate destinations
        for dest in destinations:
            dest_path = self.project_root / dest
            if not self.dry_run:
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                # Create placeholder with TODO comment
                dest_path.write_text(f'''"""
TODO: Extract relevant code from {source_path.name}

This file was created during backend reorganization.
Please extract the appropriate classes/functions from the original file.
"""

# TODO: Import and implement relevant functionality from {source_path}
''')
            
            self.changes_log.append(f"SPLIT: {source_path} -> {dest}")
            print(f"    📄 {dest}")
    
    def _move_single_file(self, source_path: Path, dest_path: Path):
        """Move a single file to its new location."""
        print(f"  📄 {source_path.name} -> {dest_path}")
        
        if not self.dry_run:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source_path), str(dest_path))
        
        self.changes_log.append(f"MOVE: {source_path} -> {dest_path}")
        self.files_to_update_imports.append(dest_path)
    
    def _update_imports(self):
        """Update import statements in moved files."""
        print("\n🔧 Updating import statements...")
        
        # This is a complex task that would require parsing Python files
        # and updating import paths. For now, create a TODO list
        
        import_updates = {
            "from shared.": "from src.shared.",
            "from classification.": "from src.core.services.classification.",
            "from tweet_services": "from src.core.services.tweet_processing",
            # Add more import mappings as needed
        }
        
        for file_path in self.files_to_update_imports:
            if not self.dry_run and file_path.exists():
                self._update_file_imports(file_path, import_updates)
            
            print(f"  🔧 {file_path}")
    
    def _update_file_imports(self, file_path: Path, import_updates: Dict[str, str]):
        """Update import statements in a specific file."""
        try:
            content = file_path.read_text()
            updated_content = content
            
            for old_import, new_import in import_updates.items():
                updated_content = updated_content.replace(old_import, new_import)
            
            if content != updated_content:
                file_path.write_text(updated_content)
                self.changes_log.append(f"UPDATE IMPORTS: {file_path}")
        
        except Exception as e:
            print(f"    ⚠️  Failed to update imports in {file_path}: {e}")
    
    def _cleanup_old_structure(self):
        """Clean up old directories and files."""
        print("\n🧹 Cleaning up old structure...")
        
        # Remove empty directories and move output directories
        cleanup_items = [
            # Move output directories to new structure
            ("local_outputs", "outputs/development/local_outputs"),
            ("local_outputs_optimized", "outputs/development/optimized"),
            ("local_outputs_classified", "outputs/development/classified"),
            ("twitter_discovery_output", "outputs/development/discovery"),
            ("test_discovery_output", "outputs/development/test_discovery"),
            ("test_browser_output", "outputs/development/test_browser"),
        ]
        
        for old_path, new_path in cleanup_items:
            old_dir = self.project_root / old_path
            new_dir = self.project_root / new_path
            
            if old_dir.exists() and old_dir.is_dir():
                if not self.dry_run:
                    new_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(old_dir), str(new_dir))
                
                self.changes_log.append(f"MOVE DIR: {old_path} -> {new_path}")
                print(f"  📁 {old_path} -> {new_path}")
    
    def _create_config_files(self):
        """Create new configuration files."""
        print("\n⚙️  Creating new configuration files...")
        
        config_files = {
            "pyproject.toml": self._get_pyproject_content(),
            "Makefile": self._get_makefile_content(),
            "docker-compose.yml": self._get_docker_compose_content(),
            "requirements/base.txt": self._get_base_requirements(),
            "requirements/development.txt": self._get_dev_requirements(),
            "requirements/testing.txt": self._get_test_requirements(),
            "config/__init__.py": '"""Configuration package."""\n',
            "config/development.py": self._get_dev_config(),
            "config/test.py": self._get_test_config(),
        }
        
        for file_path, content in config_files.items():
            full_path = self.project_root / file_path
            
            if not self.dry_run:
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content)
            
            self.changes_log.append(f"CREATE: {file_path}")
            print(f"  📄 {file_path}")
    
    def _get_pyproject_content(self) -> str:
        """Generate pyproject.toml content."""
        return '''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "genai-tweet-digest"
version = "2.0.0"
description = "AI-powered tweet digest and classification system"
readme = "README.md"
requires-python = ">=3.9"
dependencies = [
    "boto3>=1.26.0",
    "requests>=2.28.0",
    "python-dotenv>=0.19.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=22.0.0",
    "flake8>=5.0.0",
    "mypy>=0.991",
]

[tool.black]
line-length = 88
target-version = ['py39']

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
'''
    
    def _get_makefile_content(self) -> str:
        """Generate Makefile content."""
        return '''# GenAI Tweet Digest - Development Commands

.PHONY: help install test lint format clean run-dev

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\\033[36m%-20s\\033[0m %s\\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements/development.txt

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ --cov=src --cov-report=html --cov-report=term

lint:  ## Run linting
	flake8 src/ tests/
	mypy src/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

clean:  ## Clean up generated files
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

run-dev:  ## Run development server
	python -m src.applications.processors.enhanced_processor

docker-build:  ## Build Docker image
	docker build -t genai-tweet-digest .

docker-run:  ## Run Docker container
	docker-compose up -d
'''
    
    def _get_docker_compose_content(self) -> str:
        """Generate docker-compose.yml content."""
        return '''version: '3.8'

services:
  app:
    build: .
    environment:
      - ENVIRONMENT=development
      - TWITTER_BEARER_TOKEN=${TWITTER_BEARER_TOKEN}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./outputs:/app/outputs
      - ./.env:/app/.env
    ports:
      - "8000:8000"
    
  localstack:
    image: localstack/localstack:latest
    environment:
      - SERVICES=s3,dynamodb,sqs,ses
      - DEBUG=1
      - DATA_DIR=/tmp/localstack/data
    ports:
      - "4566:4566"
    volumes:
      - localstack_data:/tmp/localstack

volumes:
  localstack_data:
'''
    
    def _get_base_requirements(self) -> str:
        """Generate base requirements."""
        return '''# Core dependencies
boto3>=1.26.0
requests>=2.28.0
python-dotenv>=0.19.0
pydantic>=1.10.0
google-generativeai>=0.3.0
openai>=1.0.0
selenium>=4.10.0
webdriver-manager>=3.8.0
Pillow>=9.0.0
'''
    
    def _get_dev_requirements(self) -> str:
        """Generate development requirements."""
        return '''-r base.txt

# Development dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.8.0
black>=22.0.0
flake8>=5.0.0
mypy>=0.991
isort>=5.10.0
pre-commit>=2.20.0
'''
    
    def _get_test_requirements(self) -> str:
        """Generate testing requirements."""
        return '''-r base.txt

# Testing dependencies
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.8.0
pytest-asyncio>=0.20.0
moto>=4.0.0
responses>=0.20.0
'''
    
    def _get_dev_config(self) -> str:
        """Generate development configuration."""
        return '''"""Development configuration."""

import os

# Environment
ENVIRONMENT = "development"
DEBUG = True

# API Settings
TWITTER_API_RATE_LIMIT = 20  # requests per minute
GEMINI_API_RATE_LIMIT = 30   # requests per minute

# Processing Settings
MAX_CONCURRENT_ACCOUNTS = 1
MAX_CONCURRENT_TWEETS = 3
VISUAL_EXTRACTION_BATCH_SIZE = 2

# Output Settings
OUTPUT_DIR = "outputs/development"

# Logging
LOG_LEVEL = "DEBUG"
'''
    
    def _get_test_config(self) -> str:
        """Generate test configuration."""
        return '''"""Test configuration."""

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
'''
    
    def _print_summary(self):
        """Print migration summary."""
        print(f"\n{'='*60}")
        print(f"🎉 BACKEND REORGANIZATION {'PREVIEW' if self.dry_run else 'COMPLETE'}")
        print(f"{'='*60}")
        print(f"Total changes: {len(self.changes_log)}")
        
        change_types = {}
        for change in self.changes_log:
            change_type = change.split(':')[0]
            change_types[change_type] = change_types.get(change_type, 0) + 1
        
        for change_type, count in change_types.items():
            print(f"  {change_type}: {count}")
        
        if self.dry_run:
            print(f"\n⚠️  This was a DRY RUN. No changes were made.")
            print(f"   Run with --execute to apply changes.")
        else:
            print(f"\n✅ Migration completed successfully!")
            print(f"   Next steps:")
            print(f"   1. Review moved files and update any remaining imports")
            print(f"   2. Test the application to ensure everything works")
            print(f"   3. Update documentation to reflect new structure")
            print(f"   4. Commit changes to version control")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Reorganize backend code structure")
    parser.add_argument("--dry-run", action="store_true", default=True,
                      help="Preview changes without executing (default)")
    parser.add_argument("--execute", action="store_true",
                      help="Execute the migration")
    
    args = parser.parse_args()
    
    # Determine execution mode
    dry_run = not args.execute
    
    # Get project root
    project_root = Path(__file__).parent.parent
    
    # Create reorganizer and execute migration
    reorganizer = BackendReorganizer(project_root, dry_run=dry_run)
    success = reorganizer.execute_migration()
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main() 