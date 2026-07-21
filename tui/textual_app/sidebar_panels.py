#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SidebarPanelMixin — 侧边栏面板切换

🚪 Access - 💬 TUI - Textual App - Sidebar Panels

v8.x 从 ``tui/textual_app/app.py`` L2000–2081 抽出：
- ``_on_sidebar_panel_switch``  面板切换事件
- ``action_toggle_sidebar``      显示/隐藏侧边栏
- ``_get_sidebar_and_switch``    强制显示 + 切到指定面板
- ``action_next_panel`` / ``action_prev_panel``  上下面板循环

依赖主类的 ``self.notify`` / ``self._logger`` /
``tui.sidebar.SidebarContainer`` 部件。
"""

from __future__ import annotations

from tui.sidebar import SidebarContainer

from .imports import Container
from common.logging_manager import get_access_logger


# 面板循环顺序
PANEL_ORDER = ("goal", "file_tree", "skills", "cron")


class SidebarPanelMixin:
    """侧边栏面板切换 Mixin."""

    _logger = get_access_logger("sidebar_panels")

    # ------------------------------------------------------------------
    # 面板切换
    # ------------------------------------------------------------------

    def _on_sidebar_panel_switch(self, panel_type: str) -> None:
        try:
            sidebar = self.query_one("#sidebar-container-inner")
            if sidebar:
                sidebar.switch_to_panel(panel_type)
        except Exception as e:
            self._logger.debug(f"Failed to switch sidebar panel: {e}")

    def action_toggle_sidebar(self) -> None:
        try:
            sidebar = self.query_one("#sidebar-container")
            if not sidebar:
                return
            hiding = sidebar.styles.display != "none"
            sidebar.styles.display = "none" if hiding else "block"
            self.notify("侧边栏已隐藏" if hiding else "侧边栏已显示")
            self._logger.debug(f"Sidebar toggled, display: {sidebar.styles.display}")

            # ponytail: stop GoalPane's 1s timer when sidebar is hidden so it
            # doesn't wake the event loop every second while the user is in chat.
            try:
                inner = self.query_one("#sidebar-container-inner", SidebarContainer)
                pane = inner.goal_pane
                if hiding:
                    pane._ensure_timer_stopped()
                else:
                    pane._refresh_all()
                    pane._ensure_timer_running()
            except Exception:
                pass
        except Exception as e:
            self._logger.debug(f"Sidebar toggle failed: {e}")

    def _get_sidebar_and_switch(self, panel_type: str) -> None:
        """显示侧边栏并切换到指定面板."""
        self._logger.info(f"[_get_sidebar_and_switch] panel_type={panel_type}")
        try:
            # 先显示外层容器（如果隐藏的话）
            outer = self.query_one("#sidebar-container", Container)
            self._logger.debug(
                f"[_get_sidebar_and_switch] outer display={outer.styles.display}"
            )
            if outer.styles.display == "none":
                outer.styles.display = "block"
            # 再切换内部 SidebarContainer 的面板
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            self._logger.debug(
                f"[_get_sidebar_and_switch] inner={type(inner).__name__}"
            )
            inner.switch_to_panel(panel_type)
        except Exception as e:
            self._logger.error(f"[_get_sidebar_and_switch] Failed: {e}", exc_info=True)

    def action_next_panel(self) -> None:
        """切换到下一个面板."""
        try:
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            # 获取 TabbedContent 的当前活动面板
            tabbed = inner.query_one("TabbedContent")
            current_tab = tabbed.active
            if current_tab in PANEL_ORDER:
                idx = PANEL_ORDER.index(current_tab)
                next_panel = PANEL_ORDER[(idx + 1) % len(PANEL_ORDER)]
                self._get_sidebar_and_switch(next_panel)
        except Exception as e:
            self._logger.debug(f"action_next_panel: {e}")

    def action_prev_panel(self) -> None:
        """切换到上一个面板."""
        try:
            inner = self.query_one("#sidebar-container-inner", SidebarContainer)
            # 获取 TabbedContent 的当前活动面板
            tabbed = inner.query_one("TabbedContent")
            current_tab = tabbed.active
            if current_tab in PANEL_ORDER:
                idx = PANEL_ORDER.index(current_tab)
                prev_panel = PANEL_ORDER[(idx - 1) % len(PANEL_ORDER)]
                self._get_sidebar_and_switch(prev_panel)
        except Exception as e:
            self._logger.debug(f"action_prev_panel: {e}")


__all__ = ["SidebarPanelMixin", "PANEL_ORDER"]