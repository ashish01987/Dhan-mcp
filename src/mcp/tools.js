const { config } = require('../config');

function assertString(value, fieldName) {
  if (typeof value !== 'string' || value.trim() === '') {
    throw new Error(`${fieldName} must be a non-empty string`);
  }
}

function assertEnum(value, allowed, fieldName) {
  if (!allowed.includes(value)) {
    throw new Error(`${fieldName} must be one of: ${allowed.join(', ')}`);
  }
}

function assertPositiveInt(value, fieldName, maxValue) {
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${fieldName} must be a positive integer`);
  }

  if (maxValue && value > maxValue) {
    throw new Error(`${fieldName} cannot exceed ${maxValue}`);
  }
}

function validatePlaceOrder(params) {
  assertString(params.dhan_exchange_segment, 'dhan_exchange_segment');
  assertEnum(params.transaction_type, ['BUY', 'SELL'], 'transaction_type');
  assertEnum(params.product_type, ['CNC', 'INTRADAY', 'MARGIN', 'MTF'], 'product_type');
  assertEnum(params.order_type, ['LIMIT', 'MARKET', 'SL', 'SL-M'], 'order_type');
  assertEnum(params.validity || 'DAY', ['DAY', 'IOC'], 'validity');
  assertString(params.security_id, 'security_id');
  assertPositiveInt(params.quantity, 'quantity', config.maxOrderQuantity);

  if (params.price !== undefined && (typeof params.price !== 'number' || params.price < 0)) {
    throw new Error('price must be a non-negative number');
  }

  if (params.trigger_price !== undefined && (typeof params.trigger_price !== 'number' || params.trigger_price < 0)) {
    throw new Error('trigger_price must be a non-negative number');
  }
}

function buildTools(dhanClient) {
  const tools = {
    get_profile: {
      description: 'Fetch Dhan account profile details.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => ({ ok: true, profile: await dhanClient.getProfile() })
    },
    get_funds: {
      description: 'Fetch Dhan funds/limits.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => ({ ok: true, funds: await dhanClient.getFunds() })
    },
    get_positions: {
      description: 'Fetch open and closed positions.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => ({ ok: true, positions: await dhanClient.getPositions() })
    },
    get_holdings: {
      description: 'Fetch demat holdings.',
      inputSchema: { type: 'object', properties: {} },
      execute: async () => ({ ok: true, holdings: await dhanClient.getHoldings() })
    },
    get_order_by_id: {
      description: 'Fetch a specific order by order_id.',
      inputSchema: {
        type: 'object',
        required: ['order_id'],
        properties: { order_id: { type: 'string' } }
      },
      execute: async (params = {}) => {
        assertString(params.order_id, 'order_id');
        const order = await dhanClient.getOrderById(params.order_id);
        return { ok: true, order_id: params.order_id, order };
      }
    },
    place_order: {
      description: 'Place a Dhan order. Disabled unless ENABLE_TRADING_TOOLS=true.',
      inputSchema: {
        type: 'object',
        required: [
          'dhan_exchange_segment',
          'transaction_type',
          'product_type',
          'order_type',
          'security_id',
          'quantity'
        ],
        properties: {
          dhan_exchange_segment: { type: 'string' },
          transaction_type: { type: 'string', enum: ['BUY', 'SELL'] },
          product_type: { type: 'string', enum: ['CNC', 'INTRADAY', 'MARGIN', 'MTF'] },
          order_type: { type: 'string', enum: ['LIMIT', 'MARKET', 'SL', 'SL-M'] },
          validity: { type: 'string', enum: ['DAY', 'IOC'] },
          security_id: { type: 'string' },
          quantity: { type: 'integer', minimum: 1 },
          price: { type: 'number', minimum: 0 },
          trigger_price: { type: 'number', minimum: 0 }
        }
      },
      execute: async (params = {}) => {
        if (!config.enableTradingTools) {
          throw new Error('Trading tools are disabled. Set ENABLE_TRADING_TOOLS=true to allow order placement.');
        }

        validatePlaceOrder(params);
        const order = await dhanClient.placeOrder(params);
        return { ok: true, message: 'Order placed successfully', order };
      }
    },
    cancel_order: {
      description: 'Cancel an existing order. Disabled unless ENABLE_TRADING_TOOLS=true.',
      inputSchema: {
        type: 'object',
        required: ['order_id'],
        properties: { order_id: { type: 'string' } }
      },
      execute: async (params = {}) => {
        if (!config.enableTradingTools) {
          throw new Error('Trading tools are disabled. Set ENABLE_TRADING_TOOLS=true to allow cancellation.');
        }

        assertString(params.order_id, 'order_id');
        const response = await dhanClient.cancelOrder(params.order_id);
        return { ok: true, message: `Order ${params.order_id} cancelled successfully`, response };
      }
    }
  };

  return tools;
}

module.exports = {
  buildTools
};
