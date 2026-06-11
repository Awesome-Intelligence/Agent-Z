#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Banner Module - 重新导出自 cli.components.banner

🚪 Access - 💬 CLI - Banner 组件

此文件已迁移到 cli/components/banner.py，此文件提供向后兼容。
"""

# 重新导出自新位置
from cli.components.banner import (
    AVOCADO,
    AVOCADO_BRIGHT,
    AVOCADO_DIM,
    AVOCADO_DARK,
    WHITE,
    GRAY_DIM,
    GOLD,
    HANDSOME_LOGO,
    HERO_ASCII,
    build_welcome_banner,
    print_simple_banner,
    print_setup_banner,
    print_setup_summary,
    print_tool_status,
)

__all__ = [
    "AVOCADO",
    "AVOCADO_BRIGHT",
    "AVOCADO_DIM",
    "AVOCADO_DARK",
    "WHITE",
    "GRAY_DIM",
    "GOLD",
    "HANDSOME_LOGO",
    "HERO_ASCII",
    "build_welcome_banner",
    "print_simple_banner",
    "print_setup_banner",
    "print_setup_summary",
    "print_tool_status",
]