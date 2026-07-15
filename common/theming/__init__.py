#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""主题/样式系统（跨 tui/cli 共享）

🚪 Access - 💬 Common - Theming

本模块自 v8.x 起从 ``tui.theming`` 上移而来，供 tui/cli 两侧共用。

子模块：
- ``theme_config``    Theme dataclass（纯数据）
- ``preset_themes``   预设主题字典
- ``theme_manager``   ThemeManager 单例（持久化/回调/透明度开关）
- ``css``             CSS 静态文件 + 加载入口
- ``styles``          动态 CSS 生成（transparency / loader）
"""

from .theme_config import Theme
from .preset_themes import _PRESET_THEMES
from .theme_manager import ThemeManager, get_theme_manager

__all__ = [
    "Theme",
    "_PRESET_THEMES",
    "ThemeManager",
    "get_theme_manager",
]