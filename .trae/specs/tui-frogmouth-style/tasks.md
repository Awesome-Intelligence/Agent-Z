# Tasks - TUI Frogmouth 风格优化

## 阶段一：基础系统（半透明和设计令牌）

### Task 1: 扩展主题管理器 - 添加半透明颜色系统

- [x] Task 1.1: 在 `themes.py` 中添加透明度等级常量
  - `TRANSPARENCY_LEVELS` 字典：xs=0.05, sm=0.10, md=0.15, lg=0.25, xl=0.50

- [x] Task 1.2: 实现 `transparent()` 函数 - 将颜色转换为 rgba 格式
  - 支持 hex 颜色格式转换
  - 支持 opacity 参数

- [x] Task 1.3: 生成半透明颜色变量
  - `AVOCADO_ACCENT_10`, `AVOCADO_ACCENT_25`, `AVOCADO_ACCENT_50`
  - 状态色透明版本：`_ONLINE`, `_BUSY`, `_ERROR` 等

### Task 2: 建立设计令牌系统

- [x] Task 2.1: 创建 `styles/base.css` 文件
  - 定义 CSS 变量：`--space-xs: 2; --space-sm: 4; --space-md: 8; --space-lg: 16; --space-xl: 24;`
  - 定义圆角令牌：`--radius-sm: 2; --radius-md: 4; --radius-lg: 8;`
  - 定义透明度令牌：`--opacity-subtle: 0.1; --opacity-muted: 0.25; --opacity-medium: 0.5;`
  - 定义边框宽度：`--border-width: 1; --border-width-thick: 2; --border-width-heavy: 3;`

- [x] Task 2.2: 在 `themes.py` 中导出令牌常量供 Python 代码使用

## 阶段二：样式优化（焦点和对话框）

### Task 3: 统一焦点样式

- [x] Task 3.1: 简化 `textual_app.py` 中的焦点 CSS
  - 移除复杂的焦点边框组合
  - 统一使用 `border: heavy $accent` 模式

- [x] Task 3.2: 为侧边栏定义焦点样式
  - `border-left: heavy $accent`（左侧指示器）

- [x] Task 3.3: 为按钮定义焦点样式
  - `border: heavy $accent; background: $accent 20%;`

- [x] Task 3.4: 定义无焦点状态
  - 所有可聚焦元素默认 `border: blank`

### Task 4: 美化对话框样式

- [x] Task 4.1: 修改审批对话框 CSS
  - 使用 `border: round $primary 50%`
  - 使用 `background: $boost`

- [x] Task 4.2: 修改错误对话框 CSS
  - `background: $error 15%`
  - `border: thick $error 50%`

- [x] Task 4.3: 为风险等级定义半透明背景
  - HIGH: `$error 15%`
  - MEDIUM: `$warning 10%`
  - LOW: `$success 10%`

## 阶段三：图标系统

### Task 5: 添加消息类型图标

- [x] Task 5.1: 在 `themes.py` 中定义 `MESSAGE_ICONS` 字典
  - USER: `🧑`, ASSISTANT: `🤖`, SYSTEM: `⚙️`, TOOL: `🔧`, ERROR: `❌`, THINKING: `💭`, APPROVAL: `✅`

- [x] Task 5.2: 在 `themes.py` 中定义 `MESSAGE_COLORS` 字典
  - 每个消息类型对应的颜色

- [x] Task 5.3: 修改 `message_list.py` 的消息格式化方法
  - 使用 `Text.from_markup()` 创建 Rich Text
  - 格式：`{icon} [bold {color}]{role}[/]  [dim]{timestamp}[/]\n{content}`

### Task 6: 添加功能图标到侧边栏面板

- [x] Task 6.1: 为文件树添加文件类型图标
  - Python: `🐍`, JavaScript: `📜`, Markdown: `📝`, JSON: `📋`, 其他: `📄`

- [x] Task 6.2: 为任务列表添加状态图标
  - 待办: `📋`, 进行中: `🔄`, 完成: `✅`, 失败: `❌`

- [x] Task 6.3: 为日志面板添加级别图标
  - INFO: `ℹ️`, WARNING: `⚠️`, ERROR: `❌`, DEBUG: `🐛`

## 阶段四：CSS 模块化

### Task 7: 创建 CSS 模块架构

- [x] Task 7.1: 创建 `styles/` 目录和 `__init__.py`
  - 实现 `get_stylesheets()` 函数返回所有样式文件
  - 实现 `load_styles()` 异步加载函数

- [x] Task 7.2: 创建 `styles/base.css` - 变量和基础
  - 颜色变量定义
  - 间距令牌
  - 圆角令牌
  - 透明度令牌
  - 基础重置样式

- [x] Task 7.3: 创建 `styles/layout.css` - 布局规则
  - 滚动条样式：`scrollbar-gutter: stable; scrollbar-size: 1 8;`
  - 主布局样式
  - Flexbox 布局类

- [x] Task 7.4: 创建 `styles/components.css` - 组件样式
  - 从 `textual_app.py` 提取组件 CSS
  - 按钮、输入框、面板等

- [x] Task 7.5: 创建 `styles/animations.css` - 动画定义
  - `.streaming-indicator` 闪烁动画
  - `.thinking-indicator` 旋转动画

### Task 8: 重构 textual_app.py

- [x] Task 8.1: 移除内联 CSS（约 730-1260 行）
  - 将其拆分到对应的 CSS 模块文件

- [x] Task 8.2: 在 `on_mount()` 中调用 `load_styles()`
  - 动态加载所有 CSS 模块

- [x] Task 8.3: 更新注释说明 CSS 架构

## 阶段五：滚动条美化

### Task 9: 美化所有滚动区域

- [x] Task 9.1: 为聊天区域添加滚动条样式
  - `scrollbar-gutter: stable`
  - `scrollbar-size: 1 8`

- [x] Task 9.2: 为侧边栏面板添加滚动条样式
  - 保持与聊天区域一致

- [x] Task 9.3: 定义滚动条颜色
  - Thumb: `$accent 50%`
  - Track: `$surface`

## 阶段六：侧边栏 TabbedContent 改造

### Task 10: 重构侧边栏为 TabbedContent

- [x] Task 10.1: 创建 `SidebarPane` 基类
  - 继承 `TabPane` 类
  - 定义基础 CSS 样式

- [x] Task 10.2: 创建各个面板类
  - `TasksPane` - 任务面板
  - `FileTreePane` - 文件树面板
  - `AgentPane` - Agent 面板
  - `LogsPane` - 日志面板

- [x] Task 10.3: 重构 `SidebarContainer`
  - 使用 `TabbedContent` 替代自定义面板切换逻辑
  - 移除 `SidebarTabBar` 类
  - 更新 `compose()` 方法

- [x] Task 10.4: 添加 Tab 焦点管理
  - 设置 `can_focus=False`
  - 设置 `can_focus_children=True`
  - 定义键盘快捷键绑定

- [x] Task 10.5: 更新 CSS 样式适配 TabbedContent
  - 移除旧的 `.sidebar-tab` 样式
  - 添加 `Tabs` 和 `TabPane` 样式
  - 定义 Tab 激活状态样式

- [x] Task 10.6: 更新 `textual_app.py` 中的面板切换逻辑
  - 修改 `_on_sidebar_panel_switch` 方法
  - 修改各个面板快捷键绑定

- [x] Task 10.7: 测试 Tab 切换功能
  - 测试鼠标点击切换
  - 测试键盘导航（←→）
  - 测试焦点管理

## Task Dependencies

### 依赖关系图

```
Task 1 (半透明系统) ──┬── Task 2 (设计令牌) ──┬── Task 3 (焦点样式)
     │                      │                    │
     │                      │                    ▼
     │                      │            Task 4 (对话框)
     │                      │
     ▼                      ▼
Task 5 (消息图标) ────── Task 6 (功能图标)
          │
          ▼
Task 7 (CSS模块化) ──── Task 8 (重构)
          │
          ▼
Task 9 (滚动条美化)
          │
          ▼
Task 10 (TabbedContent改造)
```

### 并行执行建议

- **第一波并行**: Task 1, 2, 3 可以并行开发（已完成）
- **第二波并行**: Task 4, 5, 6 在 Task 1 完成后并行（已完成）
- **第三波并行**: Task 7, 8, 9 在 Task 1, 2 完成后并行（已完成）
- **第四波**: Task 10 单独执行，依赖 Task 8 完成的 CSS 模块化

## 验证方式

- [ ] 运行 `python -m cli.main --textual` 启动 TUI
- [ ] 测试焦点切换时的样式变化
- [ ] 测试消息显示是否包含图标
- [ ] 测试对话框的半透明效果
- [ ] 检查 CSS 文件是否正确加载
- [ ] 测试滚动条样式是否统一
- [ ] 测试侧边栏 Tab 切换功能
- [ ] 测试 Tab 键盘导航
- [ ] 对比 Frogmouth 的视觉效果
