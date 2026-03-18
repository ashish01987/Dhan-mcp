class StraddleStrategy {
  constructor() {
    this.name = 'Short Straddle';
    this.type = 'short_straddle';
  }

  async generateSignal(market, config, analysis) {
    const atmStrike = this.findATMStrike(market.niftySpot, config.strikeGap || 50);
    const expiry = this.getNextExpiry();

    // Short straddle: Sell ATM call and ATM put
    return {
      strategy: 'short_straddle',
      action: 'ENTER',
      strike: atmStrike,
      expiry,
      legs: [
        {
          action: 'SELL',
          instrument: 'CALL',
          strike: atmStrike,
          securityId: `NIFTY${expiry}${atmStrike}CE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'CALL', atmStrike, 0),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'SELL',
          instrument: 'PUT',
          strike: atmStrike,
          securityId: `NIFTY${expiry}${atmStrike}PE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'PUT', atmStrike, 0),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        }
      ],
      entryPrice: null,
      targetProfit: 0.5,
      stopLoss: 0.3,
      maxLoss: null
    };
  }

  findATMStrike(spotPrice, strikeGap) {
    return Math.round(spotPrice / strikeGap) * strikeGap;
  }

  getNextExpiry() {
    // Simplified - return current week expiry
    // Format: DDMMMYY (e.g., 20MAR26)
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const month = months[now.getMonth()];
    const year = String(now.getFullYear()).slice(-2);

    return `${day}${month}${year}`;
  }

  estimateOptionPrice(market, instrument, strike, delta) {
    // Simplified option pricing
    // In production, use Black-Scholes or fetch from market data
    const spotDiff = Math.abs(market.niftySpot - strike);
    const basePrice = 200 - (spotDiff / 50);
    const volatilityPremium = (market.vix / 15) * 50;

    return Math.max(basePrice + volatilityPremium, 10);
  }
}

module.exports = { StraddleStrategy };
