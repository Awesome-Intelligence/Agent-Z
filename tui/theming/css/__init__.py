#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""向后兼容 shim — ``tui.theming.css`` 已上移到 ``common.theming.css``

v8.x：原内容（get_stylesheets / get_theme_css + 4 个 CSS 文件 + themes/*.css）
已上移到 ``common.theming.css``，本包 re-export 公共符号以保持
``from tui.theming.css import get_stylesheets`` 仍然可用。
"""

from __future__ import annotations

from common.theming.css import (
    CSS_DIR,
    THEMES_DIR,
    get_stylesheets,
    get_theme_css,
)

__all__ = [
    "CSS_DIR",
    "THEMES_DIR",
    "get_stylesheets",
    "get_theme_css",
]