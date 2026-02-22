const { config } = require('../config');

class DhanApiError extends Error {
  constructor(message, status, payload) {
    super(message);
    this.name = 'DhanApiError';
    this.status = status;
    this.payload = payload;
  }
}

class DhanClient {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || config.dhanBaseUrl;
    this.accessToken = options.accessToken || config.dhanAccessToken;
    this.clientId = options.clientId || config.clientId;
    this.timeoutMs = options.timeoutMs || config.requestTimeoutMs;

    if (!this.accessToken) {
      throw new Error('DHAN_ACCESS_TOKEN is required to run the MCP server.');
    }

    if (!this.clientId) {
      throw new Error('DHAN_CLIENT_ID is required to run the MCP server.');
    }
  }

  async request(method, path, body) {
    const controller = new AbortController();
    const timeoutHandle = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'access-token': this.accessToken,
          'client-id': this.clientId
        },
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal
      });

      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new DhanApiError(
          payload.message || `Dhan request failed with status ${response.status}`,
          response.status,
          payload
        );
      }

      return payload;
    } catch (error) {
      if (error.name === 'AbortError') {
        throw new DhanApiError('Dhan request timed out', 408, {});
      }

      throw error;
    } finally {
      clearTimeout(timeoutHandle);
    }
  }

  getProfile() {
    return this.request('GET', '/profile');
  }

  getFunds() {
    return this.request('GET', '/fundlimit');
  }

  getPositions() {
    return this.request('GET', '/positions');
  }

  getHoldings() {
    return this.request('GET', '/holdings');
  }

  placeOrder(orderPayload) {
    return this.request('POST', '/orders', orderPayload);
  }

  cancelOrder(orderId) {
    return this.request('DELETE', `/orders/${orderId}`);
  }

  getOrderById(orderId) {
    return this.request('GET', `/orders/${orderId}`);
  }


  getHistoricalCharts(chartPayload) {
    return this.request('POST', '/charts/historical', chartPayload);
  }
}


module.exports = {
  DhanClient,
  DhanApiError
};
