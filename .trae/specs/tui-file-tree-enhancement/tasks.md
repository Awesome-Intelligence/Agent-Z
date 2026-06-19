# Tasks - TUI 文件树交互功能增强

## 阶段一：基础架构

### Task 1: 创建文件树节点数据结构

- [x] Task 1.1: 在 `sidebar.py` 中定义 `NodeType` 枚举
  - FILE = "file"
  - DIRECTORY = "directory"

- [x] Task 1.2: 创建 `FileTreeNode` 数据类
  - path: Path 对象
  - name: 文件/文件夹名称
  - node_type: NodeType 枚举
  - expanded: 是否展开（仅目录）
  - children: 子节点列表
  - parent: 父节点引用

- [x] Task 1.3: 实现 `_build_tree_node()` 方法
  - 递归构建文件树
  - 按文件夹优先、名称排序
  - 跳过隐藏文件（以 `.` 开头）

## 阶段二：UI 组件实现

### Task 2: 重构 FileTreePane 使用 Tree 组件

- [x] Task 2.1: 修改 FileTreePane 导入 Tree 组件
  - `from textual.widgets import Tree`

- [x] Task 2.2: 重写 `compose()` 方法
  - 使用 `Tree` 替代 `Static`
  - 传入根节点数据

- [x] Task 2.3: 定义 Tree 节点标签格式化
  - 文件夹：`▶ 📁 {name}/` (cyan)
  - 文件：`📄 {name}` (根据类型着色)

- [x] Task 2.4: 添加节点点击事件处理
  - 处理 `Tree.NodeSelected` 事件
  - 区分文件和文件夹的响应

## 阶段三：键盘导航

### Task 3: 实现键盘交互

- [x] Task 3.1: 定义键盘快捷键绑定
  - ↑: cursor_up (上移)
  - ↓: cursor_down (下移)
  - Enter: toggle_open (展开/折叠/打开)
  - Backspace: go_up (返回上级)
  - Home: go_root (回到根目录)

- [x] Task 3.2: 实现 `action_cursor_up()` 方法
  - 获取当前选中节点
  - 选中上一个可见节点

- [x] Task 3.3: 实现 `action_cursor_down()` 方法
  - 获取当前选中节点
  - 选中下一个可见节点

- [x] Task 3.4: 实现 `action_toggle_open()` 方法
  - 如果是目录：切换展开状态
  - 如果是文件：发送打开事件

- [x] Task 3.5: 实现 `action_go_up()` 方法
  - 如果当前在子目录，返回上级目录
  - 选中对应节点

- [x] Task 3.6: 实现 `action_go_root()` 方法
  - 返回根目录
  - 选中根节点

## 阶段四：鼠标交互

### Task 4: 实现鼠标操作

- [x] Task 4.1: 处理单击选择
  - Textual Tree 组件默认支持
  - 确保样式正确（高亮）

- [x] Task 4.2: 处理双击打开
  - 在 `on_tree_node_selected` 中判断双击
  - 双击文件：发送打开事件
  - 双击目录：切换展开状态

- [x] Task 4.3: 定义选中样式
  - 背景色：`$accent 25%`
  - 光标指示器：`▶`

## 阶段五：事件和消息

### Task 5: 定义文件选择消息

- [x] Task 5.1: 创建 `FileSelected` 消息类
  - 继承 `Message`
  - 包含文件路径

- [x] Task 5.2: 在 FileTreePane 中发送消息
  - 双击或回车打开文件时
  - `self.post_message(FileSelected(path))`

- [ ] Task 5.3: 在 App 中处理消息
  - 接收 `FileSelected` 事件
  - 调用文件打开逻辑

## 阶段六：样式美化

### Task 6: 美化文件树样式

- [x] Task 6.1: 定义 Tree 组件 CSS
  - 节点缩进：每层 2 个空格
  - 字体等宽
  - 选中背景色

- [x] Task 6.2: 添加展开指示器样式
  - 未展开：`▶` 青色
  - 已展开：`▼` 青色

- [x] Task 6.3: 文件夹样式
  - 图标：`📁`
  - 颜色：cyan

- [x] Task 6.4: 文件样式
  - 根据扩展名使用对应图标
  - 根据类型着色（代码文件绿色、文档黄色等）

## 阶段七：错误处理

### Task 7: 增强健壮性

- [x] Task 7.1: 处理权限错误
  - 捕获 `PermissionError`
  - 显示 `[权限不足]` 占位符

- [x] Task 7.2: 处理空目录
  - 检测无子项的目录
  - 显示 `[空目录]` 占位符

- [x] Task 7.3: 处理目录不存在
  - 捕获 `FileNotFoundError`
  - 优雅降级到用户主目录

## Task Dependencies

### 依赖关系图

```
Task 1 (数据结构) ──┬── Task 2 (UI组件)
     │                    │
     │                    ▼
     │            Task 3 (键盘导航)
     │                    │
     │                    ▼
     │            Task 4 (鼠标交互)
     │                    │
     ▼                    ▼
Task 5 (事件消息) ──→ Task 6 (样式美化)
                            │
                            ▼
                    Task 7 (错误处理)
```

### 并行执行建议

- **第一波**: Task 1 可以独立开发
- **第二波**: Task 2, 3, 4 依赖 Task 1，可以并行开发
- **第三波**: Task 5 依赖 Task 2, 3, 4
- **第四波**: Task 6, 7 可以并行开发

## 验证方式

- [ ] 运行 `python -m cli.main --textual` 启动 TUI
- [ ] 测试文件夹展开/折叠功能
- [ ] 测试键盘导航（↑↓ Enter Backspace Home）
- [ ] 测试鼠标单击选择和双击打开
- [ ] 检查文件类型图标是否正确
- [ ] 检查颜色是否按类型区分
- [ ] 测试权限错误处理
- [ ] 对比 VS Code 文件树体验