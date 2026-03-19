# ── Stage 1: deps ─────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM node:20-alpine AS runtime
WORKDIR /app

# Non-root user for security
RUN addgroup -S dhan && adduser -S dhan -G dhan

COPY --from=deps /app/node_modules ./node_modules
COPY package.json ./
COPY index.js ./

RUN chown -R dhan:dhan /app
USER dhan

# NOTE: Do NOT set DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN here.
# Always pass credentials at runtime via -e flags or docker compose env_file.
# Example: docker run --rm -i -e DHAN_CLIENT_ID=xxx -e DHAN_ACCESS_TOKEN=yyy dhan-mcp

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD node -e "process.exit(0)"

CMD ["node", "index.js"]
