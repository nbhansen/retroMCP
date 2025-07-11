# Model Context Protocol (MCP) - Research & Implementation Notes

## Overview

The Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to Large Language Models (LLMs). Think of it as a "USB-C port for AI applications" - it provides a standardized way to connect AI models to various data sources and tools.

## Core Concepts

### Architecture

MCP follows a client-server architecture:

- **MCP Hosts**: Applications like Claude Desktop that want to access data
- **MCP Clients**: Protocol clients that maintain persistent connections with servers
- **MCP Servers**: Lightweight programs that expose specific capabilities
- **Local Data Sources**: Files, databases, and services on your computer
- **Remote Services**: External systems accessible via APIs

### Protocol Details

- **Communication**: Uses JSON-RPC 2.0 for message exchange
- **Message Types**:
  - Requests (expect a response)
  - Results (successful responses)
  - Errors (failed requests)
  - Notifications (one-way messages)
- **Transport Options**:
  - Stdio transport (for local processes)
  - HTTP with SSE (for remote communication)

### Server Capabilities

MCP servers can expose three main types of capabilities:

1. **Tools**: Enable LLMs to perform actions
   - Execute commands
   - Modify state
   - Interact with external systems

2. **Resources**: Expose data and content
   - File contents
   - Database records
   - API responses
   - System information

3. **Prompts**: Create reusable templates
   - Predefined workflows
   - Common query patterns
   - Context-aware prompts

## RetroPie MCP Server Design

### Proposed Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Claude/LLM    │────▶│   MCP Client     │────▶│  MCP Server     │
│   Application   │◀────│                  │◀────│  (on Pi/Local)  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                                                           ▼
                                                  ┌─────────────────┐
                                                  │  Raspberry Pi   │
                                                  │   (RetroPie)    │
                                                  └─────────────────┘
```

### Tools to Implement

1. **Game Control**
   - `launchGame(system, romName)` - Start a specific game
   - `stopCurrentGame()` - Stop the running game
   - `listGames(system?)` - Get available games
   - `switchGame(system, romName)` - Stop current and start new

2. **System Control**
   - `restartEmulationStation()` - Restart the frontend
   - `rebootSystem()` - Reboot Raspberry Pi
   - `shutdownSystem()` - Safe shutdown
   - `setVolume(level)` - Audio control

3. **Information & Monitoring**
   - `getSystemInfo()` - CPU, memory, temperature
   - `getCurrentGame()` - What's currently running
   - `takeScreenshot()` - Capture current display

### Resources to Expose

1. **Game Library**
   - `games://list` - All available games
   - `games://[system]/list` - Games for specific system
   - `games://[system]/[rom]/info` - Game metadata

2. **System Status**
   - `system://info` - Hardware and OS information
   - `system://processes` - Running processes
   - `system://config` - RetroPie configuration

3. **Media**
   - `media://screenshots` - Saved screenshots
   - `media://boxart/[system]/[game]` - Game artwork

### Implementation Approach

1. **Language**: TypeScript (best MCP SDK support)
2. **Transport**: 
   - Local: stdio for same-machine operation
   - Remote: HTTP/SSE for network access
3. **Pi Communication**:
   - SSH for remote command execution
   - EmulationStation CLI commands
   - Direct file system access for ROM info
4. **Security**:
   - Authentication for remote access
   - Command whitelisting
   - Rate limiting

## Example Implementation

### Basic Server Structure (TypeScript)

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new Server({
  name: "retropie-mcp",
  version: "1.0.0"
}, {
  capabilities: {
    tools: {},
    resources: {}
  }
});

// Tool: Launch Game
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "launchGame") {
    const { system, romName } = request.params.arguments;
    // SSH to Pi and execute launch command
    await executeSSHCommand(`emulationstation --launch ${system} ${romName}`);
    return { content: [{ type: "text", text: `Launched ${romName} on ${system}` }] };
  }
});

// Resource: Game List
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  if (request.params.uri === "games://list") {
    const games = await fetchGameList();
    return { contents: [{ uri: request.params.uri, text: JSON.stringify(games) }] };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

## SSH Integration for Remote Control

```typescript
import { Client } from 'ssh2';

async function executeSSHCommand(command: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const conn = new Client();
    conn.on('ready', () => {
      conn.exec(command, (err, stream) => {
        if (err) reject(err);
        let output = '';
        stream.on('data', (data) => output += data);
        stream.on('close', () => {
          conn.end();
          resolve(output);
        });
      });
    }).connect({
      host: process.env.RETROPIE_HOST,
      username: process.env.RETROPIE_USER,
      privateKey: require('fs').readFileSync(process.env.SSH_KEY_PATH)
    });
  });
}
```

## Benefits of MCP for RetroPie Control

1. **Standardized Interface**: Any MCP-compatible LLM client can control RetroPie
2. **Natural Language Control**: "Launch Super Mario World" instead of complex commands
3. **Context Awareness**: LLM understands game library and system state
4. **Extensibility**: Easy to add new tools and resources
5. **Security**: Built-in authentication and controlled access

## Next Steps

1. Set up TypeScript project with MCP SDK
2. Implement basic server with game listing
3. Add SSH connectivity for remote control
4. Create tool implementations for game control
5. Test with Claude Desktop or other MCP clients
6. Add authentication and security measures
7. Document setup and usage instructions