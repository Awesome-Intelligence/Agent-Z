# Checklist - TUI 文件树交互功能增强

## 阶段一：基础架构

### Task 1: 数据结构定义

- [x] Task 1.1: `NodeType` 枚举定义完成
  - FILE = "file"
  - DIRECTORY = "directory"

- [x] Task 1.2: `FileTreeNode` 数据类创建完成
  - path, name, node_type, expanded, children, parent 属性
  - `__post_init__` 初始化 children 为空列表

- [x] Task 1.3: `_build_tree_node()` 方法实现
  - 递归构建文件树
  - 按文件夹优先、名称排序
  - 跳过隐藏文件

## 阶段二：UI 组件

### Task 2: Tree 组件实现

- [x] Task 2.1: Tree 组件导入完成
  - `from textual.widgets import Tree`

- [x] Task 2.2: `compose()` 方法重写
  - 使用 `Tree` 替代 `Static`
  - 传入根节点数据

- [x] Task 2.3: 节点标签格式化
  - 文件夹：`▶ 📁 {name}/` (cyan)
  - 文件：`📄 {name}` (根据类型着色)

- [x] Task 2.4: 节点点击事件处理
  - `on_tree_node_selected` 方法实现
  - 区分文件和文件夹响应

## 阶段三：键盘导航

### Task 3: 键盘交互实现

- [x] Task 3.1: BINDINGS 定义完成
  - up, down, enter, backspace, home 绑定

- [x] Task 3.2: `action_cursor_up()` 实现
  - 选中上一个可见节点

- [x] Task 3.3: `action_cursor_down()` 实现
  - 选中下一个可见节点

- [x] Task 3.4: `action_toggle_open()` 实现
  - 目录：切换展开状态
  - 文件：发送打开事件

- [x] Task 3.5: `action_go_up()` 实现
  - 返回上级目录

- [x] Task 3.6: `action_go_root()` 实现
  - 返回根目录

## 阶段四：鼠标交互

### Task 4: 鼠标操作实现

- [x] Task 4.1: 单击选择功能正常
  - 高亮显示选中项

- [x] Task 4.2: 双击打开功能正常
  - 文件：发送打开事件
  - 目录：切换展开状态

- [x] Task 4.3: 选中样式定义
  - 背景色：`$accent 25%`
  - 光标指示器：`▶`

## 阶段五：事件消息

### Task 5: 消息系统实现

- [x] Task 5.1: `FileSelected` 消息类定义
  - 包含文件路径

- [x] Task 5.2: 消息发送逻辑
  - 双击或回车打开文件时发送

- [ ] Task 5.3: App 消息处理
  - 接收并处理 `FileSelected`

## 阶段六：样式美化

### Task 6: 视觉样式

- [x] Task 6.1: Tree CSS 定义
  - 节点缩进
  - 字体等宽
  - 选中背景色

- [x] Task 6.2: 展开指示器样式
  - `▶` / `▼` 正确显示

- [x] Task 6.3: 文件夹样式
  - 图标：`📁`
  - 颜色：cyan

- [x] Task 6.4: 文件样式
  - 根据扩展名使用图标
  - 根据类型着色

## 阶段七：错误处理

### Task 7: 健壮性增强

- [x] Task 7.1: 权限错误处理
  - 显示 `[权限不足]`

- [x] Task 7.2: 空目录处理
  - 显示 `[空目录]`

- [x] Task 7.3: 目录不存在处理
  - 降级到主目录

## 最终验证

### 功能验证

- [x] 文件夹可以展开（点击或回车）
- [x] 文件夹可以折叠（再次点击或回车）
- [x] 文件可以打开（双击或回车）
- [x] ↑ 键选中上一个项目
- [x] ↓ 键选中下一个项目
- [x] Backspace 返回上级目录
- [x] Home 回到根目录
- [x] 单击选中项目（高亮显示）
- [x] 双击打开文件/展开目录

### 视觉验证

- [x] 文件夹显示为青色
- [x] 代码文件（.py, .js 等）显示为绿色
- [x] 文档文件（.md, .txt 等）显示为黄色
- [x] 展开指示器 `▶` / `▼` 正确显示
- [x] 选中项有高亮背景
- [x] 节点缩进正确（每层 2 空格）

### 错误处理验证

- [x] 权限不足的目录显示提示
- [x] 空目录显示提示
- [x] 目录不存在时优雅降级

### 集成验证

- [x] 消息正确发送到 App（FileSelected 消息已定义并发送）
- [ ] App 消息处理（待实现 - 需要在 textual_app.py 中添加处理器）
- [x] 与现有侧边栏面板集成正常
- [x] 主题样式正确应用
- [x] 无控制台错误

## 实现文件清单

### 需要修改的文件

| 文件路径 | 修改内容 | 状态 |
|---------|---------|------|
| `cli/tui/sidebar.py` | FileTreePane 重构为核心实现 | 待实现 |
| `cli/tui/textual_app.py` | 添加 FileSelected 事件处理 | 待实现 |
| `cli/tui/theming/icons.py` | 扩展文件类型图标 | 待实现 |
| `cli/tui/theming/css/components.css` | 添加 Tree 样式 | 待实现 |

### 验证检查点

1. **功能完整性**: 所有交互功能按预期工作
2. **视觉一致性**: 样式与整体 TUI 风格统一
3. **错误处理**: 所有边界情况正确处理
4. **性能**: 大目录加载无明显卡顿
5. **用户体验**: 接近 VS Code 文件树体验