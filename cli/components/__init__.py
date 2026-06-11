#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Components - UI 组件模块

🚪 Access - 💬 CLI - UI 组件

包含各种 UI 组件：
- ui: 主 UI 模块（门面）
- colors: 颜色和主题
- banner: ASCII Banner 渲染
- output: 输出函数
- status: 状态栏
"""

# Re-export from submodules for backward compatibility
from .ui import (
    Colors,
    Theme,
    print_info,
    print_success,
    print_warning,
    print_error,
    print_header,
    print_divider,
    print_step,
    print_box,
    Spinner,
    prompt,
    HAS_RICH,
    print_banner,
    print_banner_simple,
)

from .colors import (
    Colors as ColorCodes,
    color,
    should_use_color,
    supports_ansi,
    get_terminal_width,
    get_terminal_height,
    strip_color,
)

from .banner import (
    print_simple_banner as banner_print_simple,
    build_welcome_banner,
)

__all__ = [
    # UI
    "Colors",
    "Theme",
    "print_info",
    "print_success",
    "print_warning",
    "print_error",
    "print_header",
    "print_divider",
    "print_step",
    "print_box",
    "Spinner",
    "prompt",
    "HAS_RICH",
    "print_banner",
    "print_banner_simple",
    # Colors
    "ColorCodes",
    "color",
    "should_use_color",
    "supports_ansi",
    "get_terminal_width",
    "get_terminal_height",
    "strip_color",
    # Banner
    "build_welcome_banner",
]