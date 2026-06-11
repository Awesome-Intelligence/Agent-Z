#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Compatibility Layer - 向后兼容导入

🚪 Access - 💬 CLI - 兼容层

提供旧的导入路径兼容，使得从 `cli.ui`, `cli.curses_ui` 等导入的代码仍然可以工作。
"""

# ============================================================================
# UI Components (向后兼容)
# ============================================================================

# 从 components.ui 导入
from cli.components.ui import (
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
    status_bar,
    StatusBar,
)

# 从 components.colors 导入
from cli.components.colors import (
    should_use_color,
    supports_ansi,
    enable_ansi_support,
    get_terminal_width,
    get_terminal_height,
    strip_color as strip_ansi,
    HEX_AVOCADO,
    HEX_AVOCADO_BRIGHT,
    HEX_AVOCADO_DIM,
    RGB_AVOCADO,
    RGB_AVOCADO_BRIGHT,
    RGB_AVOCADO_DIM,
)

# 从 components.output 导入
from cli.components.output import (
    print_substep,
    print_end_step,
    print_table_row,
    print_spinner,
    prompt_yes_no,
    prompt_choice,
)

# 从 components.ui 导入 print_banner
# 从 components.banner 导入 build_welcome_banner, print_setup_banner, print_simple_banner
from cli.components.ui import (
    print_banner,
)
from cli.components.banner import (
    build_welcome_banner,
    print_setup_banner,
    print_simple_banner,
)

# ============================================================================
# TUI Components (向后兼容)
# ============================================================================

from cli.tui.curses_ui import (
    has_curses,
    curses_radiolist,
    curses_checklist,
    radio_select,
    multi_select,
    flush_stdin,
)

# ============================================================================
# Commands (向后兼容)
# ============================================================================

from cli.cli_commands.doctor import run_diagnostics
from cli.cli_commands.sessions import list_sessions, browse_sessions

# ============================================================================
# Status Module (保持原位置)
# ============================================================================

from cli.status import show_status

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
    "status_bar",
    "StatusBar",
    # Colors
    "should_use_color",
    "supports_ansi",
    "enable_ansi_support",
    "get_terminal_width",
    "get_terminal_height",
    "strip_ansi",
    "HEX_AVOCADO",
    "HEX_AVOCADO_BRIGHT",
    "HEX_AVOCADO_DIM",
    "RGB_AVOCADO",
    "RGB_AVOCADO_BRIGHT",
    "RGB_AVOCADO_DIM",
    # Output
    "print_substep",
    "print_end_step",
    "print_table_row",
    "print_spinner",
    "prompt_yes_no",
    "prompt_choice",
    # Banner
    "print_banner",
    "print_simple_banner",
    "build_welcome_banner",
    "print_setup_banner",
    # TUI
    "has_curses",
    "curses_radiolist",
    "curses_checklist",
    "radio_select",
    "multi_select",
    "flush_stdin",
    # Commands
    "run_diagnostics",
    "list_sessions",
    "browse_sessions",
    # Status
    "show_status",
]