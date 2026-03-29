#!/usr/bin/env python3
"""
Dhan Trading API Server — Python Edition
HTTP server with OAuth support for Dhan trading APIs
"""

import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any

from aiohttp import web
import dotenv
from dhanhq import DhanLogin, DhanContext, dhanhq, MarketFeed

# Load environment
dotenv.load_dotenv()

# Configuration
CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")
APP_ID = os.getenv("DHAN_APP_ID", "")
APP_SECRET = os.getenv("DHAN_APP_SECRET", "")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "")
PORT = int(os.getenv("MCP_PORT", "3005"))

# Setup logging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("dhan")

# Global state
dhan_login: Optional[DhanLogin] = None
dhan_client = None
current_consent_id: Optional[str] = None
market_feed: Optional[MarketFeed] = None
market_subscriptions: Dict[str, list] = {}  # {symbol: [ws1, ws2, ...]}
market_ticks: Dict[str, dict] = {}  # {symbol: latest_tick}


# ═══════════════════════════════════════════════════════════════════════════
# OAUTH FLOW
# ═══════════════════════════════════════════════════════════════════════════

async def init_oauth():
    """Initialize OAuth if credentials available"""
    global dhan_login
    if not APP_ID or not APP_SECRET:
        logger.info("OAuth: APP_ID/APP_SECRET not configured")
        return
    try:
        dhan_login = DhanLogin(CLIENT_ID or "")
        logger.info("OAuth: Ready. Call GET /oauth/login to start")
    except Exception as e:
        logger.error(f"OAuth init failed: {e}")


async def init_dhan_client():
    """Initialize Dhan client with available credentials"""
    global dhan_client, ACCESS_TOKEN
    if ACCESS_TOKEN:
        try:
            ctx = DhanContext(CLIENT_ID or "", ACCESS_TOKEN)
            dhan_client = dhanhq(ctx)
            logger.info("Client: Initialized with access token")
        except Exception as e:
            logger.error(f"Client init failed: {e}")
    else:
        logger.info("Client: No access token. Use OAuth or provide DHAN_ACCESS_TOKEN")


# ═══════════════════════════════════════════════════════════════════════════
# MARKET FEEDER (REAL-TIME TICKS)
# ═══════════════════════════════════════════════════════════════════════════

def on_market_connect():
    """Called when market feed connects"""
    logger.info("Market Feed: Connected to Dhan WebSocket")


def on_market_message(msg):
    """Called on market feed message"""
    logger.debug(f"Market Feed: Message received")


def on_market_close():
    """Called when market feed closes"""
    logger.info("Market Feed: Disconnected from Dhan WebSocket")


def on_market_error(err):
    """Called on market feed error"""
    logger.error(f"Market Feed: Error - {err}")


async def on_market_ticks(ticks):
    """Called when market ticks arrive - broadcasts to all subscribed clients"""
    global market_ticks, market_subscriptions

    if not ticks:
        return

    for tick in ticks:
        security_id = tick.get("securityId")
        if not security_id:
            continue

        # Store latest tick
        market_ticks[security_id] = tick

        # Broadcast to subscribed WebSocket clients
        if security_id in market_subscriptions:
            dead_sockets = []
            for ws in market_subscriptions[security_id]:
                try:
                    await ws.send_json({
                        "type": "tick",
                        "security_id": security_id,
                        "data": tick
                    })
                except Exception as e:
                    logger.debug(f"Failed to send tick to client: {e}")
                    dead_sockets.append(ws)

            # Remove dead connections
            for ws in dead_sockets:
                market_subscriptions[security_id].remove(ws)


async def init_market_feed():
    """Initialize real-time market feed"""
    global market_feed, dhan_client, CLIENT_ID, ACCESS_TOKEN

    if not dhan_client or not ACCESS_TOKEN:
        logger.info("Market Feed: Skipped (no client)")
        return

    try:
        ctx = DhanContext(CLIENT_ID or "", ACCESS_TOKEN)

        # Create market feed (start empty, clients will subscribe)
        market_feed = MarketFeed(
            ctx,
            instruments=[],  # Will add dynamically
            on_connect=on_market_connect,
            on_message=on_market_message,
            on_close=on_market_close,
            on_error=on_market_error,
            on_ticks=on_market_ticks
        )

        logger.info("Market Feed: Ready for subscriptions")
    except Exception as e:
        logger.error(f"Market Feed init failed: {e}")


# ═══════════════════════════════════════════════════════════════════════════
# HTTP HANDLERS
# ═══════════════════════════════════════════════════════════════════════════

async def handle_health(request):
    """Health check endpoint"""
    return web.json_response({
        "status": "ok",
        "server": "dhan-mcp",
        "version": "4.0.0"
    })


async def handle_api_methods(request):
    """List all available API methods"""
    return web.json_response({
        "status": "ok",
        "methods": _get_available_methods()
    })


async def handle_oauth_login(request):
    """Start OAuth flow"""
    global dhan_login, current_consent_id

    if not dhan_login:
        return web.json_response(
            {"error": "OAuth not configured. Set DHAN_APP_ID and DHAN_APP_SECRET"},
            status=400
        )

    try:
        consent_id = dhan_login.generate_login_session(APP_ID, APP_SECRET)
        current_consent_id = consent_id
        # Correct OAuth URL is at auth.dhan.co
        login_url = f"https://auth.dhan.co/login/consentApp-login?consentAppId={consent_id}"

        return web.json_response({
            "status": "ok",
            "message": "Open login_url in browser and authenticate",
            "login_url": login_url,
            "consent_id": consent_id,
            "next_step": "After login, you'll be redirected. Copy token_id from URL and call /oauth/callback?token_id=xxx"
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


async def handle_oauth_callback(request):
    """Exchange OAuth token"""
    global dhan_login, dhan_client, ACCESS_TOKEN

    token_id = request.query.get("token_id")
    if not token_id:
        return web.json_response({"error": "Missing token_id"}, status=400)

    try:
        response = dhan_login.consume_token_id(token_id, APP_ID, APP_SECRET)

        # Extract access token from response
        if isinstance(response, dict):
            access_token = response.get("accessToken")
            client_name = response.get("dhanClientName", "User")
        else:
            access_token = response
            client_name = "User"

        if not access_token:
            return web.json_response({"error": "No access token in response"}, status=500)

        ACCESS_TOKEN = access_token

        # Initialize client
        ctx = DhanContext(CLIENT_ID or "", access_token)
        dhan_client = dhanhq(ctx)

        logger.info(f"OAuth: Token exchanged successfully for {client_name}")
        return web.json_response({
            "status": "ok",
            "message": f"Successfully authenticated as {client_name}",
            "access_token": access_token[:50] + "...",
            "expiry": response.get("expiryTime") if isinstance(response, dict) else None,
            "next_step": f"Add to .env: DHAN_ACCESS_TOKEN={access_token}"
        }, dumps=lambda x: json.dumps(x, default=str))
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def handle_api(request):
    """Generic API call handler - supports all dhanhq methods"""
    global dhan_client

    if not dhan_client:
        return web.json_response(
            {"error": "Client not initialized. Authenticate with OAuth first"},
            status=401
        )

    try:
        body = await request.json()
    except:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    method = body.get("method")
    params = body.get("params", {})

    if not method:
        return web.json_response({"error": "Missing method"}, status=400)

    try:
        # ═══════════════════════════════════════════════════════════════════
        # PORTFOLIO / ACCOUNT
        # ═══════════════════════════════════════════════════════════════════
        if method == "get_fund_limits":
            result = dhan_client.get_fund_limits()
        elif method == "get_holdings":
            result = dhan_client.get_holdings()
        elif method == "get_positions":
            result = dhan_client.get_positions()
        elif method == "get_margins":
            result = dhan_client.get_margins()

        # ═══════════════════════════════════════════════════════════════════
        # ORDERS
        # ═══════════════════════════════════════════════════════════════════
        elif method == "get_order_list":
            result = dhan_client.get_order_list()
        elif method == "get_order_by_id":
            result = dhan_client.get_order_by_id(params.get("order_id"))
        elif method == "get_pending_orders":
            result = dhan_client.get_pending_orders()
        elif method == "place_order":
            result = dhan_client.place_order(
                security_id=params["security_id"],
                exchange_segment=params["exchange_segment"],
                transaction_type=params["transaction_type"],
                quantity=int(params["quantity"]),
                order_type=params["order_type"],
                product_type=params["product_type"],
                price=float(params.get("price", 0)) if params.get("price") else 0,
                trigger_price=float(params.get("trigger_price", 0)) if params.get("trigger_price") else 0,
                validity=params.get("validity", "DAY"),
                disclosed_quantity=int(params.get("disclosed_quantity", 0)) if params.get("disclosed_quantity") else 0,
                after_market_order=params.get("after_market_order", False)
            )
        elif method == "cancel_order":
            result = dhan_client.cancel_order(
                order_id=params.get("order_id"),
                leg_no=int(params.get("leg_no", 0)) if params.get("leg_no") else 0
            )
        elif method == "modify_order":
            result = dhan_client.modify_order(
                order_id=params.get("order_id"),
                order_type=params.get("order_type"),
                price=float(params.get("price", 0)) if params.get("price") else None,
                quantity=int(params.get("quantity")) if params.get("quantity") else None,
                trigger_price=float(params.get("trigger_price", 0)) if params.get("trigger_price") else None,
                disclosed_quantity=int(params.get("disclosed_quantity", 0)) if params.get("disclosed_quantity") else None
            )

        # ═══════════════════════════════════════════════════════════════════
        # TRADES
        # ═══════════════════════════════════════════════════════════════════
        elif method == "get_trade_book":
            result = dhan_client.get_trade_book()
        elif method == "get_trade_history":
            result = dhan_client.get_trade_history(
                from_date=params.get("from_date"),
                to_date=params.get("to_date")
            )

        # ═══════════════════════════════════════════════════════════════════
        # MARKET DATA - QUOTES
        # ═══════════════════════════════════════════════════════════════════
        elif method == "quote_data":
            result = dhan_client.quote_data(params.get("securities"))
        elif method == "get_quote":  # alias
            result = dhan_client.quote_data(params.get("securities"))

        # ═══════════════════════════════════════════════════════════════════
        # MARKET DATA - OHLC
        # ═══════════════════════════════════════════════════════════════════
        elif method == "ohlc_data":
            result = dhan_client.ohlc_data(params.get("securities"))
        elif method == "get_ohlc":  # alias
            result = dhan_client.ohlc_data(params.get("securities"))

        # ═══════════════════════════════════════════════════════════════════
        # MARKET DATA - TICKER
        # ═══════════════════════════════════════════════════════════════════
        elif method == "ticker_data":
            result = dhan_client.ticker_data(params.get("securities"))
        elif method == "get_ticker":  # alias
            result = dhan_client.ticker_data(params.get("securities"))

        # ═══════════════════════════════════════════════════════════════════
        # HISTORICAL DATA - INTRADAY CANDLES
        # ═══════════════════════════════════════════════════════════════════
        elif method == "intraday_minute_data":
            result = dhan_client.intraday_minute_data(
                security_id=params.get("security_id"),
                exchange_segment=params.get("exchange_segment"),
                instrument_type=params.get("instrument_type"),
                interval=int(params.get("interval", 1)),
                from_date=params.get("from_date"),
                to_date=params.get("to_date")
            )
        elif method == "get_intraday_candles":  # alias
            result = dhan_client.intraday_minute_data(
                security_id=params.get("security_id"),
                exchange_segment=params.get("exchange_segment"),
                instrument_type=params.get("instrument_type"),
                interval=int(params.get("interval", 1)),
                from_date=params.get("from_date"),
                to_date=params.get("to_date")
            )

        # ═══════════════════════════════════════════════════════════════════
        # HISTORICAL DATA - DAILY CANDLES
        # ═══════════════════════════════════════════════════════════════════
        elif method == "historical_daily_data":
            result = dhan_client.historical_daily_data(
                security_id=params.get("security_id"),
                exchange_segment=params.get("exchange_segment"),
                instrument_type=params.get("instrument_type"),
                from_date=params.get("from_date"),
                to_date=params.get("to_date"),
                expiry_code=int(params.get("expiry_code", 0))
            )
        elif method == "get_daily_candles":  # alias
            result = dhan_client.historical_daily_data(
                security_id=params.get("security_id"),
                exchange_segment=params.get("exchange_segment"),
                instrument_type=params.get("instrument_type"),
                from_date=params.get("from_date"),
                to_date=params.get("to_date"),
                expiry_code=int(params.get("expiry_code", 0))
            )

        # ═══════════════════════════════════════════════════════════════════
        # POSITIONS - CONVERSION
        # ═══════════════════════════════════════════════════════════════════
        elif method == "convert_position":
            result = dhan_client.convert_position(
                security_id=params.get("security_id"),
                exchange_segment=params.get("exchange_segment"),
                transaction_type=params.get("transaction_type"),
                position_type=params.get("position_type"),
                quantity=int(params.get("quantity")),
                old_product_type=params.get("old_product_type"),
                new_product_type=params.get("new_product_type")
            )

        # ═══════════════════════════════════════════════════════════════════
        # INVALID METHOD
        # ═══════════════════════════════════════════════════════════════════
        else:
            return web.json_response({
                "error": f"Unknown method: {method}",
                "available_methods": _get_available_methods()
            }, status=400)

        return web.json_response({
            "status": "ok",
            "data": result
        }, dumps=lambda x: json.dumps(x, default=str))

    except KeyError as e:
        logger.error(f"API error - missing param {e}: {e}")
        return web.json_response({
            "error": f"Missing required parameter: {e}"
        }, status=400)
    except Exception as e:
        logger.error(f"API error: {e}")
        return web.json_response({
            "error": str(e)
        }, status=500)


def _get_available_methods() -> dict:
    """Return list of all available API methods grouped by category"""
    return {
        "portfolio": [
            "get_fund_limits",
            "get_holdings",
            "get_positions",
            "get_margins",
        ],
        "orders": [
            "get_order_list",
            "get_order_by_id",
            "get_pending_orders",
            "place_order",
            "cancel_order",
            "modify_order",
        ],
        "trades": [
            "get_trade_book",
            "get_trade_history",
        ],
        "market_data": [
            "quote_data (alias: get_quote)",
            "ohlc_data (alias: get_ohlc)",
            "ticker_data (alias: get_ticker)",
        ],
        "historical_data": [
            "intraday_minute_data (alias: get_intraday_candles)",
            "historical_daily_data (alias: get_daily_candles)",
        ],
        "positions": [
            "convert_position",
        ]
    }


async def handle_market_ws(request):
    """WebSocket handler for real-time market data"""
    global market_feed, market_subscriptions, market_ticks

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    logger.info("Market Feed: New WebSocket client connected")

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    action = data.get("action")

                    if action == "subscribe":
                        # Subscribe to market feed for a symbol
                        security_id = data.get("security_id")
                        exchange = data.get("exchange", "NSE")
                        mode = data.get("mode", "Ticker")  # Ticker, Quote, or Full

                        if not security_id:
                            await ws.send_json({"error": "Missing security_id"})
                            continue

                        if security_id not in market_subscriptions:
                            market_subscriptions[security_id] = []

                        market_subscriptions[security_id].append(ws)

                        # Send latest tick if available
                        if security_id in market_ticks:
                            await ws.send_json({
                                "type": "latest_tick",
                                "security_id": security_id,
                                "data": market_ticks[security_id]
                            })

                        await ws.send_json({
                            "status": "subscribed",
                            "security_id": security_id,
                            "mode": mode
                        })

                        logger.info(f"Market Feed: Client subscribed to {security_id}")

                    elif action == "unsubscribe":
                        security_id = data.get("security_id")
                        if security_id in market_subscriptions:
                            if ws in market_subscriptions[security_id]:
                                market_subscriptions[security_id].remove(ws)
                        await ws.send_json({"status": "unsubscribed", "security_id": security_id})

                    elif action == "ping":
                        await ws.send_json({"pong": True})

                except json.JSONDecodeError:
                    await ws.send_json({"error": "Invalid JSON"})

            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"Market Feed: WebSocket error {ws.exception()}")

    except Exception as e:
        logger.error(f"Market Feed: Client error - {e}")
    finally:
        # Clean up subscriptions
        for subs in market_subscriptions.values():
            if ws in subs:
                subs.remove(ws)
        logger.info("Market Feed: Client disconnected")

    return ws


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════

async def main():
    """Start HTTP server"""
    logger.info("Starting Dhan Server v4.0.0")

    # Initialize
    await init_oauth()
    await init_dhan_client()
    await init_market_feed()

    # Setup HTTP app
    app = web.Application()
    app.router.add_get("/health", handle_health)
    app.router.add_get("/oauth/login", handle_oauth_login)
    app.router.add_get("/oauth/callback", handle_oauth_callback)
    app.router.add_get("/api/methods", handle_api_methods)
    app.router.add_post("/api", handle_api)
    app.router.add_get("/market", handle_market_ws)

    # Start server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    logger.info(f"Server running on http://0.0.0.0:{PORT}")
    logger.info(f"  Health: GET http://localhost:{PORT}/health")
    logger.info(f"  OAuth: GET http://localhost:{PORT}/oauth/login")
    logger.info(f"  API Methods: GET http://localhost:{PORT}/api/methods")
    logger.info(f"  API: POST http://localhost:{PORT}/api")
    logger.info(f"  Market Feed: WS ws://localhost:{PORT}/market")

    # Keep running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
