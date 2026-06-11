# Tasks - Kanban 完整升级

## 阶段一：数据库层

- [x] Task 1: 创建 kanban_db.py - SQLite 数据库抽象层 ✅
  - [x] SubTask 1.1: 实现数据库初始化和 Schema 创建
  - [x] SubTask 1.2: 实现 boards 表的 CRUD
  - [x] SubTask 1.3: 实现 tasks 表的 CRUD（含扩展字段）
  - [x] SubTask 1.4: 实现 task_dependencies 表管理
  - [x] SubTask 1.5: 实现 comments 和 events 表
  - [x] SubTask 1.6: 实现 task_runs 表

## 阶段二：核心工具升级

- [x] Task 2: 重构 kanban_tool.py - 基于 SQLite 的新实现 ✅
  - [x] SubTask 2.1: 重构 KanbanBoard 和 KanbanManager 使用 kanban_db
  - [x] SubTask 2.2: 添加 kanban_create（支持 assignee、body、parents 等）
  - [x] SubTask 2.3: 添加 kanban_show（查看任务详情含评论/事件）
  - [x] SubTask 2.4: 添加 kanban_list（支持筛选器）
  - [x] SubTask 2.5: 添加 kanban_complete（带 handoff 信息）
  - [x] SubTask 2.6: 添加 kanban_block 和 kanban_unblock
  - [x] SubTask 2.7: 添加 kanban_heartbeat
  - [x] SubTask 2.8: 添加 kanban_comment
  - [x] SubTask 2.9: 添加 kanban_link 和 kanban_unlink
  - [x] SubTask 2.10: 添加 kanban_delete（新实现）
  - [x] SubTask 2.11: 更新工具 Schema

## 阶段三：调度器

- [x] Task 3: 创建 kanban_scheduler.py - 任务调度器 ✅
  - [x] SubTask 3.1: 实现调度器主循环
  - [x] SubTask 3.2: 实现 release_stale_claims（回收超时认领）
  - [x] SubTask 3.3: 实现 recompute_ready（依赖就绪检查）
  - [x] SubTask 3.4: 实现 check_timeouts（超时检查）
  - [x] SubTask 3.5: 实现 heartbeat_claim（心跳保活）

## 阶段四：CLI 命令

- [x] Task 4: 创建 hermes_cli/kanban.py - CLI 命令 ✅
  - [x] SubTask 4.1: 实现 kanban init（初始化看板）
  - [x] SubTask 4.2: 实现 kanban create（创建任务）
  - [x] SubTask 4.3: 实现 kanban list（列出任务）
  - [x] SubTask 4.4: 实现 kanban show（查看任务）
  - [x] SubTask 4.5: 实现 kanban complete（完成任务）
  - [x] SubTask 4.6: 实现 kanban block/unblock（阻塞控制）
  - [x] SubTask 4.7: 实现 kanban comment（添加评论）
  - [x] SubTask 4.8: 实现 kanban daemon（启动调度器）

## 阶段五：测试用例

- [x] Task 5: 编写测试用例 test_kanban_tool.py ✅
  - [x] SubTask 5.1: 测试数据库初始化和 Schema
  - [x] SubTask 5.2: 测试 boards CRUD
  - [x] SubTask 5.3: 测试 tasks CRUD
  - [x] SubTask 5.4: 测试任务依赖管理
  - [x] SubTask 5.5: 测试评论和事件系统
  - [x] SubTask 5.6: 测试调度器行为
  - [x] SubTask 5.7: 测试状态机转换
  - [x] SubTask 5.8: 测试幂等键防重

## Task Dependencies

- Task 2 依赖 Task 1 ✅
- Task 3 依赖 Task 1、Task 2 ✅
- Task 4 依赖 Task 1、Task 2 ✅
- Task 5 依赖 Task 1、Task 2、Task 3 ✅

## 实施顺序

1. Task 1 (数据库层) - 先完成，因为其他都依赖它 ✅
2. Task 2 (核心工具升级) - 第二，完成后可独立运行 ✅
3. Task 3 (调度器) - 第三，与工具并行开发 ✅
4. Task 4 (CLI) - 第四，依赖核心功能 ✅
5. Task 5 (测试) - 最后，覆盖所有功能 ✅

## 完成状态

**所有任务已完成！**

## 实现文件清单

| 文件 | 说明 |
|------|------|
| `tools/kanban_db.py` | SQLite 数据库抽象层 |
| `tools/kanban_tool.py` | 工具函数（含所有 Hermes 风格 API） |
| `tools/kanban_scheduler.py` | 任务调度器 |
| `hermes_cli/kanban.py` | CLI 命令 |
| `tests/tools/test_kanban_tool.py` | 79 个测试用例 |