function parseBoolean(value, fallback = false) {
  if (value === undefined) {
    return fallback;
  }

  return ['1', 'true', 'yes', 'on'].includes(String(value).toLowerCase());
}

function parseNumber(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const config = {
  dhanBaseUrl: process.env.DHAN_BASE_URL || 'https://api.dhan.co/v2',
  dhanAccessToken: process.env.DHAN_ACCESS_TOKEN || '',
  clientId: process.env.DHAN_CLIENT_ID || '',
  requestTimeoutMs: parseNumber(process.env.DHAN_TIMEOUT_MS, 15000),
  enableTradingTools: parseBoolean(process.env.ENABLE_TRADING_TOOLS, false),
  maxOrderQuantity: parseNumber(process.env.MAX_ORDER_QUANTITY, 10000)
};

module.exports = {
  config
};
