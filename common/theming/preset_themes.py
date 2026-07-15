#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preset Themes — 内置主题字典。

🚪 Access - 💬 Common - Theming - 预设主题

本模块自 v8.x 起从 ``tui.theming.preset_themes`` 上移而来。
"""

from __future__ import annotations

from .theme_config import Theme


_PRESET_THEMES: dict[str, Theme] = {
    "default": Theme(
        theme_id="default",
        display_name_key="tui.theme.default.name",
        primary="#B180D7",
        secondary="#C9A0E0",
        accent="#B180D7",
        foreground="#FFFFFF",
        background="#1a1a1a",
        surface="#2a2a2a",
        panel="#1a1a1a",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        banner_color="#C9A0E0",
    ),
    "awesome": Theme(
        theme_id="awesome",
        display_name_key="tui.theme.awesome.name",
        primary="#A9FC6E",
        secondary="#C5FF9E",
        accent="#A9FC6E",
        foreground="#FFFFFF",
        background="#1A2E0A",
        surface="#2a2a2a",
        panel="#1a1a1a",
        success="#4CAF50",
        warning="#FF9800",
        error="#F44336",
        banner_color="#C5FF9E",
    ),
}


__all__ = ["_PRESET_THEMES"]