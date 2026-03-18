const { BaseAgent } = require('./base-agent');
const { EVENT_TYPES } = require('../workflow/event-bus');

class OrderExecutorAgent extends BaseAgent {
  constructor(mcpClient, sharedState, eventBus, config) {
    super('OrderExecutor', mcpClient, sharedState, eventBus);
    this.config = config;
    this.orderTracker = new Map();
  }

  async onStart() {
    this.eventBus.on(EVENT_TYPES.RISK_CHECK_PASSED, this.executeOrder.bind(this));
    this.log('Order executor ready');
  }

  async executeOrder(data) {
    const { signal, riskChecks } = data;

    try {
      this.log(`Executing order for signal: ${signal.action}`);

      if (!this.config.enableTrading) {
        this.log('Trading is disabled (paper trading mode)', 'warn');
        this.simulateOrder(signal);
        return;
      }

      // Execute the orders based on strategy
      const orders = await this.placeStrategyOrders(signal);

      for (const order of orders) {
        this.orderTracker.set(order.order_id, {
          signal,
          order,
          timestamp: Date.now(),
          status: 'placed'
        });

        this.sharedState.updateOrders([...this.orderTracker.values()].map(o => o.order));
        this.eventBus.emit(EVENT_TYPES.ORDER_PLACED, { signal, order });
      }

      this.log(`Successfully placed ${orders.length} orders`);

    } catch (error) {
      this.error('Order execution failed', error);
      this.eventBus.emit(EVENT_TYPES.ORDER_FAILED, {
        signal,
        error: error.message
      });
    }
  }

  async placeStrategyOrders(signal) {
    const orders = [];

    // Extract legs from signal
    const legs = signal.legs || [signal];

    for (const leg of legs) {
      const orderParams = {
        dhan_exchange_segment: leg.exchangeSegment || 'NSE_FNO',
        transaction_type: leg.action, // 'BUY' or 'SELL'
        product_type: 'INTRADAY',
        order_type: leg.orderType || 'LIMIT',
        validity: 'DAY',
        security_id: leg.securityId,
        quantity: leg.quantity,
        price: leg.price
      };

      if (leg.stopLoss) {
        orderParams.trigger_price = leg.stopLoss;
      }

      try {
        this.log(`Placing order: ${leg.action} ${leg.quantity}x ${leg.securityId} @ ${leg.price}`);
        const result = await this.mcpClient.callTool('place_order', orderParams);

        if (result.ok) {
          orders.push({
            order_id: result.order?.orderId || `mock-${Date.now()}`,
            leg,
            result
          });
        }
      } catch (error) {
        this.error(`Failed to place order for leg: ${leg.securityId}`, error);
        // Roll back previous orders if needed
        if (orders.length > 0 && this.config.rollbackOnFailure) {
          await this.rollbackOrders(orders);
        }
        throw error;
      }
    }

    return orders;
  }

  async rollbackOrders(orders) {
    this.log('Rolling back orders...', 'warn');

    for (const order of orders) {
      try {
        await this.mcpClient.callTool('cancel_order', {
          order_id: order.order_id
        });
        this.log(`Cancelled order: ${order.order_id}`);
      } catch (error) {
        this.error(`Failed to cancel order ${order.order_id}`, error);
      }
    }
  }

  simulateOrder(signal) {
    this.log('Simulating order (paper trading)');

    const mockOrders = (signal.legs || [signal]).map((leg, index) => ({
      order_id: `mock-${Date.now()}-${index}`,
      leg,
      result: {
        ok: true,
        message: 'Simulated order',
        order: {
          orderId: `mock-${Date.now()}-${index}`,
          status: 'FILLED'
        }
      }
    }));

    for (const order of mockOrders) {
      this.orderTracker.set(order.order_id, {
        signal,
        order,
        timestamp: Date.now(),
        status: 'filled'
      });
    }

    this.sharedState.updateOrders([...this.orderTracker.values()].map(o => o.order));
    this.eventBus.emit(EVENT_TYPES.ORDER_PLACED, { signal, orders: mockOrders });
  }

  async monitorOrder(orderId) {
    try {
      const order = await this.mcpClient.callTool('get_order_by_id', {
        order_id: orderId
      });

      const tracked = this.orderTracker.get(orderId);
      if (tracked) {
        tracked.status = order.order?.orderStatus || 'unknown';
        tracked.lastUpdate = Date.now();

        if (tracked.status === 'TRADED' || tracked.status === 'FILLED') {
          this.eventBus.emit(EVENT_TYPES.ORDER_FILLED, {
            order_id: orderId,
            order: tracked.order
          });
        }
      }

      return order;
    } catch (error) {
      this.error(`Failed to monitor order ${orderId}`, error);
      return null;
    }
  }

  async cancelOrder(orderId) {
    try {
      this.log(`Cancelling order: ${orderId}`);
      const result = await this.mcpClient.callTool('cancel_order', {
        order_id: orderId
      });

      const tracked = this.orderTracker.get(orderId);
      if (tracked) {
        tracked.status = 'cancelled';
      }

      this.eventBus.emit(EVENT_TYPES.ORDER_CANCELLED, {
        order_id: orderId,
        result
      });

      return result;
    } catch (error) {
      this.error(`Failed to cancel order ${orderId}`, error);
      throw error;
    }
  }
}

module.exports = { OrderExecutorAgent };
