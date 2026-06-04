#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Events Module.

Provides callbacks for bridging AIAgent events to ACP notifications.
"""

# 🧠 Decision - 💾 Memory - ACP Events

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)


@dataclass
class ACPEvent:
    """Base ACP event structure."""
    event_type: str
    data: Dict[str, Any]


@dataclass
class MessageEvent(ACPEvent):
    """Message content event."""
    content: str
    role: str = "assistant"


@dataclass
class ToolProgressEvent(ACPEvent):
    """Tool execution progress event."""
    tool_name: str
    tool_call_id: str
    status: str  # "started", "progress", "completed", "error"
    preview: Optional[str] = None
    args: Optional[Dict[str, Any]] = None


@dataclass
class ThinkingEvent(ACPEvent):
    """Thinking/reasoning event."""
    content: str


@dataclass
class PlanEvent(ACPEvent):
    """Plan/task list event."""
    entries: List[Dict[str, Any]]


class ACPSessionNotifier:
    """Notifies ACP sessions of agent events.

    This class bridges AIAgent callbacks to ACP session updates.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._handlers: Dict[str, List[Callable]] = {}
        self._pending_updates: List[Dict[str, Any]] = []

    def on_message_delta(self, delta: str) -> None:
        """Handle streaming message delta."""
        self._emit("message.delta", {"delta": delta})

    def on_message_complete(self, content: str) -> None:
        """Handle message completion."""
        self._emit("message.complete", {"content": content})

    def on_tool_start(self, tool_name: str, tool_call_id: str, args: Dict[str, Any]) -> None:
        """Handle tool start event."""
        self._emit("tool.start", {
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "args": args,
        })

    def on_tool_complete(self, tool_call_id: str, result: Any) -> None:
        """Handle tool completion event."""
        self._emit("tool.complete", {
            "tool_call_id": tool_call_id,
            "result": result,
        })

    def on_tool_error(self, tool_call_id: str, error: str) -> None:
        """Handle tool error event."""
        self._emit("tool.error", {
            "tool_call_id": tool_call_id,
            "error": error,
        })

    def on_thinking(self, content: str) -> None:
        """Handle thinking/reasoning event."""
        self._emit("thinking", {"content": content})

    def on_plan_update(self, entries: List[Dict[str, Any]]) -> None:
        """Handle plan/task list update."""
        self._emit("plan", {"entries": entries})

    def on_session_update(self, update: Dict[str, Any]) -> None:
        """Handle generic session update."""
        self._emit("session.update", update)

    def add_handler(self, event_type: str, handler: Callable) -> None:
        """Add an event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def _emit(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all handlers."""
        event = ACPEvent(event_type=event_type, data=data)
        self._pending_updates.append({
            "event": event_type,
            "data": data,
        })

        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.warning(f"Error in event handler: {e}")

    def get_pending_updates(self) -> List[Dict[str, Any]]:
        """Get and clear pending updates."""
        updates = self._pending_updates.copy()
        self._pending_updates.clear()
        return updates


# Tool name to ACP tool kind mapping
TOOL_KIND_MAP: Dict[str, str] = {
    # File operations
    "read_file": "read",
    "write_file": "edit",
    "patch": "edit",
    "search_files": "search",
    # Terminal / execution
    "terminal": "execute",
    "process": "execute",
    "execute_code": "execute",
    # Session/meta tools
    "todo": "other",
    "skill_view": "read",
    "skills_list": "read",
    "skill_manage": "edit",
    # Web / fetch
    "web_search": "fetch",
    "web_extract": "fetch",
    # Browser
    "browser_navigate": "fetch",
    "browser_click": "execute",
    "browser_type": "execute",
    "browser_snapshot": "read",
    "browser_vision": "read",
    # Agent internals
    "delegate_task": "execute",
    "vision_analyze": "read",
    "image_generate": "execute",
    "text_to_speech": "execute",
}


def get_tool_kind(tool_name: str) -> str:
    """Get the ACP tool kind for a tool name."""
    return TOOL_KIND_MAP.get(tool_name, "other")


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
        return f"vision analyze"
    if tool_name == "image_generate":
        prompt = str(args.get("prompt") or "").strip()
        if prompt and len(prompt) > 60:
            prompt = prompt[:57] + "..."
        return f"image generate: {prompt}" if prompt else "image generate"
    if tool_name == "text_to_speech":
        return f"text to speech"
    if tool_name == "browser_navigate":
        url = str(args.get("url") or "").strip()
        if url and len(url) > 60:
            url = url[:57] + "..."
        return f"navigate: {url}" if url else "navigate"
    return tool_name


def build_plan_update_from_todo_result(result: Any) -> Optional[Dict[str, Any]]:
    """Translate todo tool result into ACP plan update.

    Zed renders plan updates as its first-class task/todo panel.
    """
    if not isinstance(result, str) or not result.strip():
        return None

    try:
        # Try to parse as JSON
        data = json.loads(result.strip())
    except Exception:
        return None

    if not isinstance(data, dict) or not isinstance(data.get("todos"), list):
        return None

    todos = data["todos"]
    if not todos:
        return {"entries": []}

    status_map = {
        "pending": "pending",
        "in_progress": "in_progress",
        "completed": "completed",
        "cancelled": "completed",
    }

    entries = []
    for item in todos:
        if not isinstance(item, dict):
            continue
        content = str(item.get("content") or item.get("id") or "").strip()
        if not content:
            continue
        raw_status = str(item.get("status") or "pending").strip()
        status = status_map.get(raw_status, "pending")
        if raw_status == "cancelled":
            content = f"[cancelled] {content}"
        entries.append({
            "content": content,
            "status": status,
        })

    return {"entries": entries}


def create_tool_progress_callback(notifier: ACPSessionNotifier) -> Callable:
    """Create a tool progress callback for AIAgent.

    Returns a callback with the signature expected by AIAgent:
        tool_progress_callback(event_type: str, name: str, preview: str, args: dict, **kwargs)
    """
    import uuid

    def callback(event_type: str, name: str = None, preview: str = None, args: Any = None, **kwargs) -> None:
        if event_type == "tool.started":
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except (json.JSONDecodeError, TypeError):
                    args = {"raw": args}
            if not isinstance(args, dict):
                args = {}

            tool_call_id = f"tc-{uuid.uuid4().hex[:12]}"
            title = build_tool_title(name or "", args)

            notifier.on_tool_start(name or "", tool_call_id, args)
            notifier.on_session_update({
                "tool": {
                    "toolCallId": tool_call_id,
                    "name": name or "",
                    "title": title,
                    "kind": get_tool_kind(name or ""),
                    "status": "started",
                }
            })

        elif event_type == "tool.completed":
            tool_call_id = kwargs.get("tool_call_id")
            if tool_call_id:
                notifier.on_tool_complete(tool_call_id, preview)

    return callback


def create_message_callback(notifier: ACPSessionNotifier) -> Callable:
    """Create a message callback for AIAgent.

    Returns a callback for streaming message events.
    """
    def callback(delta: str = None, final: str = None, **kwargs) -> None:
        if delta:
            notifier.on_message_delta(delta)
        if final:
            notifier.on_message_complete(final)

    return callback


def create_thinking_callback(notifier: ACPSessionNotifier) -> Callable:
    """Create a thinking callback for AIAgent.

    Returns a callback for reasoning/thinking events.
    """
    def callback(content: str = "", **kwargs) -> None:
        if content:
            notifier.on_thinking(content)

    return callback
