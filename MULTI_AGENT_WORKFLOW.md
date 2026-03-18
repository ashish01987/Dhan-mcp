# Multi-Agent Workflow for Intraday Nifty Option Trading

This document describes the multi-agent trading workflow built using the Agent SDK pattern for automated intraday Nifty option trading.

## 🏗️ Architecture Overview

The system uses a **hierarchical multi-agent architecture** with specialized agents coordinating through an event-driven workflow:

```
                    ┌─────────────────────┐
                    │  Supervisor Agent   │
                    │   (Orchestration)   │
                    └──────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼────────┐    ┌───────▼────────┐    ┌───────▼────────┐
│ Market Analyzer│    │ Signal Generator│    │  Risk Manager  │
│   (Analysis)   │───▶│  (Strategies)   │───▶│  (Validation)  │
└────────────────┘    └─────────────────┘    └────────┬───────┘
                                                       │
        ┌──────────────────────┬───────────────────────┘
        │                      │
┌───────▼────────┐    ┌───────▼────────┐
│ Order Executor │    │Position Monitor│
│  (Execution)   │    │  (Monitoring)  │
└────────────────┘    └────────────────┘
         │                     │
         └──────────┬──────────┘
                    │
            ┌───────▼────────┐
            │   MCP Client   │
            │ (Dhan Server)  │
            └────────────────┘
```

## 🤖 Agents

### 1. Market Analyzer Agent
**Purpose**: Analyze market conditions and identify trading opportunities

**Capabilities**:
- Fetches positions and funds from Dhan via MCP
- Analyzes Nifty spot price and VIX
- Determines market trend (bullish/bearish/neutral)
- Assesses volatility (high/medium/low)
- Identifies trading opportunities based on market conditions
- Runs every 5 minutes (configurable)

**Decision Logic**:
- High volatility + neutral trend → Short Straddle
- Low volatility + neutral trend → Iron Condor
- Bullish trend + medium volatility → Bull Call Spread
- Bearish trend + medium volatility → Bear Put Spread

### 2. Signal Generator Agent
**Purpose**: Generate actionable trading signals based on strategies

**Capabilities**:
- Receives market analysis from Market Analyzer
- Selects appropriate trading strategy
- Generates detailed trade signals with multiple legs
- Calculates entry prices, quantities, and strikes
- Forwards signals to Risk Manager

**Supported Strategies**:
- Short Straddle (sell ATM call + ATM put)
- Iron Condor (4-leg range-bound strategy)
- Bull Call Spread (buy call + sell higher call)
- Bear Put Spread (buy put + sell lower put)

### 3. Risk Manager Agent
**Purpose**: Enforce risk rules and validate signals

**Risk Checks**:
- Capital availability (max 30% per trade)
- Position limits (max 3 concurrent positions)
- Daily loss limit (₹2,000 default)
- Position sizing validation
- Trading status verification
- Time-based restrictions (no new positions after 3:00 PM)

**Circuit Breakers**:
- Daily loss breaker (halts trading)
- Volatility breaker (pauses during high VIX)
- Time-based breaker (squares off at 3:20 PM)

### 4. Order Executor Agent
**Purpose**: Execute orders via Dhan MCP server

**Capabilities**:
- Places multi-leg option orders
- Supports MARKET, LIMIT, and SL orders
- Tracks order status
- Implements rollback on failure
- Supports paper trading mode (simulation)

**Safety Features**:
- Order validation before placement
- Automatic rollback if any leg fails
- Order status monitoring
- Error handling and retry logic

### 5. Position Monitor Agent
**Purpose**: Continuously monitor positions and manage exits

**Monitoring**:
- Fetches positions every minute
- Calculates real-time P&L
- Checks profit targets (50% default)
- Checks stop losses (30% default)
- Time-based exit (3:20 PM)

**Actions**:
- Automatic exit on profit target
- Automatic exit on stop loss
- Emergency square-off near market close
- Position alerts for large losses

### 6. Supervisor Agent
**Purpose**: Orchestrate the entire workflow

**Responsibilities**:
- Start/stop all agents
- Monitor agent health
- Handle critical events (halts, errors)
- Coordinate emergency exits
- Provide workflow status

## 📊 Trading Strategies

### Short Straddle
**Use Case**: High volatility with neutral trend

**Structure**:
- Sell ATM Call
- Sell ATM Put

**Profit**: Premium collected
**Risk**: Unlimited (market moves sharply in either direction)

### Iron Condor
**Use Case**: Low volatility, range-bound market

**Structure**:
- Sell OTM Call + Buy further OTM Call
- Sell OTM Put + Buy further OTM Put

**Profit**: Net premium collected
**Risk**: Limited to wing spread

### Bull Call Spread
**Use Case**: Moderately bullish trend

**Structure**:
- Buy ATM Call
- Sell OTM Call

**Profit**: Limited to spread width - premium paid
**Risk**: Limited to premium paid

### Bear Put Spread
**Use Case**: Moderately bearish trend

**Structure**:
- Buy ATM Put
- Sell OTM Put

**Profit**: Limited to spread width - premium paid
**Risk**: Limited to premium paid

## 🔄 Event-Driven Workflow

The agents communicate via events:

```
MARKET_DATA_UPDATE
    ↓
MARKET_ANALYSIS_COMPLETE
    ↓
SIGNAL_GENERATED
    ↓
RISK_CHECK_PASSED / RISK_CHECK_FAILED
    ↓
ORDER_PLACED
    ↓
ORDER_FILLED
    ↓
POSITION_OPENED
    ↓
TARGET_HIT / STOP_LOSS_HIT / TIME_BASED_EXIT
    ↓
POSITION_CLOSED
```

## ⚙️ Configuration

Edit environment variables or `/src/workflow/trading-config.js`:

```bash
# Trading
ENABLE_TRADING=false              # Set true for live trading
INITIAL_CAPITAL=100000            # Starting capital
LOT_SIZE=50                       # Nifty lot size
STRIKE_GAP=50                     # Strike interval

# Risk Management
MAX_POSITIONS=3                   # Maximum concurrent positions
MAX_DAILY_LOSS=2000              # Daily loss limit in ₹
MAX_CAPITAL_PER_TRADE=0.3        # 30% max per trade
PROFIT_TARGET=0.5                # 50% profit target
STOP_LOSS=0.3                    # 30% stop loss
MAX_VIX=25                       # Max VIX for trading

# Strategy
CONDOR_WING=200                  # Iron Condor wing width
SPREAD_WIDTH=100                 # Spread width for directional

# Intervals
ANALYSIS_INTERVAL_MS=300000      # 5 minutes
MONITOR_INTERVAL_MS=60000        # 1 minute

# Safety
ROLLBACK_ON_FAILURE=true
SQUARE_OFF_ON_HALT=true
STOP_AFTER_TARGET=false

# Mock Data (for testing)
MOCK_NIFTY_SPOT=22450
MOCK_VIX=18.2
```

## 🚀 Running the Workflow

### Prerequisites

```bash
# Set Dhan credentials
export DHAN_ACCESS_TOKEN=your_access_token
export DHAN_CLIENT_ID=your_client_id

# Enable trading tools (required for order execution)
export ENABLE_TRADING_TOOLS=true

# Configure trading parameters
export ENABLE_TRADING=false  # Start with paper trading
```

### Start the Workflow

```bash
# Production
npm run workflow

# Development (with auto-restart)
npm run workflow:dev
```

### Expected Output

```
============================================================
🏦 Dhan Multi-Agent Trading Workflow
    Intraday Nifty Option Trading System
============================================================

🚀 Initializing Multi-Agent Trading Workflow...
📡 Starting MCP client...
✅ MCP client connected
📊 Strategies loaded
🤖 Agents initialized
👨‍✈️ Supervisor agent ready

🎯 Starting Multi-Agent Workflow...

✅ Multi-Agent Workflow is now running!

📋 Configuration:
   - Trading Enabled: false
   - Initial Capital: ₹100000
   - Max Positions: 3
   - Max Daily Loss: ₹2000
   - Profit Target: 50%
   - Stop Loss: 30%

📊 Agents Status:
   - marketAnalyzer: ✅ Active
   - signalGenerator: ✅ Active
   - riskManager: ✅ Active
   - orderExecutor: ✅ Active
   - positionMonitor: ✅ Active

⏳ Workflow is running. Press Ctrl+C to stop.
```

## 🔐 Safety Features

1. **Paper Trading Mode**: Test strategies without real orders
2. **Risk Limits**: Enforced at multiple levels
3. **Circuit Breakers**: Auto-halt on excessive losses
4. **Position Limits**: Maximum concurrent positions
5. **Time Restrictions**: No new positions after 3:00 PM
6. **Auto Square-Off**: All positions closed by 3:20 PM
7. **Rollback Support**: Failed multi-leg orders are rolled back
8. **Error Handling**: Comprehensive error handling at every layer

## 📈 Monitoring

The workflow prints status updates every minute:

```
📊 Status Update [2026-03-18T13:30:00Z]
   Workflow: running | Trading: active
   Positions: 2 | Daily P&L: ₹850.50
   Signals: 3 | Alerts: 0
```

Alerts are displayed when triggered:

```
⚠️  Recent Alerts:
   - [high] Position NIFTY18MAR22450CE down 45%
   - [medium] Signal rejected: Insufficient capital
```

## 🧪 Testing

### Paper Trading (Recommended for Testing)

```bash
export ENABLE_TRADING=false
npm run workflow
```

Orders will be simulated without placing real trades.

### Live Trading (Use with Caution)

```bash
export ENABLE_TRADING=true
export ENABLE_TRADING_TOOLS=true
npm run workflow
```

⚠️ **Warning**: Live trading involves real money. Start with small position sizes and monitor closely.

## 📁 File Structure

```
src/
├── agents/
│   ├── base-agent.js           # Base class for all agents
│   ├── market-analyzer.js      # Market analysis agent
│   ├── signal-generator.js     # Signal generation agent
│   ├── risk-manager.js         # Risk management agent
│   ├── order-executor.js       # Order execution agent
│   ├── position-monitor.js     # Position monitoring agent
│   └── supervisor.js           # Supervisor orchestration agent
├── strategies/
│   ├── straddle.js            # Short straddle strategy
│   ├── iron-condor.js         # Iron condor strategy
│   └── directional.js         # Directional spreads
├── workflow/
│   ├── shared-state.js        # Centralized state management
│   ├── event-bus.js           # Event-driven communication
│   ├── mcp-client.js          # MCP client for Dhan server
│   └── trading-config.js      # Trading configuration
├── multi-agent-workflow.js     # Main workflow entry point
├── server.js                   # MCP server (existing)
├── dhan/                       # Dhan API client (existing)
└── mcp/                        # MCP tools (existing)
```

## 🔧 Customization

### Add a New Strategy

1. Create strategy file in `src/strategies/`:

```javascript
class MyStrategy {
  async generateSignal(market, config, analysis) {
    return {
      strategy: 'my_strategy',
      action: 'ENTER',
      legs: [
        // Define option legs
      ]
    };
  }
}
```

2. Register in `multi-agent-workflow.js`:

```javascript
this.strategies = {
  my_strategy: new MyStrategy(),
  // ... existing strategies
};
```

### Modify Risk Parameters

Edit `src/workflow/trading-config.js` or set environment variables.

### Add Custom Indicators

Extend `MarketAnalyzerAgent` in `src/agents/market-analyzer.js`:

```javascript
async analyzeMarket(marketData) {
  // Add your custom indicators
  const rsi = this.calculateRSI(marketData);
  const vwap = this.calculateVWAP(marketData);

  // Use in opportunity identification
  const opportunity = this.identifyOpportunity(analysis, state);
}
```

## 🐛 Troubleshooting

### MCP Client Connection Issues

- Ensure `DHAN_ACCESS_TOKEN` and `DHAN_CLIENT_ID` are set
- Check if MCP server is running: `npm start`
- Verify environment variables: `printenv | grep DHAN`

### Trading Tools Disabled

- Set `ENABLE_TRADING_TOOLS=true` to enable order placement
- This is a safety feature - tools are disabled by default

### Orders Not Executing

- Check if `ENABLE_TRADING=true` (paper trading mode is default)
- Verify risk checks are passing in logs
- Check trading hours (9:15 AM - 3:15 PM)

### High CPU Usage

- Increase analysis interval: `ANALYSIS_INTERVAL_MS=600000` (10 min)
- Increase monitor interval: `MONITOR_INTERVAL_MS=120000` (2 min)

## 📚 Additional Resources

- [Dhan API Documentation](https://api.dhan.co)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Nifty Options Trading Guide](https://www.nseindia.com)

## ⚖️ Disclaimer

This is an educational project demonstrating multi-agent workflows for algorithmic trading.

**Important**:
- Trading involves substantial risk of loss
- Past performance does not guarantee future results
- Test thoroughly in paper trading mode before live trading
- Use appropriate position sizing and risk management
- This software is provided "as is" without warranty

## 📄 License

MIT License - See LICENSE file for details
