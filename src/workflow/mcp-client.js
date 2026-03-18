const { spawn } = require('child_process');
const { config } = require('../config');

class MCPClient {
  constructor(serverPath) {
    this.serverPath = serverPath || '/home/runner/work/Dhan-mcp/Dhan-mcp/src/server.js';
    this.process = null;
    this.requestId = 0;
    this.pendingRequests = new Map();
    this.buffer = '';
    this.isInitialized = false;
  }

  async start() {
    return new Promise((resolve, reject) => {
      this.process = spawn('node', [this.serverPath], {
        stdio: ['pipe', 'pipe', 'pipe'],
        env: process.env
      });

      this.process.stdout.on('data', (chunk) => {
        this.handleData(chunk);
      });

      this.process.stderr.on('data', (data) => {
        console.error(`MCP Server stderr: ${data}`);
      });

      this.process.on('error', (error) => {
        reject(new Error(`Failed to start MCP server: ${error.message}`));
      });

      setTimeout(async () => {
        try {
          await this.initialize();
          resolve();
        } catch (error) {
          reject(error);
        }
      }, 1000);
    });
  }

  handleData(chunk) {
    this.buffer += chunk.toString();

    while (true) {
      const headerEnd = this.buffer.indexOf('\r\n\r\n');
      if (headerEnd === -1) break;

      const headerPart = this.buffer.slice(0, headerEnd);
      const match = /Content-Length:\s*(\d+)/i.exec(headerPart);
      if (!match) break;

      const contentLength = Number(match[1]);
      const messageStart = headerEnd + 4;
      const messageEnd = messageStart + contentLength;

      if (this.buffer.length < messageEnd) break;

      const messageJson = this.buffer.slice(messageStart, messageEnd);
      const message = JSON.parse(messageJson);

      this.handleMessage(message);

      this.buffer = this.buffer.slice(messageEnd);
    }
  }

  handleMessage(message) {
    if (message.id && this.pendingRequests.has(message.id)) {
      const { resolve, reject } = this.pendingRequests.get(message.id);
      this.pendingRequests.delete(message.id);

      if (message.error) {
        reject(new Error(message.error.message));
      } else {
        resolve(message.result);
      }
    }
  }

  sendRequest(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++this.requestId;
      const request = {
        jsonrpc: '2.0',
        id,
        method,
        params
      };

      this.pendingRequests.set(id, { resolve, reject });

      const json = JSON.stringify(request);
      const message = `Content-Length: ${Buffer.byteLength(json, 'utf8')}\r\n\r\n${json}`;

      this.process.stdin.write(message);

      setTimeout(() => {
        if (this.pendingRequests.has(id)) {
          this.pendingRequests.delete(id);
          reject(new Error('Request timeout'));
        }
      }, 30000);
    });
  }

  async initialize() {
    const result = await this.sendRequest('initialize', {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: {
        name: 'multi-agent-workflow',
        version: '1.0.0'
      }
    });

    this.isInitialized = true;
    return result;
  }

  async listTools() {
    if (!this.isInitialized) {
      throw new Error('MCP client not initialized');
    }
    const result = await this.sendRequest('tools/list');
    return result.tools;
  }

  async callTool(name, args = {}) {
    if (!this.isInitialized) {
      throw new Error('MCP client not initialized');
    }

    const result = await this.sendRequest('tools/call', {
      name,
      arguments: args
    });

    if (result.content && result.content[0] && result.content[0].text) {
      return JSON.parse(result.content[0].text);
    }

    return result;
  }

  async stop() {
    if (this.process) {
      this.process.kill();
      this.process = null;
      this.isInitialized = false;
    }
  }
}

module.exports = { MCPClient };
