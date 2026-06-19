# 创建 common/terminal 共享模块规范

## Why

当前 CLI 和 TUI 之间存在交叉依赖：
- `tui/core/curses_ui.py` 被 CLI 使用
- `cli/components/` 被 TUI 使用

需要创建一个共享的终端 UI 模块来消除循环依赖。

## What Changes

### 新目录结构

```
handsome-agent/
├── cli/
│   ├── cli_commands/
│   ├── components/             # CLI 专用组件
│   ├── main.py
│   └── ... (其他 CLI 文件)
│
├── tui/
│   ├── core/                  # TUI 专用（不含 curses_ui）
│   ├── views/
│   ├── widgets/
│   ├── textual_app/
│   ├── theming/
│   └── main.py
│
├── common/
│   └── terminal/               # 🆕 共享终端 UI 模块
│       ├── __init__.py
│       ├── curses_ui.py        # 从 tui/core/ 移入
│       ├── colors.py           # 从 cli/components/ 移入
│       ├── banner.py           # 从 cli/components/ 移入
│       └── output.py          # 从 cli/components/ 移入
```

### 迁移的文件

| 源路径 | 目标路径 |
|--------|----------|
| `tui/core/curses_ui.py` | `common/terminal/curses_ui.py` |
| `cli/components/colors.py` | `common/terminal/colors.py` |
| `cli/components/banner.py` | `common/terminal/banner.py` |
| `cli/components/output.py` | `common/terminal/output.py` |
| `cli/components/ui.py` | `common/terminal/ui.py` |

### 导入路径变更

| 旧路径 | 新路径 |
|--------|--------|
| `from cli.components.colors import ...` | `from common.terminal.colors import ...` |
| `from cli.components.banner import ...` | `from common.terminal.banner import ...` |
| `from cli.components.ui import ...` | `from common.terminal.ui import ...` |
| `from cli.components.output import ...` | `from common.terminal.output import ...` |
| `from tui.core.curses_ui import ...` | `from common.terminal.curses_ui import ...` |

## Impact

- 需要更新所有引用这些模块的文件
- `cli/components/` 和 `tui/core/` 中移出的文件需要删除

## Success Criteria

- [ ] `common/terminal/` 目录创建
- [ ] 所有共享组件迁移到 `common/terminal/`
- [ ] 所有导入路径更新
- [ ] 无循环依赖
- [ ] `python -m cli.main` 正常工作
