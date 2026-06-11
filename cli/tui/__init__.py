#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI (Terminal User Interface) - 终端界面渲染层

🚪 Access - 💬 CLI - TUI 渲染层

提供 curses 和其他 TUI 组件，用于构建交互式终端界面。

模块：
- curses_ui: 跨平台 curses UI 组件
- rich_panel: Rich 库面板组件
- theme_engine: 主题引擎
- layout_manager: 布局管理器
"""

from .curses_ui import (
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    flush_stdin,
)

__all__ = [
    "has_curses",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
    "flush_stdin",
]