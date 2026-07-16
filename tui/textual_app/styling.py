#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""StylingMixin — 主题/样式/透明度控制

🚪 Access - 💬 TUI - Textual App - Styling

v8.x 阶段 E：从 ``tui/textual_app/app.py`` L234–253、L558–662 抽出：
- ``build_textual_themes()`` 纯函数：构造 Textual ``Theme`` 列表
- ``StylingMixin``：
  - ``_load_stylesheets``  加载基础 CSS
  - ``_apply_theme_class``  切换主题 class
  - ``_load_theme_css``     异步加载主题 CSS
  - ``_load_theme_css_sync``  同步切换主题（CSS 预加载）
  - ``_on_theme_changed``   主题变更回调
  - ``update_theme_css``    手动刷新
  - ``set_theme`` / ``get_current_theme_id`` / ``list_available_themes``
  - ``_update_transparency_styles`` / ``is_transparency_enabled``

依赖主类的 ``self._theme_manager`` / ``self._logger`` /
``self._theme_css_loaded`` / ``self._theme_css_paths``。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

from .imports import Theme, get_stylesheets, Click, Static, on, t

logger = logging.getLogger(__name__)


# ============================================================================
# 纯函数：构造 Textual Theme 列表
# ============================================================================


def build_textual_themes() -> list:
    """从 ``common.theming.preset_themes`` 构造 Textual ``Theme`` 列表.

    Returns:
        Textual Theme 列表；TEXTUAL 不可用时返回空列表
    """
    try:
        from common.theming.preset_themes import _PRESET_THEMES
    except ImportError:
        return []

    return [
        Theme(
            name=t.theme_id,
            primary=t.primary,
            secondary=t.secondary,
            accent=t.accent,
            foreground=t.foreground,
            background=t.background,
            surface=t.surface,
            panel=t.panel,
            success=t.success,
            warning=t.warning,
            error=t.error,
            dark=True,
        )
        for t in _PRESET_THEMES.values()
    ]


# ============================================================================
# StylingMixin
# ============================================================================


class StylingMixin:
    """主题/样式/透明度 Mixin.

    依赖主类（``AgentApp``）初始化时设置以下属性：
    - ``self._theme_manager``           ThemeManager 单例
    - ``self._logger``                  logger
    - ``self._theme_css_loaded``        bool
    - ``self._theme_css_paths``         list
    - ``self.theme_id``                 str
    """

    _logger = logging.getLogger(__name__)
    _theme_manager = None
    _theme_css_loaded: bool = False
    _theme_css_paths: list = []
    theme_id: str = "default"
    _widget_cache: dict = {}

    # ------------------------------------------------------------------
    # 基础样式加载
    # ------------------------------------------------------------------

    async def _load_stylesheets(self) -> None:
        if get_stylesheets is None:
            self._logger.debug("CSS module not available, using inline CSS")
            return

        try:
            # 加载基础 CSS
            stylesheets = get_stylesheets()
            for css_file in stylesheets:
                css_path = Path(css_file)
                if css_path.exists():
                    await self.add_stylesheet(str(css_path))
                    self._logger.debug(f"Loaded stylesheet: {css_path.name}")
                else:
                    self._logger.debug(f"Stylesheet not found: {css_path}")

            self._theme_css_loaded = True

            # 预加载所有主题的 CSS（避免切换时闪烁）
            if self._theme_manager:
                for tid in self._theme_manager.list_theme_ids():
                    css_path = self._theme_manager.get_theme_css_path(tid)
                    if css_path and css_path.exists():
                        await self.add_stylesheet(str(css_path))
                        self._logger.debug(f"Preloaded theme CSS: {css_path.name}")

            # 应用初始主题 class
            self._apply_theme_class()
        except Exception as e:
            self._logger.debug(f"Failed to load stylesheets: {e}")

    # ------------------------------------------------------------------
    # 主题切换
    # ------------------------------------------------------------------

    def _apply_theme_class(self) -> None:
        self._logger.debug(
            f"[_apply_theme_class] Called, _theme_css_loaded={self._theme_css_loaded}, theme_id={self.theme_id}"
        )

        if not self._theme_css_loaded:
            self.set_timer(0.5, self._apply_theme_class)
            return

        try:
            # 获取 Screen 组件
            screen = self.screen
            if not screen:
                self._logger.warning("[_apply_theme_class] No screen found")
                return

            # 获取所有主题 ID 并移除旧主题 class
            if self._theme_manager:
                theme_ids = self._theme_manager.list_theme_ids()
                for tid in theme_ids:
                    screen.remove_class(f"theme-{tid}")

            # 添加新主题 class 到 Screen
            screen.add_class(f"theme-{self.theme_id}")
            self._logger.info(f"Applied theme class: theme-{self.theme_id}")
        except Exception as e:
            self._logger.error(f"[_apply_theme_class] Error: {e}")

    async def _load_theme_css(self, theme_id: str) -> None:
        """加载主题 CSS 文件（异步）."""
        if not self._theme_manager:
            return

        try:
            # 卸载之前的主题 CSS
            for css_path in self._theme_css_paths:
                try:
                    await self.remove_stylesheet(css_path)
                except Exception:
                    pass
            self._theme_css_paths.clear()

            # 加载新的主题 CSS
            theme_css_path = self._theme_manager.get_theme_css_path(theme_id)
            if theme_css_path and theme_css_path.exists():
                await self.add_stylesheet(str(theme_css_path))
                self._theme_css_paths.append(str(theme_css_path))
                self._logger.debug(f"Loaded theme CSS: {theme_css_path.name}")
        except Exception as e:
            self._logger.debug(f"Failed to load theme CSS: {e}")

    def _load_theme_css_sync(self, theme_id: str) -> None:
        """切换主题 CSS（CSS 已预加载，只需记录当前主题）."""
        # CSS 在初始化时已全部预加载，这里只需记录即可
        self._logger.info(
            f"[SYNC] Theme CSS already preloaded, switching to: {theme_id}"
        )

    @on(Click, "#theme-toggle")
    def _on_theme_toggle_click(self, event: Click | None = None) -> None:
        """处理主题切换按钮点击事件."""
        self._logger.info("Theme toggle clicked!")
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return

        current_theme = self._theme_manager.get_current_theme_id()
        available_themes = self._theme_manager.list_theme_ids()
        if len(available_themes) < 2:
            self._logger.warning("Not enough themes available to toggle")
            return

        current_index = available_themes.index(current_theme)
        next_index = (current_index + 1) % len(available_themes)
        next_theme = available_themes[next_index]

        self.set_theme(next_theme)

    def action_toggle_theme(self) -> None:
        """切换主题（快捷键 Ctrl+Shift+T）."""
        self._on_theme_toggle_click(None)

    def _update_theme_toggle_tooltip(self) -> None:
        """更新主题切换按钮的 tooltip，显示当前主题名称."""
        if not self._theme_manager:
            return

        theme_toggle = self._widget_cache.get("theme_toggle")
        if not theme_toggle:
            try:
                theme_toggle = self.query_one("#theme-toggle", Static)
                self._widget_cache["theme_toggle"] = theme_toggle
            except Exception:
                return

        theme_name = t("tui.command.toggle_theme")
        theme_toggle.tooltip = theme_name

    def _on_theme_changed(self, theme_id: str) -> None:
        """主题变更回调（CSS 已预加载，只需更新 class）."""
        # CSS 在初始化时已全部预加载，这里只需更新 class
        self.theme_id = theme_id
        self.theme = theme_id  # 切换 Textual 原生主题（驱动 $primary 等核心变量）
        self._apply_theme_class()
        self._update_theme_toggle_tooltip()

        # 清除 banner 颜色缓存并重新渲染（切换 Banner 颜色）
        cache_key = f"_banner_color_{theme_id}"
        if hasattr(self, cache_key):
            delattr(self, cache_key)
        self._render_welcome_banner()

    def update_theme_css(self) -> None:
        self._apply_theme_class()

    # ------------------------------------------------------------------
    # 主题控制（公开 API）
    # ------------------------------------------------------------------

    def set_theme(self, theme_id: str) -> bool:
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False

        success = self._theme_manager.set_theme(theme_id)
        if success:
            self._logger.info(f"Theme changed to: {theme_id}")
        else:
            self.notify(f"Theme '{theme_id}' not found")
            self._logger.warning(f"Theme not found: {theme_id}")

        return success

    def get_current_theme_id(self) -> str:
        if self._theme_manager:
            return self._theme_manager.get_current_theme_id()
        return "default"

    def list_available_themes(self) -> list:
        if self._theme_manager:
            return self._theme_manager.list_theme_ids()
        return ["default"]

    # ------------------------------------------------------------------
    # 透明度（毛玻璃）
    # ------------------------------------------------------------------

    def _update_transparency_styles(self, enabled: bool) -> None:
        transparent_mappings = {
            "#app-header": "transparent-header",
            "#status-bar": "transparent-status-bar",
            "#app-footer": "transparent-footer",
            "#sidebar-container": "transparent-sidebar",
            "#chat-area": "transparent-chat",
            "#user-input": "transparent-input",
            "#welcome-banner": "transparent-welcome",
        }

        try:
            for widget_id, transparent_class in transparent_mappings.items():
                try:
                    widget = self.query_one(widget_id)

                    if enabled:
                        widget.add_class(transparent_class)
                    else:
                        widget.remove_class(transparent_class)

                except Exception:
                    pass
        except Exception as e:
            self._logger.debug(f"Failed to update transparency styles: {e}")

    def is_transparency_enabled(self) -> bool:
        if self._theme_manager:
            return self._theme_manager.is_transparency_enabled()
        return False


__all__ = ["StylingMixin", "build_textual_themes"]