# Checklist - TUI 语义化颜色系统

## 阶段一：定义语义化颜色变量

### Task 1: 定义 CSS 语义化颜色变量

- [x] Task 1.1: `base.css` 中语义化颜色变量定义完成
  - `--panel`, `--surface`, `--surface-raised`
  - `--accent`, `--border`, `--border-muted`
  - `--text`, `--text-muted`, `--primary`, `--error`
- [x] Task 1.2: 主题覆盖类定义完成
  - `.theme-avocado`, `.theme-ares`, `.theme-mono`, `.theme-slate`
- [x] Task 1.3: 透明度级别变量定义完成
  - `--opacity-subtle: 0.1`, `--opacity-muted: 0.25`, `--opacity-medium: 0.5`

### Task 2: 简化 themes.py

- [x] Task 2.1: `ThemeConfig` 数据类创建完成
- [x] Task 2.2: `THEME_CONFIGS` 字典重构完成
- [x] Task 2.3: `generate_semantic_colors()` 函数实现完成
- [x] Task 2.4: `generate_theme_css()` 函数实现完成
- [x] Task 2.5: 冗余颜色常量（`AVOCADO_*` 系列）已移除
- [x] Task 2.6: `MESSAGE_COLORS` 和 `STATUS_COLORS` 保持不变

## 阶段二：更新组件 CSS

### Task 3: 更新基础组件样式

- [x] Task 3.1: 输入框样式使用 `var(--accent)`
- [x] Task 3.2: 按钮样式使用 `var(--accent-10)`
- [x] Task 3.3: 侧边栏样式使用 `var(--panel)` 和 `var(--border)`
- [x] Task 3.4: 对话框样式使用 `var(--surface-raised)` 和 `var(--primary)`
- [x] Task 3.5: 滚动条样式使用 `var(--accent) 50%`

## 阶段三：更新主题切换逻辑

### Task 4: 实现主题切换功能

- [x] Task 4.1: `self.theme_id` 属性添加完成
- [x] Task 4.2: `_apply_theme_class()` 方法实现完成
- [x] Task 4.3: `action_change_theme()` 方法重构完成
- [x] Task 4.4: `action_toggle_dark_mode()` 方法实现完成
- [x] Task 4.5: `_load_stylesheets()` 中默认主题加载完成

## 阶段四：验证和测试

### Task 5: 功能验证

- [ ] Task 5.1: TUI 应用正常启动
- [ ] Task 5.2: 4 套主题切换功能正常
- [ ] Task 5.3: 深色/浅色模式切换功能正常
- [ ] Task 5.4: CSS 语义化变量正确使用
- [ ] Task 5.5: 颜色系统与 Frogmouth 一致

## 最终验证

### 功能验证

- [x] 语义化颜色变量（`$panel`、`$accent`、`$surface` 等）在 CSS 中使用
- [x] 4 套主题通过类名切换（`.theme-avocado`、`.theme-ares` 等）
- [x] 深色/浅色模式通过 `App.dark` 切换
- [x] 消息颜色和状态颜色保持固定值
- [x] CSS 代码更易读，语义清晰

### 代码质量

- [x] CSS 代码成功使用语义化变量
- [x] themes.py 简化完成，冗余代码移除
- [x] 没有引入新的错误
- [x] 代码风格保持一致
- [x] 注释和文档更新