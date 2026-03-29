# Dhan MCP Server — Python Edition

A Model Context Protocol (MCP) server for Dhan trading APIs built with the official **dhanhq** Python library.

## Features

✅ **OAuth Authentication** — Secure user-driven OAuth flow
✅ **Full Dhan API** — All trading, market data, and portfolio APIs
✅ **HTTP Transport** — Persistent server mode for Docker
✅ **Official Library** — Uses `dhanhq` Python package directly

## Setup

### Option A: Docker (Recommended)

1. **Create `.env`**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with credentials (see below)

3. **Start server**:
   ```bash
   docker compose up -d
   ```

4. **Check health**:
   ```bash
   curl http://localhost:3005/health
   ```

### Option B: Local Python

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run server**:
   ```bash
   python server.py
   ```

## OAuth Flow

### Step 1: Start OAuth
```bash
curl http://localhost:3005/oauth/login
```

### Step 2: User Login
Open the returned `login_url` in browser and authenticate

### Step 3: Token Exchange
Server automatically exchanges token for access_token at callback

## Available Tools

**Authentication**
- oauth_start, oauth_exchange_token

**Portfolio**
- get_fund_limits, get_holdings, get_positions

**Orders**
- get_order_list, get_order_by_id, place_order, cancel_order, modify_order

**Market Data**
- get_quote, get_market_depth, get_ohlc

**Historical Data**
- get_intraday_candles, get_daily_candles, get_trade_history

**Account**
- get_account_summary

## Configuration

```bash
# Required
DHAN_CLIENT_ID=your_client_id

# OAuth (Recommended)
DHAN_APP_ID=your_app_id
DHAN_APP_SECRET=your_app_secret

# OR Static Token
DHAN_ACCESS_TOKEN=your_access_token

# Server
MCP_TRANSPORT=http|stdio
MCP_PORT=3005
```

## License

MIT
