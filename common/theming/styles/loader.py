#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一 CSS 样式表加载器

🚪 Access - 💬 Common - Theming - Styles - Loader

提供：
- list_app_stylesheets()：按加载顺序列出应用基础样式（base/layout/components/animations）
- list_theme_stylesheets(theme_id)：返回单个主题 CSS 文件路径

本模块自 v8.x 起为 tui App 的样式注入提供**单一加载入口**，
消除原先 ``app.py`` 与 ``theming/css/__init__.py`` 两条加载路径并存的混乱。
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ..css import CSS_DIR, THEMES_DIR


def list_app_stylesheets() -> List[str]:
    """获取所有应用级样式表文件路径（不含主题）。

    加载顺序：base → layout → components → animations

    Returns:
        样式表文件路径字符串列表
    """
    return [
        str(CSS_DIR / "base.css"),
        str(CSS_DIR / "layout.css"),
        str(CSS_DIR / "components.css"),
        str(CSS_DIR / "animations.css"),
    ]


def list_theme_stylesheets(theme_id: str) -> List[Path]:
    """获取单个主题的 CSS 文件路径列表。

    Args:
        theme_id: 主题 ID（``default`` / ``awesome`` / 其他已注册主题）

    Returns:
        主题 CSS 文件的 Path 列表（空列表表示主题不存在）
    """
    path = THEMES_DIR / f"{theme_id}.css"
    return [path] if path.exists() else []


__all__ = ["list_app_stylesheets", "list_theme_stylesheets"]