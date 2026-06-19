# Tasks - CLI/TUI 目录结构清理

## Task 1: 删除重复的 themes 目录

- [x] Task 1.1: 确认 `cli/tui/themes/` 与 `cli/tui/theming/` 内容重复
- [x] Task 1.2: 删除 `cli/tui/themes/` 目录

## Task 2: 删除旧 TUI 子目录（迁移后残留）

- [x] Task 2.1: 删除 `cli/tui/core/` 目录
- [x] Task 2.2: 删除 `cli/tui/services/` 目录
- [x] Task 2.3: 删除 `cli/tui/textual_app/` 目录
- [x] Task 2.4: 删除 `cli/tui/views/` 目录
- [x] Task 2.5: 删除 `cli/tui/widgets/` 目录
- [x] Task 2.6: 删除 `cli/tui/theming/` 目录
- [x] Task 2.7: 删除 `cli/tui/sidebar.py`

## Task 3: 更新兼容层

- [x] Task 3.1: 更新 `cli/tui/__init__.py` 确保所有重导出正确
- [x] Task 3.2: 添加注释说明这是兼容层

## Task 4: 验证

- [x] Task 4.1: 验证 `from cli.tui import TEXTUAL_AVAILABLE` 仍然工作
- [x] Task 4.2: 验证 `from tui import TEXTUAL_AVAILABLE` 正常工作
- [x] Task 4.3: 验证 CLI 入口 `python -m cli.main` 正常

## Task Dependencies

```
Task 1 ──→ Task 2 ──→ Task 3 ──→ Task 4
(可顺序执行，删除后更新兼容层，最后验证)
```
