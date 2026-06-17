# TUI 布局优化规范

## Why

当前 TUI 界面存在边距不统一、层级嵌套过深的问题，导致：
1. 界面右边缘无法贴紧终端边缘
2. sidebar-toggle 折叠时仍占空间
3. 布局层级复杂，维护困难

## What Changes

### 1. 统一边距
- 关键区域设置 `margin: 0; padding: 0`
- 移除不必要的内边距

### 2. 简化层级
- 减少不必要的 Container 嵌套
- 优化 sidebar-toggle 折叠逻辑

### 3. 修复布局间隙
- sidebar-toggle 折叠时隐藏
- 确保各区域无缝贴合

## Impact

- Affected specs: TUI 布局结构
- Affected code: `cli/tui/textual_app.py`

## MODIFIED Requirements

### Requirement: Sidebar Toggle 折叠行为

系统 SHALL 在侧边栏折叠时同时隐藏 toggle 按钮。

#### Scenario: 折叠侧边栏
- **WHEN** 用户折叠侧边栏时
- **THEN** 侧边栏和 toggle 按钮同时隐藏，chat-area 扩展到右边

#### Scenario: 展开侧边栏
- **WHEN** 用户展开侧边栏时
- **THEN** 侧边栏和 toggle 按钮同时显示

### Requirement: 边距统一

系统 SHALL 统一关键区域的边距设置。

#### Scenario: 关键区域边距
- **WHEN** 渲染界面时
- **THEN** `#main-area`、`#chat-area` 等关键区域使用 `margin: 0; padding: 0`

### Requirement: 层级简化

系统 SHALL 减少不必要的 Container 嵌套。

#### Scenario: 层级结构
- **WHEN** 分析组件层级时
- **THEN** main-area 直接包含 chat-area、sidebar-toggle、sidebar-container，而非多层嵌套

## Technical Implementation

### 1. Toggle 折叠逻辑修改

```python
def _toggle_sidebar(self) -> None:
    sidebar = self.query_one("#sidebar-container", Container)
    toggle_btn = self.query_one("#sidebar-toggle", ClickableStatic)
    
    if sidebar.has_class("collapsed"):
        # 展开
        sidebar.remove_class("collapsed")
        toggle_btn.styles.display = "block"  # 显示 toggle
        toggle_btn.update("▶")
    else:
        # 折叠
        sidebar.add_class("collapsed")
        toggle_btn.styles.display = "none"   # 隐藏 toggle
        toggle_btn.update("◀")
```

### 2. 边距统一设置

```css
/* 统一关键区域边距 */
#main-area {
    margin: 0;
    padding: 0;
}

#chat-area {
    margin: 0;
    padding: 0;
}

#sidebar-container {
    margin: 0;
    padding: 0;
}

/* 移除 chat-log 的 padding */
#chat-log {
    padding: 0;
}
```

### 3. 层级优化

```python
# 优化后的 compose 结构
with Horizontal(id="main-area"):
    with VerticalScroll(id="chat-area"):
        yield RichLog(id="chat-log", auto_scroll=True)
    
    # toggle 折叠时隐藏
    yield ClickableStatic("▶", id="sidebar-toggle", markup=False)
    
    with Container(id="sidebar-container"):
        yield SidebarTabBar(...)
        yield SidebarContainer(...)
```

## Success Criteria

- [ ] sidebar-toggle 折叠时同时隐藏
- [ ] 关键区域边距统一为 0
- [ ] 界面右边缘贴合终端边缘
- [ ] 组件层级结构简化