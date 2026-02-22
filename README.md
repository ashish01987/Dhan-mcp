# Dhan MCP Server

A working MCP server that wraps core Dhan REST APIs as MCP tools.

## What this server exposes

### Read-only tools
- `get_profile`
- `get_funds`
- `get_positions`
- `get_holdings`
- `get_order_by_id`
- `get_historical_charts`

### Trading tools (disabled by default)
- `place_order`
- `cancel_order`

To enable trading tools explicitly:

```bash
export ENABLE_TRADING_TOOLS=true
```

## Setup

```bash
npm install
```

Create environment variables (for example in `.env`):

```env
DHAN_ACCESS_TOKEN=your_access_token
DHAN_CLIENT_ID=your_client_id
DHAN_BASE_URL=https://api.dhan.co/v2
DHAN_TIMEOUT_MS=15000
ENABLE_TRADING_TOOLS=false
MAX_ORDER_QUANTITY=10000
```


### Historical chart tool payload
`get_historical_charts` maps to Dhan historical charts REST API (`/charts/historical`) and expects:

- `security_id` (string)
- `exchange_segment` (string)
- `instrument` (`EQUITY`, `FUTIDX`, `FUTCOM`, `FUTCUR`, `OPTIDX`, `OPTCUR`, `OPTFUT`, `OPTSTK`, `INDEX`)
- `expiry_code` (`0` current, `1` next, `2` far, `3` farther)
- `from_date` (`YYYY-MM-DD`)
- `to_date` (`YYYY-MM-DD`)
- optional `oi` (boolean)

## Run as MCP stdio server

```bash
npm start
```

This process is intended to be launched by an MCP-compatible host/client.

## Architecture

```text
src/
  server.js         # MCP stdio entrypoint
  config.js         # environment and runtime config
  dhan/
    client.js       # Dhan REST wrapper + normalized errors
  mcp/
    tools.js        # MCP tool declarations + input validation
```

## Safety defaults included
- Trading tools are opt-in via `ENABLE_TRADING_TOOLS=true`.
- `place_order` validates payload shape and enforces `MAX_ORDER_QUANTITY`.
- Timeouts are applied on all Dhan REST calls.

## Notes
- Tool I/O is intentionally JSON-structured for LLM friendliness.
- For production, add retries/backoff, audit logs, and idempotency keys for order placement.

## License
MIT
