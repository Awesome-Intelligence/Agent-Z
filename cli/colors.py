#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Colors Module - 重新导出自 cli.components.colors

🚪 Access - 💬 CLI - 颜色系统

此文件已迁移到 cli/components/colors.py，此文件提供向后兼容。
"""

# 重新导出自新位置
from common.terminal.colors import (
    Colors,
    Theme,
    should_use_color,
    supports_ansi,
    enable_ansi_support,
    color,
    colorize,
    strip_color,
    get_skin_color,
    get_skin_branding,
    success,
    error,
    warning,
    info,
    accent,
    dim,
    bold,
    get_rich_console,
    get_terminal_width,
    get_terminal_height,
    HEX_AVOCADO,
    HEX_AVOCADO_BRIGHT,
    HEX_AVOCADO_DIM,
    RGB_AVOCADO,
    RGB_AVOCADO_BRIGHT,
    RGB_AVOCADO_DIM,
    RGB_GOLD,
    HEX_GOLD,
)

__all__ = [
    "Colors",
    "Theme",
    "should_use_color",
    "supports_ansi",
    "enable_ansi_support",
    "color",
    "colorize",
    "strip_color",
    "get_skin_color",
    "get_skin_branding",
    "success",
    "error",
    "warning",
    "info",
    "accent",
    "dim",
    "bold",
    "get_rich_console",
    "get_terminal_width",
    "get_terminal_height",
    "HEX_AVOCADO",
    "HEX_AVOCADO_BRIGHT",
    "HEX_AVOCADO_DIM",
    "RGB_AVOCADO",
    "RGB_AVOCADO_BRIGHT",
    "RGB_AVOCADO_DIM",
    "RGB_GOLD",
    "HEX_GOLD",
]