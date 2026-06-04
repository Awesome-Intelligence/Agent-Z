"""
ACP (Agent Communication Protocol) Module.

This module provides Agent-to-Agent communication capabilities using the ACP protocol.

Features:
- Session Management - Create, resume, and manage agent sessions
- Multiple Transports - stdio (for terminal integration) and HTTP (for remote access)
- Tool Integration - Expose agent tools via ACP
- Permission System - Permission requests for dangerous operations
- Event System - Bridge AIAgent events to ACP notifications
- Authentication - Auth methods detection and validation

Usage:

    # CLI
    python -m agent.acp.entry --transport stdio
    python -m agent.acp.entry --transport http --port 8002

    # In code
    from agent.acp import ACPServer

    server = ACPServer(agent)
    response = await server.handle_request({
        "jsonrpc": "2.0",
        "id": "1",
        "method": "session/new",
        "params": {"cwd": "/project"}
    })
"""

# 🧠 Decision - 💾 Memory - ACP Module

from agent.acp.adapter import ACPServer, ACPError
from agent.acp.session import SessionManager, SessionState, SessionStatus
from agent.acp.transport import StdioTransport, HttpTransport, WebSocketTransport
from agent.acp.auth import (
    detect_provider,
    has_provider,
    build_auth_methods,
    validate_api_key,
    get_auth_config,
    TERMINAL_SETUP_AUTH_METHOD_ID,
)
from agent.acp.permissions import (
    PermissionManager,
    PermissionLevel,
    PermissionRequest,
    get_permission_manager,
    is_tool_allowed,
    request_permission,
    resolve_permission,
)
from agent.acp.events import (
    ACPSessionNotifier,
    ACPEvent,
    MessageEvent,
    ToolProgressEvent,
    ThinkingEvent,
    PlanEvent,
    get_tool_kind,
    build_tool_title,
    create_tool_progress_callback,
    create_message_callback,
    create_thinking_callback,
)
from agent.acp.tools import (
    ToolKind,
    TOOL_KIND_MAP,
    get_tool_kind,
    make_tool_call_id,
    build_tool_title,
    build_tool_start,
    build_tool_complete,
    build_tool_error,
    build_tool_progress,
    ACPToolRegistry,
    get_tool_registry,
)

__version__ = "1.0.0"

__all__ = [
    # Core
    "ACPServer",
    "ACPError",
    # Session
    "SessionManager",
    "SessionState",
    "SessionStatus",
    # Transport
    "StdioTransport",
    "HttpTransport",
    "WebSocketTransport",
    # Auth
    "detect_provider",
    "has_provider",
    "build_auth_methods",
    "validate_api_key",
    "get_auth_config",
    "TERMINAL_SETUP_AUTH_METHOD_ID",
    # Permissions
    "PermissionManager",
    "PermissionLevel",
    "PermissionRequest",
    "get_permission_manager",
    "is_tool_allowed",
    "request_permission",
    "resolve_permission",
    # Events
    "ACPSessionNotifier",
    "ACPEvent",
    "MessageEvent",
    "ToolProgressEvent",
    "ThinkingEvent",
    "PlanEvent",
    "get_tool_kind",
    "build_tool_title",
    "create_tool_progress_callback",
    "create_message_callback",
    "create_thinking_callback",
    # Tools
    "ToolKind",
    "TOOL_KIND_MAP",
    "make_tool_call_id",
    "build_tool_start",
    "build_tool_complete",
    "build_tool_error",
    "build_tool_progress",
    "ACPToolRegistry",
    "get_tool_registry",
]
