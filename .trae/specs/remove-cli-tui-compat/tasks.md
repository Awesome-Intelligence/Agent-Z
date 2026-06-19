# Tasks - 删除 CLI/TUI 兼容层

## Task 1: 删除兼容层文件

- [x] Task 1.1: 删除 `cli/tui/__init__.py`

## Task 2: 更新 cli/main.py 导入

- [x] Task 2.1: 更新 `cli/main.py` 中的 `from cli.tui import ...` → `from tui import ...`

## Task 3: 更新测试文件导入

- [x] Task 3.1: 更新 `tests/unit/cli/tui/test_streaming_text.py` 导入路径
- [x] Task 3.2: 更新 `tests/unit/cli/tui/test_message_list.py` 导入路径

## Task 4: 删除旧测试目录

- [x] Task 4.1: 删除 `tests/unit/cli/tui/` 目录

## Task 5: 验证

- [x] Task 5.1: 验证 `from tui import ...` 正常工作
- [x] Task 5.2: 验证 `python -m cli.main` 正常
- [x] Task 5.3: 确认无遗留的 `from cli.tui` 导入
