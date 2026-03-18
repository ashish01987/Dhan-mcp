class BaseAgent {
  constructor(name, mcpClient, sharedState, eventBus) {
    this.name = name;
    this.mcpClient = mcpClient;
    this.sharedState = sharedState;
    this.eventBus = eventBus;
    this.isActive = false;
  }

  async start() {
    this.isActive = true;
    this.log(`Agent ${this.name} started`);
    await this.onStart();
  }

  async stop() {
    this.isActive = false;
    this.log(`Agent ${this.name} stopped`);
    await this.onStop();
  }

  async onStart() {
    // Override in subclass
  }

  async onStop() {
    // Override in subclass
  }

  log(message, level = 'info') {
    const timestamp = new Date().toISOString();
    console.log(`[${timestamp}] [${this.name}] [${level.toUpperCase()}] ${message}`);
  }

  error(message, error) {
    this.log(`${message}: ${error.message}`, 'error');
    this.eventBus.emit('AGENT_ERROR', {
      agent: this.name,
      message,
      error: error.message,
      stack: error.stack
    });
  }
}

module.exports = { BaseAgent };
