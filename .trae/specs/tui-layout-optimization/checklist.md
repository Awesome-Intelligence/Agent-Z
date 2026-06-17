# Checklist

## 功能验证

- [x] 侧边栏折叠时 toggle 按钮同时隐藏
- [x] 侧边栏展开时 toggle 按钮同时显示
- [x] 侧边栏折叠后 chat-area 扩展到右边
- [x] 侧边栏展开后布局恢复正常

## 边距验证

- [x] `#main-area` 边距为 0
- [x] `#chat-area` 边距为 0
- [x] `#sidebar-container` 边距为 0
- [x] `#chat-log` 无额外 padding

## 界面贴合验证

- [x] 界面右边缘贴合终端边缘
- [x] 界面左边缘贴合终端边缘
- [x] 无多余的空白间隙

## 层级验证

- [x] compose 方法中没有不必要的 Container 嵌套
- [x] main-area 直接包含必要的子元素