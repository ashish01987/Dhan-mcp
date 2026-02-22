const { DhanClient, DhanApiError } = require('./dhan/client');
const { buildTools } = require('./mcp/tools');

const SERVER_INFO = {
  name: 'dhan-mcp',
  version: '1.1.0'
};

const JSON_RPC_VERSION = '2.0';

function sendMessage(message) {
  const json = JSON.stringify(message);
  const payload = `Content-Length: ${Buffer.byteLength(json, 'utf8')}\r\n\r\n${json}`;
  process.stdout.write(payload);
}

function sendResult(id, result) {
  sendMessage({ jsonrpc: JSON_RPC_VERSION, id, result });
}

function sendError(id, code, message, data) {
  sendMessage({
    jsonrpc: JSON_RPC_VERSION,
    id,
    error: {
      code,
      message,
      data
    }
  });
}

function listTools(toolMap) {
  return Object.entries(toolMap).map(([name, tool]) => ({
    name,
    description: tool.description,
    inputSchema: tool.inputSchema
  }));
}

async function handleRequest(request, toolMap) {
  const { id, method, params } = request;

  if (method === 'initialize') {
    sendResult(id, {
      protocolVersion: '2024-11-05',
      serverInfo: SERVER_INFO,
      capabilities: {
        tools: {}
      }
    });
    return;
  }

  if (method === 'notifications/initialized') {
    return;
  }

  if (method === 'tools/list') {
    sendResult(id, { tools: listTools(toolMap) });
    return;
  }

  if (method === 'tools/call') {
    const toolName = params && params.name;
    const tool = toolMap[toolName];

    if (!tool) {
      sendError(id, -32602, `Unknown tool: ${toolName}`);
      return;
    }

    try {
      const data = await tool.execute((params && params.arguments) || {});
      sendResult(id, {
        content: [
          {
            type: 'text',
            text: JSON.stringify(data, null, 2)
          }
        ]
      });
    } catch (error) {
      if (error instanceof DhanApiError) {
        sendError(id, -32000, error.message, {
          status: error.status,
          payload: error.payload
        });
        return;
      }

      sendError(id, -32001, error.message);
    }
    return;
  }

  sendError(id, -32601, `Method not found: ${method}`);
}

function parseFrames(buffer, onMessage) {
  let working = buffer;

  while (true) {
    const headerEnd = working.indexOf('\r\n\r\n');
    if (headerEnd === -1) {
      break;
    }

    const headerPart = working.slice(0, headerEnd);
    const match = /Content-Length:\s*(\d+)/i.exec(headerPart);
    if (!match) {
      throw new Error('Missing Content-Length header');
    }

    const contentLength = Number(match[1]);
    const messageStart = headerEnd + 4;
    const messageEnd = messageStart + contentLength;

    if (working.length < messageEnd) {
      break;
    }

    const messageJson = working.slice(messageStart, messageEnd);
    onMessage(JSON.parse(messageJson));
    working = working.slice(messageEnd);
  }

  return working;
}

async function main() {
  const dhanClient = new DhanClient();
  const tools = buildTools(dhanClient);
  let buffer = '';

  process.stdin.setEncoding('utf8');
  process.stderr.write('Dhan MCP server started over stdio.\n');

  process.stdin.on('data', (chunk) => {
    buffer += chunk;

    try {
      buffer = parseFrames(buffer, (request) => {
        handleRequest(request, tools).catch((error) => {
          sendError(request.id, -32099, error.message);
        });
      });
    } catch (error) {
      process.stderr.write(`Protocol parse error: ${error.message}\n`);
    }
  });
}

main().catch((error) => {
  process.stderr.write(`Fatal error: ${error.message}\n`);
  process.exit(1);
});
