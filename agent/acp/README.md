# ACP (Agent Communication Protocol) Module

This module provides Agent-to-Agent communication capabilities using the ACP protocol.

## Features

- **Session Management** - Create, resume, and manage agent sessions
- **Multiple Transports** - stdio (for terminal integration) and HTTP (for remote access)
- **Tool Integration** - Expose agent tools via ACP
- **JSON-RPC 2.0** - Standard protocol format

## Usage

```python
from agent.acp.adapter import ACPServer

# Create server with agent
server = ACPServer(agent)
await server.start()

# Or via CLI
python -m agent.acp.adapter --transport stdio
```

## Protocol

The ACP protocol is based on JSON-RPC 2.0 with sessions.

Key methods:
- `initialize` - Initialize connection
- `session/new` - Create new session
- `session/load` - Load existing session
- `session/prompt` - Send prompt to session
- `session/cancel` - Cancel ongoing operation
```

