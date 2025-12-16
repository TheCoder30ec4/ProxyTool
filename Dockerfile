# Use Python 3.12 slim image as base
FROM python:3.12-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies including network tools
# Note: Docker containers have internet access by default
# This ensures DNS resolution and network connectivity work properly
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ca-certificates \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Configure system to prefer IPv4 over IPv6 for DNS resolution
# This fixes issues with Supabase connections when IPv6 is disabled in Docker
RUN echo "precedence ::ffff:0:0/96  100" > /etc/gai.conf

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files first
COPY pyproject.toml ./

# Install dependencies using uv
# uv will read dependencies from pyproject.toml
RUN uv pip install --system --no-cache .

# Copy application code (after dependencies are installed for better caching)
COPY . .

# Create directories for logs and temp files
RUN mkdir -p logs temp Inputs

# Expose port
EXPOSE 8000

# Network configuration
# Docker containers have internet access by default (bridge network)
# This allows the application to connect to external services like:
# - Supabase database (postgresql://*.supabase.co)
# - Groq API (api.groq.com)
# - Other external APIs
# If you need to restrict network access, use Docker network options:
# docker run --network host (host networking)
# docker run --network bridge (default bridge, allows internet)

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
# The container will have full internet access to connect to Supabase and other services
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

