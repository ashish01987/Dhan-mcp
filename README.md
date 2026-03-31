# NIFTY 50 Live Feed - OAuth-Integrated MCP Server

A production-ready real-time market data monitoring system for NIFTY 50 using DhanHQ WebSocket API with OAuth authentication.

## 🌟 Features

- **OAuth Authentication** - Secure token-based access (no hardcoded credentials)
- **Real-Time WebSocket Feed** - Live tick data streaming from DhanHQ
- **Event Listeners** - Automatic callback-based updates
- **MCP Server Integration** - Access via HTTP endpoints
- **Live Dashboard** - Beautiful terminal-based monitoring display
- **Production Ready** - Proper error handling and reconnection logic

---

## 🚀 Quick Start (5 minutes)

### 1. Get Your Dhan Credentials

1. Go to https://web.dhan.co
2. Log in to your account
3. Navigate to **Settings → API Keys**
4. Copy three values:
   - **Client ID** (format: 10xxxxxxxx)
   - **App ID** (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
   - **App Secret** (format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)

### 2. Start the HTTP Backend

```bash
export DHAN_CLIENT_ID=your_client_id_here
export DHAN_APP_ID=your_app_id_here
export DHAN_APP_SECRET=your_app_secret_here

cd /c/dhan-mcp
python server.py
```

**Output:**
```
✅ Server running on http://0.0.0.0:3005
📋 Available endpoints:
   OAuth:      GET  http://localhost:3005/oauth/login
   OAuth Token: GET  http://localhost:3005/api/oauth/token
   API:        POST http://localhost:3005/api
```

### 3. Set Your OAuth Token (New Terminal)

Get your access token from: https://web.dhan.co → Settings → API Keys

```bash
curl -X POST http://localhost:3005/api/oauth/set-token -H "Content-Type: application/json" -d "{\"access_token\":\"3a71454e-7b42-4d82-a157-080c35416971\"}"

```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "Access token set successfully",
  "next_step": "WebSocket can now connect via MCP server"
}
```

### 4. Start the MCP Server

```bash
python mcp_server.py
```

**Output:**
```
✅ MCP Server: http://0.0.0.0:3008
✅ HTTP Backend: http://localhost:3005
📡 61 tools available
```

### 5. Start Live Monitoring (New Terminal)

```bash
python monitor_nifty.py
```

**Live Output:**
```
================================================================================
                        NIFTY 50 LIVE MONITOR
================================================================================
Time                 LTP          Change          Bid          Ask          Vol
--------------------------------------------------------------------------------
23:45:32             24850.50     +50.25 (0.21%)   24850.00     24851.00     1,234,567
23:45:33             24851.25     +0.75 (0.00%)    24850.50     24852.00     1,245,678
```

---

## 📊 Understanding the Live Monitor

### Display Columns

| Column | Meaning | Example |
|--------|---------|---------|
| **Time** | Update timestamp | 23:45:32 |
| **LTP** | Last Traded Price | 24850.50 |
| **Change** | Price change from previous tick | +50.25 (0.21%) |
| **Bid** | Market bid price | 24850.00 |
| **Ask** | Market ask price | 24851.00 |
| **Vol** | Trading volume | 1,234,567 |

### Summary Section

Every 10 seconds, you'll see:
```
Summary                                   Spread: 1.00
Open                 24800.00             High                 24875.50
Low                  24750.00             Close                24850.50
```

---

## ⚙️ Configuration

### Monitor Duration

```bash
# Monitor for specific duration (in seconds)
python monitor_nifty.py 300   # 5 minutes
python monitor_nifty.py 3600  # 1 hour
python monitor_nifty.py       # Run until Ctrl+C
```

### Subscribe to Different Instruments

Edit `monitor_nifty.py` in the `setup_websocket()` method:

```python
# Subscribe to NIFTY 50 (default)
{"instruments": [["NSE", "99926000", "Quote"]]}

# Subscribe to Bank NIFTY
{"instruments": [["NSE", "99926009", "Quote"]]}

# Subscribe to multiple instruments
{"instruments": [
    ["NSE", "99926000", "Quote"],  # NIFTY 50
    ["NSE", "99926009", "Quote"]   # Bank NIFTY
]}
```

---

## 🔧 API Endpoints

### Test WebSocket Connection

```bash
# Connect to DhanHQ via OAuth
curl -X POST http://localhost:3008/messages \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ws_connect", "arguments": {}}}'

# Subscribe to NIFTY 50
curl -X POST http://localhost:3008/messages \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ws_subscribe", "arguments": {"instruments": [["NSE", "99926000", "Quote"]]}}}'

# Get tick data
curl -X POST http://localhost:3008/messages \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ws_get_ticks", "arguments": {}}}'

# Get connection status
curl -X POST http://localhost:3008/messages \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ws_status", "arguments": {}}}'
```

---

## 🐛 Troubleshooting

### "No tick data received yet"

**Causes:** Market closed, token lacks permission, websocket not connected

**Solution:**
```bash
# Check WebSocket status
curl -X POST http://localhost:3008/messages \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "ws_status", "arguments": {}}}'
```

### "Failed to fetch OAuth token"

**Solution:**
```bash
# Set new token
curl -X POST http://localhost:3005/api/oauth/set-token \
  -H "Content-Type: application/json" \
  -d '{"access_token":"FRESH_TOKEN"}'
```

### "Connection refused on port 3008"

**Solution:**
```bash
# Kill existing process and restart
wmic process where "commandline like '%mcp_server%'" delete
python mcp_server.py
```

---

## 📈 System Architecture

```
Dhan Account (OAuth Provider)
     ↓ OAuth Token
HTTP Backend (port 3005)
     ↓
MCP Server (port 3008)
     ↓ WebSocket
DhanHQ Market Feed
     ↓ Event Listeners
Live Monitor Display
```

---

## 📚 Requirements

- Python 3.8+
- DhanHQ account with API access
- OAuth credentials (Client ID, App ID, App Secret)

---

## ✅ Verification Checklist

- [ ] Dhan credentials obtained
- [ ] HTTP backend running on port 3005
- [ ] OAuth token set in backend
- [ ] MCP server running on port 3008
- [ ] WebSocket connected
- [ ] Subscribed to NIFTY 50
- [ ] Live monitor displaying data

---

**Happy Trading! 📈**
