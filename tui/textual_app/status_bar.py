#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StatusBarMixin — 底部状态栏更新

🚪 Access - 💬 TUI - Textual App - Status Bar

v8.x 从 ``tui/textual_app/app.py`` L664–781 抽出：
- ``_update_status_bar``         主状态栏刷新
- ``_update_used_tools``         工具使用统计
- ``_update_queue_display``      队列状态显示
- ``_toggle_budget_mode``        Goal/迭代模式切换
- ``_on_click_mode_toggle``      切换按钮点击

依赖主类的 ``self._widget_cache`` / ``self._used_tools`` /
``self._pending_queue`` / ``self._agent`` / ``self._current_token_count`` /
``self._current_status`` / ``self._STATUS_ICONS``。
"""

from __future__ import annotations

import logging

from tui.core.formatters import format_token_count

from .imports import Click, on, t  # type: ignore[attr-defined]

logger = logging.getLogger(__name__)


class StatusBarMixin:
    """状态栏更新 Mixin."""

    _logger = logging.getLogger(__name__)
    _widget_cache: dict = {}
    _used_tools: set = set()
    _pending_queue: list = []
    _current_token_count: int = 0
    _current_status: str = "online"
    _STATUS_ICONS: dict = {"online": "🟢", "busy": ["⏳"], "offline": "⚫"}
    context_length: int = 0

    # ------------------------------------------------------------------
    # 主状态栏
    # ------------------------------------------------------------------

    def _update_status_bar(self) -> None:
        try:
            # 使用缓存的 widgets（避免频繁 query_one）
            icon_widget = self._widget_cache.get("status_icon")
            if icon_widget:
                icon_widget.update(self._STATUS_ICONS.get(self._current_status, "😐"))

            tokens_widget = self._widget_cache.get("status_tokens")
            if tokens_widget:
                if self.context_length:
                    tokens_widget.update(
                        f"│ {format_token_count(self._current_token_count)}"
                        f"/{format_token_count(self.context_length)} "
                    )
                else:
                    tokens_widget.update("│ n/a ")

            time_widget = self._widget_cache.get("status_time")
            if time_widget:
                time_widget.update("│ 0m 0s ")

            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update status bar: {e}")

    def _update_used_tools(self) -> None:
        """更新已使用工具的显示."""
        try:
            tools_widget = self._widget_cache.get("status_tools")
            if tools_widget:
                count = len(self._used_tools)
                if count > 0:
                    # 显示工具名称（限制总长度）
                    tools_str = ",".join(sorted(self._used_tools))
                    if len(tools_str) > 15:
                        # 如果太长，缩写
                        sorted_tools = sorted(self._used_tools)
                        tools_str = ",".join(sorted_tools[:3])
                        if count > 3:
                            tools_str += f",+{count-3}"
                    tools_widget.update(f"🔧{tools_str}")
                else:
                    tools_widget.update("🔧")
        except Exception as e:
            self._logger.debug(f"Failed to update tools display: {e}")

    def _update_queue_display(self, queue_len_override=None) -> None:
        """更新队列状态显示（状态栏 + 输入框内容）.

        Args:
            queue_len_override: 可选，强制使用指定队列长度（用于 pop 后准确反映剩余数量）
        """
        queue_len = (
            queue_len_override
            if queue_len_override is not None
            else len(self._pending_queue)
        )
        try:
            queue_widget = self._widget_cache.get("status_queue")
            text_area = self._widget_cache.get("user_input")
            if queue_len > 0:
                # 状态栏显示排队数量
                if queue_widget:
                    queue_widget.update(f"⏳ {queue_len}")
                    queue_widget.set_class(True, "has-queue")
                # 输入框直接显示队首排队消息，禁用编辑
                if text_area:
                    text_area.text = self._pending_queue[0]
                    text_area.disabled = True
            else:
                # 队列空：恢复空闲状态
                if queue_widget:
                    queue_widget.update("")
                    queue_widget.set_class(False, "has-queue")
                if text_area:
                    text_area.text = ""
                    text_area.disabled = False
                    text_area.placeholder = t(
                        "tui.input.placeholder", "输入消息...Enter 发送"
                    )
        except Exception as e:
            self._logger.debug(f"Failed to update queue display: {e}")

    # ------------------------------------------------------------------
    # 模式切换
    # ------------------------------------------------------------------

    def _toggle_budget_mode(self) -> None:
        """切换 Goal 模式和迭代模式."""
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "state")
            ):
                state = self._agent.state
                from agent.state import BudgetMode

                if state.budget_mode == BudgetMode.TURN:
                    state._enable_iteration_mode()
                    mode_icon = t("tui.status.bar.mode_iter")
                    mode_text = t("tui.status.bar.mode_iter").replace("⚡ ", "")
                else:
                    state._enable_goal_mode()
                    mode_icon = t("tui.status.bar.mode_goal", "🎯 Goal")
                    mode_text = "Goal"

                # 更新按钮显示
                toggle_widget = self._widget_cache.get("status_mode_toggle")
                if toggle_widget:
                    toggle_widget.update(mode_icon)

                self._logger.info(f"Budget mode switched to: {mode_text}")
        except Exception as e:
            self._logger.debug(f"Failed to toggle budget mode: {e}")

    @on(Click, "#status-mode-toggle")
    def _on_click_mode_toggle(self, event) -> None:
        """处理模式切换按钮点击事件."""
        self._logger.info("Mode toggle clicked!")
        self._toggle_budget_mode()


__all__ = ["StatusBarMixin"]