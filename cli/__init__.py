"""
TUI module for the Handsome Agent.

This package contains the Text User Interface implementation that provides
user interaction capabilities and argument parsing with rich terminal UI.

Directory Structure:
    cli/
    ├── main.py              # 主入口
    ├── _parser.py           # 参数解析
    ├── commands/            # CLI 命令系统
    │   ├── doctor.py       # 诊断检查
    │   └── sessions.py     # 会话管理
    ├── tui/                 # TUI 渲染层
    │   └── curses_ui.py    # Curses UI 组件
    ├── components/          # UI 组件
    │   ├── ui.py           # UI 组件（门面）
    │   ├── colors.py       # 颜色和主题
    │   ├── output.py       # 输出函数
    │   └── banner.py       # Banner 渲染
    └── compat.py           # 向后兼容导入
"""

# Re-export from compat layer for backward compatibility
from . import compat

# Re-export main modules for easy access
from . import main
from . import _parser
from . import ui
from . import colors
from . import cli_output
from . import banner
from . import curses_ui
from . import status
from . import setup_wizard

__version__ = "0.0.1"
__author__ = "Handsome Agent Team"

# Expose key components at package level
__all__ = [
    "main",
    "_parser",
    "ui",
    "colors",
    "cli_output",
    "banner",
    "curses_ui",
    "status",
    "setup_wizard",
    "compat",
]