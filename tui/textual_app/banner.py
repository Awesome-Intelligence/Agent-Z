#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BannerMixin — 欢迎横幅核心渲染

🚪 Access - 💬 TUI - Textual App - Banner

依赖主类的 ``self._banner_cache`` / ``self._widget_cache`` / ``self._theme_manager`` / ``self.cwd`` / ``self._logger``。
"""

from __future__ import annotations

import logging

from tui.services.project_info import (
    get_project_path,
    get_skills_count,
    get_skills_path,
    get_tools_count,
    get_tools_path,
)

from .imports import RichText

logger = logging.getLogger(__name__)

# 从 common.terminal.banner 导入统一的 Logo
from common.terminal.banner import AGENT_Z_LOGO


def _parse_logo_lines() -> tuple:
    """解析 AGENT_Z_LOGO 为行列表."""
    lines = []
    for line in AGENT_Z_LOGO.split('\n'):
        clean_line = line.replace('[bold #FFFFFF]', '').replace('[/]', '')
        lines.append(clean_line)
    return tuple(lines)


_BANNER_LINES = _parse_logo_lines()


class BannerMixin:
    """欢迎横幅 Mixin."""

    _logger = logging.getLogger(__name__)
    _widget_cache: dict = {}
    _banner_cache: dict = {}
    _banner_cache_initialized: bool = False
    _theme_manager = None
    cwd: str = ""

    # ------------------------------------------------------------------
    # 缓存初始化
    # ------------------------------------------------------------------

    def _init_banner_cache(self) -> None:
        """初始化 Banner 缓存."""
        if self._banner_cache_initialized:
            return

        try:
            self._banner_cache["project_path"] = get_project_path()
            self._banner_cache["skills_path"] = get_skills_path()
            self._banner_cache["tools_path"] = get_tools_path()
            self._banner_cache["skills_count"] = get_skills_count()
            self._banner_cache["tools_count"] = get_tools_count()
            try:
                from cli import __version__ as app_version
                self._banner_cache["version"] = app_version
            except ImportError:
                self._banner_cache["version"] = "unknown"
            self._banner_cache_initialized = True
            self._logger.debug("Banner cache initialized")
        except Exception as e:
            self._logger.error(f"Failed to initialize banner cache: {e}")

    def _get_theme_banner_color(self) -> str:
        """获取 banner 颜色（始终白色，不随主题切换）."""
        return "#FFFFFF"

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------

    def _render_welcome_banner(self) -> None:
        """渲染欢迎 Banner."""
        if not self._banner_cache_initialized:
            self._init_banner_cache()

        banner_color = self._get_theme_banner_color()
        welcome_lines = [
            f"[bold {banner_color}]{line}[/]" for line in _BANNER_LINES
        ]

        welcome_widget = self._widget_cache.get("welcome_banner")
        if welcome_widget:
            welcome_text = RichText.from_markup("\n".join(welcome_lines))
            welcome_widget.update(welcome_text)

        # 获取随机问候语
        try:
            from common.i18n import get_random_greeting
            greeting = get_random_greeting()
        except Exception:
            greeting = "存在先于本质。"

        # 渲染右侧信息栏
        current_mode = "Agent"
        try:
            if hasattr(self, "_agent") and self._agent and hasattr(self._agent, "get_mode"):
                current_mode = self._agent.get_mode()
        except Exception:
            pass

        cwd_path = self.cwd or "unknown"
        max_chars = 40
        if len(cwd_path) > max_chars:
            cwd_path = cwd_path[:max_chars - 3] + "..."

        version_widget = self._widget_cache.get("version_info")
        if version_widget and self._banner_cache.get("version"):
            version_text = RichText.from_markup(
                f"[dim]{self._banner_cache['version']}[/] [dim]·[/] [italic dim]{greeting}[/]"
            )
            version_widget.update(version_text)

        mode_widget = self._widget_cache.get("skills_info")
        if mode_widget:
            mode_text = RichText.from_markup(f"[bright_black]{cwd_path}[/]")
            mode_widget.update(mode_text)

        greeting_widget = self._widget_cache.get("tools_info")
        if greeting_widget:
            greeting_widget.update("")


__all__ = ["BannerMixin"]
