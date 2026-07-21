#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ApprovalMixin — Tool 调用审批流程

🚪 Access - 💬 TUI - Textual App - Approval

v8.x 从 ``tui/textual_app/app.py`` L1819–1924 抽出：
- ``request_tool_approval``     请求用户批准
- ``_show_approval_dialog``     弹窗展示
- ``_generate_tool_preview``    工具参数预览（敏感字段脱敏）
- ``_handle_approval_result``   接收用户选择
- ``on_approval_confirmed`` / ``on_approval_rejected``  事件处理
- ``set_approval_mode`` / ``get_approval_mode``  审批模式控制
- ``is_sensitive_operation``    敏感操作判定

依赖主类的 ``self._approval_manager`` / ``self._logger`` /
``self._pending_tool_call`` / ``self._approval_callback``。
"""

from __future__ import annotations

import logging

from common.logging_manager import get_access_logger
from .imports import (
    ApprovalConfirmed,
    ApprovalDialog,
    ApprovalManager,
    ApprovalMode,
    ApprovalRejected,
    RiskLevel,
    create_approval_dialog,
)

logger = get_access_logger("approval")


class ApprovalMixin:
    """Tool 审批流程 Mixin."""

    _logger = get_access_logger("approval")
    _approval_manager = None
    _pending_tool_call: dict | None = None
    _approval_callback = None

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def request_tool_approval(
        self,
        tool_name: str,
        tool_args: dict,
        callback,
    ) -> bool:
        if not self._approval_manager:
            callback(True)
            return False

        if not self._approval_manager.should_approve(tool_name):
            self._logger.debug(f"Tool '{tool_name}' does not require approval")
            callback(True)
            return False

        self._pending_tool_call = {
            "name": tool_name,
            "args": tool_args,
        }
        self._approval_callback = callback
        self._show_approval_dialog(tool_name, tool_args)
        return True

    def set_approval_mode(self, mode) -> None:
        if self._approval_manager:
            self._approval_manager.set_mode(mode)
            self._logger.info(f"Approval mode changed to: {mode}")

    def get_approval_mode(self):
        if self._approval_manager:
            return self._approval_manager.mode
        return ApprovalMode.AUTO

    def is_sensitive_operation(self, operation: str) -> bool:
        if self._approval_manager:
            return self._approval_manager.is_sensitive_operation(operation)
        return False

    # ------------------------------------------------------------------
    # Dialog 展示
    # ------------------------------------------------------------------

    def _show_approval_dialog(self, tool_name: str, tool_args: dict) -> None:
        if not ApprovalDialog:
            self._logger.warning("ApprovalDialog not available, rejecting operation")
            self._handle_approval_result(False)
            return

        risk_level = (
            self._approval_manager.get_risk_level(tool_name)
            if self._approval_manager
            else RiskLevel.MEDIUM
        )
        preview = self._generate_tool_preview(tool_name, tool_args)

        dialog = create_approval_dialog(
            operation=tool_name,
            preview=preview,
            risk_level=risk_level,
        )

        self._logger.info(
            f"Showing approval dialog for: {tool_name} (risk: {risk_level.value})"
        )
        self.screen.mount(dialog)

    def _generate_tool_preview(self, tool_name: str, tool_args: dict) -> str:
        preview_parts = []

        for key, value in tool_args.items():
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."

            if key.lower() in ("password", "token", "secret", "key", "api_key"):
                value_str = "***"

            preview_parts.append(f"{key}={value_str}")

        preview = "; ".join(preview_parts)

        if len(preview) > 100:
            preview = preview[:97] + "..."

        return preview

    # ------------------------------------------------------------------
    # 用户响应处理
    # ------------------------------------------------------------------

    def _handle_approval_result(self, approved: bool) -> None:
        if self._approval_callback:
            operation = (
                self._pending_tool_call["name"]
                if self._pending_tool_call
                else "unknown"
            )
            self._logger.info(
                f"Approval result for '{operation}': {'approved' if approved else 'rejected'}"
            )

            try:
                self._approval_callback(approved)
            except Exception as e:
                self._logger.error(f"Error in approval callback: {e}")

        self._pending_tool_call = None
        self._approval_callback = None

    def on_approval_confirmed(self, event) -> None:
        self._handle_approval_result(True)

    def on_approval_rejected(self, event) -> None:
        self._handle_approval_result(False)


__all__ = ["ApprovalMixin"]