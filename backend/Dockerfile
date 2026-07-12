# ============================================================
# ARISE — Autonomous RFP Intelligence and Sales Engine
# Production Multi-Stage Dockerfile
# ============================================================

# ─── Stage 1: Builder ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies into a prefix directory (for clean copy)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ─── Stage 2: Production Runtime ─────────────────────────────
FROM python:3.11-slim AS production

LABEL maintainer="ARISE Team"
LABEL org.opencontainers.image.title="ARISE Backend"
LABEL org.opencontainers.image.description="Autonomous RFP Intelligence and Sales Engine — FastAPI backend"
LABEL org.opencontainers.image.version="1.0.0"

# Runtime system dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Create non-root user with least privilege
RUN groupadd -r arise && useradd -r -g arise -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy application source
COPY --chown=appuser:arise . .

# Create runtime directories with proper ownership
RUN mkdir -p /knowledge_base/rfps /knowledge_base/uploads /knowledge_base/outputs \
             /knowledge_base/rate_cards /knowledge_base/scope_templates \
             /knowledge_base/clause_library /knowledge_base/solution_templates \
             /knowledge_base/.rag_cache && \
    chown -R appuser:arise /app /knowledge_base

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

EXPOSE 8000

# Production: no --reload, workers based on CPU cores
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--http", "httptools"]
