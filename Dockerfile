# Multi-stage Dockerfile for unified dhan-mcp service
# Runs both HTTP server (server.py) and MCP server (mcp_server.py) in one container

FROM python:3.11-slim

LABEL maintainer="Dhan MCP Server"
LABEL description="Unified Dhan Trading API HTTP Server + MCP Wrapper"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    supervisor \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (layer caching optimization)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py mcp_server.py ./
COPY trading_analytics.py portfolio_analyzer.py alert_manager.py ./

# Create non-root user for security
RUN useradd -m -u 1000 dhan && chown -R dhan:dhan /app

# Switch to non-root user
USER dhan

# Copy supervisord configuration
COPY --chown=dhan:dhan supervisord.conf /app/supervisord.conf

# Expose port for documentation (HTTP server internal)
EXPOSE 3005

# Health check - verify HTTP server is responding
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:3005/health || exit 1

# Start supervisord to manage both server.py and mcp_server.py
CMD ["supervisord", "-c", "/app/supervisord.conf"]
