# Checklist - CLI 目录重构为 TUI

## 目录结构

- [x] `cli/cli_commands/` 目录创建成功
- [x] `cli/tui/` 目录创建成功
- [x] `cli/components/` 目录创建成功

## 文件迁移

- [x] `cli/curses_ui.py` 移动到 `cli/tui/curses_ui.py`
- [x] `cli/ui.py` 移动到 `cli/components/ui.py`
- [x] `cli/banner.py` 移动到 `cli/components/banner.py`
- [x] `cli/colors.py` 移动到 `cli/components/colors.py`
- [x] `cli/cli_output.py` 移动到 `cli/components/output.py`

## 导入更新

- [x] `cli/main.py` 导入路径更新
- [x] `cli/ui.py` 从新位置重新导出
- [x] `cli/colors.py` 从新位置重新导出
- [x] `cli/cli_output.py` 从新位置重新导出
- [x] `cli/banner.py` 从新位置重新导出
- [x] `cli/curses_ui.py` 从新位置重新导出
- [x] `cli/compat.py` 兼容层创建

## 功能验证

- [x] `from cli import ui` 正常工作
- [x] `from cli import colors` 正常工作
- [x] `from cli import curses_ui` 正常工作
- [x] `from cli import banner` 正常工作
- [x] `python -m cli.main --version` 正常运行
- [x] `python -m cli.main status` 正常运行

## 代码质量

- [x] 无遗留的旧导入路径（保持向后兼容）
- [x] 所有 `__init__.py` 文件正确导出
- [x] 文档字符串已更新