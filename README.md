# Dhan MCP Server

A **Model Context Protocol (MCP) server** for the [Dhan trading API](https://dhanhq.co/docs/v2/), enabling Claude (and any MCP client) to execute trades, fetch market data, manage orders and analyse your portfolio through natural language.

---

## Features — 36 tools across 9 categories

| Category | Tools |
|---|---|
| **Core** | Fund limits, holdings, positions, orders (place/cancel/list), quotes, market depth, OHLC |
| **Candle Data** | Intraday (1/5/15/25/60 min) and daily/weekly/monthly historical OHLCV |
| **Super Orders** | Entry + target + stop-loss + trailing stop in a single call |
| **Forever Orders** | GTT with SINGLE and OCO (one-cancels-other) support |
| **Conditional Triggers** | Auto-place orders when SMA/EMA/RSI/price conditions are met |
| **Trader's Control** | Kill switch, P&L-based auto-exit |
| **Margin Calculator** | Pre-trade margin, brokerage & leverage check (single + basket) |
| **Ledger** | Full account debit/credit statement |
| **Option Chain** | Full CE/PE chain with OI, IV, Greeks + expiry list |

---

## Prerequisites

- A [Dhan](https://dhan.co) trading account with API access
- Your **Client ID** and **Access Token** from the Dhan developer portal

> **Super Orders, Forever Orders and Conditional Triggers** require your server's IP to be whitelisted in the Dhan portal under *Settings → API → Static IP*.

---

## Quick start — Docker (recommended)

```bash
git clone https://github.com/ashish01987/Dhan-mcp.git
cd Dhan-mcp
cp .env.example .env          # fill in your credentials
docker compose up --build -d
```

### Claude Desktop config (Docker)

```json
{
  "mcpServers": {
    "dhan": {
      "command": "docker",
      "args": ["run", "--rm", "-i",
        "-e", "DHAN_CLIENT_ID=your_client_id",
        "-e", "DHAN_ACCESS_TOKEN=your_access_token",
        "dhan-mcp:latest"
      ]
    }
  }
}
```

> Or build the image once and reference it by name. Credentials are **never** baked into the image — they are always passed at runtime via `-e`.

---

## Quick start — Node.js (without Docker)

```bash
git clone https://github.com/ashish01987/Dhan-mcp.git
cd Dhan-mcp
npm install
cp .env.example .env          # fill in your credentials
```

### Claude Desktop config (Node.js)

```json
{
  "mcpServers": {
    "dhan": {
      "command": "node",
      "args": ["C:/path/to/Dhan-mcp/index.js"],
      "env": {
        "DHAN_CLIENT_ID": "your_client_id",
        "DHAN_ACCESS_TOKEN": "your_access_token"
      }
    }
  }
}
```

---

## Docker reference

```bash
# Build image
docker build -t dhan-mcp .

# Run once (interactive, stdio)
docker run --rm -i \
  -e DHAN_CLIENT_ID=your_id \
  -e DHAN_ACCESS_TOKEN=your_token \
  dhan-mcp

# Run with docker compose (reads from .env automatically)
docker compose up --build

# Stop
docker compose down

# Rebuild after code changes
docker compose up --build --force-recreate
```

---

## Example prompts

```
Show my fund limits
What are my current holdings?
Get daily candles for security 1333 (Reliance) from 2025-01-01 to 2025-03-01
Buy 10 shares of security 1333 at market price as CNC
Place a super order: buy 5 shares at 1200, target 1300, stop-loss 1150, trailing jump 10
Create a forever OCO order: buy at 1200 trigger 1199, target 1300 trigger 1299
Set auto-exit if I make ₹5000 profit or lose ₹2000 today
Activate kill switch
How much margin do I need to buy 50 shares at 1200?
Show my ledger for last month
Get NIFTY option chain for expiry 2025-03-27
```

---

## Tool reference

### Core trading
| Tool | Description |
|---|---|
| `get_fund_limits` | Available balance, SOD limit, withdrawable balance |
| `get_holdings` | All demat equity holdings |
| `get_positions` | Open intraday and short-term positions |
| `get_order_list` | All orders placed today |
| `get_order_by_id` | Details of a specific order |
| `place_order` | Place LIMIT/MARKET/SL orders |
| `cancel_order` | Cancel a pending order |
| `get_trade_history` | Historical trades between two dates |
| `get_quote` | Live LTP for one or more instruments |
| `get_market_depth` | Full bid/ask order book |
| `get_ohlc` | OHLC snapshot |

### Candle data
| Tool | Description |
|---|---|
| `get_intraday_candles` | 1/5/15/25/60-minute OHLCV bars |
| `get_daily_candles` | Daily / weekly / monthly historical candles |

### Super Orders
| Tool | Description |
|---|---|
| `place_super_order` | Entry + target + SL + trailing stop in one call |
| `modify_super_order` | Modify ENTRY_LEG / TARGET_LEG / STOP_LOSS_LEG |
| `cancel_super_order` | Cancel a specific leg or entire super order |
| `get_super_orders` | List all super orders for today |

### Forever Orders (GTT)
| Tool | Description |
|---|---|
| `create_forever_order` | SINGLE forever order or OCO pair |
| `modify_forever_order` | Update price, qty, trigger, validity |
| `cancel_forever_order` | Cancel by order ID |
| `get_forever_orders` | List all active forever orders |

### Conditional Triggers
| Tool | Description |
|---|---|
| `create_conditional_trigger` | Trigger orders on price/indicator conditions (SMA, EMA, RSI…) |
| `get_all_triggers` | List all active triggers |
| `delete_trigger` | Remove a trigger by alert ID |

### Trader's Control
| Tool | Description |
|---|---|
| `set_kill_switch` | ACTIVATE or DEACTIVATE trading for the day |
| `get_kill_switch` | Check kill switch status |
| `set_pnl_exit` | Auto-exit all positions at profit/loss threshold |
| `get_pnl_exit` | View current P&L exit configuration |
| `stop_pnl_exit` | Disable active P&L exit rule |

### Margin & Funds
| Tool | Description |
|---|---|
| `calculate_margin` | Margin, brokerage & leverage for a single order |
| `calculate_margin_multi` | Margin for a basket of orders |
| `get_ledger` | Full account debit/credit ledger |

### Option Chain
| Tool | Description |
|---|---|
| `get_option_chain` | Full CE/PE chain with OI, IV, Greeks |
| `get_expiry_dates` | Available expiry dates for an underlying |

### P&L Analysis (computed)
| Tool | Description |
|---|---|
| `get_pnl_summary` | Holding + position P&L breakdown |
| `get_trade_pnl` | Realized P&L from trade history |

---

## Exchange segments

| Value | Market |
|---|---|
| `NSE_EQ` | NSE Equities |
| `BSE_EQ` | BSE Equities |
| `NSE_FNO` | NSE Futures & Options |
| `BSE_FNO` | BSE Futures & Options |
| `MCX_COMM` | MCX Commodities |
| `IDX_I` | Indices |

---

## Security

- **Never commit your `.env` file** — it is listed in `.gitignore` and `.dockerignore`
- Credentials are always passed via environment variables — they are **never** baked into the Docker image
- The Docker image runs as a non-root user (`dhan`) for least-privilege security
- Fallback values in `index.js` are placeholder strings, not real credentials

---

## Rate limits (Dhan API)

| Type | Per second | Per day |
|---|---|---|
| Order APIs | 10 | 7,000 |
| Data APIs | 5 | 100,000 |
| Quote APIs | 1 | Unlimited |

---

## License

MIT
