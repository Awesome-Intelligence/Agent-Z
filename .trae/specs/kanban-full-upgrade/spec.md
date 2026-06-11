# Kanban 完整升级规格

## Why

当前 Handsome Agent 的 Kanban 工具功能简单，仅支持基础的看板和任务 CRUD。为了支持多智能体协作、任务追踪和 Worker 调度，需要升级为完整的任务协作系统，参考 Hermes 的 Kanban 实现。

## What Changes

### 1. 存储升级
- 从 JSON 文件迁移到 SQLite 数据库
- 支持多 Board 和租户隔离
- 支持复杂查询（按状态、优先级、assignee 筛选）

### 2. 状态机扩展
- 新增状态：triage/todo/ready/running/blocked/done/archived
- 阻塞原因记录
- 阻塞→就绪转换

### 3. 评论/事件系统
- 任务线程评论
- 事件历史记录
- Worker handoff 上下文传递

### 4. 依赖管理
- 父子任务链接（kanban_link）
- 依赖就绪自动提升（父任务完成 → 子任务 ready）
- 循环依赖检测

### 5. 调度器
- 任务回收（认领超时）
- 任务分派（分配给 Profile/Worker）
- 心跳保活机制（heartbeat_claim）
- 最大运行时限制（max_runtime_seconds）

### 6. 多智能体协作
- Worker 任务认领机制
- 任务 handoff（created_cards、artifacts）
- 幂等键防重（idempotency_key）

### 7. CLI 命令
- 完整的 `hermes kanban` CLI 命令
- Dashboard 可视化

## Impact

- Affected specs: 工具系统、Agent 执行循环
- Affected code:
  - `tools/kanban_tool.py` - 核心 Kanban 实现
  - `tools/kanban_db.py` - SQLite 数据库层
  - `tools/kanban_scheduler.py` - 调度器
  - `hermes_cli/kanban.py` - CLI 命令
  - `tests/tools/test_kanban_tool.py` - 测试用例

## ADDED Requirements

### Requirement: SQLite 存储

系统 SHALL 提供 SQLite 数据库存储 Kanban 数据，支持多 Board 和租户隔离。

#### Scenario: 数据库初始化
- **WHEN** KanbanManager 初始化
- **THEN** 创建/打开 `~/.handsome_agent/kanban.db`，包含 boards、tasks、comments、events 表

### Requirement: 扩展状态机

系统 SHALL 支持完整的状态转换：triage → todo → ready → running → blocked/done → archived。

#### Scenario: 状态转换
- **WHEN** 任务从 running 转换到 blocked
- **THEN** 记录阻塞原因，更新 updated_at

### Requirement: 评论系统

系统 SHALL 支持任务评论和事件历史记录。

#### Scenario: 添加评论
- **WHEN** 调用 kanban_comment
- **THEN** 在数据库中创建 comment 记录，关联到 task_id

### Requirement: 依赖管理

系统 SHALL 支持父子任务依赖，父任务完成后子任务自动就绪。

#### Scenario: 依赖完成
- **WHEN** 父任务状态变为 done
- **THEN** 检查所有子任务，如果所有父任务都 done，则将子任务状态改为 ready

### Requirement: 调度器

系统 SHALL 提供任务调度器，支持任务回收、心跳保活和超时限制。

#### Scenario: 任务超时
- **WHEN** 任务运行时间超过 max_runtime_seconds
- **THEN** 标记任务为 timed_out，重新入队

### Requirement: CLI 命令

系统 SHALL 提供完整的 CLI 命令用于 Kanban 管理。

#### Scenario: CLI 列出任务
- **WHEN** 运行 `python -m tools kanban_list`
- **THEN** 显示所有任务列表，支持筛选参数

## MODIFIED Requirements

### Requirement: 现有 Kanban 工具

**MODIFIED**: 扩展现有 kanban_* 工具函数，添加 board_id、task_id 以外的新参数。

## REMOVED Requirements

无

## 技术实现细节

### 数据库 Schema

```sql
-- boards 表
CREATE TABLE boards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    tenant TEXT
);

-- tasks 表
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    board_id TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    status TEXT DEFAULT 'todo',
    priority INTEGER DEFAULT 0,
    assignee TEXT,
    created_by TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    blocked_reason TEXT,
    workspace_kind TEXT DEFAULT 'scratch',
    workspace_path TEXT,
    max_runtime_seconds INTEGER,
    FOREIGN KEY (board_id) REFERENCES boards(id)
);

-- task_dependencies 表
CREATE TABLE task_dependencies (
    parent_id TEXT NOT NULL,
    child_id TEXT NOT NULL,
    PRIMARY KEY (parent_id, child_id),
    FOREIGN KEY (parent_id) REFERENCES tasks(id),
    FOREIGN KEY (child_id) REFERENCES tasks(id)
);

-- comments 表
CREATE TABLE comments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- events 表
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    payload TEXT,
    created_at TEXT NOT NULL,
    run_id INTEGER,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);

-- task_runs 表
CREATE TABLE task_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    profile TEXT,
    status TEXT,
    outcome TEXT,
    summary TEXT,
    error TEXT,
    metadata TEXT,
    started_at TEXT,
    ended_at TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(id)
);
```

### 工具函数列表

| 函数 | 说明 |
|------|------|
| kanban_create_board | 创建看板 |
| kanban_list_boards | 列出看板 |
| kanban_view_board | 查看看板详情 |
| kanban_delete_board | 删除看板 |
| kanban_create | 创建任务 |
| kanban_show | 查看任务详情 |
| kanban_list | 列出任务 |
| kanban_update | 更新任务 |
| kanban_complete | 完成任务 |
| kanban_block | 阻塞任务 |
| kanban_unblock | 解阻塞任务 |
| kanban_heartbeat | 心跳保活 |
| kanban_comment | 添加评论 |
| kanban_link | 链接依赖 |
| kanban_unlink | 取消链接 |
| kanban_delete | 删除任务 |

### 调度器行为

1. 每 60 秒检查一次
2. 回收陈旧声明（认领超时）
3. 提升就绪任务（依赖已满足）
4. 检查超时任务

### 状态流转

```
triage → todo → ready → running → done
                  ↓         ↓
               blocked   timed_out
                  ↓
                ready
```