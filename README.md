# Dhan MCP Server

A working MCP server that wraps core Dhan REST APIs as MCP tools.

## What this server exposes

### Read-only tools
This repository is intended to host an MCP server that wraps Dhan REST APIs and exposes them as MCP tools for an LLM client.

## How to build an MCP server from your Dhan REST APIs

### 1) Decide what should be exposed as MCP tools
Map each high-value Dhan REST operation to a tool, for example:

- `get_profile`
- `get_funds`
- `get_positions`
- `get_holdings`
- `get_order_by_id`

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
- `place_order`
- `cancel_order`
- `get_order_status`

A good MCP tool is:
- focused (one clear action)
- validated (strict input schema)
- safe (sensible defaults, guardrails for trading actions)

### 2) Keep Dhan authentication and signatures in one API client
Create a thin `DhanClient` that handles:
- base URL
- API key/token headers
- request retries / timeout
- error normalization

This keeps tool handlers clean.

### 3) Expose REST endpoints as MCP tools
Each MCP tool should:
1. validate inputs
2. call `DhanClient`
3. return clean JSON for LLM consumption

Example tool mappings:
- MCP `get_positions` -> `GET /positions`
- MCP `place_order` -> `POST /orders`
- MCP `cancel_order` -> `DELETE /orders/{id}`

### 4) Add strict input schemas
For actions like `place_order`, enforce:
- `exchange` enum
- `symbol` pattern
- `quantity > 0`
- `order_type` enum
- optional risk checks (max quantity/notional)

Without schema validation, MCP tools become unsafe quickly.

### 5) Return LLM-friendly responses
Prefer structured responses over raw REST payloads. Example:

```json
{
  "ok": true,
  "order_id": "12345",
  "status": "submitted",
  "message": "Order placed successfully"
}
```

Include both a machine-friendly key set and short human-readable `message`.

### 6) Add essential operational safety
For production-like use, add:
- per-tool rate limiting
- request id + audit logs
- idempotency keys for order placement
- environment switch (`paper` vs `live`)
- explicit confirmation workflow for irreversible actions

### 7) Suggested project layout

```text
src/
  server.js
  mcp/
    tools.js
    schemas.js
  dhan/
    client.js
    endpoints.js
  config.js
```

### 8) Minimal implementation flow
1. Start with read-only tools (`get_profile`, `get_positions`).
2. Add write tools (`place_order`, `cancel_order`) with stronger validation.
3. Add tests with mocked Dhan responses.
4. Integrate with your MCP client (Claude Desktop/Cursor/custom host).

## Quick pseudo-code (Node.js)

```js
// tool handler pseudo-code
async function placeOrderTool(input) {
  validatePlaceOrder(input);
  const result = await dhanClient.placeOrder(input);

  return {
    ok: true,
    order_id: result.orderId,
    status: result.status,
    message: 'Order placed successfully'
  };
}
```

## Practical next step
If you share your exact Dhan API list (paths + request/response examples), you can generate a concrete MCP `tools` contract and implementation skeleton in one pass.

## License
MIT
