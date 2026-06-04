"""
API module - OpenAI-compatible API Server for Handsome Agent.

This module provides an OpenAI-compatible API server that can be used with
any OpenAI-compatible frontend (Open WebUI, LobeChat, LibreChat, etc.).

Key features:
- Chat Completions API (OpenAI compatible)
- Responses API (OpenAI compatible)
- Runs API (async execution with SSE events)
- Session management with continuity headers
- CORS support for web frontends

Usage:
    from api import create_api_server

    server = create_api_server(config)
    await server.start()

Or via CLI:
    python -m api.server --host 0.0.0.0 --port 8001
"""

# 🏃 Execution - 🛠️ ToolExec - API Module

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from api.api_server import APIServerAdapter

__version__ = "1.0.0"

__all__ = [
    "APIServerAdapter",
    "create_api_server",
    "check_api_server_requirements",
    "AIOHTTP_AVAILABLE",
]

# Import these lazily to allow the module to be imported without aiohttp
def __getattr__(name: str):
    """Lazy import for optional dependencies."""
    if name == "APIServerAdapter":
        from api.api_server import APIServerAdapter

        return APIServerAdapter
    if name == "create_api_server":
        from api.api_server import create_api_server

        return create_api_server
    if name == "check_api_server_requirements":
        from api.api_server import check_api_server_requirements

        return check_api_server_requirements
    if name == "AIOHTTP_AVAILABLE":
        from api.api_server import AIOHTTP_AVAILABLE

        return AIOHTTP_AVAILABLE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
