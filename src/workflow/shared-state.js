class SharedState {
  constructor() {
    this.state = {
      market: {
        niftySpot: 0,
        vix: 0,
        timestamp: null,
        trend: 'neutral',
        volatility: 'normal'
      },
      positions: [],
      orders: [],
      pnl: {
        realized: 0,
        unrealized: 0,
        daily: 0
      },
      risk: {
        capitalDeployed: 0,
        marginUsed: 0,
        marginAvailable: 0,
        positionsCount: 0,
        maxDailyLoss: 0,
        currentDailyLoss: 0
      },
      signals: [],
      alerts: [],
      tradingStatus: 'active', // active, paused, halted
      lastUpdate: null
    };
  }

  getState() {
    return JSON.parse(JSON.stringify(this.state));
  }

  updateMarket(marketData) {
    this.state.market = { ...this.state.market, ...marketData };
    this.state.lastUpdate = Date.now();
  }

  updatePositions(positions) {
    this.state.positions = positions;
    this.state.risk.positionsCount = positions.length;
    this.state.lastUpdate = Date.now();
  }

  updateOrders(orders) {
    this.state.orders = orders;
    this.state.lastUpdate = Date.now();
  }

  updatePnL(pnl) {
    this.state.pnl = { ...this.state.pnl, ...pnl };
    this.state.lastUpdate = Date.now();
  }

  updateRisk(risk) {
    this.state.risk = { ...this.state.risk, ...risk };
    this.state.lastUpdate = Date.now();
  }

  addSignal(signal) {
    this.state.signals.push({
      ...signal,
      timestamp: Date.now(),
      id: `signal-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    });
    this.state.lastUpdate = Date.now();
  }

  addAlert(alert) {
    this.state.alerts.push({
      ...alert,
      timestamp: Date.now(),
      id: `alert-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    });
    this.state.lastUpdate = Date.now();
  }

  setTradingStatus(status) {
    this.state.tradingStatus = status;
    this.state.lastUpdate = Date.now();
  }

  clearSignals() {
    this.state.signals = [];
    this.state.lastUpdate = Date.now();
  }

  clearAlerts() {
    this.state.alerts = [];
    this.state.lastUpdate = Date.now();
  }

  reset() {
    this.state = {
      market: {
        niftySpot: 0,
        vix: 0,
        timestamp: null,
        trend: 'neutral',
        volatility: 'normal'
      },
      positions: [],
      orders: [],
      pnl: {
        realized: 0,
        unrealized: 0,
        daily: 0
      },
      risk: {
        capitalDeployed: 0,
        marginUsed: 0,
        marginAvailable: 0,
        positionsCount: 0,
        maxDailyLoss: 0,
        currentDailyLoss: 0
      },
      signals: [],
      alerts: [],
      tradingStatus: 'active',
      lastUpdate: null
    };
  }
}

module.exports = { SharedState };
