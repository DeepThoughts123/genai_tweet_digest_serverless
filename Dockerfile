# ----- Builder stage (installs deps) -----
FROM --platform=linux/amd64 python:3.11-slim AS builder

# Install system packages required by some Python deps (boto3 etc. need none; keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files first for cache
COPY requirements.txt /app/

RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

# ----- Final runtime image -----
FROM --platform=linux/amd64 python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source - following troubleshooting guide
# Copy the contents of src directory directly into /app
COPY src/ .

# Set the PYTHONPATH to the workdir
ENV PYTHONPATH=/app

# Default command - no "src." prefix needed since we copied contents directly
ENTRYPOINT ["python", "-m", "fargate.async_runner"] 