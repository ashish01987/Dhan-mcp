# Dhan MCP API Reference

Complete list of all supported APIs from the dhanhq library, exposed through the dhan-mcp HTTP server.

## Discovery

### List All Available Methods
```bash
curl http://localhost:3005/api/methods
```

Response:
```json
{
  "status": "ok",
  "methods": {
    "portfolio": [...],
    "orders": [...],
    "trades": [...],
    "market_data": [...],
    "historical_data": [...],
    "positions": [...]
  }
}
```

## Portfolio / Account APIs

### Get Fund Limits
Get available fund balance and utilization.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_fund_limits"}'
```

Response:
```json
{
  "status": "ok",
  "data": {
    "availableBalance": 50000,
    "utilisedBalance": 10000,
    "totalBalance": 60000
  }
}
```

### Get Holdings
Get current stock holdings (delivery positions).

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_holdings"}'
```

### Get Positions
Get current open positions (intraday + delivery).

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_positions"}'
```

### Get Margins
Get margin details and leverage utilization.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_margins"}'
```

## Orders APIs

### Get Order List
Get all orders placed today.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_order_list"}'
```

### Get Order by ID
Get specific order details.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_order_by_id",
    "params": {
      "order_id": "123456"
    }
  }'
```

### Get Pending Orders
Get all pending orders (not executed/cancelled).

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_pending_orders"}'
```

### Place Order
Create a new order.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "place_order",
    "params": {
      "security_id": "1333",
      "exchange_segment": "NSE_EQ",
      "transaction_type": "BUY",
      "quantity": 1,
      "order_type": "MARKET",
      "product_type": "INTRADAY",
      "price": 2500.0,
      "trigger_price": 0.0,
      "validity": "DAY",
      "disclosed_quantity": 0,
      "after_market_order": false
    }
  }'
```

**Parameters:**
- `security_id` (string): Security ID from exchange
- `exchange_segment` (string): NSE_EQ, NSE_FNO, etc.
- `transaction_type` (string): BUY or SELL
- `quantity` (int): Number of shares/contracts
- `order_type` (string): MARKET, LIMIT, STOP_LOSS, etc.
- `product_type` (string): INTRADAY, DELIVERY, MTF, etc.
- `price` (float): Price for limit orders
- `trigger_price` (float): Stop/trigger price
- `validity` (string): DAY, GTC, IOC, FOK
- `disclosed_quantity` (int, optional): Iceberg order quantity
- `after_market_order` (bool, optional): True for AMO orders

### Cancel Order
Cancel a pending order.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "cancel_order",
    "params": {
      "order_id": "123456",
      "leg_no": 0
    }
  }'
```

### Modify Order
Change price/quantity of pending order.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "modify_order",
    "params": {
      "order_id": "123456",
      "order_type": "LIMIT",
      "price": 2600.0,
      "quantity": 2,
      "trigger_price": null,
      "disclosed_quantity": 0
    }
  }'
```

## Trades APIs

### Get Trade Book
Get all executed trades.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{"method": "get_trade_book"}'
```

### Get Trade History
Get trades within date range.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_trade_history",
    "params": {
      "from_date": "2026-03-01",
      "to_date": "2026-03-30"
    }
  }'
```

## Market Data APIs

### Quote Data
Get current price, bid/ask for securities.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "quote_data",
    "params": {
      "securities": [
        {"security_id": "1333", "exchange_segment": "NSE_EQ"},
        {"security_id": "25", "exchange_segment": "IDX_I"}
      ]
    }
  }'
```

Aliases: `get_quote`

### OHLC Data
Get open, high, low, close for securities.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "ohlc_data",
    "params": {
      "securities": [
        {"security_id": "1333", "exchange_segment": "NSE_EQ"}
      ]
    }
  }'
```

Aliases: `get_ohlc`

### Ticker Data
Get last trade price and volume.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "ticker_data",
    "params": {
      "securities": [
        {"security_id": "1333", "exchange_segment": "NSE_EQ"}
      ]
    }
  }'
```

Aliases: `get_ticker`

## Historical Data APIs

### Intraday Candles (Minute Data)
Get minute-by-minute OHLC candles.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "intraday_minute_data",
    "params": {
      "security_id": "1333",
      "exchange_segment": "NSE_EQ",
      "instrument_type": "EQUITY",
      "interval": 1,
      "from_date": "2026-03-29",
      "to_date": "2026-03-29"
    }
  }'
```

**Intervals:** 1, 5, 15, 30, 60 minutes

Aliases: `get_intraday_candles`

### Daily Candles (Historical Data)
Get daily OHLC candles.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "historical_daily_data",
    "params": {
      "security_id": "1333",
      "exchange_segment": "NSE_EQ",
      "instrument_type": "EQUITY",
      "from_date": "2026-01-01",
      "to_date": "2026-03-30",
      "expiry_code": 0
    }
  }'
```

Aliases: `get_daily_candles`

## Position Conversion APIs

### Convert Position
Convert intraday position to delivery or vice versa.

```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "convert_position",
    "params": {
      "security_id": "1333",
      "exchange_segment": "NSE_EQ",
      "transaction_type": "BUY",
      "position_type": "LONG",
      "quantity": 10,
      "old_product_type": "INTRADAY",
      "new_product_type": "DELIVERY"
    }
  }'
```

## Request/Response Format

### Request
```json
{
  "method": "method_name",
  "params": {
    "param1": "value1",
    "param2": 123
  }
}
```

### Success Response
```json
{
  "status": "ok",
  "data": { ... }
}
```

### Error Response
```json
{
  "error": "Error message",
  "available_methods": { ... }
}
```

## Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| security_id | string | Unique security identifier from exchange |
| exchange_segment | string | NSE_EQ, NSE_FNO, BSE_EQ, MCX_COMM, IDX_I, etc. |
| instrument_type | string | EQUITY, OPTIDX, FUTIDX, etc. |
| transaction_type | string | BUY or SELL |
| order_type | string | MARKET, LIMIT, STOP_LOSS, STOP_LOSS_LIMIT |
| product_type | string | INTRADAY, DELIVERY, MTF (margin trading) |
| validity | string | DAY, GTC (good till cancelled), IOC, FOK |

## Example: Complete Order Workflow

```python
import requests
import json

API_URL = "http://localhost:3005/api"

def api_call(method, params=None):
    """Helper to call dhan API"""
    payload = {"method": method}
    if params:
        payload["params"] = params
    resp = requests.post(API_URL, json=payload)
    return resp.json()

# 1. Check available fund
fund = api_call("get_fund_limits")
print(f"Available: ₹{fund['data']['availableBalance']}")

# 2. Place order
order = api_call("place_order", {
    "security_id": "1333",
    "exchange_segment": "NSE_EQ",
    "transaction_type": "BUY",
    "quantity": 1,
    "order_type": "LIMIT",
    "product_type": "INTRADAY",
    "price": 2500.0,
    "validity": "DAY"
})
order_id = order['data']['orderId']
print(f"Order placed: {order_id}")

# 3. Get order status
order_status = api_call("get_order_by_id", {"order_id": order_id})
print(f"Status: {order_status['data']['orderStatus']}")

# 4. Cancel if needed
cancel = api_call("cancel_order", {"order_id": order_id})
print(f"Cancelled: {cancel['data']['orderId']}")
```

## Rate Limits

- REST APIs: ~100 requests/min per security
- WebSocket: Real-time, no limit
- Historical data: Depends on date range

## Authentication

All API calls require:
1. Server initialized with `DHAN_ACCESS_TOKEN` or OAuth
2. Valid token in environment variable or obtained via `/oauth/login`
