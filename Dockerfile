# ----- Builder stage (installs deps) -----
FROM python:3.11-slim AS builder

# Install system packages required by some Python deps (boto3 etc. need none; keep minimal)
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirement files first for cache
COPY requirements.txt /app/

RUN pip install --upgrade pip && pip install --prefix=/install -r requirements.txt

# ----- Final runtime image -----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY src/ /app/src/
COPY shared/ /app/shared/
COPY src/fargate /app/src/fargate
COPY src/shared /app/src/shared
COPY src/lambda_functions /app/src/lambda_functions

# Default command (can be overridden)
ENTRYPOINT ["python", "-m", "src.fargate.async_runner"] 