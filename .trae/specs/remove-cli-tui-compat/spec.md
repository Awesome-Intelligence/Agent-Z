# 删除 CLI/TUI 兼容层规范

## Why

TUI 已迁移到顶层 `tui/` 目录，兼容层 `cli/tui/__init__.py` 不再需要。

## What Changes

### **BREAKING** 删除兼容层

1. 删除 `cli/tui/__init__.py`
2. 更新 `cli/main.py` 中的导入路径
3. 更新测试文件中的导入路径
4. 删除测试目录 `tests/unit/cli/tui/`

### 导入路径变更

| 旧路径 | 新路径 |
|--------|--------|
| `from cli.tui import ...` | `from tui import ...` |
| `from cli.tui.widgets.xxx import ...` | `from tui.widgets.xxx import ...` |

## Impact

- **BREAKING**: `from cli.tui import ...` 将不再工作
- 影响文件: `cli/main.py`, `tests/unit/cli/tui/*.py`

## Success Criteria

- [ ] `cli/tui/__init__.py` 已删除
- [ ] `cli/main.py` 使用 `from tui import ...`
- [ ] 测试文件使用新导入路径
- [ ] `python -m cli.main` 正常工作
