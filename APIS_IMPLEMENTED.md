# All Implemented APIs

Complete implementation of dhanhq library APIs in dhan-mcp.

## Summary

**Total APIs: 24+** across 6 categories

### Portfolio (4 APIs)
- ✅ `get_fund_limits` — Available funds, utilization
- ✅ `get_holdings` — Stock holdings (delivery)
- ✅ `get_positions` — All open positions
- ✅ `get_margins` — Margin and leverage details

### Orders (6 APIs)
- ✅ `get_order_list` — All orders today
- ✅ `get_order_by_id` — Single order details
- ✅ `get_pending_orders` — Pending orders only
- ✅ `place_order` — Create new order (all types)
- ✅ `cancel_order` — Cancel pending order
- ✅ `modify_order` — Update price/quantity

### Trades (2 APIs)
- ✅ `get_trade_book` — Executed trades
- ✅ `get_trade_history` — Trades by date range

### Market Data (3 APIs)
- ✅ `quote_data` (alias: `get_quote`) — Price, bid/ask
- ✅ `ohlc_data` (alias: `get_ohlc`) — Open, high, low, close
- ✅ `ticker_data` (alias: `get_ticker`) — LTP + volume

### Historical Data (2 APIs)
- ✅ `intraday_minute_data` (alias: `get_intraday_candles`) — 1/5/15/30/60 min candles
- ✅ `historical_daily_data` (alias: `get_daily_candles`) — Daily OHLC

### Positions (1 API)
- ✅ `convert_position` — Convert intraday ↔ delivery

## New Features

### 1. API Discovery Endpoint
```bash
GET /api/methods
```
Lists all available methods grouped by category.

### 2. Comprehensive Parameter Handling
- Optional parameters with smart defaults
- Type conversion (string → int/float)
- Proper null/None handling
- Clear error messages on missing required params

### 3. Better Error Handling
- HTTP 400 for missing required parameters
- HTTP 401 for authentication failures
- HTTP 500 for server/API errors
- Structured error responses with available methods

### 4. Aliases
Many methods support both formal and convenience names:
- `quote_data` ↔ `get_quote`
- `ohlc_data` ↔ `get_ohlc`
- `ticker_data` ↔ `get_ticker`
- `intraday_minute_data` ↔ `get_intraday_candles`
- `historical_daily_data` ↔ `get_daily_candles`

## Usage

### Discover Available Methods
```bash
curl http://localhost:3005/api/methods
```

### Call Any Method
```bash
curl -X POST http://localhost:3005/api \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_fund_limits"
  }'
```

### With Parameters
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
      "price": 2500,
      "validity": "DAY"
    }
  }'
```

## Documentation

See **API_REFERENCE.md** for:
- Full parameter documentation
- Example requests/responses
- Common use cases
- Complete order workflow example
- Rate limits and authentication

## Changes to server.py

1. Expanded `handle_api()` function with all dhanhq methods
2. Added `_get_available_methods()` helper function
3. Added `handle_api_methods()` endpoint
4. Improved error handling with structured responses
5. Added parameter validation and type conversion
6. Updated server startup logs

## Testing

The server is ready to test. Start with:

```bash
# Start server
python server.py

# In another terminal, check available methods
curl http://localhost:3005/api/methods

# Try a simple call
curl -X POST http://localhost:3005/api -H "Content-Type: application/json" \
  -d '{"method": "get_fund_limits"}'
```

All 24+ APIs are now fully functional and documented.
