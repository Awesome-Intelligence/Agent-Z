#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""透明度（毛玻璃）CSS 动态生成器

🚪 Access - 💬 Common - Theming - Styles - Transparency

本模块自 v8.x 起接收 ``tui.theming.theme_manager.generate_transparent_css``
的逻辑，作为透明 CSS 的**单一来源**，供 tui App 运行时注入。
"""

from __future__ import annotations

from typing import Optional


def generate_transparent_css(
    level: float = 0.85,
    *,
    enabled: bool = True,
) -> str:
    """生成支持透明度的 CSS 变量块。

    Args:
        level: 透明度级别（0.0 完全透明 - 1.0 完全不透明）。
               默认 0.85。
        enabled: 是否启用透明度。False 时返回空字符串。

    Returns:
        CSS 字符串。``enabled=False`` 时返回空字符串。
    """
    if not enabled:
        return ""

    # 规范化到 [0.0, 1.0]
    alpha = max(0.0, min(1.0, float(level)))

    # hex8 格式: #RRGGBBAA (AA 是 alpha)
    alpha_hex = format(int(alpha * 255), "02X")

    return f"""/* ============================================================================
   透明度配置 (Frosted Glass Effect) — 由 common.theming.styles.transparency 生成
   ============================================================================ */

:root {{
    --transparency-alpha: {alpha};
    --transparency-hex: {alpha_hex};
}}

/* 毛玻璃效果样式类（运行时 add_stylesheet 注入） */
.transparent-surface {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-header {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-footer {{
    background: rgba(33, 38, 45, {alpha});
}}

.transparent-sidebar {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-input {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-border {{
    border: solid rgba(48, 54, 61, {alpha});
}}
"""


__all__ = ["generate_transparent_css"]