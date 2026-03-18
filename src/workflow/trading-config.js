const tradingConfig = {
  // Trading parameters
  enableTrading: process.env.ENABLE_TRADING === 'true' || false,
  initialCapital: Number(process.env.INITIAL_CAPITAL) || 100000,
  lotSize: Number(process.env.LOT_SIZE) || 50,
  strikeGap: Number(process.env.STRIKE_GAP) || 50,

  // Risk management
  maxPositions: Number(process.env.MAX_POSITIONS) || 3,
  maxDailyLoss: Number(process.env.MAX_DAILY_LOSS) || 2000,
  maxCapitalPerTrade: Number(process.env.MAX_CAPITAL_PER_TRADE) || 0.3,
  maxPositionSizePercent: Number(process.env.MAX_POSITION_SIZE_PERCENT) || 0.25,
  profitTarget: Number(process.env.PROFIT_TARGET) || 0.5,
  stopLoss: Number(process.env.STOP_LOSS) || 0.3,
  maxVix: Number(process.env.MAX_VIX) || 25,

  // Strategy parameters
  condorWing: Number(process.env.CONDOR_WING) || 200,
  spreadWidth: Number(process.env.SPREAD_WIDTH) || 100,

  // Agent intervals (in milliseconds)
  analysisIntervalMs: Number(process.env.ANALYSIS_INTERVAL_MS) || 300000, // 5 minutes
  monitorIntervalMs: Number(process.env.MONITOR_INTERVAL_MS) || 60000, // 1 minute

  // Safety settings
  rollbackOnFailure: process.env.ROLLBACK_ON_FAILURE !== 'false',
  squareOffOnHalt: process.env.SQUARE_OFF_ON_HALT !== 'false',
  stopAfterTarget: process.env.STOP_AFTER_TARGET === 'true' || false,

  // Mock data for testing (when real market data not available)
  mockNiftySpot: Number(process.env.MOCK_NIFTY_SPOT) || 22450,
  mockVix: Number(process.env.MOCK_VIX) || 18.2,

  // Logging
  logLevel: process.env.LOG_LEVEL || 'info',
  enableEventLog: process.env.ENABLE_EVENT_LOG !== 'false'
};

module.exports = { tradingConfig };
