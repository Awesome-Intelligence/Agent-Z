#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LoadingMixin — 加载动画与状态图标

🚪 Access - 💬 TUI - Textual App - Loading

v8.x 从 ``tui/textual_app/app.py`` L1091–1175 抽出：
- ``_start_loading_animation`` / ``_stop_loading_animation``
- ``_update_busy_animation``
- ``_update_status_icon`` / ``set_agent_status``
- ``_STATUS_ICONS`` 类级常量

依赖：
- ``LoadingIndicator``（来自 ``tui.textual_app.imports``）
- 主类的 ``query_one`` / ``set_timer`` / ``notify`` / ``self._widget_cache``
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .imports import LoadingIndicator

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# ============================================================================
# LoadingMixin
# ============================================================================


class LoadingMixin:
    """加载动画与状态图标 Mixin。"""

    # 状态图标映射（与 tui.theming.icons 保持兼容）
    _STATUS_ICONS: dict[str, object] = {
        "online": "🟢",
        "busy": ["⏳", "⌛", "🔄", "✨"],
        "away": "🌙",
        "offline": "⚫",
        "error": "🔴",
        "thinking": "💭",
    }

    # 依赖主类初始化时填充
    _is_loading: bool = False
    _current_status: str = "online"
    _busy_frame_index: int = 0
    _use_native_loading: bool = False
    _loading_indicator: object = None
    _widget_cache: dict = {}
    _breathing_timer: object = None
    _breathing_bright: bool = True

    # ------------------------------------------------------------------
    # 公开 API
    # ------------------------------------------------------------------

    def set_agent_status(self, status: str) -> None:
        """设置 Agent 状态."""
        if status in self._STATUS_ICONS:
            self._current_status = status
        logger.debug(f"Agent status changed to: {status}")

    # ------------------------------------------------------------------
    # 加载动画生命周期
    # ------------------------------------------------------------------

    def _start_loading_animation(self) -> None:
        if self._is_loading:
            return
        self._is_loading = True

        # 更新状态为忙碌
        self._current_status = "busy"
        self._busy_frame_index = 0

        # 开启呼吸效果
        self._breathing_bright = True
        self._breathing_timer = self.set_timer(0.75, self._breathing_pulse)

        if self._use_native_loading and LoadingIndicator is not None:
            # 使用 Textual 原生 LoadingIndicator
            try:
                if self._loading_indicator is None:
                    self._loading_indicator = LoadingIndicator()
                    self.query_one("#status-bar").mount(self._loading_indicator)
            except Exception:
                pass
        else:
            # 使用状态图标动画
            self._update_status_icon()
            self._update_busy_animation()

    def _stop_loading_animation(self) -> None:
        self._is_loading = False

        # 更新状态为在线
        self._current_status = "online"
        self._busy_frame_index = 0

        # 停止呼吸效果
        if self._breathing_timer is not None:
            self._breathing_timer.stop()
            self._breathing_timer = None

        if self._use_native_loading and self._loading_indicator is not None:
            # 移除 Textual 原生 LoadingIndicator
            try:
                self._loading_indicator.remove()
                self._loading_indicator = None
            except Exception:
                pass
        else:
            # 更新状态图标
            self._update_status_icon()

    def _breathing_pulse(self) -> None:
        """呼吸效果：切换状态栏亮度."""
        if not self._is_loading:
            return
        self._breathing_bright = not self._breathing_bright
        status_bar = self.query_one("#status-bar")
        status_bar.styles.opacity = 1.0 if self._breathing_bright else 0.5
        self._breathing_timer = self.set_timer(0.75, self._breathing_pulse)

    def _update_busy_animation(self) -> None:
        """更新 busy 状态的动画图标."""
        if not self._is_loading or self._current_status != "busy":
            return
        self._busy_frame_index = (self._busy_frame_index + 1) % 4
        self._update_status_icon()
        self.set_timer(0.5, self._update_busy_animation)

    def _update_status_icon(self) -> None:
        """更新状态图标."""
        icon_widget = self._widget_cache.get("status_icon")
        if icon_widget:
            status_icon = self._STATUS_ICONS.get(self._current_status, "😐")
            # busy 状态使用动画帧
            if self._current_status == "busy" and isinstance(status_icon, list):
                icon = status_icon[self._busy_frame_index % len(status_icon)]
            else:
                icon = status_icon
            icon_widget.update(icon)


__all__ = ["LoadingMixin"]