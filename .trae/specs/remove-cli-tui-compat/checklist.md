# Checklist - 删除 CLI/TUI 兼容层

## 文件删除检查

- [x] `cli/tui/__init__.py` 已删除
- [x] `tests/unit/cli/tui/` 目录已删除

## 代码更新检查

- [x] `cli/main.py` 导入已更新为 `from tui import ...`
- [x] `tests/unit/cli/tui/test_streaming_text.py` 导入已更新
- [x] `tests/unit/cli/tui/test_message_list.py` 导入已更新

## 功能验证检查

- [x] `from tui import TEXTUAL_AVAILABLE` 正常工作
- [x] `python -m cli.main` 正常
- [x] 无遗留的 `from cli.tui` 导入
