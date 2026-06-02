# Production-grade Dockerfile for Aegis
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml .
COPY aegis/ aegis/
RUN pip install --user --no-cache-dir ".[server]"

# ========== Production Image ==========
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OPENAI_MODEL=gpt-4o-mini

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 gateway && \
    mkdir -p /app/logs /app/data && \
    chown -R gateway:gateway /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/gateway/.local
ENV PATH=/home/gateway/.local/bin:$PATH

# Copy application code
COPY --chown=gateway:gateway . .

# Switch to non-root user
USER gateway

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

# Expose port
EXPOSE 8000

# Run application (import string supports workers cleanly)
CMD ["python", "-m", "uvicorn", "aegis.server:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4"]
