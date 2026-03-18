const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class PositionMonitorAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config) {
    super('PositionMonitor', mcpClient, sharedState, eventBus);
    this.config = config;
    this.monitorInterval = null;
    this.positionTargets = new Map();
  }

  async onStart() {
    this.eventBus.on(EVENT_TYPES.ORDER_FILLED, this.trackPosition.bind(this));

    // Start periodic monitoring every minute
    this.monitorInterval = setInterval(() => {
      this.monitorPositions().catch(err => this.error('Position monitoring failed', err));
    }, this.config.monitorIntervalMs || 60000);

    this.log('Position monitor ready');
  }

  async onStop() {
    if (this.monitorInterval) {
      clearInterval(this.monitorInterval);
    }
  }

  trackPosition(data) {
    const { order_id, order } = data;

    // Set profit target and stop loss for the position
    this.positionTargets.set(order_id, {
      orderId: order_id,
      targetProfit: this.config.profitTarget || 0.5, // 50%
      stopLoss: this.config.stopLoss || 0.3, // 30%
      entryTime: Date.now()
    });

    this.log(`Tracking position: ${order_id}`);
  }

  async monitorPositions() {
    try {
      this.log('Monitoring open positions...');

      const positions = await this.mcpClient.callTool('get_positions');

      if (!positions.ok || !positions.positions) {
        this.log('No positions data available', 'warn');
        return;
      }

      this.sharedState.updatePositions(positions.positions);

      // Calculate P&L
      const pnl = this.calculatePnL(positions.positions);
      this.sharedState.updatePnL(pnl);

      // Check each position against targets
      for (const position of positions.positions) {
        await this.checkPositionTargets(position, pnl);
      }

      // Check time-based exit
      await this.checkTimeBasedExit();

    } catch (error) {
      this.error('Position monitoring failed', error);
    }
  }

  calculatePnL(positions) {
    let realized = 0;
    let unrealized = 0;

    for (const position of positions) {
      const positionPnL = position.realizedProfit || 0;
      const unrealizedPnL = position.unrealizedProfit || 0;

      realized += positionPnL;
      unrealized += unrealizedPnL;
    }

    return {
      realized,
      unrealized,
      daily: realized + unrealized
    };
  }

  async checkPositionTargets(position, pnl) {
    const dailyPnL = pnl.daily;
    const dailyPnLPercent = dailyPnL / (this.config.initialCapital || 100000);

    // Check profit target
    if (dailyPnLPercent >= this.config.profitTarget) {
      this.log(`Profit target hit! Daily P&L: ${dailyPnL}`, 'info');
      this.eventBus.emit(EVENT_TYPES.TARGET_HIT, {
        position,
        pnl: dailyPnL,
        percent: dailyPnLPercent
      });

      // Trigger exit
      await this.exitPosition(position, 'PROFIT_TARGET');
    }

    // Check stop loss
    if (dailyPnLPercent <= -this.config.stopLoss) {
      this.log(`Stop loss hit! Daily P&L: ${dailyPnL}`, 'warn');
      this.eventBus.emit(EVENT_TYPES.STOP_LOSS_HIT, {
        position,
        pnl: dailyPnL,
        percent: dailyPnLPercent
      });

      // Trigger exit
      await this.exitPosition(position, 'STOP_LOSS');
    }

    // Position-specific checks
    const positionPnL = (position.unrealizedProfit || 0) + (position.realizedProfit || 0);
    const positionValue = position.buyValue || position.sellValue || 10000;
    const positionPnLPercent = positionPnL / positionValue;

    if (positionPnLPercent <= -0.5) {
      // Individual position down 50%
      this.log(`Individual position loss exceeded: ${position.securityId}`, 'warn');
      this.sharedState.addAlert({
        type: 'position_loss',
        message: `Position ${position.securityId} down ${(positionPnLPercent * 100).toFixed(2)}%`,
        severity: 'high'
      });
    }
  }

  async checkTimeBasedExit() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();

    // Square off all positions by 3:20 PM
    if (hours === 15 && minutes >= 20) {
      this.log('Market close approaching, squaring off all positions', 'info');

      const state = this.sharedState.getState();
      for (const position of state.positions) {
        await this.exitPosition(position, 'TIME_BASED_EXIT');
      }

      this.eventBus.emit(EVENT_TYPES.EMERGENCY_EXIT, {
        reason: 'market_close',
        time: now.toISOString()
      });
    }
  }

  async exitPosition(position, reason) {
    try {
      this.log(`Exiting position: ${position.securityId} (Reason: ${reason})`);

      // Determine exit action (opposite of entry)
      const exitAction = position.positionType === 'LONG' ? 'SELL' : 'BUY';

      const exitSignal = {
        action: exitAction,
        securityId: position.securityId,
        quantity: Math.abs(position.netQty || position.quantity || 0),
        orderType: 'MARKET',
        reason,
        exchangeSegment: position.exchangeSegment || 'NSE_FNO'
      };

      this.eventBus.emit(EVENT_TYPES.SIGNAL_GENERATED, exitSignal);
      this.eventBus.emit(EVENT_TYPES.POSITION_CLOSED, {
        position,
        reason
      });

    } catch (error) {
      this.error(`Failed to exit position ${position.securityId}`, error);
    }
  }

  async squareOffAllPositions() {
    const state = this.sharedState.getState();
    this.log(`Squaring off ${state.positions.length} positions`, 'warn');

    for (const position of state.positions) {
      await this.exitPosition(position, 'SQUARE_OFF');
    }
  }
}

module.exports = { PositionMonitorAgent };
