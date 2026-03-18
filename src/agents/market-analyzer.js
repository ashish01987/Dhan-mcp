const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class MarketAnalyzerAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config) {
    super('MarketAnalyzer', mcpClient, sharedState, eventBus);
    this.config = config;
    this.analysisInterval = null;
  }

  async onStart() {
    this.eventBus.on(EVENT_TYPES.MARKET_DATA_UPDATE, this.analyzeMarket.bind(this));

    // Start periodic analysis every 5 minutes
    this.analysisInterval = setInterval(() => {
      this.fetchAndAnalyze().catch(err => this.error('Analysis failed', err));
    }, this.config.analysisIntervalMs || 300000);

    // Run initial analysis
    await this.fetchAndAnalyze();
  }

  async onStop() {
    if (this.analysisInterval) {
      clearInterval(this.analysisInterval);
    }
  }

  async fetchAndAnalyze() {
    try {
      this.log('Fetching market data...');

      const [positions, funds] = await Promise.all([
        this.mcpClient.callTool('get_positions'),
        this.mcpClient.callTool('get_funds')
      ]);

      // Update shared state
      this.sharedState.updatePositions(positions.positions || []);

      const marketData = {
        niftySpot: this.config.mockNiftySpot || 22450,
        vix: this.config.mockVix || 18.2,
        timestamp: Date.now()
      };

      this.sharedState.updateMarket(marketData);

      // Perform analysis
      await this.analyzeMarket(marketData);

    } catch (error) {
      this.error('Failed to fetch market data', error);
    }
  }

  async analyzeMarket(marketData) {
    try {
      this.log('Analyzing market conditions...');

      const state = this.sharedState.getState();
      const analysis = {
        marketState: this.determineMarketState(marketData),
        trend: this.determineTrend(marketData),
        volatility: this.assessVolatility(marketData.vix),
        tradingOpportunity: false,
        recommendation: null,
        confidence: 0
      };

      // Check for trading opportunities
      if (this.isWithinTradingHours()) {
        const opportunity = this.identifyOpportunity(analysis, state);
        if (opportunity) {
          analysis.tradingOpportunity = true;
          analysis.recommendation = opportunity;
          analysis.confidence = this.calculateConfidence(analysis);

          this.log(`Trading opportunity identified: ${opportunity.type}`);
          this.eventBus.emit(EVENT_TYPES.MARKET_ANALYSIS_COMPLETE, analysis);
        }
      } else {
        this.log('Outside trading hours, skipping opportunity analysis');
      }

      return analysis;

    } catch (error) {
      this.error('Market analysis failed', error);
      throw error;
    }
  }

  determineMarketState(marketData) {
    // Simplified market state determination
    if (marketData.vix > 20) return 'volatile';
    if (marketData.vix < 15) return 'calm';
    return 'normal';
  }

  determineTrend(marketData) {
    // Simplified trend determination
    // In production, use technical indicators like moving averages
    const currentPrice = marketData.niftySpot;
    const previousPrice = this.sharedState.getState().market.niftySpot || currentPrice;

    if (currentPrice > previousPrice * 1.002) return 'bullish';
    if (currentPrice < previousPrice * 0.998) return 'bearish';
    return 'neutral';
  }

  assessVolatility(vix) {
    if (vix > 20) return 'high';
    if (vix < 15) return 'low';
    return 'medium';
  }

  identifyOpportunity(analysis, state) {
    // Check if we already have open positions
    if (state.positions.length >= this.config.maxPositions) {
      this.log('Max positions reached, no new opportunities');
      return null;
    }

    // Check daily loss limit
    if (state.pnl.daily < -this.config.maxDailyLoss) {
      this.log('Daily loss limit reached, no new opportunities');
      return null;
    }

    // Identify strategy based on market conditions
    if (analysis.volatility === 'high' && analysis.trend === 'neutral') {
      return {
        type: 'short_straddle',
        reason: 'High volatility with neutral trend suggests premium collection',
        marketConditions: analysis
      };
    }

    if (analysis.volatility === 'low' && analysis.trend === 'neutral') {
      return {
        type: 'iron_condor',
        reason: 'Low volatility with neutral trend, good for range-bound strategy',
        marketConditions: analysis
      };
    }

    if (analysis.trend === 'bullish' && analysis.volatility === 'medium') {
      return {
        type: 'bull_call_spread',
        reason: 'Bullish trend with moderate volatility',
        marketConditions: analysis
      };
    }

    if (analysis.trend === 'bearish' && analysis.volatility === 'medium') {
      return {
        type: 'bear_put_spread',
        reason: 'Bearish trend with moderate volatility',
        marketConditions: analysis
      };
    }

    return null;
  }

  calculateConfidence(analysis) {
    let confidence = 0.5;

    if (analysis.volatility === 'high') confidence += 0.1;
    if (analysis.trend !== 'neutral') confidence += 0.15;
    if (analysis.marketState === 'normal') confidence += 0.1;

    return Math.min(confidence, 0.95);
  }

  isWithinTradingHours() {
    const now = new Date();
    const hours = now.getHours();
    const minutes = now.getMinutes();

    // Market hours: 9:15 AM to 3:15 PM
    if (hours < 9 || hours > 15) return false;
    if (hours === 9 && minutes < 15) return false;
    if (hours === 15 && minutes > 15) return false;

    return true;
  }
}

module.exports = { MarketAnalyzerAgent };
