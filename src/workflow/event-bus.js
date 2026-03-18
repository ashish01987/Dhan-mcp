const EventEmitter = require('events');

class EventBus extends EventEmitter {
  constructor() {
    super();
    this.setMaxListeners(50);
    this.eventLog = [];
    this.maxLogSize = 1000;
  }

  emit(event, ...args) {
    const eventData = {
      event,
      timestamp: Date.now(),
      data: args[0]
    };

    this.eventLog.push(eventData);
    if (this.eventLog.length > this.maxLogSize) {
      this.eventLog.shift();
    }

    return super.emit(event, ...args);
  }

  getEventLog() {
    return [...this.eventLog];
  }

  clearEventLog() {
    this.eventLog = [];
  }
}

const EVENT_TYPES = {
  // Market events
  MARKET_DATA_UPDATE: 'market_data_updated',
  MARKET_ANALYSIS_COMPLETE: 'market_analysis_complete',

  // Signal events
  SIGNAL_GENERATED: 'signal_generated',
  SIGNAL_APPROVED: 'signal_approved',
  SIGNAL_REJECTED: 'signal_rejected',

  // Risk events
  RISK_CHECK_PASSED: 'risk_check_passed',
  RISK_CHECK_FAILED: 'risk_check_failed',
  RISK_ALERT: 'risk_alert',

  // Order events
  ORDER_PLACED: 'order_placed',
  ORDER_FILLED: 'order_filled',
  ORDER_FAILED: 'order_failed',
  ORDER_CANCELLED: 'order_cancelled',

  // Position events
  POSITION_OPENED: 'position_opened',
  POSITION_CLOSED: 'position_closed',
  POSITION_ALERT: 'position_alert',

  // System events
  TRADING_HALTED: 'trading_halted',
  TRADING_RESUMED: 'trading_resumed',
  STOP_LOSS_HIT: 'stop_loss_hit',
  TARGET_HIT: 'target_hit',
  EMERGENCY_EXIT: 'emergency_exit',

  // Agent events
  AGENT_ERROR: 'agent_error',
  AGENT_READY: 'agent_ready',
  WORKFLOW_COMPLETE: 'workflow_complete'
};

module.exports = { EventBus, EVENT_TYPES };
