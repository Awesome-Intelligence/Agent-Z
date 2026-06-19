#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Output Module - 重新导出自 cli.components.output

🚪 Access - 💬 CLI - 输出函数

此文件已迁移到 cli/components/output.py，此文件提供向后兼容。
"""

# 重新导出自新位置
from common.terminal.output import (
    Colors,
    Theme,
    should_use_color,
    get_terminal_width,
    get_terminal_height,
    strip_color,
    print_info,
    print_success,
    print_warning,
    print_error,
    print_header,
    print_debug,
    print_divider,
    prompt,
    prompt_yes_no,
    prompt_choice,
    print_step,
    print_substep,
    print_end_step,
    print_spinner,
    Spinner,
    print_box,
    print_table_row,
    print_rich_table,
    print_stream_start,
    print_stream_chunk,
    print_stream_end,
    StreamingPrinter,
)

__all__ = [
    "Colors",
    "Theme",
    "should_use_color",
    "get_terminal_width",
    "get_terminal_height",
    "strip_color",
    "print_info",
    "print_success",
    "print_warning",
    "print_error",
    "print_header",
    "print_debug",
    "print_divider",
    "prompt",
    "prompt_yes_no",
    "prompt_choice",
    "print_step",
    "print_substep",
    "print_end_step",
    "print_spinner",
    "Spinner",
    "print_box",
    "print_table_row",
    "print_rich_table",
    "print_stream_start",
    "print_stream_chunk",
    "print_stream_end",
    "StreamingPrinter",
]