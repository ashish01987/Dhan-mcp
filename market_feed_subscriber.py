#!/usr/bin/env python3
"""
market_feed_subscriber.py — Production WebSocket subscriber for dhan-mcp server

Connects to the local dhan-mcp HTTP server's WebSocket endpoint, subscribes to
market data for specified securities, assembles 1-min OHLC candles, and writes
JSON files with persistent market data (mirrors trader project's feed_feeder.py).

Usage:
  python market_feed_subscriber.py                    # default NIFTY + BANKNIFTY
  python market_feed_subscriber.py --symbols "1333" "25"
  python market_feed_subscriber.py --output /path/to/dir
  python market_feed_subscriber.py --interval 5

Features:
  • WebSocket connection to ws://localhost:3005/market
  • Per-security subscription management
  • 1-min OHLC candle assembly from ticks
  • JSON file output with candle + metadata
  • Exponential backoff reconnect (2, 4, 8, 16, 30s)
  • Graceful shutdown (Ctrl+C / SIGTERM)
"""

import argparse
import asyncio
import json
import signal
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, Dict

import websockets

# ── Constants ─────────────────────────────────────────────────────────────────

IST = timezone(timedelta(hours=5, minutes=30))
MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)
BACKOFF_SEQUENCE = [2, 4, 8, 16, 30]

# Default securities (maps security_id → display name)
DEFAULT_SECURITIES = {
    "13": "NIFTY",
    "25": "BANKNIFTY",
}


# ── Per-security state ────────────────────────────────────────────────────────

@dataclass
class SymbolState:
    """Tracks candle assembly and metadata for a single security."""
    security_id: str
    symbol_name: str
    completed_candles: list[dict] = field(default_factory=list)
    forming_candle: Optional[dict] = None
    last_ltp: float = 0.0
    update_count: int = 0
    last_write_epoch: float = 0.0


# ── Candle assembly ───────────────────────────────────────────────────────────

def _process_tick(state: SymbolState, ltp: float, timestamp_sec: int) -> bool:
    """
    Incorporate a tick into candle state.
    Returns True if a 1-min candle was sealed.
    """
    minute_epoch = (timestamp_sec // 60) * 60

    if state.forming_candle is None:
        state.forming_candle = {
            "minute": minute_epoch,
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp,
            "tick_count": 1,
        }
        state.last_ltp = ltp
        return False

    if minute_epoch > state.forming_candle["minute"]:
        # Seal current forming candle
        c = state.forming_candle
        ist_dt = datetime.fromtimestamp(c["minute"], tz=IST)

        state.completed_candles.append({
            "timestamp": ist_dt.isoformat(),
            "unix_ts": c["minute"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c.get("tick_count", 0),
        })

        # Open new forming candle
        state.forming_candle = {
            "minute": minute_epoch,
            "open": ltp,
            "high": ltp,
            "low": ltp,
            "close": ltp,
            "tick_count": 1,
        }
        state.last_ltp = ltp
        state.update_count += 1
        return True

    # Same minute — update high/low/close
    c = state.forming_candle
    if ltp > c["high"]:
        c["high"] = ltp
    if ltp < c["low"]:
        c["low"] = ltp
    c["close"] = ltp
    c["tick_count"] = c.get("tick_count", 0) + 1
    state.last_ltp = ltp
    return False


# ── File writer ────────────────────────────────────────────────────────────────

def _write_json(state: SymbolState, session_date: str, output_dir: Path) -> None:
    """Write live session JSON file for this security."""
    output_dir.mkdir(parents=True, exist_ok=True)

    all_candles = list(state.completed_candles)
    if state.forming_candle is not None:
        c = state.forming_candle
        ist_dt = datetime.fromtimestamp(c["minute"], tz=IST)
        all_candles.append({
            "timestamp": ist_dt.isoformat(),
            "unix_ts": c["minute"],
            "open": c["open"],
            "high": c["high"],
            "low": c["low"],
            "close": c["close"],
            "volume": c.get("tick_count", 0),
            "_forming": True,
        })

    payload = {
        "security_id": state.security_id,
        "symbol": state.symbol_name,
        "session_date": session_date,
        "last_updated": datetime.now(IST).isoformat(),
        "candle_count": len(all_candles),
        "candles_1min": all_candles,
        "update_count": state.update_count,
        "source": "dhan_mcp_websocket",
    }

    fname = f"{state.symbol_name.lower()}_live.json"
    fpath = output_dir / fname
    fpath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    state.last_write_epoch = datetime.now(IST).timestamp()


# ── WebSocket logic ────────────────────────────────────────────────────────────

async def _subscribe_to_security(ws, security_id: str) -> None:
    """Send WebSocket subscription message."""
    msg = {
        "action": "subscribe",
        "security_id": security_id,
        "exchange": "NSE",
        "mode": "Ticker"
    }
    await ws.send(json.dumps(msg))


async def _feed_loop(
    ws_url: str,
    states: Dict[str, SymbolState],
    session_date: str,
    output_dir: Path,
    write_interval: int,
    stop_event: asyncio.Event,
) -> None:
    """Main WebSocket loop. Connects, subscribes, processes ticks."""
    backoff_idx = 0
    tick_count = 0

    while not stop_event.is_set():
        try:
            now_str = datetime.now(IST).isoformat()
            print(f"[{now_str}] Connecting to dhan-mcp WebSocket…")

            async with websockets.connect(
                ws_url,
                max_size=2**20,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                # Subscribe to all securities
                for sec_id in states.keys():
                    await _subscribe_to_security(ws, sec_id)

                now_str = datetime.now(IST).isoformat()
                print(f"[{now_str}] Subscribed to {len(states)} securities")
                backoff_idx = 0

                async for raw_msg in ws:
                    if stop_event.is_set():
                        break

                    try:
                        data = json.loads(raw_msg)
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type")
                    sec_id = data.get("security_id")

                    if sec_id not in states:
                        continue

                    state = states[sec_id]

                    if msg_type == "latest_tick":
                        continue

                    if msg_type != "tick":
                        continue

                    tick_data = data.get("data", {})
                    ltp = float(tick_data.get("ltp", 0) or 0)

                    if ltp <= 0:
                        continue

                    now_epoch = int(datetime.now(IST).timestamp())

                    candle_sealed = _process_tick(
                        state,
                        ltp=ltp,
                        timestamp_sec=now_epoch,
                    )

                    tick_count += 1

                    now_epoch = datetime.now(IST).timestamp()
                    time_since_write = now_epoch - state.last_write_epoch

                    if candle_sealed:
                        _write_json(state, session_date, output_dir)
                        last_close = state.completed_candles[-1]["close"] if state.completed_candles else "N/A"
                        print(
                            f"[{datetime.now(IST).isoformat()}] "
                            f"{state.symbol_name} candle #{len(state.completed_candles):03d}  "
                            f"close={last_close}"
                        )
                    elif time_since_write >= write_interval:
                        _write_json(state, session_date, output_dir)

                    # Auto-stop at market close
                    now_ist = datetime.now(IST)
                    close_dt = now_ist.replace(
                        hour=MARKET_CLOSE[0], minute=MARKET_CLOSE[1],
                        second=0, microsecond=0
                    )
                    if now_ist > close_dt:
                        now_str = datetime.now(IST).isoformat()
                        print(f"[{now_str}] Market closed. Total ticks: {tick_count}")
                        stop_event.set()
                        break

        except websockets.exceptions.ConnectionClosedError as exc:
            now_str = datetime.now(IST).isoformat()
            print(f"[{now_str}] Connection closed: {exc}")
        except OSError as exc:
            now_str = datetime.now(IST).isoformat()
            print(f"[{now_str}] Network error: {exc}")
        except Exception as exc:
            now_str = datetime.now(IST).isoformat()
            print(f"[{now_str}] Error: {exc}")

        if stop_event.is_set():
            break

        wait = BACKOFF_SEQUENCE[min(backoff_idx, len(BACKOFF_SEQUENCE) - 1)]
        backoff_idx += 1
        now_str = datetime.now(IST).isoformat()
        print(f"[{now_str}] Reconnecting in {wait}s…")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            pass


# ── Market hours helper ────────────────────────────────────────────────────────

def _wait_for_market_open() -> bool:
    """If before 09:15, block until market opens. Returns False if weekend."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        print("Weekend — no market session.")
        return False

    open_dt = now.replace(
        hour=MARKET_OPEN[0], minute=MARKET_OPEN[1], second=0, microsecond=0
    )
    if now < open_dt:
        wait_secs = (open_dt - now).total_seconds()
        print(f"Market opens at 09:15. Waiting {wait_secs/60:.1f} min…")
        import time
        slept = 0
        while slept < wait_secs:
            time.sleep(min(10, wait_secs - slept))
            slept += 10
    return True


# ── Entry point ────────────────────────────────────────────────────────────────

async def _main(
    ws_url: str,
    securities: Dict[str, str],
    output_dir: Path,
    write_interval: int,
) -> None:
    """Run the market feed subscriber."""
    session_date = datetime.now(IST).strftime("%Y-%m-%d")

    states: Dict[str, SymbolState] = {
        sec_id: SymbolState(security_id=sec_id, symbol_name=symbol_name)
        for sec_id, symbol_name in securities.items()
    }

    stop_event = asyncio.Event()

    def _shutdown(signum, frame):
        now_str = datetime.now(IST).isoformat()
        print(f"\n[{now_str}] Shutdown signal received…")
        asyncio.get_event_loop().call_soon_threadsafe(stop_event.set)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("=" * 60)
    print("  Dhan MCP Market Feed Subscriber")
    print(f"  WebSocket  : {ws_url}")
    print(f"  Securities : {', '.join(securities.values())}")
    print(f"  Output     : {output_dir}")
    print("=" * 60)

    await _feed_loop(ws_url, states, session_date, output_dir, write_interval, stop_event)

    print(f"\n[{datetime.now(IST).isoformat()}] Writing final state…")
    for state in states.values():
        _write_json(state, session_date, output_dir)
        print(
            f"  {state.symbol_name}: {len(state.completed_candles)} candles, "
            f"updates={state.update_count}"
        )
    print("Done.")


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Subscribe to dhan-mcp market feed and assemble candles"
    )
    parser.add_argument(
        "--server",
        default="ws://localhost:3005/market",
        help="WebSocket URL (default: ws://localhost:3005/market)",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=None,
        help="Security IDs (default: 13 25)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./marketdata/livesession"),
        help="Output directory (default: ./marketdata/livesession)",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=5,
        help="Write interval seconds (default: 5)",
    )

    args = parser.parse_args()

    if args.symbols:
        securities = {
            sec_id: DEFAULT_SECURITIES.get(sec_id, f"SEC_{sec_id}")
            for sec_id in args.symbols
        }
    else:
        securities = DEFAULT_SECURITIES

    if not _wait_for_market_open():
        sys.exit(0)

    asyncio.run(_main(
        ws_url=args.server,
        securities=securities,
        output_dir=args.output,
        write_interval=args.interval,
    ))


if __name__ == "__main__":
    main()
