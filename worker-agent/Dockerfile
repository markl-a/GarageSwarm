# Multi-Agent Worker - Multi-Tool Docker Image
# Supports: Claude Code, Gemini CLI, Aider, and more

FROM python:3.11-slim AS base

LABEL maintainer="Multi-Agent Platform"
LABEL description="Worker agent with multiple AI CLI tool support"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# ===== System Dependencies =====
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Node.js for Claude Code
    nodejs \
    npm \
    # Common utilities
    curl \
    git \
    ca-certificates \
    # Process management
    tini \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ===== Tool Installation (Conditional) =====

# Claude Code CLI
ARG INSTALL_CLAUDE_CODE=true
RUN if [ "$INSTALL_CLAUDE_CODE" = "true" ]; then \
    echo "Installing Claude Code CLI..." && \
    npm install -g @anthropic-ai/claude-code && \
    echo "Claude Code installed successfully"; \
    fi

# Gemini CLI (google-generativeai)
ARG INSTALL_GEMINI_CLI=false
RUN if [ "$INSTALL_GEMINI_CLI" = "true" ]; then \
    echo "Installing Gemini CLI..." && \
    pip install --no-cache-dir google-generativeai && \
    echo "Gemini CLI installed successfully"; \
    fi

# Aider
ARG INSTALL_AIDER=false
RUN if [ "$INSTALL_AIDER" = "true" ]; then \
    echo "Installing Aider..." && \
    pip install --no-cache-dir aider-chat && \
    echo "Aider installed successfully"; \
    fi

# OpenHands (formerly OpenDevin)
ARG INSTALL_OPENHANDS=false
RUN if [ "$INSTALL_OPENHANDS" = "true" ]; then \
    echo "Installing OpenHands..." && \
    pip install --no-cache-dir openhands-ai && \
    echo "OpenHands installed successfully"; \
    fi

# ===== Worker Agent Setup =====
WORKDIR /app

# Install Python dependencies first (for caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create directories for tool configs and workspace
RUN mkdir -p /root/.claude /root/.aider /workspace

# ===== Runtime Configuration =====

# Environment variables with defaults
ENV BACKEND_URL=http://host.docker.internal:8002 \
    MACHINE_NAME=docker-worker \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Workspace volume
VOLUME ["/workspace"]

# Tool config volumes (can be mounted)
VOLUME ["/root/.claude", "/root/.aider"]

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('${BACKEND_URL}/api/v1/health')" || exit 1

# Use tini as init system for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--", "/entrypoint.sh"]
CMD ["python", "src/main.py"]
