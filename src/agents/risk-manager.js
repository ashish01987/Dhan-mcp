const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class RiskManagerAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config) {
    super('RiskManager', mcpClient, sharedState, eventBus);
    this.config = config;
  }

  async onStart() {
    this.eventBus.on(EVENT_TYPES.SIGNAL_GENERATED, this.evaluateRisk.bind(this));
    this.log('Risk manager ready');
  }

  async evaluateRisk(signal) {
    try {
      this.log(`Evaluating risk for signal: ${signal.action}`);

      // Fetch current funds and positions
      const [funds, positions] = await Promise.all([
        this.mcpClient.callTool('get_funds'),
        this.mcpClient.callTool('get_positions')
      ]);

      const riskChecks = await this.performRiskChecks(signal, funds, positions);

      if (riskChecks.approved) {
        this.log('Risk checks passed');
        this.eventBus.emit(EVENT_TYPES.RISK_CHECK_PASSED, {
          signal,
          riskChecks
        });
      } else {
        this.log(`Risk checks failed: ${riskChecks.reasons.join(', ')}`, 'warn');
        this.eventBus.emit(EVENT_TYPES.RISK_CHECK_FAILED, {
          signal,
          riskChecks
        });
        this.sharedState.addAlert({
          type: 'risk_rejection',
          message: `Signal rejected: ${riskChecks.reasons.join(', ')}`,
          severity: 'medium'
        });
      }

    } catch (error) {
      this.error('Risk evaluation failed', error);
      this.eventBus.emit(EVENT_TYPES.RISK_CHECK_FAILED, { signal, error: error.message });
    }
  }

  async performRiskChecks(signal, funds, positions) {
    const state = this.sharedState.getState();
    const checks = [];
    const reasons = [];

    // Check 1: Available capital
    const availableBalance = funds.funds?.availablelBalance || 0;
    const requiredMargin = this.calculateRequiredMargin(signal);

    const capitalCheck = requiredMargin < availableBalance * this.config.maxCapitalPerTrade;
    checks.push({ name: 'capital', passed: capitalCheck });
    if (!capitalCheck) {
      reasons.push(`Insufficient capital: Required ${requiredMargin}, Available ${availableBalance}`);
    }

    // Check 2: Maximum positions
    const currentPositions = positions.positions?.length || 0;
    const positionLimitCheck = currentPositions < this.config.maxPositions;
    checks.push({ name: 'position_limit', passed: positionLimitCheck });
    if (!positionLimitCheck) {
      reasons.push(`Max positions reached: ${currentPositions}/${this.config.maxPositions}`);
    }

    // Check 3: Daily loss limit
    const dailyPnL = state.pnl.daily;
    const dailyLossCheck = dailyPnL > -this.config.maxDailyLoss;
    checks.push({ name: 'daily_loss', passed: dailyLossCheck });
    if (!dailyLossCheck) {
      reasons.push(`Daily loss limit exceeded: ${dailyPnL}`);
    }

    // Check 4: Position sizing
    const positionSize = this.calculatePositionSize(signal);
    const maxPositionValue = availableBalance * this.config.maxPositionSizePercent;
    const positionSizeCheck = positionSize <= maxPositionValue;
    checks.push({ name: 'position_size', passed: positionSizeCheck });
    if (!positionSizeCheck) {
      reasons.push(`Position size too large: ${positionSize} > ${maxPositionValue}`);
    }

    // Check 5: Trading status
    const tradingStatusCheck = state.tradingStatus === 'active';
    checks.push({ name: 'trading_status', passed: tradingStatusCheck });
    if (!tradingStatusCheck) {
      reasons.push(`Trading is ${state.tradingStatus}`);
    }

    // Check 6: Time-based checks
    const timeCheck = this.isWithinTradingWindow();
    checks.push({ name: 'trading_time', passed: timeCheck });
    if (!timeCheck) {
      reasons.push('Outside trading window');
    }

    const approved = checks.every(check => check.passed);

    return {
      approved,
      checks,
      reasons,
      requiredMargin,
      positionSize,
      recommendation: approved ? 'PROCEED' : 'REJECT'
    };
  }

  calculateRequiredMargin(signal) {
    // Simplified margin calculation
    // In production, use actual margin requirements from broker
    const quantity = signal.quantity || 50;
    const price = signal.price || signal.entryPrice || 200;

    return quantity * price * 0.2; // Assume 20% margin
  }

  calculatePositionSize(signal) {
    const quantity = signal.quantity || 50;
    const price = signal.price || signal.entryPrice || 200;

    return quantity * price;
  }

  isWithinTradingWindow() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();

    // No new positions after 3:00 PM
    if (hours >= 15) return false;

    // Market hours: 9:15 AM to 3:00 PM
    if (hours < 9 || hours > 15) return false;
    if (hours === 9 && minutes < 15) return false;

    return true;
  }

  async checkCircuitBreakers() {
    const state = this.sharedState.getState();

    // Daily loss breaker
    if (state.pnl.daily < -this.config.maxDailyLoss) {
      this.log('Daily loss breaker triggered!', 'warn');
      this.sharedState.setTradingStatus('halted');
      this.eventBus.emit(EVENT_TYPES.TRADING_HALTED, {
        reason: 'daily_loss_limit',
        pnl: state.pnl.daily
      });
      return false;
    }

    // Volatility breaker
    if (state.market.vix > this.config.maxVix) {
      this.log('Volatility breaker triggered!', 'warn');
      this.sharedState.setTradingStatus('paused');
      this.eventBus.emit(EVENT_TYPES.TRADING_HALTED, {
        reason: 'high_volatility',
        vix: state.market.vix
      });
      return false;
    }

    return true;
  }
}

module.exports = { RiskManagerAgent };
