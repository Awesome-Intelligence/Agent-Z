# Checklist - TUI Frogmouth 风格优化

## 阶段一：基础系统

### Task 1: 半透明颜色系统

- [x] Task 1.1: `TRANSPARENCY_LEVELS` 字典定义完成
- [x] Task 1.2: `transparent()` 函数实现并测试
- [x] Task 1.3: 半透明颜色变量生成完成

### Task 2: 设计令牌系统

- [x] Task 2.1: `styles/base.css` 文件创建完成
- [x] Task 2.2: 令牌常量在 `themes.py` 中导出

## 阶段二：样式优化

### Task 3: 焦点样式统一

- [x] Task 3.1: `textual_app.py` 焦点 CSS 简化
- [x] Task 3.2: 侧边栏焦点样式定义
- [x] Task 3.3: 按钮焦点样式定义
- [x] Task 3.4: 无焦点状态 `border: blank` 定义

### Task 4: 对话框样式美化

- [x] Task 4.1: 审批对话框半透明边框
- [x] Task 4.2: 错误对话框半透明背景
- [x] Task 4.3: 风险等级颜色定义

## 阶段三：图标系统

### Task 5: 消息类型图标

- [x] Task 5.1: `MESSAGE_ICONS` 字典定义
- [x] Task 5.2: `MESSAGE_COLORS` 字典定义
- [x] Task 5.3: `message_list.py` 格式化方法更新

### Task 6: 功能图标

- [x] Task 6.1: 文件类型图标定义
- [x] Task 6.2: 任务状态图标定义
- [x] Task 6.3: 日志级别图标定义

## 阶段四：CSS 模块化

### Task 7: CSS 模块架构

- [x] Task 7.1: `styles/__init__.py` 创建完成
- [x] Task 7.2: `styles/base.css` 创建完成
- [x] Task 7.3: `styles/layout.css` 创建完成
- [x] Task 7.4: `styles/components.css` 创建完成
- [x] Task 7.5: `styles/animations.css` 创建完成

### Task 8: 重构 textual_app.py

- [x] Task 8.1: 内联 CSS 移除完成
- [x] Task 8.2: 动态加载 CSS 模块
- [x] Task 8.3: 注释更新完成

## 阶段五：滚动条美化

### Task 9: 滚动条样式

- [x] Task 9.1: 聊天区域滚动条美化
- [x] Task 9.2: 侧边栏滚动条美化
- [x] Task 9.3: 滚动条颜色统一定义

## 阶段六：侧边栏 TabbedContent 改造

### Task 10: 重构侧边栏为 TabbedContent

- [x] Task 10.1: `SidebarPane` 基类创建完成
- [x] Task 10.2: 各面板类创建完成（TasksPane, FileTreePane, AgentPane, LogsPane）
- [x] Task 10.3: `SidebarContainer` 使用 `TabbedContent` 替代
- [x] Task 10.4: Tab 焦点管理添加完成
- [x] Task 10.5: CSS 样式适配 TabbedContent
- [x] Task 10.6: `textual_app.py` 面板切换逻辑更新
- [x] Task 10.7: Tab 切换功能测试通过

## 最终验证

### 功能验证

- [x] TUI 应用可以正常启动
- [x] 焦点样式显示正确（简洁的 `border: heavy`）
- [x] 半透明效果显示正确
- [x] 消息显示包含正确的 Emoji 图标
- [x] 对话框显示轻量化半透明样式
- [x] CSS 模块正确加载
- [x] 滚动条样式统一且稳定
- [x] 侧边栏 Tab 切换功能正常
- [x] Tab 键盘导航（←→）功能正常

### 视觉对比

- [x] 焦点指示器与 Frogmouth 风格一致
- [x] 半透明层次与 Frogmouth 风格一致
- [x] 整体视觉效果接近 Frogmouth
- [x] 界面更加精致美观
- [x] 侧边栏 Tab 样式与 Frogmouth 一致

### 代码质量

- [x] CSS 代码成功拆分为多个模块
- [x] 没有引入新的错误
- [x] 代码风格保持一致
- [x] 注释和文档更新
- [x] 侧边栏重构代码质量检查通过

## 实现文件清单

### 核心实现文件

| 文件路径 | 功能说明 | 状态 |
|---------|---------|------|
| `cli/tui/theming/colors.py` | 半透明颜色系统 | ✅ |
| `cli/tui/theming/icons.py` | 图标系统 | ✅ |
| `cli/tui/theming/css/__init__.py` | CSS 模块加载器 | ✅ |
| `cli/tui/theming/css/base.css` | 基础样式和设计令牌 | ✅ |
| `cli/tui/theming/css/layout.css` | 布局规则 | ✅ |
| `cli/tui/theming/css/components.css` | 组件样式 | ✅ |
| `cli/tui/theming/css/animations.css` | 动画定义 | ✅ |
| `cli/tui/sidebar.py` | 侧边栏 TabbedContent 实现 | ✅ |

### 已验证的实现细节

1. **半透明颜色系统** (`colors.py`):
   - `TRANSPARENCY_LEVELS` 字典定义完成（xs=0.05, sm=0.10, md=0.15, lg=0.25, xl=0.50）
   - `transparent()` 函数支持 hex 到 rgba 转换
   - 状态颜色常量定义完成

2. **图标系统** (`icons.py`):
   - `MESSAGE_ICONS` 定义 7 种消息类型图标
   - `MESSAGE_COLORS` 定义对应颜色
   - `FILE_TYPE_ICONS` 定义 60+ 文件类型图标
   - `TASK_STATUS_ICONS` 定义任务状态图标
   - `LOG_LEVEL_ICONS` 定义日志级别图标
   - `AGENT_STATUS_ICONS` 定义 Agent 状态图标
   - `PANEL_ICONS` 定义面板图标

3. **CSS 模块化** (`css/`):
   - `get_stylesheets()` 返回 4 个 CSS 文件路径
   - `get_theme_css()` 支持主题加载
   - base.css 定义完整的设计令牌系统
   - components.css 定义焦点样式（`border: heavy $accent`）

4. **侧边栏实现** (`sidebar.py`):
   - `SidebarPane` 基类继承 `TabPane`
   - `TasksPane`, `FileTreePane`, `AgentPane`, `LogsPane` 四个面板
   - `SidebarContainer` 使用 `TabbedContent` + `TabPane`
   - Tab 键盘导航绑定（ctrl+left, ctrl+right）
   - `switch_to_panel()` 方法用于面板切换

### 验证通过的功能

- ✅ 半透明颜色生成函数正常工作
- ✅ 图标系统覆盖消息、文件、任务、日志、Agent 等场景
- ✅ CSS 模块按正确顺序加载（base → layout → components → animations）
- ✅ 焦点样式统一使用 `border: heavy $accent` 模式
- ✅ 侧边栏 Tab 切换功能正常
- ✅ Tab 键盘导航（ctrl+←/→）功能正常
- ✅ 主题 CSS 文件可正确加载