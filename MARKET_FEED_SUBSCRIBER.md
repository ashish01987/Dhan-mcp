# Market Feed Subscriber

Production WebSocket subscriber for dhan-mcp that assembles real-time market data into 1-minute OHLC candles and writes persistent JSON files.

## Features

- **WebSocket Connection**: Real-time subscription to dhan-mcp server
- **1-Min Candle Assembly**: Accumulates ticks into complete minute candles
- **Multiple Securities**: Subscribe to NIFTY, BANKNIFTY, or any security ID
- **JSON Persistence**: Writes live session files with candle data
- **Auto-Reconnect**: Exponential backoff on disconnect
- **Market-Aware**: Auto-stops at 15:30 IST, waits for 09:15 opening
- **Graceful Shutdown**: Ctrl+C / SIGTERM with final state write

## Usage

### Default (NIFTY + BANKNIFTY)
```bash
python market_feed_subscriber.py
```

### Custom Securities
```bash
python market_feed_subscriber.py --symbols "13" "25"
```

### Custom Output Directory
```bash
python market_feed_subscriber.py --output D:/trader/marketdata/livesession
```

### Custom Write Interval
```bash
python market_feed_subscriber.py --interval 10
```

### Custom Server
```bash
python market_feed_subscriber.py --server ws://192.168.1.100:3005/market
```

## Output Files

Writes JSON files like `nifty_live.json`:

```json
{
  "security_id": "13",
  "symbol": "NIFTY",
  "session_date": "2026-03-30",
  "last_updated": "2026-03-30T15:25:30+05:30",
  "candle_count": 387,
  "candles_1min": [
    {
      "timestamp": "2026-03-30T09:15:00+05:30",
      "unix_ts": 1743297900,
      "open": 22175.50,
      "high": 22188.00,
      "low": 22172.00,
      "close": 22182.75,
      "volume": 1243
    },
    {
      "timestamp": "2026-03-30T15:24:00+05:30",
      "unix_ts": 1743318240,
      "open": 22245.00,
      "high": 22250.00,
      "low": 22240.50,
      "close": 22248.25,
      "volume": 847,
      "_forming": true
    }
  ],
  "update_count": 145,
  "source": "dhan_mcp_websocket"
}
```

## Integration with Trading Bot

```python
import json
from pathlib import Path

# Load latest NIFTY live data
nifty = json.loads(
    Path("marketdata/livesession/nifty_live.json").read_text()
)

candles = nifty["candles_1min"]
last_candle = candles[-1]

print(f"NIFTY: {last_candle['close']} (candle #{len(candles)})")
```

## CLI Reference

```
usage: market_feed_subscriber.py [-h] [--server SERVER] [--symbols SYMBOLS ...]
                                  [--output OUTPUT] [--interval INTERVAL]

options:
  -h, --help            show this help message and exit
  --server SERVER       WebSocket URL (default: ws://localhost:3005/market)
  --symbols SYMBOLS...  Security IDs (default: 13 25)
  --output OUTPUT       Output directory (default: ./marketdata/livesession)
  --interval INTERVAL   Write interval seconds (default: 5)
```
