#!/usr/bin/env python3
"""
Live NIFTY 50 Monitor - Real-time price updates via MCP Server
Monitors NIFTY 50 index with bid/ask spreads and volume
"""

import requests
import json
import time
import sys
import os
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

MCP_SERVER = "http://localhost:3008"

class NIFTYMonitor:
    def __init__(self):
        self.prev_ltp = None
        self.last_update = None

    def call_mcp_tool(self, tool_name, arguments=None):
        """Call MCP tool"""
        try:
            response = requests.post(
                f"{MCP_SERVER}/messages",
                json={
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments or {}
                    }
                },
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    text = data[0].get('text', '{}')
                    return json.loads(text)
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def setup_websocket(self):
        """Setup websocket connection and subscription"""
        print("🔌 Setting up WebSocket connection...")

        # Connect
        result = self.call_mcp_tool("ws_connect")
        if result and result.get("status") == "connected":
            print(f"✅ Connected to DhanHQ (OAuth: {result.get('oauth')})")
        else:
            print(f"❌ Connection failed: {result}")
            return False

        time.sleep(2)

        # Subscribe to NIFTY 50
        print("📊 Subscribing to NIFTY 50...")
        result = self.call_mcp_tool("ws_subscribe", {
            "instruments": [["NSE", "99926000", "Quote"]]
        })
        if result and result.get("status") == "subscribed":
            print(f"✅ Subscribed to {result.get('count')} instrument")
            print(f"   Instruments: {', '.join(result.get('instruments', []))}")
        else:
            print(f"❌ Subscription failed: {result}")
            return False

        return True

    def get_live_data(self):
        """Get live tick data from buffer"""
        return self.call_mcp_tool("ws_get_ticks")

    def format_price_display(self, data):
        """Format price data for display"""
        if not data or data.get("status") != "success":
            return None

        ticks = data.get("ticks", {})
        if not ticks:
            return None

        # Get first (and usually only) tick
        tick_key = list(ticks.keys())[0]
        tick = ticks[tick_key]

        ltp = tick.get('ltp', 0)
        bid = tick.get('bid', 0)
        ask = tick.get('ask', 0)
        spread = ask - bid if bid and ask else 0

        return {
            'ltp': ltp,
            'bid': bid,
            'ask': ask,
            'spread': spread,
            'open': tick.get('open', 0),
            'high': tick.get('high', 0),
            'low': tick.get('low', 0),
            'close': tick.get('close', 0),
            'volume': tick.get('volume', 0),
            'oi': tick.get('oi', 0),
            'timestamp': tick.get('timestamp', '')
        }

    def calculate_change(self, current, previous):
        """Calculate price change"""
        if previous is None or previous == 0:
            return 0, 0
        change = current - previous
        pct = (change / previous) * 100
        return change, pct

    def display_header(self):
        """Display monitor header"""
        print("\n" + "=" * 80)
        print("🟢 NIFTY 50 LIVE MONITOR".center(80))
        print("=" * 80)
        print(f"{'Time':<20} {'LTP':<12} {'Change':<15} {'Bid':<12} {'Ask':<12} {'Vol':<15}")
        print("-" * 80)

    def display_tick(self, tick_data):
        """Display single tick"""
        if not tick_data:
            print("⏳ Waiting for data...")
            return

        ltp = tick_data['ltp']
        change, pct = self.calculate_change(ltp, self.prev_ltp)

        # Price color indicator
        if change > 0:
            direction = "📈"
        elif change < 0:
            direction = "📉"
        else:
            direction = "➡️ "

        time_str = datetime.now().strftime("%H:%M:%S")
        change_str = f"{direction} {change:+.2f} ({pct:+.2f}%)"
        volume_str = f"{tick_data['volume']:,.0f}"

        print(f"{time_str:<20} {ltp:<12.2f} {change_str:<15} {tick_data['bid']:<12.2f} "
              f"{tick_data['ask']:<12.2f} {volume_str:<15}")

        self.prev_ltp = ltp

    def display_summary(self, tick_data):
        """Display summary information"""
        if not tick_data:
            return

        print("\n" + "-" * 80)
        spread_str = f"Spread: {tick_data['spread']:.2f}"
        print(f"{'Summary':<40} {spread_str:<40}")
        print(f"{'Open':<20} {tick_data['open']:<20} {'High':<20} {tick_data['high']:<20}")
        print(f"{'Low':<20} {tick_data['low']:<20} {'Close':<20} {tick_data['close']:<20}")
        print("-" * 80)

    def run(self, duration_seconds=None):
        """Run live monitor"""
        if not self.setup_websocket():
            return

        print("\n⏰ Starting live monitoring (Press Ctrl+C to stop)...\n")
        time.sleep(3)  # Wait for first data

        self.display_header()

        start_time = time.time()
        last_summary = 0

        try:
            while True:
                if duration_seconds and (time.time() - start_time) > duration_seconds:
                    print("\n✅ Monitoring completed")
                    break

                # Get latest data
                data = self.get_live_data()

                if data and data.get("status") == "success":
                    tick_data = self.format_price_display(data)
                    if tick_data:
                        self.display_tick(tick_data)

                        # Show summary every 10 seconds
                        if time.time() - last_summary > 10:
                            self.display_summary(tick_data)
                            last_summary = time.time()
                else:
                    status = data.get("status") if data else "No data"
                    message = data.get("message") if data else ""
                    if status == "waiting" or status == "connecting":
                        print(f"⏳ {message or status}...")

                time.sleep(1)  # Update every second

        except KeyboardInterrupt:
            print("\n\n🛑 Monitoring stopped by user")
            self.call_mcp_tool("ws_disconnect")
            print("✅ WebSocket disconnected")

if __name__ == "__main__":
    monitor = NIFTYMonitor()

    # Run for specified duration or until stopped
    duration = None
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
            print(f"Running for {duration} seconds...\n")
        except:
            pass

    monitor.run(duration_seconds=duration)
