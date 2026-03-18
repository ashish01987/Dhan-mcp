const { MCPClient } = require('./workflow/mcp-client');
const { SharedState } = require('./workflow/shared-state');
const { EventBus } = require('./workflow/event-bus');
const { tradingConfig } = require('./workflow/trading-config');

// Import agents
const { MarketAnalyzerAgent } = require('./agents/market-analyzer');
const { SignalGeneratorAgent } = require('./agents/signal-generator');
const { RiskManagerAgent } = require('./agents/risk-manager');
const { OrderExecutorAgent } = require('./agents/order-executor');
const { PositionMonitorAgent } = require('./agents/position-monitor');
const { SupervisorAgent } = require('./agents/supervisor');

// Import strategies
const { StraddleStrategy } = require('./strategies/straddle');
const { IronCondorStrategy } = require('./strategies/iron-condor');
const { DirectionalStrategy } = require('./strategies/directional');

class MultiAgentWorkflow {
  constructor(config) {
    this.config = config;
    this.mcpClient = null;
    this.sharedState = null;
    this.eventBus = null;
    this.agents = {};
    this.supervisor = null;
    this.strategies = {};
  }

  async initialize() {
    console.log('🚀 Initializing Multi-Agent Trading Workflow...');

    // Initialize core components
    this.mcpClient = new MCPClient();
    this.sharedState = new SharedState();
    this.eventBus = new EventBus();

    // Start MCP client
    console.log('📡 Starting MCP client...');
    await this.mcpClient.start();
    console.log('✅ MCP client connected');

    // Initialize strategies
    this.strategies = {
      short_straddle: new StraddleStrategy(),
      iron_condor: new IronCondorStrategy(),
      bull_call_spread: new DirectionalStrategy(),
      bear_put_spread: new DirectionalStrategy()
    };
    console.log('📊 Strategies loaded');

    // Initialize agents
    this.agents = {
      marketAnalyzer: new MarketAnalyzerAgent(
        this.mcpClient,
        this.sharedState,
        this.eventBus,
        this.config
      ),
      signalGenerator: new SignalGeneratorAgent(
        this.mcpClient,
        this.sharedState,
        this.eventBus,
        this.config,
        this.strategies
      ),
      riskManager: new RiskManagerAgent(
        this.mcpClient,
        this.sharedState,
        this.eventBus,
        this.config
      ),
      orderExecutor: new OrderExecutorAgent(
        this.mcpClient,
        this.sharedState,
        this.eventBus,
        this.config
      ),
      positionMonitor: new PositionMonitorAgent(
        this.mcpClient,
        this.sharedState,
        this.eventBus,
        this.config
      )
    };
    console.log('🤖 Agents initialized');

    // Initialize supervisor
    this.supervisor = new SupervisorAgent(
      this.mcpClient,
      this.sharedState,
      this.eventBus,
      this.config,
      this.agents
    );
    console.log('👨‍✈️ Supervisor agent ready');
  }

  async start() {
    console.log('\n🎯 Starting Multi-Agent Workflow...\n');

    try {
      await this.supervisor.start();

      console.log('\n✅ Multi-Agent Workflow is now running!');
      console.log('\n📋 Configuration:');
      console.log(`   - Trading Enabled: ${this.config.enableTrading}`);
      console.log(`   - Initial Capital: ₹${this.config.initialCapital}`);
      console.log(`   - Max Positions: ${this.config.maxPositions}`);
      console.log(`   - Max Daily Loss: ₹${this.config.maxDailyLoss}`);
      console.log(`   - Profit Target: ${this.config.profitTarget * 100}%`);
      console.log(`   - Stop Loss: ${this.config.stopLoss * 100}%`);
      console.log('\n📊 Agents Status:');
      for (const [name, agent] of Object.entries(this.agents)) {
        console.log(`   - ${name}: ${agent.isActive ? '✅ Active' : '❌ Inactive'}`);
      }
      console.log('\n');

    } catch (error) {
      console.error('❌ Failed to start workflow:', error.message);
      throw error;
    }
  }

  async stop() {
    console.log('\n🛑 Stopping Multi-Agent Workflow...');

    try {
      if (this.supervisor) {
        await this.supervisor.stop();
      }

      if (this.mcpClient) {
        await this.mcpClient.stop();
      }

      console.log('✅ Workflow stopped successfully');

    } catch (error) {
      console.error('❌ Error stopping workflow:', error.message);
    }
  }

  getStatus() {
    if (this.supervisor) {
      return this.supervisor.getWorkflowStatus();
    }
    return { status: 'not_initialized' };
  }

  getState() {
    return this.sharedState.getState();
  }
}

// Main execution
async function main() {
  console.log('\n' + '='.repeat(60));
  console.log('🏦 Dhan Multi-Agent Trading Workflow');
  console.log('    Intraday Nifty Option Trading System');
  console.log('='.repeat(60) + '\n');

  const workflow = new MultiAgentWorkflow(tradingConfig);

  // Graceful shutdown
  const shutdown = async () => {
    console.log('\n\n📴 Shutdown signal received...');
    await workflow.stop();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  try {
    await workflow.initialize();
    await workflow.start();

    // Keep the workflow running
    console.log('⏳ Workflow is running. Press Ctrl+C to stop.\n');

    // Optionally print status every minute
    setInterval(() => {
      const status = workflow.getStatus();
      const state = workflow.getState();

      console.log(`\n📊 Status Update [${new Date().toISOString()}]`);
      console.log(`   Workflow: ${status.status} | Trading: ${status.tradingStatus}`);
      console.log(`   Positions: ${status.positions} | Daily P&L: ₹${state.pnl.daily.toFixed(2)}`);
      console.log(`   Signals: ${status.signals} | Alerts: ${status.alerts}`);

      if (state.alerts.length > 0) {
        console.log('\n⚠️  Recent Alerts:');
        state.alerts.slice(-3).forEach(alert => {
          console.log(`   - [${alert.severity}] ${alert.message}`);
        });
      }
    }, 60000); // Every minute

  } catch (error) {
    console.error('\n❌ Fatal error:', error.message);
    console.error(error.stack);
    await workflow.stop();
    process.exit(1);
  }
}

// Run the workflow if this file is executed directly
if (require.main === module) {
  main().catch(error => {
    console.error('Fatal error:', error);
    process.exit(1);
  });
}

module.exports = { MultiAgentWorkflow };
