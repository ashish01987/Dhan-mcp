class IronCondorStrategy {
  constructor() {
    this.name = 'Iron Condor';
    this.type = 'iron_condor';
  }

  async generateSignal(market, config, analysis) {
    const atmStrike = this.findATMStrike(market.niftySpot, config.strikeGap || 50);
    const expiry = this.getNextExpiry();
    const wing = config.condorWing || 200; // Distance between strikes

    // Iron Condor:
    // Sell OTM call, Buy further OTM call
    // Sell OTM put, Buy further OTM put
    const sellCallStrike = atmStrike + wing;
    const buyCallStrike = atmStrike + (wing * 2);
    const sellPutStrike = atmStrike - wing;
    const buyPutStrike = atmStrike - (wing * 2);

    return {
      strategy: 'iron_condor',
      action: 'ENTER',
      atmStrike,
      expiry,
      legs: [
        {
          action: 'SELL',
          instrument: 'CALL',
          strike: sellCallStrike,
          securityId: `NIFTY${expiry}${sellCallStrike}CE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'CALL', sellCallStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'BUY',
          instrument: 'CALL',
          strike: buyCallStrike,
          securityId: `NIFTY${expiry}${buyCallStrike}CE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'CALL', buyCallStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'SELL',
          instrument: 'PUT',
          strike: sellPutStrike,
          securityId: `NIFTY${expiry}${sellPutStrike}PE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'PUT', sellPutStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        },
        {
          action: 'BUY',
          instrument: 'PUT',
          strike: buyPutStrike,
          securityId: `NIFTY${expiry}${buyPutStrike}PE`,
          quantity: config.lotSize || 50,
          price: this.estimateOptionPrice(market, 'PUT', buyPutStrike),
          orderType: 'LIMIT',
          exchangeSegment: 'NSE_FNO'
        }
      ],
      targetProfit: 0.5,
      stopLoss: 0.3,
      maxLoss: wing * (config.lotSize || 50)
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
    const basePrice = Math.max(200 - (spotDiff / 50), 5);
    const volatilityPremium = (market.vix / 15) * 30;

    return Math.max(basePrice + volatilityPremium, 5);
  }
}

module.exports = { IronCondorStrategy };
