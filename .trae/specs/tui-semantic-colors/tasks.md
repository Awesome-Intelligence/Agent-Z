# Tasks - TUI 语义化颜色系统

## 阶段一：定义语义化颜色变量

### Task 1: 定义 CSS 语义化颜色变量

- [x] Task 1.1: 在 `cli/tui/styles/base.css` 中定义语义化颜色变量
  - `--panel`: 面板背景色，继承 `$panel`
  - `--surface`: 表面背景色，继承 `$surface`
  - `--surface-raised`: 提升层背景，继承 `$boost`
  - `--accent`: 强调色，继承 `$accent`
  - `--border`: 普通边框色，继承 `$border`
  - `--border-muted`: 暗淡边框色，继承 `$border-muted`
  - `--text`: 主文字色，继承 `$text`
  - `--text-muted`: 次要文字色，继承 `$text-muted`
  - `--primary`: 主色调（对话框），继承 `$primary`
  - `--error`: 错误色，继承 `$error`

- [x] Task 1.2: 定义主题覆盖类
  - `.theme-avocado`: 牛油果绿主题
  - `.theme-ares`: 战争之神主题
  - `.theme-mono`: 单色主题
  - `.theme-slate`: 酷蓝主题

- [x] Task 1.3: 定义透明度级别变量
  - `--opacity-subtle: 0.1`
  - `--opacity-muted: 0.25`
  - `--opacity-medium: 0.5`

### Task 2: 简化 themes.py

- [x] Task 2.1: 创建 `ThemeConfig` 数据类
  - name: 主题显示名称
  - accent: 强调色
  - accent_bright: 亮强调色
  - accent_dim: 暗强调色
  - accent_dark: 最暗强调色

- [x] Task 2.2: 重构 `THEMES` 字典
  - 保留 4 套主题配置
  - 使用 `ThemeConfig` 实例

- [x] Task 2.3: 添加 `generate_semantic_colors()` 函数
  - 生成 CSS 语义化颜色变量字典

- [x] Task 2.4: 添加 `generate_theme_css()` 函数
  - 生成主题覆盖类 CSS 字符串

- [x] Task 2.5: 移除冗余颜色常量
  - 移除 `AVOCADO_PRIMARY`, `AVOCADO_BRIGHT`, `AVOCADO_DIM`, `AVOCADO_DARK`
  - 保留 `MESSAGE_COLORS` 和 `STATUS_COLORS`

## 阶段二：更新组件 CSS

### Task 3: 更新基础组件样式

- [x] Task 3.1: 更新输入框样式
  - 使用 `var(--accent)` 替代硬编码颜色
  - 焦点状态使用 `border: heavy var(--accent)`

- [x] Task 3.2: 更新按钮样式
  - 使用 `var(--accent)` 和 `var(--accent-10)`

- [x] Task 3.3: 更新侧边栏样式
  - 背景使用 `var(--panel)`
  - 边框使用 `var(--border)`
  - 焦点使用 `border-left: heavy var(--accent)`

- [x] Task 3.4: 更新对话框样式
  - 背景使用 `var(--surface-raised)` 或 `var(--error) 15%`
  - 边框使用 `var(--primary)` 或 `var(--error) 50%`

- [x] Task 3.5: 更新滚动条样式
  - 使用 `var(--accent) 50%` 和 `var(--accent)`

## 阶段三：更新主题切换逻辑

### Task 4: 实现主题切换功能

- [x] Task 4.1: 修改 `HandsomeAgentApp.__init__()`
  - 添加 `self.theme_id` 属性
  - 默认值为 "avocado"

- [x] Task 4.2: 实现 `_apply_theme_class()` 方法
  - 移除旧主题类
  - 添加新主题类

- [x] Task 4.3: 实现 `action_change_theme()` 方法
  - 循环切换主题
  - 调用 `_apply_theme_class()`

- [x] Task 4.4: 实现 `action_toggle_dark_mode()` 方法
  - 切换 `self.dark` 属性
  - 使用 Textual 内置深色/浅色模式

- [x] Task 4.5: 在 `_load_stylesheets()` 中加载默认主题
  - 添加 `theme-avocado` 类
  - 设置深色模式

## 阶段四：验证和测试

### Task 5: 功能验证

- [ ] Task 5.1: 启动 TUI 应用
  - 验证应用正常启动
  - 验证默认主题（牛油果绿）正常显示

- [ ] Task 5.2: 测试主题切换
  - 按 `Ctrl+Shift+T` 切换主题
  - 验证 4 套主题颜色正确应用

- [ ] Task 5.3: 测试深色/浅色模式切换
  - 按 `F10` 切换深色/浅色模式
  - 验证 Textual 内置颜色正确切换

- [ ] Task 5.4: 检查 CSS 语义化变量
  - 检查 `--panel`、`--accent` 等变量是否正确使用
  - 检查主题覆盖类是否正确定义

- [ ] Task 5.5: 对比 Frogmouth 颜色系统
  - 确认语义化变量命名一致
  - 确认主题切换机制一致

## Task Dependencies

### 依赖关系图

```
Task 1 (语义化颜色变量) ──→ Task 2 (简化 themes.py) ──→ Task 3 (更新组件样式)
                                                                          │
                                                                          ▼
                                                          Task 4 (主题切换功能)
                                                                          │
                                                                          ▼
                                                                   Task 5 (验证测试)
```

## 验证方式

- [ ] 运行 `python -m cli.main --textual` 启动 TUI
- [ ] 测试 4 套主题切换是否正常
- [ ] 测试深色/浅色模式切换是否正常
- [ ] 检查 CSS 代码中语义化变量的使用
- [ ] 对比 Frogmouth 的颜色系统设计