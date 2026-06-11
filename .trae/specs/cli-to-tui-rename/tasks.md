# Tasks - CLI 目录重构为 TUI

## 阶段 1：目录结构创建

- [x] Task 1.1: 创建 `cli/cli_commands/` 目录结构
  - [x] 创建 `cli/cli_commands/__init__.py`
  - [x] 创建 `cli/cli_commands/doctor.py` - 诊断检查命令（基础版本）
  - [x] 创建 `cli/cli_commands/sessions.py` - 会话管理命令（基础版本）

- [x] Task 1.2: 创建 `cli/tui/` 目录结构
  - [x] 创建 `cli/tui/__init__.py`
  - [x] 移动 `cli/curses_ui.py` → `cli/tui/curses_ui.py`

- [x] Task 1.3: 创建 `cli/components/` 目录结构
  - [x] 创建 `cli/components/__init__.py`
  - [x] 移动 `cli/ui.py` → `cli/components/ui.py`
  - [x] 移动 `cli/banner.py` → `cli/components/banner.py`
  - [x] 移动 `cli/colors.py` → `cli/components/colors.py`
  - [x] 移动 `cli/cli_output.py` → `cli/components/output.py`

## 阶段 2：导入路径更新

- [x] Task 2.1: 更新 `cli/main.py` 导入路径
  - [x] 更新 `cli/components/` 相关导入
  - [x] 更新 `cli/tui/` 相关导入
  - [x] 更新 `cli/cli_commands/` 相关导入

- [x] Task 2.2: 创建兼容层 (`cli/compat.py`)
  - [x] 创建 `cli/compat.py` 提供旧导入路径兼容
  - [x] 记录需要更新的外部导入

- [x] Task 2.3: 更新其他模块导入路径
  - [x] 更新 `cli/ui.py` 从新位置重新导出
  - [x] 更新 `cli/colors.py` 从新位置重新导出
  - [x] 更新 `cli/cli_output.py` 从新位置重新导出
  - [x] 更新 `cli/banner.py` 从新位置重新导出
  - [x] 更新 `cli/curses_ui.py` 从新位置重新导出

## 阶段 3：验证

- [x] Task 3.1: 运行现有测试
  - [x] 验证 `from cli import ui` 正常工作
  - [x] 验证 `from cli import colors` 正常工作
  - [x] 验证 `from cli import curses_ui` 正常工作
  - [x] 验证 `from cli import banner` 正常工作

- [x] Task 3.2: 手动验证 CLI 功能
  - [x] 验证 `python -m cli.main --version` 正常运行
  - [x] 验证 `python -m cli.main status` 正常运行

## Task Dependencies

- 所有任务已完成