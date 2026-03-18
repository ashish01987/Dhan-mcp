const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class SupervisorAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config, agents) {
    super('Supervisor', mcpClient, sharedState, eventBus);
    this.config = config;
    this.agents = agents;
    this.workflowStatus = 'initializing';
  }

  async onStart() {
    this.log('Supervisor agent starting...');

    // Register event handlers
    this.registerEventHandlers();

    // Start all agents
    await this.startAgents();

    this.workflowStatus = 'running';
    this.log('Multi-agent workflow started successfully');
    this.eventBus.emit(EVENT_TYPES.AGENT_READY, { agent: 'Supervisor' });
  }

  async onStop() {
    this.workflowStatus = 'stopping';
    await this.stopAgents();
    this.log('Multi-agent workflow stopped');
  }

  registerEventHandlers() {
    // Monitor critical events
    this.eventBus.on(EVENT_TYPES.TRADING_HALTED, this.handleTradingHalted.bind(this));
    this.eventBus.on(EVENT_TYPES.EMERGENCY_EXIT, this.handleEmergencyExit.bind(this));
    this.eventBus.on(EVENT_TYPES.AGENT_ERROR, this.handleAgentError.bind(this));
    this.eventBus.on(EVENT_TYPES.STOP_LOSS_HIT, this.handleStopLoss.bind(this));
    this.eventBus.on(EVENT_TYPES.TARGET_HIT, this.handleTargetHit.bind(this));
  }

  async startAgents() {
    this.log('Starting all agents...');

    for (const [name, agent] of Object.entries(this.agents)) {
      try {
        await agent.start();
        this.log(`Started agent: ${name}`);
      } catch (error) {
        this.error(`Failed to start agent: ${name}`, error);
        throw error;
      }
    }
  }

  async stopAgents() {
    this.log('Stopping all agents...');

    for (const [name, agent] of Object.entries(this.agents)) {
      try {
        await agent.stop();
        this.log(`Stopped agent: ${name}`);
      } catch (error) {
        this.error(`Failed to stop agent: ${name}`, error);
      }
    }
  }

  async handleTradingHalted(data) {
    this.log(`Trading halted: ${data.reason}`, 'warn');
    this.workflowStatus = 'halted';

    // Notify all agents
    this.sharedState.addAlert({
      type: 'trading_halted',
      message: `Trading halted due to: ${data.reason}`,
      severity: 'critical',
      data
    });

    // Square off all positions if needed
    if (this.config.squareOffOnHalt) {
      await this.squareOffAllPositions();
    }
  }

  async handleEmergencyExit(data) {
    this.log(`Emergency exit triggered: ${data.reason}`, 'warn');

    this.sharedState.addAlert({
      type: 'emergency_exit',
      message: `Emergency exit: ${data.reason}`,
      severity: 'critical',
      data
    });

    // Force exit all positions
    await this.squareOffAllPositions();
  }

  handleAgentError(data) {
    this.log(`Agent error: ${data.agent} - ${data.message}`, 'error');

    this.sharedState.addAlert({
      type: 'agent_error',
      message: `${data.agent}: ${data.message}`,
      severity: 'high',
      data
    });

    // Check if critical agent failed
    const criticalAgents = ['RiskManager', 'OrderExecutor'];
    if (criticalAgents.includes(data.agent)) {
      this.log('Critical agent failed, halting workflow', 'error');
      this.sharedState.setTradingStatus('halted');
    }
  }

  async handleStopLoss(data) {
    this.log('Stop loss triggered, taking defensive action', 'warn');

    // Pause new trading
    this.sharedState.setTradingStatus('paused');

    // Wait for positions to be squared off
    await this.wait(5000);

    // Check if we should resume
    const state = this.sharedState.getState();
    if (state.pnl.daily > -this.config.maxDailyLoss) {
      this.log('Resuming trading after stop loss');
      this.sharedState.setTradingStatus('active');
    }
  }

  async handleTargetHit(data) {
    this.log('Profit target achieved!', 'info');

    this.sharedState.addAlert({
      type: 'target_achieved',
      message: `Daily profit target achieved: ${data.pnl}`,
      severity: 'info',
      data
    });

    // Optional: Stop trading for the day after target
    if (this.config.stopAfterTarget) {
      this.log('Stopping trading for the day');
      this.sharedState.setTradingStatus('completed');
      await this.squareOffAllPositions();
    }
  }

  async squareOffAllPositions() {
    this.log('Squaring off all positions...', 'warn');

    if (this.agents.positionMonitor) {
      await this.agents.positionMonitor.squareOffAllPositions();
    }
  }

  getWorkflowStatus() {
    const state = this.sharedState.getState();

    return {
      status: this.workflowStatus,
      tradingStatus: state.tradingStatus,
      positions: state.positions.length,
      dailyPnL: state.pnl.daily,
      alerts: state.alerts.length,
      signals: state.signals.length,
      timestamp: Date.now()
    };
  }

  async wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

module.exports = { SupervisorAgent };
