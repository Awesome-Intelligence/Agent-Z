# CLI/TUI 目录结构清理规范

## Why

当前项目存在以下问题：

1. **重复目录**: `cli/tui/themes/` 和 `cli/tui/theming/` 内容重复
2. **旧目录残留**: `cli/tui/` 已迁移到顶层 `tui/`，但旧目录仍存在
3. **根目录文件膨胀**: `cli/` 下有 30+ 个独立文件，缺乏组织

## What Changes

### 1. 删除重复目录

```
删除: cli/tui/themes/
保留: cli/tui/theming/
```

### 2. 删除旧目录（保留兼容层）

```
删除: cli/tui/ 子目录内容
保留: cli/tui/__init__.py 作为兼容层（从 tui/ 重导出）
```

### 3. 保留的文件

| 文件/目录 | 状态 | 原因 |
|-----------|------|------|
| `cli/tui/__init__.py` | ✅ 保留 | 兼容层 |
| `cli/tui/sidebar.py` | ❌ 删除 | 已迁移到 `tui/sidebar.py` |
| `cli/tui/core/` | ❌ 删除 | 已迁移到 `tui/core/` |
| `cli/tui/services/` | ❌ 删除 | 已迁移到 `tui/services/` |
| `cli/tui/textual_app/` | ❌ 删除 | 已迁移到 `tui/textual_app/` |
| `cli/tui/views/` | ❌ 删除 | 已迁移到 `tui/views/` |
| `cli/tui/widgets/` | ❌ 删除 | 已迁移到 `tui/widgets/` |
| `cli/tui/theming/` | ❌ 删除 | 已迁移到 `tui/theming/` |
| `cli/tui/themes/` | ❌ 删除 | 重复目录 |

## Impact

- 导入路径 `from cli.tui import ...` 仍可工作（通过兼容层）
- 新代码应使用 `from tui import ...`

## Success Criteria

- [ ] `cli/tui/` 只保留 `__init__.py` 文件
- [ ] 所有 TUI 代码只存在于 `tui/` 顶层目录
- [ ] 向后兼容导入仍然工作
