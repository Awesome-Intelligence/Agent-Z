# Checklist - 创建 common/terminal 共享模块

## 目录创建检查

- [x] `common/terminal/` 目录已创建
- [x] `common/terminal/__init__.py` 已创建

## 文件迁移检查

- [x] `common/terminal/curses_ui.py` 已创建
- [x] `common/terminal/colors.py` 已创建
- [x] `common/terminal/banner.py` 已创建
- [x] `common/terminal/output.py` 已创建
- [x] `common/terminal/ui.py` 已创建

## 源文件删除检查

- [x] `tui/core/curses_ui.py` 已删除
- [x] `cli/components/colors.py` 已删除
- [x] `cli/components/banner.py` 已删除
- [x] `cli/components/output.py` 已删除
- [x] `cli/components/ui.py` 已删除

## 导入路径更新检查

- [x] `cli/main.py` 导入已更新
- [x] `cli/cli_commands/sessions.py` 导入已更新
- [x] `cli/compat.py` 导入已更新
- [x] `cli/banner.py` 导入已更新
- [x] `cli/colors.py` 导入已更新
- [x] `cli/ui.py` 导入已更新
- [x] `cli/cli_output.py` 导入已更新
- [x] `tui/__init__.py` 导入已更新
- [x] `tui/textual_app/app.py` 导入已更新

## 功能验证检查

- [x] `python -m cli.main` 正常工作
- [x] `from cli import main` 正常工作
- [x] `from tui import TEXTUAL_AVAILABLE` 正常工作
- [x] 无循环依赖
- [x] `from common.terminal import ...` 正常工作
