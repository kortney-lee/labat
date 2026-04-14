# LABAT Agents — Unified Dockerfile
# Agents: LABAT (paid ads), Alex/Astra (SEO), Shania (posting), Maya (engagement)
# Each agent is a separate Cloud Run service using the same image with APP_MODULE override.

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# System dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ /app/src/

# Create necessary directories
RUN mkdir -p /app/data /app/logs

# Cloud Run sets PORT automatically, default to 8080 for local
ENV PORT=8080

# Default to LABAT main — override via APP_MODULE env var at deploy time
#   wihy-labat     → src.apps.labat_app:app
#   wihy-alex      → src.apps.alex_app:app
#   wihy-shania    → src.apps.shania_app:app
#   wihy-astra     → src.apps.astra_app:app
#   wihy-maya      → src.apps.maya_app:app
ENV APP_MODULE=src.apps.labat_app:app

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8080

CMD uvicorn $APP_MODULE --host 0.0.0.0 --port $PORT --workers 1
