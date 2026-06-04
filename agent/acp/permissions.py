#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Permissions Module.

Provides permission/approval system for ACP protocol.
"""

# 🧠 Decision - 💾 Memory - ACP Permissions

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)


class PermissionLevel(Enum):
    """Permission levels for ACP sessions."""
    FULL = "full"           # Allow all operations
    READONLY = "readonly"   # Read-only mode
    TOOL_RESTRICTED = "tool_restricted"  # Only specific tools
    NONE = "none"           # No operations allowed


@dataclass
class PermissionOption:
    """A permission option for approval requests."""
    option_id: str
    kind: str
    name: str
    description: Optional[str] = None


@dataclass
class PermissionRequest:
    """A permission request for dangerous operations."""
    request_id: str
    tool_name: str
    command: str
    description: str
    options: List[PermissionOption]
    callback: Callable


# Default permission options
DEFAULT_OPTIONS = [
    PermissionOption(
        option_id="allow_once",
        kind="allow_once",
        name="Allow once",
        description="Allow this operation once"
    ),
    PermissionOption(
        option_id="allow_session",
        kind="allow_always",
        name="Allow for session",
        description="Allow this operation for the current session"
    ),
    PermissionOption(
        option_id="deny",
        kind="reject_once",
        name="Deny",
        description="Deny this operation"
    ),
]


PERMANENT_OPTIONS = [
    PermissionOption(
        option_id="allow_once",
        kind="allow_once",
        name="Allow once",
        description="Allow this operation once"
    ),
    PermissionOption(
        option_id="allow_always",
        kind="allow_always",
        name="Allow always",
        description="Always allow this operation"
    ),
    PermissionOption(
        option_id="deny",
        kind="reject_once",
        name="Deny",
        description="Deny this operation"
    ),
    PermissionOption(
        option_id="deny_always",
        kind="reject_always",
        name="Deny always",
        description="Always deny this operation"
    ),
]


class PermissionManager:
    """Manages permissions for ACP sessions."""

    def __init__(self):
        self._session_permissions: Dict[str, PermissionLevel] = {}
        self._session_tool_allowlist: Dict[str, List[str]] = {}
        self._session_approvals: Dict[str, List[str]] = {}  # Approved tools per session
        self._pending_requests: Dict[str, PermissionRequest] = {}
        self._always_allow_tools: set = {
            "read_file", "search_files", "terminal", "process",
            "todo", "memory", "session_search",
        }

    def get_session_permission(self, session_id: str) -> PermissionLevel:
        """Get the permission level for a session."""
        return self._session_permissions.get(session_id, PermissionLevel.FULL)

    def set_session_permission(self, session_id: str, level: PermissionLevel) -> None:
        """Set the permission level for a session."""
        self._session_permissions[session_id] = level

    def is_tool_allowed(self, session_id: str, tool_name: str) -> bool:
        """Check if a tool is allowed for a session."""
        permission = self.get_session_permission(session_id)

        if permission == PermissionLevel.FULL:
            return True
        if permission == PermissionLevel.NONE:
            return False
        if permission == PermissionLevel.READONLY:
            # Only allow read operations
            return tool_name in {"read_file", "search_files", "skills_list", "session_search"}
        if permission == PermissionLevel.TOOL_RESTRICTED:
            allowlist = self._session_tool_allowlist.get(session_id, [])
            return tool_name in allowlist

        return False

    def set_tool_allowlist(self, session_id: str, tools: List[str]) -> None:
        """Set the tool allowlist for a session."""
        self._session_tool_allowlist[session_id] = tools
        self._session_permissions[session_id] = PermissionLevel.TOOL_RESTRICTED

    def is_dangerous_tool(self, tool_name: str) -> bool:
        """Check if a tool is considered dangerous and needs approval."""
        dangerous_tools = {
            "terminal", "process", "execute_code",
            "write_file", "patch",
            "delegate_task",
            "skill_manage",
        }
        return tool_name in dangerous_tools

    def request_permission(
        self,
        session_id: str,
        tool_name: str,
        command: str,
        description: str = "",
        callback: Optional[Callable] = None,
    ) -> PermissionRequest:
        """Request permission for a dangerous operation."""
        import uuid

        request_id = f"perm-{uuid.uuid4().hex[:12]}"

        # Build options based on session approvals
        always_approved = self._session_approvals.get(session_id, [])
        allow_permanent = tool_name not in always_approved

        options = PERMANENT_OPTIONS if allow_permanent else DEFAULT_OPTIONS

        request = PermissionRequest(
            request_id=request_id,
            tool_name=tool_name,
            command=command,
            description=description,
            options=options,
            callback=callback,
        )

        self._pending_requests[request_id] = request
        return request

    def resolve_permission(
        self,
        request_id: str,
        option_id: str,
    ) -> str:
        """Resolve a permission request.

        Returns the approval result string:
            - "once": Allow once
            - "session": Allow for session
            - "always": Always allow
            - "deny": Deny
            - "deny_always": Always deny
        """
        request = self._pending_requests.pop(request_id, None)
        if not request:
            return "deny"

        # Map option ID to approval result
        option_to_result = {
            "allow_once": "once",
            "allow_session": "session",
            "allow_always": "always",
            "deny": "deny",
            "deny_always": "deny",
        }

        result = option_to_result.get(option_id, "deny")

        # Update session approvals
        if result in ("session", "always"):
            if request.session_id not in self._session_approvals:
                self._session_approvals[request.session_id] = []
            if request.tool_name not in self._session_approvals[request.session_id]:
                self._session_approvals[request.session_id].append(request.tool_name)

        # Call callback if provided
        if request.callback:
            try:
                request.callback(result)
            except Exception as e:
                logger.warning(f"Error in permission callback: {e}")

        return result

    def clear_session_permissions(self, session_id: str) -> None:
        """Clear all permissions for a session."""
        self._session_permissions.pop(session_id, None)
        self._session_tool_allowlist.pop(session_id, None)
        self._session_approvals.pop(session_id, None)

    def get_permission_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current permission status for a session."""
        permission = self.get_session_permission(session_id)
        approvals = self._session_approvals.get(session_id, [])
        allowlist = self._session_tool_allowlist.get(session_id, [])

        return {
            "session_id": session_id,
            "permission_level": permission.value,
            "always_approved_tools": approvals,
            "tool_allowlist": allowlist,
        }


# Global permission manager instance
_permission_manager: Optional[PermissionManager] = None


def get_permission_manager() -> PermissionManager:
    """Get the global permission manager instance."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


def is_tool_allowed(session_id: str, tool_name: str) -> bool:
    """Quick check if a tool is allowed for a session."""
    return get_permission_manager().is_tool_allowed(session_id, tool_name)


def request_permission(
    session_id: str,
    tool_name: str,
    command: str,
    description: str = "",
    callback: Optional[Callable] = None,
) -> PermissionRequest:
    """Quick request for permission."""
    return get_permission_manager().request_permission(
        session_id, tool_name, command, description, callback
    )


def resolve_permission(request_id: str, option_id: str) -> str:
    """Quick resolve a permission request."""
    return get_permission_manager().resolve_permission(request_id, option_id)
