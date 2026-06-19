# Checklist - CLI/TUI 目录结构清理

## 目录清理检查

- [x] `cli/tui/themes/` 目录已删除
- [x] `cli/tui/core/` 目录已删除
- [x] `cli/tui/services/` 目录已删除
- [x] `cli/tui/textual_app/` 目录已删除
- [x] `cli/tui/views/` 目录已删除
- [x] `cli/tui/widgets/` 目录已删除
- [x] `cli/tui/theming/` 目录已删除
- [x] `cli/tui/sidebar.py` 文件已删除

## 保留检查

- [x] `cli/tui/__init__.py` 兼容层文件保留
- [x] `tui/` 顶层目录完整

## 功能验证检查

- [x] `from cli.tui import TEXTUAL_AVAILABLE` 向后兼容导入正常（有 DeprecationWarning）
- [x] `from tui import TEXTUAL_AVAILABLE` 新导入路径正常
- [x] `python -m cli.main` CLI 入口正常
- [x] TUI 侧边栏功能正常

## 代码检查

- [x] `cli/tui/__init__.py` 兼容层代码正确
- [x] 无遗留的 `cli.tui.` 子目录引用
