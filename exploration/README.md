# Exploration

This folder contains experimental features and prototypes for the GenAI Tweet Digest serverless application. Each subfolder represents a distinct feature or idea being explored.

## Current Features

### 📸 Visual Tweet Capture (`visual_tweet_capture/`)

Browser-based visual capture of Twitter conversations and threads using Selenium automation.

**Key Features:**
- Individual tweet capture at 60% page zoom
- Intelligent duplicate detection  
- ID-based tweet ordering
- Clean subfolder organization
- Production-ready metadata structure

**Status:** ✅ Complete and production-ready

## Project Structure

```
exploration/
├── README.md                    ← This file
├── env_template.txt            ← Environment setup template
├── .gitignore                  ← Git ignore configuration
└── visual_tweet_capture/       ← Visual tweet capture feature
    ├── README.md               ← Feature documentation
    ├── visual_tweet_capturer.py ← Core implementation
    ├── test_*.py               ← Test scripts
    ├── *.md                    ← Strategy documentation
    └── visual_captures/        ← Example results
```

## Adding New Features

When exploring new ideas or features:

1. Create a new subfolder with a descriptive name
2. Add a README.md explaining the feature
3. Include implementation files and tests
4. Update this main README to list the new feature

## Environment Setup

Copy `env_template.txt` to `.env` and configure your API keys:

```bash
cp env_template.txt .env
# Edit .env with your actual API keys
```

## Requirements

See individual feature folders for specific requirements. Generally:
- Python 3.8+
- Required packages vary by feature
- API keys for Twitter and other services

Each feature folder contains its own detailed setup and usage instructions. 