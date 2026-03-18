const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class SignalGeneratorAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config, strategies) {
    super('SignalGenerator', mcpClient, sharedState, eventBus);
    this.config = config;
    this.strategies = strategies;
  }

  async onStart() {
    this.eventBus.on(EVENT_TYPES.MARKET_ANALYSIS_COMPLETE, this.generateSignal.bind(this));
    this.log('Signal generator ready');
  }

  async generateSignal(analysis) {
    try {
      if (!analysis.tradingOpportunity || !analysis.recommendation) {
        return;
      }

      this.log(`Generating signal for: ${analysis.recommendation.type}`);

      const state = this.sharedState.getState();
      const strategyType = analysis.recommendation.type;
      const strategy = this.strategies[strategyType];

      if (!strategy) {
        this.log(`Strategy ${strategyType} not found`, 'warn');
        return;
      }

      const signal = await strategy.generateSignal(
        state.market,
        this.config,
        analysis
      );

      if (signal) {
        signal.strategyType = strategyType;
        signal.reason = analysis.recommendation.reason;
        signal.confidence = analysis.confidence;
        signal.timestamp = Date.now();

        this.sharedState.addSignal(signal);
        this.log(`Signal generated: ${signal.action} ${signal.strategy}`);
        this.eventBus.emit(EVENT_TYPES.SIGNAL_GENERATED, signal);
      }

    } catch (error) {
      this.error('Failed to generate signal', error);
    }
  }
}

module.exports = { SignalGeneratorAgent };
