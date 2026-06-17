# TUI Frogmouth 风格优化规范

## Why

当前 Handsome-Agent 的 TUI 界面在视觉精致度上与 Frogmouth 存在差距。通过学习和借鉴 Frogmouth 的设计模式，可以显著提升界面的美观度和专业感。主要差距体现在：焦点样式过于复杂、缺少半透明层次、图标系统不完善、CSS 架构不够模块化，以及侧边栏面板实现不够优雅。

## What Changes

### 核心优化点

1. **焦点样式统一** - 采用 Frogmouth 的简洁 `border: heavy` 模式
2. **半透明层次系统** - 建立完整的透明度等级系统
3. **图标系统增强** - 为消息类型和功能添加 Emoji 图标
4. **CSS 模块化** - 将大型 CSS 拆分为可维护的模块
5. **颜色变量规范化** - 建立语义化的变量命名系统
6. **对话框轻量化** - 使用半透明边框和背景
7. **滚动条美化** - 使用 `scrollbar-gutter: stable`
8. **设计令牌系统** - 建立间距、圆角、边框等设计基础
9. **侧边栏 TabbedContent 化** - 使用 Textual 内置 TabbedContent 替代自定义 Button

### 设计目标

参考 Frogmouth 的精致设计，实现：
- 焦点指示清晰简洁
- 层次感通过透明度表达
- 信息通过图标快速识别
- CSS 代码可维护性强
- 视觉风格统一一致
- 侧边栏使用原生 Tab 组件

## Impact

- Affected specs: TUI 视觉体验、用户体验
- Affected code: `cli/tui/textual_app.py`, `cli/tui/themes.py`, `cli/tui/sidebar.py`, `cli/tui/widgets/`

## ADDED Requirements

### Requirement: 焦点样式统一

系统 SHALL 使用 Frogmouth 风格的简洁焦点样式。

#### Scenario: 焦点状态显示
- **WHEN** 输入框获得焦点时
- **THEN** 显示 `border: heavy $accent`，无其他复杂样式

#### Scenario: 侧边栏焦点状态
- **WHEN** 侧边栏获得焦点时
- **THEN** 显示左侧 `border-left: heavy $accent`

#### Scenario: 按钮焦点状态
- **WHEN** 按钮获得焦点时
- **THEN** 显示 `border: heavy $accent`，背景微变

### Requirement: 半透明层次系统

系统 SHALL 建立完整的半透明颜色系统。

#### Scenario: 10% 透明度 - 微交互反馈
- **WHEN** 需要微妙的悬停效果时
- **THEN** 使用 `$accent 10%` 或 `rgba(accent, 0.1)`

#### Scenario: 25% 透明度 - 选择状态
- **WHEN** 需要表示选中但非焦点时
- **THEN** 使用 `$accent 25%`

#### Scenario: 50% 透明度 - 次要强调
- **WHEN** 需要次要强调元素时
- **THEN** 使用 `$accent 50%`

#### Scenario: 错误/警告状态
- **WHEN** 显示错误对话框背景时
- **THEN** 使用 `$error 15%` 背景 + `$error 50%` 边框

### Requirement: 图标系统增强

系统 SHALL 为不同消息类型和功能添加 Emoji 图标。

#### Scenario: 消息类型图标
- **WHEN** 渲染用户消息时
- **THEN** 显示 `🧑` 图标

#### Scenario: 助手消息图标
- **WHEN** 渲染助手消息时
- **THEN** 显示 `🤖` 图标

#### Scenario: 系统消息图标
- **WHEN** 渲染系统消息时
- **THEN** 显示 `⚙️` 图标

#### Scenario: 工具执行图标
- **WHEN** 渲染工具执行消息时
- **THEN** 显示 `🔧` 图标

#### Scenario: 错误消息图标
- **WHEN** 渲染错误消息时
- **THEN** 显示 `❌` 图标

#### Scenario: 思考内容图标
- **WHEN** 渲染思考内容时
- **THEN** 显示 `💭` 图标

### Requirement: 消息 Rich Text 格式化

系统 SHALL 使用 Rich Text 丰富消息显示。

#### Scenario: 用户消息格式
- **WHEN** 渲染用户消息时
- **THEN** 使用 `Text.from_markup(f"🧑 [bold]{name}[/]\n{content}")`

#### Scenario: 助手消息格式
- **WHEN** 渲染助手消息时
- **THEN** 使用 `Text.from_markup(f"🤖 [bold]{name}[/]\n[dim]{timestamp}[/]\n{content}")`

#### Scenario: 带描述的选项列表
- **WHEN** 渲染命令面板选项时
- **THEN** 显示标题 + 描述 + 快捷键的完整信息

### Requirement: CSS 模块化架构

系统 SHALL 将 CSS 代码拆分为独立的模块文件。

#### Scenario: 基础样式模块
- **WHEN** 加载样式时
- **THEN** 先加载 `styles/base.css`（包含变量定义）

#### Scenario: 布局样式模块
- **WHEN** 加载样式时
- **THEN** 再加载 `styles/layout.css`（包含布局规则）

#### Scenario: 组件样式模块
- **WHEN** 加载样式时
- **THEN** 最后加载 `styles/components.css`（包含组件样式）

### Requirement: 滚动条美化

系统 SHALL 美化滚动条样式并稳定布局。

#### Scenario: 聊天区域滚动条
- **WHEN** 渲染聊天区域时
- **THEN** 设置 `scrollbar-gutter: stable; scrollbar-size: 1 8;`

#### Scenario: 侧边栏滚动条
- **WHEN** 渲染侧边栏面板时
- **THEN** 设置相同的滚动条样式

### Requirement: 设计令牌系统

系统 SHALL 建立基础设计令牌。

#### Scenario: 间距令牌
- **WHEN** 定义组件间距时
- **THEN** 使用 CSS 变量：`--space-xs: 2; --space-sm: 4; --space-md: 8; --space-lg: 16;`

#### Scenario: 圆角令牌
- **WHEN** 定义组件圆角时
- **THEN** 使用 CSS 变量：`--radius-sm: 2; --radius-md: 4; --radius-lg: 8;`

#### Scenario: 透明度令牌
- **WHEN** 定义透明度时
- **THEN** 使用 CSS 变量：`--opacity-subtle: 0.1; --opacity-muted: 0.25; --opacity-medium: 0.5;`

### Requirement: 侧边栏 TabbedContent 改造

系统 SHALL 使用 Textual 内置 TabbedContent 替代自定义 Button 实现。

#### Scenario: 面板组件继承
- **WHEN** 创建侧边栏面板时
- **THEN** 继承 `TabPane` 类

#### Scenario: 面板激活
- **WHEN** 需要切换到某个面板时
- **THEN** 设置 `TabbedContent.active = panel_id`

#### Scenario: Tab 组件使用
- **WHEN** 定义侧边栏 Tab 时
- **THEN** 使用 `TabbedContent` + `TabPane` 组合

#### Scenario: 焦点管理
- **WHEN** 侧边栏组件获得焦点时
- **THEN** 设置 `can_focus=False` + `can_focus_children=True`

#### Scenario: 键盘导航
- **WHEN** 用户按下左右方向键时
- **THEN** 自动切换到上一个/下一个 Tab

## Technical Implementation

### 1. 半透明颜色系统 (themes.py)

```python
# 扩展主题管理器
TRANSPARENCY_LEVELS = {
    "xs": 0.05,   # 极淡 - 背景微变
    "sm": 0.10,   # 淡 - 悬停效果
    "md": 0.15,   # 中 - 选择状态
    "lg": 0.25,   # 重 - 次要强调
    "xl": 0.50,   # 浓 - 焦点指示
}

# 半透明颜色生成
def transparent(color: str, opacity: float) -> str:
    """将颜色转换为 rgba 格式"""
    # 实现颜色到 rgba 的转换
    pass

# 应用示例
AVOCADO_ACCENT_10 = transparent(AVOCADO_PRIMARY, 0.10)
AVOCADO_ACCENT_25 = transparent(AVOCADO_PRIMARY, 0.25)
AVOCADO_ACCENT_50 = transparent(AVOCADO_PRIMARY, 0.50)
```

### 2. 焦点样式统一 (textual_app.py)

```python
DEFAULT_CSS = """
/* 统一的焦点样式 */
TextArea:focus,
Input:focus {
    border: heavy $accent;
}

.sidebar:focus {
    border-left: heavy $accent;
}

Button:focus {
    border: heavy $accent;
    background: $accent 20%;
}

/* 无焦点状态保持简洁 */
TextArea {
    border: blank;
}

Button {
    border: blank;
}
"""
```

### 3. 图标系统 (message_list.py)

```python
from rich.text import Text

# 消息类型图标映射
MESSAGE_ICONS = {
    "USER": "🧑",
    "ASSISTANT": "🤖",
    "SYSTEM": "⚙️",
    "TOOL": "🔧",
    "ERROR": "❌",
    "THINKING": "💭",
    "APPROVAL": "✅",
}

def format_message(self, message: Message) -> Text:
    icon = MESSAGE_ICONS.get(message.type, "💬")
    color = MESSAGE_COLORS.get(message.type, "#c9d1d9")
    return Text.from_markup(
        f"{icon} [bold {color}]{message.role}[/]  "
        f"[dim]{message.timestamp}[/]\n"
        f"{message.content}"
    )
```

### 4. CSS 模块化架构

```
cli/tui/
├── styles/
│   ├── __init__.py
│   ├── base.css          # 变量定义、基础重置
│   ├── layout.css        # 布局系统
│   ├── components.css    # 组件样式
│   └── animations.css    # 动画定义
└── textual_app.py
```

```python
# styles/__init__.py
def get_stylesheets() -> list[str]:
    """获取所有样式表文件路径"""
    return [
        "styles/base.css",
        "styles/layout.css",
        "styles/components.css",
        "styles/animations.css",
    ]

async def load_styles(self) -> None:
    """加载所有样式表"""
    for stylesheet in get_stylesheets():
        await self.add_stylesheet(stylesheet)
```

### 5. 滚动条美化 (layout.css)

```css
/* 稳定滚动条布局 */
.scroll-area {
    scrollbar-gutter: stable;
    scrollbar-size: 1 8;
}

/* 滚动条样式 */
ScrollbarThumb {
    background: $accent 50%;
    color: $accent;
}

ScrollbarThumb:hover {
    background: $accent;
}

ScrollbarTrack {
    background: $surface;
}
```

### 6. 对话框轻量化 (approval_dialog.py)

```python
DEFAULT_CSS = """
ApprovalDialog > Vertical {
    border: round $primary 50%;     # 半透明边框
    background: $boost;            # 提升背景
    width: 60%;
    max-height: 70%;
}

.risk-high {
    border: thick $error 50%;       # 红色半透明边框
    background: $error 15%;        # 红色淡背景
}
"""
```

### 7. 侧边栏 TabbedContent 实现

参考 frogmouth 的实现：

```python
# cli/tui/sidebar.py
from textual.widgets import TabbedContent, TabPane
from textual.widgets import Static, RichLog
from textual.containers import Vertical

class SidebarPane(TabPane):
    """侧边栏面板基类"""
    DEFAULT_CSS = """
    SidebarPane {
        padding: 1;
    }
    """

class TasksPane(SidebarPane):
    """任务面板"""
    pass

class FileTreePane(SidebarPane):
    """文件树面板"""
    pass

class AgentPane(SidebarPane):
    """Agent 面板"""
    pass

class LogsPane(SidebarPane):
    """日志面板"""
    pass

class SidebarContainer(Vertical):
    """侧边栏主容器"""
    DEFAULT_CSS = """
    SidebarContainer {
        width: 40;
        background: $panel;
        dock: right;
    }

    SidebarContainer Tabs {
        height: 3;
    }

    SidebarContainer TabPane {
        border: blank;
    }
    """

    def compose(self) -> ComposeResult:
        with TabbedContent(id="sidebar-tabs"):
            yield TasksPane("📋 任务", id="tasks")
            yield FileTreePane("📁 文件", id="file_tree")
            yield AgentPane("🤖 Agent", id="agent")
            yield LogsPane("📜 日志", id="logs")
```

### 8. 焦点管理

```python
class SidebarContainer(Vertical):
    can_focus = False
    can_focus_children = True

    BINDINGS = [
        Binding(",", "previous_tab", ""),
        Binding(".", "next_tab", ""),
    ]

    def action_previous_tab(self) -> None:
        self.query_one(Tabs).action_previous_tab()
        self.focus_active_pane()

    def action_next_tab(self) -> None:
        self.query_one(Tabs).action_next_tab()
        self.focus_active_pane()
```

## Migration from Current Implementation

### 当前问题

1. 焦点样式过于复杂（多种边框组合）
2. 缺少半透明效果系统
3. 消息显示缺少图标
4. CSS 代码集中在 3300+ 行文件
5. 颜色变量命名不够语义化
6. 滚动条没有统一处理
7. 侧边栏使用自定义 Button 而非原生 TabbedContent

### 迁移步骤

1. **扩展主题管理器**
   - 在 `themes.py` 中添加半透明颜色生成函数
   - 建立透明度等级常量

2. **统一焦点样式**
   - 简化所有组件的焦点 CSS
   - 使用 `border: heavy` 统一模式

3. **添加图标系统**
   - 在 `themes.py` 中定义消息类型图标
   - 在 `message_list.py` 中使用 Rich Text 格式化

4. **CSS 模块化**
   - 创建 `styles/` 目录
   - 拆分 CSS 到多个文件
   - 修改 `textual_app.py` 动态加载

5. **优化对话框**
   - 应用半透明边框
   - 使用 `border: round` 柔和风格

6. **美化滚动条**
   - 添加 `scrollbar-gutter: stable`
   - 统一样式定义

7. **侧边栏 TabbedContent 改造**
   - 创建 `SidebarPane` 基类继承 `TabPane`
   - 将每个面板改为继承 `SidebarPane`
   - 移除自定义 Button TabBar
   - 使用 `TabbedContent` 替代
   - 更新 CSS 样式适配 TabbedContent

## Success Criteria

- [ ] 焦点样式统一为 `border: heavy` 模式
- [ ] 建立完整的半透明层次系统
- [ ] 消息类型显示对应 Emoji 图标
- [ ] CSS 代码拆分为独立模块文件
- [ ] 颜色变量使用语义化命名
- [ ] 对话框使用轻量化半透明样式
- [ ] 滚动条使用 `scrollbar-gutter: stable`
- [ ] 建立间距、圆角等设计令牌
- [ ] 侧边栏使用 TabbedContent 替代自定义 Button
- [ ] Tab 支持键盘导航（←→切换）
- [ ] 整体视觉风格接近 Frogmouth
