#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Tools Module.

Provides tool definitions and management for ACP protocol.
"""

# 🧠 Decision - 💾 Memory - ACP Tools

import json
import logging
import uuid
from typing import Any, Callable, Dict, List, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)


class ToolKind:
    """Tool kind constants for ACP."""
    READ = "read"
    WRITE = "write"
    EDIT = "edit"
    EXECUTE = "execute"
    SEARCH = "search"
    FETCH = "fetch"
    THINK = "think"
    OTHER = "other"


# Tool name to kind mapping
TOOL_KIND_MAP: Dict[str, str] = {
    # File operations
    "read_file": ToolKind.READ,
    "write_file": ToolKind.EDIT,
    "patch": ToolKind.EDIT,
    "search_files": ToolKind.SEARCH,
    "terminal": ToolKind.EXECUTE,
    "process": ToolKind.EXECUTE,
    "execute_code": ToolKind.EXECUTE,
    # Session/meta tools
    "todo": ToolKind.OTHER,
    "memory": ToolKind.OTHER,
    "session_search": ToolKind.READ,
    "skill_view": ToolKind.READ,
    "skills_list": ToolKind.READ,
    "skill_manage": ToolKind.WRITE,
    # Web / fetch
    "web_search": ToolKind.FETCH,
    "web_extract": ToolKind.FETCH,
    "browser_navigate": ToolKind.FETCH,
    "browser_click": ToolKind.EXECUTE,
    "browser_type": ToolKind.EXECUTE,
    "browser_snapshot": ToolKind.READ,
    "browser_vision": ToolKind.READ,
    # Agent internals
    "delegate_task": ToolKind.EXECUTE,
    "vision_analyze": ToolKind.READ,
    "image_generate": ToolKind.EXECUTE,
    "text_to_speech": ToolKind.EXECUTE,
    "clarify": ToolKind.OTHER,
    "cronjob": ToolKind.OTHER,
}


def get_tool_kind(tool_name: str) -> str:
    """Get the ACP tool kind for a tool name."""
    return TOOL_KIND_MAP.get(tool_name, ToolKind.OTHER)


def make_tool_call_id() -> str:
    """Generate a unique tool call ID."""
    return f"tc-{uuid.uuid4().hex[:12]}"


def build_tool_title(tool_name: str, args: Dict[str, Any]) -> str:
    """Build a human-readable title for a tool call."""
    if tool_name == "terminal":
        cmd = args.get("command", "")
        if len(cmd) > 80:
            cmd = cmd[:77] + "..."
        return f"terminal: {cmd}"
    if tool_name == "read_file":
        return f"read: {args.get('path', '?')}"
    if tool_name == "write_file":
        return f"write: {args.get('path', '?')}"
    if tool_name == "patch":
        mode = args.get("mode", "replace")
        path = args.get("path", "?")
        return f"patch ({mode}): {path}"
    if tool_name == "search_files":
        return f"search: {args.get('pattern', '?')}"
    if tool_name == "web_search":
        return f"web search: {args.get('query', '?')}"
    if tool_name == "web_extract":
        urls = args.get("urls", [])
        if urls:
            return f"extract: {urls[0]}" + (f" (+{len(urls)-1})" if len(urls) > 1 else "")
        return "web extract"
    if tool_name == "process":
        action = str(args.get("action") or "").strip() or "manage"
        sid = str(args.get("session_id") or "").strip()
        return f"process {action}: {sid}" if sid else f"process {action}"
    if tool_name == "delegate_task":
        tasks = args.get("tasks")
        if isinstance(tasks, list) and tasks:
            return f"delegate batch ({len(tasks)} tasks)"
        goal = args.get("goal", "")
        if goal and len(goal) > 60:
            goal = goal[:57] + "..."
        return f"delegate: {goal}" if goal else "delegate task"
    if tool_name == "session_search":
        query = str(args.get("query") or "").strip()
        return f"session search: {query}" if query else "recent sessions"
    if tool_name == "memory":
        action = str(args.get("action") or "manage").strip() or "manage"
        target = str(args.get("target") or "memory").strip() or "memory"
        return f"memory {action}: {target}"
    if tool_name == "execute_code":
        code = str(args.get("code") or "").strip()
        first_line = next((line.strip() for line in code.splitlines() if line.strip()), "")
        if first_line:
            if len(first_line) > 70:
                first_line = first_line[:67] + "..."
            return f"python: {first_line}"
        return "python code"
    if tool_name == "todo":
        items = args.get("todos")
        if isinstance(items, list):
            return f"todo ({len(items)} item{'s' if len(items) != 1 else ''})"
        return "todo"
    if tool_name == "skill_view":
        name = str(args.get("name") or "?").strip() or "?"
        file_path = str(args.get("file_path") or "").strip()
        suffix = f"/{file_path}" if file_path else ""
        return f"skill: {name}{suffix}"
    if tool_name == "skills_list":
        return "skills list"
    if tool_name == "skill_manage":
        action = args.get("action", "list")
        return f"skill manage: {action}"
    if tool_name == "vision_analyze":
        return "vision analyze"
    if tool_name == "image_generate":
        prompt = str(args.get("prompt") or "").strip()
        if prompt and len(prompt) > 60:
            prompt = prompt[:57] + "..."
        return f"image generate: {prompt}" if prompt else "image generate"
    if tool_name == "text_to_speech":
        return "text to speech"
    if tool_name == "browser_navigate":
        url = str(args.get("url") or "").strip()
        if url and len(url) > 60:
            url = url[:57] + "..."
        return f"navigate: {url}" if url else "navigate"
    return tool_name


def build_tool_start(tool_call_id: str, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Build a tool start event."""
    title = build_tool_title(tool_name, args)
    kind = get_tool_kind(tool_name)

    return {
        "toolCallId": tool_call_id,
        "name": tool_name,
        "title": title,
        "kind": kind,
        "status": "started",
        "args": args,
    }


def build_tool_complete(tool_call_id: str, result: Any) -> Dict[str, Any]:
    """Build a tool complete event."""
    if isinstance(result, dict):
        content = json.dumps(result)
    elif isinstance(result, str):
        content = result
    else:
        content = str(result)

    return {
        "toolCallId": tool_call_id,
        "status": "completed",
        "result": content,
    }


def build_tool_error(tool_call_id: str, error: str) -> Dict[str, Any]:
    """Build a tool error event."""
    return {
        "toolCallId": tool_call_id,
        "status": "error",
        "error": error,
    }


def build_tool_progress(tool_call_id: str, progress: str) -> Dict[str, Any]:
    """Build a tool progress event."""
    return {
        "toolCallId": tool_call_id,
        "status": "progress",
        "progress": progress,
    }


class ACPToolRegistry:
    """Registry of tools exposed via ACP."""

    def __init__(self):
        self._tools: Dict[str, Dict[str, Any]] = {}

    def register(self, name: str, description: str, input_schema: Dict[str, Any]) -> None:
        """Register a tool with ACP."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        }

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a tool definition."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return list(self._tools.values())

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            return True
        return False


# Global tool registry
_tool_registry: Optional[ACPToolRegistry] = None


def get_tool_registry() -> ACPToolRegistry:
    """Get the global tool registry."""
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ACPToolRegistry()
        _register_default_tools()
    return _tool_registry


def _register_default_tools() -> None:
    """Register default ACP tools."""
    registry = _tool_registry

    # File system tools
    registry.register(
        "fs/read_text_file",
        "Read text file content",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
            },
            "required": ["path"],
        },
    )

    registry.register(
        "fs/write_text_file",
        "Write content to text file",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to write"},
                "content": {"type": "string", "description": "Content to write"},
            },
            "required": ["path", "content"],
        },
    )

    registry.register(
        "fs/list_directory",
        "List directory contents",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path"},
            },
        },
    )

    # Session tools
    registry.register(
        "session/get_history",
        "Get conversation history for a session",
        {
            "type": "object",
            "properties": {
                "sessionId": {"type": "string", "description": "Session ID"},
            },
            "required": ["sessionId"],
        },
    )

    registry.register(
        "session/list",
        "List all sessions",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Maximum number of sessions"},
            },
        },
    )

    registry.register(
        "session/delete",
        "Delete a session",
        {
            "type": "object",
            "properties": {
                "sessionId": {"type": "string", "description": "Session ID to delete"},
            },
            "required": ["sessionId"],
        },
    )
