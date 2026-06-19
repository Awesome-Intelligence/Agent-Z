# TUI 文件树交互功能增强规范

## Why

当前 Handsome-Agent 的 TUI 文件面板（FileTreePane）仅支持静态展示当前目录下的文件列表，无法展开子目录、选择文件或进行交互操作。通过参考 Frogmouth 的实现，可以实现类似 VS Code 侧边栏的可交互文件树，提升用户体验和工作效率。

## What Changes

### 核心功能

1. **可展开的文件树** - 支持文件夹的展开/折叠
2. **键盘导航** - 使用 ↑↓ 键选择文件/文件夹，回车键打开文件/展开文件夹
3. **鼠标交互** - 单击选择，双击打开文件/展开文件夹
4. **文件类型图标** - 根据文件类型显示对应图标
5. **当前目录高亮** - 清晰显示当前打开的文件所在目录

### 设计目标

参考 VS Code 和 Frogmouth 的文件树设计，实现：
- 清晰的层次结构（缩进表示层级）
- 直观的展开/折叠指示器（▶/▼）
- 文件/文件夹图标区分
- 当前文件高亮显示
- 键盘和鼠标双支持

## Impact

- Affected specs: TUI 侧边栏、文件面板交互
- Affected code: `cli/tui/sidebar.py`, `cli/tui/theming/icons.py`, `cli/tui/textual_app.py`

## ADDED Requirements

### Requirement: 可展开的文件树

系统 SHALL 提供支持展开/折叠的文件树组件。

#### Scenario: 目录展开
- **WHEN** 用户点击文件夹或按回车键在文件夹上
- **THEN** 加载该目录下的子项并显示
- **AND** 展开指示器从 `▶` 变为 `▼`

#### Scenario: 目录折叠
- **WHEN** 用户再次点击已展开的文件夹
- **THEN** 隐藏该目录下的子项
- **AND** 展开指示器从 `▼` 变回 `▶`

#### Scenario: 文件打开
- **WHEN** 用户双击文件或按回车键在文件上
- **THEN** 发送文件打开事件到主应用
- **AND** 高亮显示该文件

### Requirement: 键盘导航

系统 SHALL 支持完整的键盘导航。

#### Scenario: 上下选择
- **WHEN** 用户按 ↑ 键
- **THEN** 选中上一个可见项

- **WHEN** 用户按 ↓ 键
- **THEN** 选中下一个可见项

#### Scenario: 回车确认
- **WHEN** 当前选中项是文件夹且未展开
- **THEN** 展开该文件夹

- **WHEN** 当前选中项是文件夹且已展开
- **THEN** 折叠该文件夹

- **WHEN** 当前选中项是文件
- **THEN** 打开该文件

#### Scenario: 折叠所有
- **WHEN** 用户按 Home 键
- **THEN** 选中当前目录

- **WHEN** 用户按 Backspace 键
- **THEN** 如果当前在某子目录，则返回上级目录

### Requirement: 鼠标交互

系统 SHALL 支持鼠标操作。

#### Scenario: 单击选择
- **WHEN** 用户单击某项
- **THEN** 高亮该项并设置为当前选中

#### Scenario: 双击打开
- **WHEN** 用户双击文件夹
- **THEN** 展开/折叠该文件夹

- **WHEN** 用户双击文件
- **THEN** 打开该文件

### Requirement: 视觉样式

系统 SHALL 提供清晰的视觉反馈。

#### Scenario: 文件夹显示
- **WHEN** 渲染文件夹时
- **THEN** 显示展开指示器 + 文件夹图标 + 名称
- **AND** 使用青色 (cyan) 显示

#### Scenario: 文件显示
- **WHEN** 渲染文件时
- **THEN** 显示文件类型图标 + 文件名
- **AND** 根据文件类型使用对应颜色

#### Scenario: 选中状态
- **WHEN** 某项被选中时
- **THEN** 显示高亮背景色 ($accent 25%)
- **AND** 显示光标指示器 (▶)

#### Scenario: 展开指示器
- **WHEN** 文件夹未展开时
- **THEN** 显示 `▶` 字符

- **WHEN** 文件夹已展开时
- **THEN** 显示 `▼` 字符

#### Scenario: 层级缩进
- **WHEN** 渲染子目录项时
- **THEN** 每层缩进 2 个空格

### Requirement: 错误处理

系统 SHALL 优雅处理错误情况。

#### Scenario: 目录无法访问
- **WHEN** 尝试访问某个目录时发生权限错误
- **THEN** 显示 `[权限不足]` 提示
- **AND** 不崩溃，继续显示其他内容

#### Scenario: 空目录
- **WHEN** 目录为空时
- **THEN** 显示 `[空目录]` 提示

## Technical Implementation

### 1. 数据结构

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from enum import Enum

class NodeType(Enum):
    """节点类型"""
    FILE = "file"
    DIRECTORY = "directory"

@dataclass
class FileTreeNode:
    """文件树节点"""
    path: Path
    name: str
    node_type: NodeType
    expanded: bool = False
    children: list["FileTreeNode"] = None
    parent: Optional["FileTreeNode"] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []
```

### 2. FileTreePane 实现

```python
from textual.app import ComposeResult
from textual.widgets import Static, Tree
from textual.containers import Vertical
from textual.message import Message
from textual.events import Click

class FileTreePane(SidebarPane):
    """可交互的文件树面板"""

    class FileSelected(Message):
        """文件选中消息"""
        def __init__(self, path: Path) -> None:
            self.path = path
            super().__init__()

    def __init__(self, cwd: str = None) -> None:
        self._cwd = Path(cwd) if cwd else Path.cwd()
        self._root = self._build_tree_node(self._cwd)
        super().__init__(id="file_tree", title="📁 文件")

    def compose(self) -> ComposeResult:
        yield Tree("root", data=self._root)

    def _build_tree_node(self, path: Path, parent: FileTreeNode = None) -> FileTreeNode:
        """递归构建文件树节点"""
        node = FileTreeNode(
            path=path,
            name=path.name,
            node_type=NodeType.DIRECTORY if path.is_dir() else NodeType.FILE,
            parent=parent
        )

        if path.is_dir():
            try:
                items = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                for item in items:
                    if not item.name.startswith("."):  # 跳过隐藏文件
                        child = self._build_tree_node(item, node)
                        node.children.append(child)
            except PermissionError:
                pass  # 权限错误处理

        return node
```

### 3. 图标映射

```python
# 展开指示器
EXPAND_ICON = "▶"      # 未展开
COLLAPSE_ICON = "▼"    # 已展开

# 节点图标
FOLDER_ICON = "📁"
FILE_ICON = "📄"

# 颜色
FOLDER_COLOR = "cyan"
FILE_COLORS = {
    ".py": "green",
    ".md": "yellow",
    ".json": "magenta",
    # ...
}
```

### 4. 键盘绑定

```python
BINDINGS = [
    Binding("up", "cursor_up", "上"),
    Binding("down", "cursor_down", "下"),
    Binding("enter", "open_selected", "打开"),
    Binding("backspace", "go_up", "返回"),
    Binding("home", "go_root", "根目录"),
]
```

### 5. 事件处理

```python
def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
    """处理节点选中事件"""
    node = event.node.data
    if node.node_type == NodeType.FILE:
        self.post_message(self.FileSelected(node.path))

def action_toggle_expand(self) -> None:
    """切换展开/折叠状态"""
    selected = self.query_one(Tree).selected_node
    if selected and selected.data.node_type == NodeType.DIRECTORY:
        selected.toggle()
```

## Success Criteria

- [ ] 文件夹可以展开和折叠
- [ ] 文件可以通过双击或回车打开
- [ ] ↑↓ 键可以上下选择
- [ ] 当前选中项有高亮显示
- [ ] 展开指示器正确显示
- [ ] 文件类型图标正确显示
- [ ] 支持鼠标单击选择和双击打开
- [ ] 权限错误不会导致崩溃
- [ ] 整体体验接近 VS Code 文件树