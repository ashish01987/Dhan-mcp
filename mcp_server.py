import asyncio
import logging
import httpx
import os
import json
import pandas as pd
import numpy as np
from ta import trend, momentum, volatility
from scipy.stats import norm
from datetime import datetime, timedelta
import pytz

# HTTP server imports
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

# MCP imports
from mcp.server import Server

# WebSocket/MarketFeed imports
try:
    from dhanhq import DhanContext, MarketFeed
    DHAN_AVAILABLE = True
except ImportError:
    DHAN_AVAILABLE = False
    logger.warning("DhanHQ library not available - websocket streaming disabled")

# Import helper modules
from trading_analytics import (
    calculate_sma, calculate_ema, calculate_rsi, calculate_macd,
    calculate_bollinger_bands, calculate_atr, calculate_support_resistance,
    calculate_call_option_greek, calculate_put_option_greek,
    calculate_position_size, calculate_risk_reward, calculate_max_drawdown,
    calculate_sharpe_ratio, calculate_win_rate, calculate_profit_factor
)
from portfolio_analyzer import (
    get_portfolio_metrics, calculate_portfolio_pnl, calculate_concentration_risk,
    get_sector_allocation, get_expiry_analysis, get_greeks_summary
)
from alert_manager import AlertManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables
HTTP_SERVER_URL = os.getenv("HTTP_SERVER_URL", "http://localhost:3005")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "")
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# OAuth configuration
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")
OAUTH_AUTH_URL = os.getenv("OAUTH_AUTH_URL", "")
OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL", "")
OAUTH_SCOPE = os.getenv("OAUTH_SCOPE", "trading portfolio orders")

http_client = None
alert_manager = None
oauth_token = None

# Set logging level based on DEBUG_MODE
if DEBUG_MODE:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug(f"Debug mode enabled")
    logger.debug(f"MCP Server URL: {MCP_SERVER_URL}")
    logger.debug(f"HTTP Server URL: {HTTP_SERVER_URL}")

# Initialize MCP server
server = Server("dhan-mcp-server")

# Initialize FastAPI app for HTTP server
app = FastAPI(
    title="Dhan MCP Server",
    description="Trading and Portfolio Management MCP Server",
    version="1.0.0"
)

# MCP Server configuration
MCP_PORT = int(os.getenv("MCP_PORT", "3008"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")

# WebSocket/Market Feed configuration
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "")

# WebSocket manager class
class WebsocketManager:
    """Manages DhanHQ websocket connections for live market feed using OAuth"""

    def __init__(self):
        self.market_feed = None
        self.dhan_context = None
        self.subscribed_instruments = set()
        self.tick_data_buffer = {}  # Store latest tick for each instrument
        self.is_connected = False
        self.access_token = None
        self.feed_connected = False

    def on_connect(self, market_feed):
        """Called when market feed connects"""
        self.feed_connected = True
        logger.info("Market Feed Connected")

    def on_ticks(self, market_feed, ticks):
        """Called when tick data arrives - store in buffer"""
        if not ticks:
            return

        for tick in ticks:
            try:
                # Store tick data with timestamp
                instrument_key = f"{tick.get('exchange_tokens', '')}"
                self.tick_data_buffer[instrument_key] = {
                    "timestamp": tick.get('exchange_timestamp'),
                    "ltp": tick.get('ltp'),  # Last Traded Price
                    "open": tick.get('open'),
                    "high": tick.get('high'),
                    "low": tick.get('low'),
                    "close": tick.get('close'),
                    "volume": tick.get('volume'),
                    "oi": tick.get('oi'),  # Open Interest
                    "bid": tick.get('bid'),
                    "ask": tick.get('ask'),
                    "bid_qty": tick.get('bid_qty'),
                    "ask_qty": tick.get('ask_qty')
                }
            except Exception as e:
                logger.debug(f"Error processing tick: {e}")
        logger.debug(f"Received {len(ticks)} ticks")

    def on_message(self, market_feed, message):
        """Called on any message"""
        logger.debug(f"Market message: {message}")

    def on_error(self, market_feed, error):
        """Called on error"""
        logger.error(f"Market Feed Error: {error}")

    def on_close(self, market_feed):
        """Called when market feed disconnects"""
        self.feed_connected = False
        logger.info("Market Feed Disconnected")

    async def get_oauth_token(self):
        """Fetch the OAuth access token from the HTTP backend or environment"""
        # Check environment first
        env_token = os.getenv("DHAN_ACCESS_TOKEN")
        if env_token:
            return env_token

        try:
            # Use direct HTTP request without httpx client
            import urllib.request
            import json as json_module

            url = f"{HTTP_SERVER_URL}/api/oauth/token"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json_module.loads(response.read().decode())
                token = data.get("access_token")
                if token:
                    logger.info(f"Fetched token from HTTP backend")
                    return token
            return None
        except Exception as e:
            logger.debug(f"Failed to fetch OAuth token: {e}")
            return None

    async def connect(self):
        """Connect to DhanHQ websocket using OAuth token from HTTP backend"""
        if not DHAN_AVAILABLE:
            return {"error": "DhanHQ library not available"}

        try:
            logger.info(f"Attempting to fetch token from {HTTP_SERVER_URL}/api/oauth/token")
            logger.info(f"http_client initialized: {http_client is not None}")

            # Fetch access token from HTTP backend (set by OAuth flow)
            self.access_token = await self.get_oauth_token()
            logger.info(f"Token fetch result: {self.access_token[:20] if self.access_token else 'None'}...")

            if not self.access_token:
                return {
                    "error": "No OAuth token available",
                    "steps": [
                        "1. Complete OAuth authentication at HTTP backend",
                        "2. Visit: http://localhost:3005/oauth/login",
                        "3. Complete login and callback with token_id",
                        "4. Then call ws_connect again"
                    ]
                }

            if not DHAN_CLIENT_ID:
                return {"error": "DHAN_CLIENT_ID environment variable not set"}

            self.dhan_context = DhanContext(DHAN_CLIENT_ID, self.access_token)
            self.is_connected = True
            logger.info(f"WebSocket connected via OAuth - Client: {DHAN_CLIENT_ID}")
            return {"status": "connected", "client_id": DHAN_CLIENT_ID, "oauth": True}
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}", exc_info=True)
            return {"error": str(e)}

    def subscribe(self, instruments):
        """Subscribe to market feed for instruments

        instruments: list of tuples (exchange, security_id, subscription_type)
        Example: [("NSE", "1333", "Ticker"), ("NSE", "1333", "Quote")]
        """
        if not self.is_connected or not DHAN_AVAILABLE:
            return {"error": "WebSocket not connected"}

        try:
            # Convert string types to MarketFeed types
            converted_instruments = []
            for exchange, sec_id, sub_type in instruments:
                exchange_enum = getattr(MarketFeed, exchange, MarketFeed.NSE)
                sub_enum = getattr(MarketFeed, sub_type, MarketFeed.Ticker)
                converted_instruments.append((exchange_enum, sec_id, sub_enum))

            if not self.market_feed:
                # Create market feed with event listeners
                self.market_feed = MarketFeed(
                    self.dhan_context,
                    converted_instruments,
                    version="v2",
                    on_connect=self.on_connect,
                    on_ticks=self.on_ticks,
                    on_message=self.on_message,
                    on_error=self.on_error,
                    on_close=self.on_close
                )
                # Start the market feed to begin receiving data
                self.market_feed.start()
                logger.info("Market Feed started with event listeners")
            else:
                # Subscribe to additional symbols
                self.market_feed.subscribe_symbols(converted_instruments)

            self.subscribed_instruments.update([f"{e}-{s}" for e, s, _ in instruments])
            logger.info(f"Subscribed to {len(converted_instruments)} instruments")
            return {
                "status": "subscribed",
                "count": len(converted_instruments),
                "instruments": list(self.subscribed_instruments),
                "message": "Live feed started - tick data will update in real-time"
            }
        except Exception as e:
            logger.error(f"Subscription failed: {e}")
            return {"error": str(e)}

    def unsubscribe(self, instruments):
        """Unsubscribe from market feed"""
        if not self.market_feed:
            return {"error": "Market feed not initialized"}

        try:
            converted_instruments = []
            for exchange, sec_id, sub_type in instruments:
                exchange_enum = getattr(MarketFeed, exchange, MarketFeed.NSE)
                sub_enum = getattr(MarketFeed, sub_type, MarketFeed.Ticker)
                converted_instruments.append((exchange_enum, sec_id, sub_enum))

            self.market_feed.unsubscribe_symbols(converted_instruments)
            self.subscribed_instruments.difference_update([f"{e}-{s}" for e, s, _ in instruments])
            logger.info(f"✅ Unsubscribed from {len(converted_instruments)} instruments")
            return {"status": "unsubscribed", "count": len(converted_instruments)}
        except Exception as e:
            logger.error(f"Unsubscribe failed: {e}")
            return {"error": str(e)}

    def get_tick_data(self):
        """Get latest tick data from buffer (populated by event listeners)"""
        if not self.market_feed:
            return {"error": "Market feed not initialized"}

        if not self.feed_connected:
            return {
                "status": "connecting",
                "message": "Waiting for market feed to connect...",
                "buffered_ticks": len(self.tick_data_buffer)
            }

        try:
            if not self.tick_data_buffer:
                return {
                    "status": "waiting",
                    "message": "No tick data received yet. Feed is listening...",
                    "subscribed_instruments": list(self.subscribed_instruments)
                }

            # Return latest ticks from buffer
            return {
                "status": "success",
                "feed_connected": self.feed_connected,
                "tick_count": len(self.tick_data_buffer),
                "ticks": self.tick_data_buffer,
                "message": "Real-time data updates via event listeners"
            }
        except Exception as e:
            logger.error(f"Get tick data failed: {e}", exc_info=True)
            return {"error": str(e)}

    def disconnect(self):
        """Disconnect from websocket"""
        try:
            if self.market_feed:
                self.market_feed.disconnect()
            self.is_connected = False
            self.subscribed_instruments.clear()
            logger.info("✅ WebSocket disconnected")
            return {"status": "disconnected"}
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            return {"error": str(e)}

    def get_status(self):
        """Get websocket status"""
        return {
            "connected": self.is_connected,
            "subscribed_count": len(self.subscribed_instruments),
            "instruments": list(self.subscribed_instruments)
        }

# Global websocket manager
ws_manager = WebsocketManager() if DHAN_AVAILABLE else None

# Global tools dictionary for registration
TOOLS = {
    # =====================================================================
    # AUTHENTICATION TOOLS
    # =====================================================================
    "get_auth_url": {
        "description": "Get OAuth authentication URL for Dhan API",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "verify_auth_token": {
        "description": "Verify OAuth token and get user info",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token_id": {"type": "string", "description": "OAuth token ID"}
            },
            "required": ["token_id"]
        }
    },

    # =====================================================================
    # PORTFOLIO & ACCOUNT TOOLS
    # =====================================================================
    "get_portfolio": {
        "description": "Get current portfolio holdings with P&L",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_positions": {
        "description": "Get open positions (stocks and options)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_margins": {
        "description": "Get account margins and available balance",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_account_info": {
        "description": "Get detailed account information",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },

    # =====================================================================
    # ORDER MANAGEMENT TOOLS
    # =====================================================================
    "place_order": {
        "description": "Place a new order (BUY/SELL)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "quantity": {"type": "integer", "description": "Order quantity"},
                "price": {"type": "number", "description": "Order price"},
                "side": {"type": "string", "enum": ["BUY", "SELL"], "description": "Order side"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "description": "Order type"}
            },
            "required": ["security_id", "quantity", "side", "order_type"]
        }
    },
    "cancel_order": {
        "description": "Cancel an existing order",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to cancel"}
            },
            "required": ["order_id"]
        }
    },
    "get_orders": {
        "description": "Get order history and status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter by status (PENDING, FILLED, CANCELLED)"}
            },
            "required": []
        }
    },

    # =====================================================================
    # TRADE EXECUTION & BOOK TOOLS
    # =====================================================================
    "get_trade_book": {
        "description": "Get executed trades (filled orders)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_trade_details": {
        "description": "Get details of a specific trade",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trade_id": {"type": "string", "description": "Trade ID"}
            },
            "required": ["trade_id"]
        }
    },
    "exit_position": {
        "description": "Exit a position (sell all or partial quantity)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "quantity": {"type": "integer", "description": "Quantity to exit (omit for all)"}
            },
            "required": ["security_id"]
        }
    },

    # =====================================================================
    # MARKET DATA TOOLS
    # =====================================================================
    "get_quote": {
        "description": "Get real-time price quote for a security",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID (e.g., NIFTY, INFY)"}
            },
            "required": ["security_id"]
        }
    },
    "get_candles": {
        "description": "Get historical candle data (OHLC)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "timeframe": {"type": "string", "enum": ["1min", "5min", "15min", "30min", "1hour", "daily"], "description": "Timeframe"},
                "from_date": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "End date (YYYY-MM-DD)"}
            },
            "required": ["security_id", "timeframe", "from_date", "to_date"]
        }
    },
    "search_instruments": {
        "description": "Search for instruments by name or symbol",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (name, symbol, or ISIN)"}
            },
            "required": ["query"]
        }
    },

    # =====================================================================
    # TECHNICAL ANALYSIS TOOLS
    # =====================================================================
    "analyze_technical": {
        "description": "Comprehensive technical analysis with multiple indicators",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "timeframe": {"type": "string", "description": "Timeframe (1min, 5min, 15min, etc)"},
                "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"}
            },
            "required": ["security_id", "timeframe", "from_date", "to_date"]
        }
    },
    "get_sma": {
        "description": "Get Simple Moving Average",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "period": {"type": "integer", "description": "SMA period (default 20)"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "get_rsi": {
        "description": "Get Relative Strength Index",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "period": {"type": "integer", "description": "RSI period (default 14)"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "get_macd": {
        "description": "Get MACD indicator",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "get_bollinger_bands": {
        "description": "Get Bollinger Bands",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "period": {"type": "integer", "description": "Period (default 20)"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "get_atr": {
        "description": "Get Average True Range",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "period": {"type": "integer", "description": "Period (default 14)"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "get_support_resistance": {
        "description": "Get support and resistance levels",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },
    "analyze_trend": {
        "description": "Analyze trend (uptrend, downtrend, consolidation)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "timeframe": {"type": "string", "description": "Timeframe"}
            },
            "required": ["security_id", "timeframe"]
        }
    },

    # =====================================================================
    # RISK MANAGEMENT TOOLS
    # =====================================================================
    "calculate_position_size": {
        "description": "Calculate ideal position size based on risk management",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_size": {"type": "number", "description": "Account size"},
                "risk_percentage": {"type": "number", "description": "Risk percentage (e.g., 2 for 2%)"},
                "entry_price": {"type": "number", "description": "Entry price"},
                "stop_loss": {"type": "number", "description": "Stop loss price"}
            },
            "required": ["account_size", "risk_percentage", "entry_price", "stop_loss"]
        }
    },
    "calculate_risk_reward": {
        "description": "Calculate Risk:Reward ratio",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry_price": {"type": "number", "description": "Entry price"},
                "stop_loss": {"type": "number", "description": "Stop loss price"},
                "target_price": {"type": "number", "description": "Target price"}
            },
            "required": ["entry_price", "stop_loss", "target_price"]
        }
    },
    "calculate_portfolio_risk": {
        "description": "Analyze total portfolio risk",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "suggest_stop_loss": {
        "description": "Suggest stop loss level using ATR or support/resistance",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "entry_price": {"type": "number", "description": "Entry price"},
                "method": {"type": "string", "enum": ["atr", "support_resistance"], "description": "Method (default: atr)"}
            },
            "required": ["security_id", "entry_price"]
        }
    },
    "check_portfolio_limits": {
        "description": "Check if portfolio exceeds risk limits",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },

    # =====================================================================
    # PORTFOLIO ANALYTICS TOOLS
    # =====================================================================
    "get_portfolio_summary": {
        "description": "Get portfolio overview",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_portfolio_pnl": {
        "description": "Get detailed P&L breakdown",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_trade_statistics": {
        "description": "Get trade metrics (win rate, profit factor, etc)",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_sector_analysis": {
        "description": "Get holdings allocation by sector",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_expiry_analysis": {
        "description": "Analyze option positions by expiry",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_portfolio_greeks": {
        "description": "Get aggregate portfolio Greeks",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },

    # =====================================================================
    # SMART ORDER TOOLS
    # =====================================================================
    "place_bracket_order": {
        "description": "Place bracket order with SL and TP",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "quantity": {"type": "integer", "description": "Quantity"},
                "entry_price": {"type": "number", "description": "Entry price"},
                "stop_loss": {"type": "number", "description": "Stop loss price"},
                "target": {"type": "number", "description": "Target price"}
            },
            "required": ["security_id", "quantity", "entry_price", "stop_loss", "target"]
        }
    },
    "place_trailing_stop_order": {
        "description": "Place order with trailing stop",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "quantity": {"type": "integer", "description": "Quantity"},
                "entry_price": {"type": "number", "description": "Entry price"},
                "trail_percent": {"type": "number", "description": "Trail percentage"}
            },
            "required": ["security_id", "quantity", "entry_price", "trail_percent"]
        }
    },
    "place_oco_order": {
        "description": "Place One-Cancels-Other order",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "quantity": {"type": "integer", "description": "Quantity"},
                "entry_price": {"type": "number", "description": "Entry price"},
                "stop_loss": {"type": "number", "description": "Stop loss"},
                "target": {"type": "number", "description": "Target"}
            },
            "required": ["security_id", "quantity", "entry_price", "stop_loss", "target"]
        }
    },
    "batch_place_orders": {
        "description": "Place multiple orders in sequence",
        "inputSchema": {
            "type": "object",
            "properties": {
                "orders_list": {"type": "array", "description": "List of order dicts"}
            },
            "required": ["orders_list"]
        }
    },

    # =====================================================================
    # OPTION ANALYSIS TOOLS
    # =====================================================================
    "get_option_greeks": {
        "description": "Get Greeks for an option",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Option security ID"},
                "strike": {"type": "number", "description": "Strike price"},
                "expiry": {"type": "string", "description": "Expiry date (YYYY-MM-DD)"},
                "option_type": {"type": "string", "enum": ["CALL", "PUT"], "description": "Option type"}
            },
            "required": ["security_id", "strike", "expiry", "option_type"]
        }
    },
    "analyze_option_chain": {
        "description": "Analyze option chain for expiry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "expiry": {"type": "string", "description": "Expiry date (YYYY-MM-DD)"}
            },
            "required": ["security_id", "expiry"]
        }
    },
    "get_option_payoff_diagram": {
        "description": "Generate payoff diagram for option position",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "strikes": {"type": "array", "description": "List of strikes"},
                "expiry": {"type": "string", "description": "Expiry"}
            },
            "required": ["security_id", "strikes", "expiry"]
        }
    },
    "analyze_iv_term_structure": {
        "description": "Compare IV across expiries and strikes",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"}
            },
            "required": ["security_id"]
        }
    },
    "get_put_call_ratio": {
        "description": "Get put-call ratio for sentiment",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "expiry": {"type": "string", "description": "Expiry (optional)"}
            },
            "required": ["security_id"]
        }
    },
    "find_max_pain": {
        "description": "Find max pain level for expiry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "expiry": {"type": "string", "description": "Expiry date (YYYY-MM-DD)"}
            },
            "required": ["security_id", "expiry"]
        }
    },

    # =====================================================================
    # ALERT MANAGEMENT TOOLS
    # =====================================================================
    "create_price_alert": {
        "description": "Create price alert for a security",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "price": {"type": "number", "description": "Alert price"},
                "direction": {"type": "string", "enum": ["above", "below", "equals"], "description": "Direction"},
                "description": {"type": "string", "description": "Alert description"}
            },
            "required": ["security_id", "price", "direction"]
        }
    },
    "create_volume_alert": {
        "description": "Create volume alert",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "volume_threshold": {"type": "integer", "description": "Volume threshold"}
            },
            "required": ["security_id", "volume_threshold"]
        }
    },
    "create_position_alert": {
        "description": "Create P&L alert for position",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "pnl_threshold": {"type": "number", "description": "P&L threshold"}
            },
            "required": ["security_id", "pnl_threshold"]
        }
    },
    "get_active_alerts": {
        "description": "List all active alerts",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },

    # =====================================================================
    # BACKTESTING TOOLS
    # =====================================================================
    "backtest_strategy": {
        "description": "Run backtest on historical data",
        "inputSchema": {
            "type": "object",
            "properties": {
                "security_id": {"type": "string", "description": "Security ID"},
                "strategy_name": {"type": "string", "description": "Strategy (SMA_Crossover, RSI, MACD, etc)"},
                "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"},
                "initial_capital": {"type": "number", "description": "Initial capital"}
            },
            "required": ["security_id", "strategy_name", "from_date", "to_date", "initial_capital"]
        }
    },
    "analyze_backtest_results": {
        "description": "Get detailed backtest metrics",
        "inputSchema": {
            "type": "object",
            "properties": {
                "backtest_id": {"type": "string", "description": "Backtest ID"}
            },
            "required": ["backtest_id"]
        }
    },
    "compare_strategies": {
        "description": "Compare performance of two strategies",
        "inputSchema": {
            "type": "object",
            "properties": {
                "strategy1": {"type": "string", "description": "Strategy 1 name"},
                "strategy2": {"type": "string", "description": "Strategy 2 name"},
                "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"}
            },
            "required": ["strategy1", "strategy2", "from_date", "to_date"]
        }
    },

    # =====================================================================
    # MARKET ANALYSIS TOOLS
    # =====================================================================
    "analyze_market_breadth": {
        "description": "Analyze market breadth",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"}
            },
            "required": ["from_date", "to_date"]
        }
    },
    "get_sector_performance": {
        "description": "Get sector returns and volatility",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "get_economic_events": {
        "description": "Get upcoming economic events",
        "inputSchema": {"type": "object", "properties": {}, "required": []}
    },
    "analyze_index_correlation": {
        "description": "Analyze correlation between indices",
        "inputSchema": {
            "type": "object",
            "properties": {
                "from_date": {"type": "string", "description": "From date (YYYY-MM-DD)"},
                "to_date": {"type": "string", "description": "To date (YYYY-MM-DD)"}
            },
            "required": ["from_date", "to_date"]
        }
    },

    # =====================================================================
    # WEBSOCKET LIVE MARKET FEED TOOLS
    # =====================================================================
    "ws_connect": {
        "description": "Connect to DhanHQ websocket for live market feed using OAuth",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "ws_subscribe": {
        "description": "Subscribe to live market feed (ticker/quote/full)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instruments": {
                    "type": "array",
                    "description": "List of instruments [[exchange, security_id, type], ...]",
                    "items": {"type": "array"}
                }
            },
            "required": ["instruments"]
        }
    },
    "ws_unsubscribe": {
        "description": "Unsubscribe from market feed instruments",
        "inputSchema": {
            "type": "object",
            "properties": {
                "instruments": {
                    "type": "array",
                    "description": "List of instruments to unsubscribe",
                    "items": {"type": "array"}
                }
            },
            "required": ["instruments"]
        }
    },
    "ws_get_ticks": {
        "description": "Get latest tick/quote data from websocket feed",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "ws_disconnect": {
        "description": "Disconnect from websocket",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "ws_status": {
        "description": "Get websocket connection status and subscribed instruments",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
}


# =============================================================================
# ASYNC CLIENT MANAGEMENT
# =============================================================================

async def init_oauth():
    """Initialize OAuth token handling from HTTP backend"""
    logger.info("OAuth token management: tokens fetched from HTTP backend (/api/oauth/token)")
    if DEBUG_MODE:
        logger.debug(f"HTTP Server URL: {HTTP_SERVER_URL}")
        logger.debug(f"Token endpoint: {HTTP_SERVER_URL}/api/oauth/token")


async def init_http_client():
    """Initialize HTTP client for API calls"""
    global http_client
    http_client = httpx.AsyncClient(timeout=30)
    logger.info("HTTP client initialized")
    await init_oauth()


async def close_http_client():
    """Close HTTP client"""
    global http_client
    if http_client:
        await http_client.aclose()
        logger.info("HTTP client closed")


async def call_http_api(method: str, params: dict = None):
    """Call HTTP server API with optional OAuth authentication"""
    if not http_client:
        return {"error": "HTTP client not initialized"}

    try:
        url = f"{HTTP_SERVER_URL}/api"
        headers = {}

        # Add OAuth token for API calls (obtained from HTTP backend)
        if oauth_token:
            headers["Authorization"] = f"Bearer {oauth_token}"
            if DEBUG_MODE:
                logger.debug(f"Using OAuth token for API call to {method}")

        payload = {"method": method, "params": params or {}}
        response = await http_client.post(url, json=payload, headers=headers)

        if DEBUG_MODE:
            logger.debug(f"API call {method} returned status {response.status_code}")

        return response.json()
    except Exception as e:
        logger.error(f"API call error: {e}")
        return {"error": str(e)}


# =============================================================================
# MCP SERVER TOOL HANDLERS
# =============================================================================

@server.list_tools()
async def list_tools():
    """List all available tools"""
    return [
        {
            "name": name,
            "description": info["description"],
            "inputSchema": info.get("inputSchema", {"type": "object", "properties": {}, "required": []})
        }
        for name, info in TOOLS.items()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """Handle tool calls from Claude"""
    logger.info(f"Tool call: {name} with args: {arguments}")

    try:
        # Handle websocket tools
        if name == "ws_connect":
            result = await ws_manager.connect()
        elif name == "ws_subscribe":
            result = ws_manager.subscribe(arguments.get("instruments", []))
        elif name == "ws_unsubscribe":
            result = ws_manager.unsubscribe(arguments.get("instruments", []))
        elif name == "ws_get_ticks":
            result = ws_manager.get_tick_data()
        elif name == "ws_disconnect":
            result = ws_manager.disconnect()
        elif name == "ws_status":
            result = ws_manager.get_status()
        else:
            # Call HTTP server to handle tool logic
            result = await call_http_api(name, arguments)

        return [{"type": "text", "text": json.dumps(result, indent=2)}]
    except Exception as e:
        logger.error(f"Error calling tool {name}: {str(e)}")
        return [{"type": "text", "text": f"Error calling tool {name}: {str(e)}"}]


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

# =============================================================================
# HTTP ENDPOINTS FOR MCP COMMUNICATION
# =============================================================================

@app.post("/messages")
async def handle_mcp_messages(request: Request):
    """Handle MCP protocol messages via HTTP"""
    try:
        body = await request.json()

        if DEBUG_MODE:
            logger.debug(f"Received MCP message: {body.get('method', 'unknown')}")

        # Process MCP message
        # This is a simplified handler - production would need full MCP protocol support
        method = body.get("method")
        params = body.get("params", {})

        if method == "tools/list":
            return JSONResponse({"tools": await list_tools()})
        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})
            result = await call_tool(tool_name, tool_args)
            return JSONResponse(result)
        else:
            return JSONResponse({"error": f"Unknown method: {method}"}, status_code=400)

    except Exception as e:
        logger.error(f"Error handling MCP message: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "server": "dhan-mcp"}


@app.get("/")
async def root():
    """Root endpoint with server info"""
    return {
        "name": "Dhan MCP Server",
        "version": "1.0.0",
        "status": "running",
        "websocket_ready": True,
        "debug_mode": DEBUG_MODE,
        "endpoints": {
            "health": "/health",
            "messages": "/messages",
            "docs": "/docs",
            "tools": "/tools"
        }
    }


@app.get("/tools")
async def get_tools():
    """Get list of available tools (REST endpoint)"""
    tools = await list_tools()
    return {"tools": tools}


# =============================================================================
# STARTUP AND SHUTDOWN HANDLERS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize when server starts"""
    logger.info("=" * 70)
    logger.info("Initializing Dhan MCP Server (WebSocket + HTTP)")
    logger.info("=" * 70)
    logger.info(f"HTTP Backend: {HTTP_SERVER_URL}")
    if MCP_SERVER_URL:
        logger.info(f"MCP Server URL: {MCP_SERVER_URL}")
    logger.info(f"Debug Mode: {DEBUG_MODE}")
    logger.info(f"📡 MCP Server: http://{MCP_HOST}:{MCP_PORT}")
    logger.info("=" * 70)

    await init_http_client()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when server stops"""
    await close_http_client()
    logger.info("MCP server shut down")


# =============================================================================
# RUN SERVER
# =============================================================================

def run_server():
    """Start the HTTP MCP server"""
    uvicorn.run(
        app,
        host=MCP_HOST,
        port=MCP_PORT,
        log_level="info" if DEBUG_MODE else "warning"
    )


async def main():
    """Main entry point - kept for compatibility"""
    run_server()


if __name__ == "__main__":
    run_server()
