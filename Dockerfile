# Multi-stage Docker build for talk project

# Build stage
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files, README, and source code (needed for package build)
COPY pyproject.toml uv.lock README.md ./
COPY talk/ ./talk/

# Install dependencies
RUN uv sync --frozen

# Production stage
FROM python:3.11-slim

# Accept build argument for git SHA
ARG GIT_SHA=unknown

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY talk/ ./talk/

# Write git SHA to version file
RUN echo "${GIT_SHA}" > /app/version.txt

# Copy migrations
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Copy startup scripts
COPY scripts/ ./scripts/
RUN chmod +x /app/scripts/start.sh

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the startup script
CMD ["/app/scripts/start.sh"]
