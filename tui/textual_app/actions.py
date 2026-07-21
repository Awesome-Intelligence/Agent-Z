#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ActionsMixin — Textual 快捷键 action_* 方法

🚪 Access - 💬 TUI - Textual App - Actions

v8.x 从 ``tui/textual_app/app.py`` 抽出：
- ``action_open_help`` / ``action_open_settings`` / ``action_open_log_screen``
- ``action_copy`` / ``action_quit``

Textual 通过 ``BINDINGS`` 表识别 ``action_*`` 名字，所以这些方法必须保留
在主类的 MRO 中（mixin 继承有效）。
"""

from __future__ import annotations

import logging

from common.logging_manager import get_access_logger
from .imports import HelpScreen, LogScreen, SettingsScreen

logger = get_access_logger("actions")


class ActionsMixin:
    """快捷键 action 方法 Mixin."""

    _logger = get_access_logger("actions")

    # ------------------------------------------------------------------
    # Screen 切换
    # ------------------------------------------------------------------

    def action_open_log_screen(self) -> None:
        """打开全局日志窗口 (Alt+L)."""
        if LogScreen:
            # 检查是否已经打开（直接判断当前屏幕）
            if isinstance(self.screen, LogScreen):
                self.pop_screen()
                return
            self.push_screen(LogScreen())
            self._logger.debug("Log screen opened")
        else:
            self.notify("日志窗口不可用")

    def action_open_help(self) -> None:
        if HelpScreen:
            self.push_screen(HelpScreen())
            self._logger.debug("Help screen opened")
        else:
            self.notify("Help: q=quit, Ctrl+B=sidebar, Ctrl+T=new tab")

    def action_open_settings(self) -> None:
        """打开设置界面."""
        if SettingsScreen:
            self.push_screen(SettingsScreen())
            self._logger.debug("Settings screen opened")
        else:
            self.notify("Settings not available")

    # ------------------------------------------------------------------
    # 编辑器快捷
    # ------------------------------------------------------------------

    def action_copy(self) -> None:
        try:
            focused_widget = self.focused
            if focused_widget is not None:
                if hasattr(focused_widget, "selected_text"):
                    selected_text = focused_widget.selected_text
                    if selected_text:
                        self.app.copy_to_clipboard(selected_text)
                        self.notify("已复制选中内容")
                        return
                elif hasattr(focused_widget, "text"):
                    text = getattr(focused_widget, "text", "")
                    if text:
                        self.app.copy_to_clipboard(text)
                        self.notify("已复制内容")
                        return
            self.notify("无可复制内容")
        except Exception as e:
            self._logger.debug(f"Copy action failed: {e}")

    def action_quit(self) -> None:
        self._logger.info("User requested quit")
        self.app.exit()


__all__ = ["ActionsMixin"]