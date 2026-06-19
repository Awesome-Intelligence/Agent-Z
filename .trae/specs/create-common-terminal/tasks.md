# Tasks - 创建 common/terminal 共享模块

## Task 1: 创建 common/terminal 目录结构

- [ ] Task 1.1: 创建 `common/terminal/` 目录
- [ ] Task 1.2: 创建 `common/terminal/__init__.py`

## Task 2: 迁移 curses_ui

- [ ] Task 2.1: 复制 `tui/core/curses_ui.py` → `common/terminal/curses_ui.py`
- [ ] Task 2.2: 删除 `tui/core/curses_ui.py`

## Task 3: 迁移 colors

- [ ] Task 3.1: 复制 `cli/components/colors.py` → `common/terminal/colors.py`
- [ ] Task 3.2: 删除 `cli/components/colors.py`

## Task 4: 迁移 banner

- [ ] Task 4.1: 复制 `cli/components/banner.py` → `common/terminal/banner.py`
- [ ] Task 4.2: 删除 `cli/components/banner.py`

## Task 5: 迁移 output

- [ ] Task 5.1: 复制 `cli/components/output.py` → `common/terminal/output.py`
- [ ] Task 5.2: 删除 `cli/components/output.py`

## Task 6: 迁移 ui

- [ ] Task 6.1: 复制 `cli/components/ui.py` → `common/terminal/ui.py`
- [ ] Task 6.2: 删除 `cli/components/ui.py`

## Task 7: 更新导入路径

- [ ] Task 7.1: 更新 `cli/main.py` 导入
- [ ] Task 7.2: 更新 `cli/cli_commands/sessions.py` 导入
- [ ] Task 7.3: 更新 `cli/compat.py` 导入
- [ ] Task 7.4: 更新 `tui/textual_app/app.py` 导入
- [ ] Task 7.5: 更新 `tui/sidebar.py` 导入
- [ ] Task 7.6: 更新其他文件的导入

## Task 8: 验证

- [ ] Task 8.1: 验证 `python -m cli.main` 正常
- [ ] Task 8.2: 验证 TUI 功能正常
- [ ] Task 8.3: 确认无循环依赖
