# TUI 语义化颜色系统规范

## Why

当前 Handsome Agent 的 TUI 使用自定义颜色命名（如 `avocado-primary`、`avocado-bright`），这种方式：
1. 颜色含义不直观，需要记忆颜色对应的语义
2. 主题切换时需要大量修改颜色变量
3. 与 Frogmouth 等成熟 Textual 项目的设计风格不一致

Frogmouth 使用 Textual 内置的语义化颜色变量（`$panel`、`$accent`、`$text`、`$primary`、`$error` 等），让样式代码更易读、更易维护。

## What Changes

### 核心变更

1. **采用语义化颜色变量** - 使用 `$panel`、`$accent`、`$surface`、`$border` 等语义化命名
2. **保留 4 套主题** - 通过 Textual 的 `App.dark` 和 CSS 变量覆盖实现主题切换
3. **简化设计令牌** - 颜色令牌只定义语义化变量，主题色通过继承实现
4. **兼容现有功能** - 消息颜色、状态颜色等业务颜色保持不变

### 设计目标

参考 Frogmouth 的语义化颜色系统：
- 颜色变量语义清晰，一眼看出用途
- 主题切换简单，只需切换 `App.dark`
- CSS 代码更易读
- 与 Textual 框架设计理念一致

## Impact

- Affected specs: TUI 视觉体验、主题系统
- Affected code: `cli/tui/themes.py`, `cli/tui/textual_app.py`, `cli/tui/styles/base.css`

## ADDED Requirements

### Requirement: 语义化颜色变量系统

系统 SHALL 使用 Textual 内置的语义化颜色变量。

#### Scenario: 面板背景色
- **WHEN** 定义面板容器背景时
- **THEN** 使用 `$panel` 变量

#### Scenario: 强调色/焦点色
- **WHEN** 定义焦点边框或强调元素时
- **THEN** 使用 `$accent` 变量

#### Scenario: 主内容区背景
- **WHEN** 定义主内容区背景时
- **THEN** 使用 `$surface` 变量

#### Scenario: 边框颜色
- **WHEN** 定义普通边框时
- **THEN** 使用 `$border` 变量

#### Scenario: 主色调（对话框边框）
- **WHEN** 定义对话框或卡片边框时
- **THEN** 使用 `$primary` 变量

#### Scenario: 文字颜色
- **WHEN** 定义普通文字颜色时
- **THEN** 使用 `$text` 变量

#### Scenario: 次要文字颜色
- **WHEN** 定义次要/暗淡文字时
- **THEN** 使用 `$text-muted` 变量

### Requirement: 深色/浅色主题支持

系统 SHALL 通过 Textual 内置机制支持深色/浅色主题切换。

#### Scenario: 深色模式
- **WHEN** `App.dark = True` 时
- **THEN** Textual 自动应用深色主题颜色

#### Scenario: 浅色模式
- **WHEN** `App.dark = False` 时
- **THEN** Textual 自动应用浅色主题颜色

#### Scenario: 主题切换快捷键
- **WHEN** 用户按下主题切换快捷键时
- **THEN** 切换 `App.dark` 属性

### Requirement: 自定义主题色覆盖

系统 SHALL 支持在语义化变量基础上定义主题强调色。

#### Scenario: 牛油果绿主题
- **WHEN** 选择牛油果绿主题时
- **THEN** `$accent` 变量被覆盖为 `#8B9A46`

#### Scenario: 战争之神主题
- **WHEN** 选择战争之神主题时
- **THEN** `$accent` 变量被覆盖为 `#CD7F32`

#### Scenario: 单色主题
- **WHEN** 选择单色主题时
- **THEN** 所有颜色使用灰度值

#### Scenario: 酷蓝主题
- **WHEN** 选择酷蓝主题时
- **THEN** `$accent` 变量被覆盖为 `#607D8B`

### Requirement: 业务颜色保持不变

系统 SHALL 保持消息类型颜色和状态颜色的现有定义。

#### Scenario: 消息颜色
- **WHEN** 渲染用户/助手/系统消息时
- **THEN** 使用 `MESSAGE_COLORS` 中的固定颜色值

#### Scenario: 状态颜色
- **WHEN** 显示在线/忙碌/错误状态时
- **THEN** 使用 `STATUS_COLORS` 中的固定颜色值

## Technical Implementation

### 1. 语义化颜色变量定义 (base.css)

```css
/* 语义化颜色变量 - 兼容 Textual 内置变量 */
:root {
    /* 面板和容器 */
    --panel: $panel;           /* 继承 Textual 面板色 */
    --surface: $surface;       /* 继承 Textual 表面色 */
    --surface-raised: $boost;  /* 提升层背景 */

    /* 强调色 - 主题相关 */
    --accent: $accent;         /* 继承 Textual 强调色 */

    /* 边框 */
    --border: $border;         /* 普通边框 */
    --border-muted: $border-muted;  /* 暗淡边框 */

    /* 文字 */
    --text: $text;             /* 主文字 */
    --text-muted: $text-muted; /* 次要文字 */
}

/* 牛油果绿主题覆盖 */
.theme-avocado {
    --accent: #8B9A46;
    --accent-bright: #A0B45A;
    --accent-dim: #647030;
    --accent-dark: #465A1E;
}

/* 战争之神主题覆盖 */
.theme-ares {
    --accent: #CD7F32;
    --accent-bright: #E8A060;
    --accent-dim: #A06028;
    --accent-dark: #7A4520;
}

/* 单色主题覆盖 */
.theme-mono {
    --accent: #808080;
    --accent-bright: #A0A0A0;
    --accent-dim: #606060;
    --accent-dark: #404040;
}

/* 酷蓝主题覆盖 */
.theme-slate {
    --accent: #607D8B;
    --accent-bright: #78909C;
    --accent-dim: #455A64;
    --accent-dark: #37474F;
}
```

### 2. 主题配置 (themes.py)

```python
# 主题定义 - 语义化颜色配置
THEMES = {
    "avocado": ThemeConfig(
        name="Avocado Green",
        accent="#8B9A46",
        accent_bright="#A0B45A",
        accent_dim="#647030",
        accent_dark="#465A1E",
    ),
    "ares": ThemeConfig(
        name="War God",
        accent="#CD7F32",
        accent_bright="#E8A060",
        accent_dim="#A06028",
        accent_dark="#7A4520",
    ),
    "mono": ThemeConfig(
        name="Monochrome",
        accent="#808080",
        accent_bright="#A0A0A0",
        accent_dim="#606060",
        accent_dark="#404040",
    ),
    "slate": ThemeConfig(
        name="Cool Blue",
        accent="#607D8B",
        accent_bright="#78909C",
        accent_dim="#455A64",
        accent_dark="#37474F",
    ),
}

# 语义化颜色变量生成
def generate_semantic_colors(theme: ThemeConfig) -> dict[str, str]:
    """生成 CSS 语义化颜色变量"""
    return {
        "--accent": theme.accent,
        "--accent-bright": theme.accent_bright,
        "--accent-dim": theme.accent_dim,
        "--accent-dark": theme.accent_dark,
    }

# 生成主题 CSS
def generate_theme_css(theme_id: str) -> str:
    """生成主题 CSS，包含语义化颜色变量"""
    theme = THEMES.get(theme_id, THEMES["avocado"])
    colors = generate_semantic_colors(theme)
    css_parts = [f".theme-{theme_id} {{"]
    for var, value in colors.items():
        css_parts.append(f"    {var}: {value};")
    css_parts.append("}")
    return "\n".join(css_parts)
```

### 3. 简化后的组件 CSS

```css
/* 简化后的焦点样式 - 使用语义化变量 */
Input:focus,
TextArea:focus {
    border: heavy var(--accent);
}

Button:focus {
    border: heavy var(--accent);
    background: var(--accent) 20%;
}

/* 侧边栏 - 使用语义化变量 */
SidebarContainer {
    background: var(--panel);
    border-left: solid var(--border);
}

SidebarContainer:focus-within {
    border-left: heavy var(--accent);
}

/* 对话框 - 使用语义化变量 */
ApprovalDialog > Vertical {
    background: var(--surface-raised);
    border: round var(--primary);
}

ErrorDialog > Vertical {
    background: var(--error) 15%;
    border: thick var(--error) 50%;
}

/* 滚动条 - 使用语义化变量 */
ScrollbarThumb {
    background: var(--accent) 50%;
}

ScrollbarThumb:hover {
    background: var(--accent);
}
```

### 4. 消息颜色保持不变

```python
# 消息类型颜色 - 业务颜色，保持固定值
MESSAGE_COLORS = {
    "USER": "#58a6ff",
    "ASSISTANT": "#3fb950",
    "SYSTEM": "#8b949e",
    "TOOL": "#a371f7",
    "ERROR": "#f85149",
    "THINKING": "#f0883e",
    "APPROVAL": "#3fb950",
}

# 状态颜色 - 业务颜色，保持固定值
STATUS_COLORS = {
    "ONLINE": "#3fb950",
    "BUSY": "#f0883e",
    "ERROR": "#f85149",
}
```

### 5. 主题切换实现

```python
class HandsomeAgentApp(App):
    def __init__(self):
        super().__init__()
        self.theme_id = "avocado"  # 默认主题
        self.dark = True           # 默认深色模式

    def action_toggle_theme(self) -> None:
        """切换主题（主题色变化）"""
        themes = list(THEMES.keys())
        current_index = themes.index(self.theme_id)
        next_index = (current_index + 1) % len(themes)
        self.theme_id = themes[next_index]
        self.update_theme_css()

    def action_toggle_dark_mode(self) -> None:
        """切换深色/浅色模式"""
        self.dark = not self.dark

    def update_theme_css(self) -> None:
        """更新主题 CSS"""
        # 移除旧主题类
        for theme_id in THEMES:
            self.remove_class(f"theme-{theme_id}")
        # 添加新主题类
        self.add_class(f"theme-{self.theme_id}")
```

## Migration from Current Implementation

### 当前问题

1. 颜色变量命名复杂（`avocado-primary`、`avocado-bright` 等）
2. 需要手动管理大量颜色变量
3. 样式代码中直接使用十六进制颜色值
4. 与 Frogmouth 的设计风格不一致

### 迁移步骤

1. **定义语义化颜色变量**
   - 在 `base.css` 中定义 `--panel`、`--surface`、`--accent` 等变量
   - 继承 Textual 内置变量 `$panel`、`$surface`、`$accent` 等

2. **定义主题覆盖类**
   - 创建 `.theme-avocado`、`.theme-ares` 等类
   - 在这些类中覆盖 `--accent` 等变量

3. **更新组件 CSS**
   - 将硬编码颜色替换为语义化变量
   - 保持消息颜色和状态颜色的固定值

4. **简化 themes.py**
   - 保留 `THEMES` 配置
   - 移除大量 `AVOCADO_*` 颜色常量
   - 添加 `generate_semantic_colors()` 函数

5. **更新 textual_app.py**
   - 在 `on_mount()` 中添加默认主题类
   - 实现主题切换逻辑

## Success Criteria

- [ ] 语义化颜色变量（`$panel`、`$accent`、`$surface` 等）在 CSS 中使用
- [ ] 4 套主题通过类名切换（`.theme-avocado`、`.theme-ares` 等）
- [ ] 深色/浅色模式通过 `App.dark` 切换
- [ ] 消息颜色和状态颜色保持固定值
- [ ] CSS 代码更易读，语义清晰
- [ ] 主题切换功能正常工作
- [ ] 与 Frogmouth 的颜色系统风格一致