from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="genai-tweets-digest-backend",
    version="1.0.0",
    author="GenAI Tweets Digest Team",
    author_email="contact@genai-digest.com",
    description="Backend service for GenAI Tweets Digest - Weekly AI content curation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/genai-tweets-digest",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.9",
    install_requires=[
        "fastapi>=0.115.12",
        "uvicorn[standard]>=0.34.2",
        "tweepy>=4.15.0",
        "google-genai>=1.16.1",
        "python-dotenv>=1.1.0",
        "pydantic>=2.11.5",
        "pydantic[email]>=2.11.5",
    ],
    extras_require={
        "dev": [
            "pytest>=8.3.5",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
        ],
        "test": [
            "pytest>=8.3.5",
            "pytest-asyncio>=0.21.0",
            "httpx>=0.28.1",
        ],
        "production": [
            "gunicorn>=21.2.0",
            "prometheus-client>=0.17.0",
            "sentry-sdk[fastapi]>=1.32.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "genai-digest-server=backend.app.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "backend": ["py.typed"],
    },
) 