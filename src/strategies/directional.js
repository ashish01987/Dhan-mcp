class DirectionalStrategy {
  constructor() {
    this.name = 'Directional Spread';
    this.type = 'directional';
  }

  async generateSignal(market, config, analysis) {
    const trend = analysis.marketConditions?.trend || 'neutral';
    const atmStrike = this.findATMStrike(market.niftySpot, config.strikeGap || 50);
    const expiry = this.getNextExpiry();
    const spreadWidth = config.spreadWidth || 100;

    if (trend === 'bullish') {
      return this.bullCallSpread(market, atmStrike, expiry, spreadWidth, config);
    } else if (trend === 'bearish') {
      return this.bearPutSpread(market, atmStrike, expiry, spreadWidth, config);
    }

    return null;
  }

  bullCallSpread(market, atmStrike, expiry, spreadWidth, config) {
    // Buy ATM call, Sell OTM call
    const buyStrike = atmStrike;
    const sellStrike = atmStrike + spreadWidth;

    return {
      strategy: 'bull_call_spread',
      action: 'ENTER',
      expiry,
      legs: [
        {
          action: 'BUY',
          instrument: 'CALL',
          strike: buyStrike,
          securityId: `NIFTY${expiry}${buyStrike}CE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'CALL', buyStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'SELL',
          instrument: 'CALL',
          strike: sellStrike,
          securityId: `NIFTY${expiry}${sellStrike}CE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'CALL', sellStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        }
      ],
      targetProfit: 0.5,
      stopLoss: 0.3,
      maxLoss: spreadWidth * (config.lotSize || 50)
    };
  }

  bearPutSpread(market, atmStrike, expiry, spreadWidth, config) {
    // Buy ATM put, Sell OTM put
    const buyStrike = atmStrike;
    const sellStrike = atmStrike - spreadWidth;

    return {
      strategy: 'bear_put_spread',
      action: 'ENTER',
      expiry,
      legs: [
        {
          action: 'BUY',
          instrument: 'PUT',
          strike: buyStrike,
          securityId: `NIFTY${expiry}${buyStrike}PE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'PUT', buyStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'SELL',
          instrument: 'PUT',
          strike: sellStrike,
          securityId: `NIFTY${expiry}${sellStrike}PE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'PUT', sellStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        }
      ],
      targetProfit: 0.5,
      stopLoss: 0.3,
      maxLoss: spreadWidth * (config.lotSize || 50)
    };
  }

  findATMStrike(spotPrice, strikeGap) {
    return Math.round(spotPrice / strikeGap) * strikeGap;
  }

  getNextExpiry() {
    const now = new Date();
    const day = String(now.getDate()).padStart(2, '0');
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
    const month = months[now.getMonth()];
    const year = String(now.getFullYear()).slice(-2);

    return `${day}${month}${year}`;
  }

  estimateOptionPrice(market, instrument, strike) {
    const spotDiff = Math.abs(market.niftySpot - strike);
    const basePrice = Math.max(200 - (spotDiff / 50), 10);
    const volatilityPremium = (market.vix / 15) * 40;

    return Math.max(basePrice + volatilityPremium, 10);
  }
}

module.exports = { DirectionalStrategy };
