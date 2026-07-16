#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TUI 通用格式化工具（纯函数）

🚪 Access - 💬 TUI - Core - 格式化

v8.x 从 ``tui/textual_app/app.py::_format_context`` 抽出。
所有函数**不依赖 Textual**，可在 cli/agent 等场景复用。
"""

from __future__ import annotations

from typing import Optional


def format_token_count(tokens: Optional[int]) -> str:
    """将 token 数字格式化为可读字符串。

    规则：
    - ``None`` 或 0/负数 → ``"?"``
    - >= 1,000,000 → ``"{n}M"`` 或 ``"{n.n}M"``
    - >= 1,000 → ``"{n}K"`` 或 ``"{n.n}K"``
    - < 1,000 → 原样数字字符串

    Args:
        tokens: token 数量，可为 None

    Returns:
        可读字符串（如 ``"45K"``、``"1.2M"``、``"?"``）
    """
    if not tokens:
        return "?"

    if tokens >= 1_000_000:
        val = tokens / 1_000_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}M"
        return f"{val:.1f}M"
    elif tokens >= 1_000:
        val = tokens / 1_000
        rounded = round(val)
        if abs(val - rounded) < 0.05:
            return f"{rounded}K"
        return f"{val:.1f}K"
    return str(tokens)


# 兼容别名（与原 app.py 方法同名）
format_context = format_token_count


__all__ = ["format_token_count", "format_context"]