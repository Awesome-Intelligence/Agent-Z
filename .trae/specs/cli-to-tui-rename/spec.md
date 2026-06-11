# CLI 目录重构为 TUI 规范

## Why
当前 `cli/` 目录命名不准确，包含了 CLI 命令系统和 TUI 渲染组件。参考 Hermes 的目录结构，需要明确区分 CLI（命令系统）和 TUI（终端界面渲染）。

## What Changes

### 目录结构变更

**变更前：**
```
cli/
├── main.py              # 主入口
├── _parser.py          # 参数解析
├── ui.py                # UI 组件（混合）
├── curses_ui.py         # Curses TUI
├── banner.py            # Banner
├── colors.py            # 颜色
├── commands.py          # 斜杠命令
├── setup_wizard.py      # 设置向导
└── ...                  # 其他模块
```

**变更后：**
```
cli/
├── main.py              # 主入口（CLI + TUI 共用）
├── _parser.py          # 参数解析
│
├── commands/            # 🆕 CLI 命令系统
│   ├── __init__.py
│   ├── doctor.py        # 诊断检查
│   ├── logs.py          # 日志查看
│   ├── sessions.py      # 会话管理
│   ├── gateway.py       # Gateway 服务
│   └── ...
│
├── tui/                 # 🆕 TUI 渲染层
│   ├── __init__.py
│   ├── curses_ui.py     # Curses UI（现有代码移入）
│   ├── rich_panel.py    # Rich 面板
│   ├── theme_engine.py  # 主题引擎
│   └── layout_manager.py
│
├── components/          # 🆕 UI 组件
│   ├── __init__.py
│   ├── ui.py            # UI 组件（现有 ui.py 移入）
│   ├── banner.py        # Banner（现有代码移入）
│   ├── colors.py        # 颜色（现有代码移入）
│   ├── status.py        # 状态栏
│   └── spinner.py       # 加载动画
│
├── setup_wizard.py      # 设置向导（保持位置）
├── interactive_select.py # 交互选择（保持位置）
└── ...                  # 其他辅助模块
```

### 文件重命名映射

| 原路径 | 新路径 | 说明 |
|--------|--------|------|
| `cli/ui.py` | `cli/components/ui.py` | UI 组件 |
| `cli/banner.py` | `cli/components/banner.py` | Banner |
| `cli/colors.py` | `cli/components/colors.py` | 颜色定义 |
| `cli/curses_ui.py` | `cli/tui/curses_ui.py` | Curses TUI |
| `cli/status.py` | `cli/components/status.py` | 状态栏 |
| `cli/cli_output.py` | `cli/components/output.py` | 输出组件 |

### 导入路径更新

所有从 `cli/` 导入的模块需要更新为新的路径：
- `from cli.ui import ...` → `from cli.components.ui import ...`
- `from cli.curses_ui import ...` → `from cli.tui.curses_ui import ...`
- `from cli.banner import ...` → `from cli.components.banner import ...`

## Impact

### 影响的规格
- CLI 命令系统
- TUI 渲染系统

### 影响的代码
- `cli/main.py` - 导入路径更新
- `cli/_parser.py` - 无变化
- 所有使用 `cli.ui`, `cli.curses_ui`, `cli.banner` 等的模块

## ADDED Requirements

### Requirement: 目录结构规范化
系统 SHALL 提供清晰的目录结构，区分 CLI 命令系统和 TUI 渲染层。

### Requirement: 导入兼容性
重构后，原有导入路径需要在过渡期内保持兼容。

## MODIFIED Requirements

### Requirement: CLI 模块组织
原有 CLI 模块需要重新组织到 `commands/` 子目录。

## REMOVED Requirements

无

## 技术细节

### 1. 目录创建顺序
1. 创建 `cli/commands/` 目录
2. 创建 `cli/tui/` 目录
3. 创建 `cli/components/` 目录
4. 移动文件到新位置

### 2. 导入更新策略
使用 `__init__.py` 中的别名，保持向后兼容：
```python
# cli/components/__init__.py
from .ui import UI
from .banner import print_banner

# cli/tui/__init__.py
from .curses_ui import CursesUI
```

### 3. 迁移脚本
提供迁移脚本，帮助用户迁移自定义配置。