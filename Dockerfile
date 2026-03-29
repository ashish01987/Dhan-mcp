# ── Python MCP Server for Dhan ────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY server.py .

# Non-root user for security
RUN useradd -m -u 1000 dhan && chown -R dhan:dhan /app
USER dhan

ENV MCP_TRANSPORT=http
ENV MCP_PORT=3005
EXPOSE 3005

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:3005/health || exit 1

CMD ["python", "server.py"]
