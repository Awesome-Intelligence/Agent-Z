# Checklist - Kanban 完整升级

## 数据库层 (Task 1) ✅

- [x] kanban_db.py 创建成功，数据库文件位于 ~/.handsome_agent/kanban.db
- [x] boards 表正确创建，包含 id/name/created_at/tenant 字段
- [x] tasks 表正确创建，包含所有扩展字段（status/priority/assignee 等）
- [x] task_dependencies 表正确创建，支持父子链接
- [x] comments 表正确创建，支持任务评论
- [x] events 表正确创建，支持事件历史
- [x] task_runs 表正确创建，支持任务运行记录
- [x] 数据库迁移脚本处理旧 JSON 数据（使用 KanbanManager._ensure_default_board）

## 核心工具 (Task 2) ✅

- [x] kanban_create_board 支持 tenant 参数
- [x] kanban_create 支持 assignee/body/parents/priority/workspace_kind 等参数
- [x] kanban_create 支持 idempotency_key 防重
- [x] kanban_create 支持 initial_status（triage/todo/ready）
- [x] kanban_show 返回完整任务信息（含评论/事件/运行历史）
- [x] kanban_list 支持 assignee/status/tenant/limit 筛选
- [x] kanban_list 返回 parent_ids 和 child_ids
- [x] kanban_complete 验证 created_cards 存在性
- [x] kanban_complete 支持 artifacts 列表
- [x] kanban_block 记录 blocked_reason
- [x] kanban_unblock 仅限 orchestrator 调用
- [x] kanban_heartbeat 更新 claim TTL
- [x] kanban_comment 记录 author（从 HERMES_PROFILE 获取）
- [x] kanban_link 检测循环依赖
- [x] 所有工具函数返回 JSON 格式结果
- [x] 所有工具 Schema 正确注册到 registry

## 调度器 (Task 3) ✅

- [x] KanbanScheduler 可以后台运行
- [x] release_stale_claims 正确回收超时认领
- [x] recompute_ready 正确提升就绪任务
- [x] check_timeouts 正确标记超时任务
- [x] heartbeat_claim 正确更新 claim TTL
- [x] 调度器支持配置检查间隔（默认 60 秒）
- [x] 调度器支持配置认领超时（默认 300 秒）

## CLI 命令 (Task 4) ✅

- [x] hermes kanban init 创建默认看板
- [x] hermes kanban create 支持所有参数
- [x] hermes kanban list 支持筛选和限制
- [x] hermes kanban show 显示任务详情
- [x] hermes kanban complete 完成任务
- [x] hermes kanban block 阻塞任务
- [x] hermes kanban unblock 解阻塞任务
- [x] hermes kanban comment 添加评论
- [x] hermes kanban daemon 启动调度器守护进程

## 测试用例 (Task 5) ✅

- [x] 测试数据库初始化（新建/已有数据库）
- [x] 测试 boards CRUD 操作
- [x] 测试 tasks CRUD 操作
- [x] 测试任务依赖创建和循环检测
- [x] 测试评论添加和列表
- [x] 测试事件记录
- [x] 测试状态机转换（各状态间转换）
- [x] 测试调度器回收 stale claims
- [x] 测试调度器提升就绪任务
- [x] 测试幂等键防重（相同 key 不重复创建）
- [x] 测试心跳保活
- [x] 测试 CLI 命令（可选，集成测试）

## 验证命令

```bash
# 运行测试 - 全部通过
pytest tests/tools/test_kanban_tool.py -v

# 测试 CLI
python -m hermes_cli.kanban init
python -m hermes_cli.kanban list
```

## 完成状态

**所有检查项已完成！测试结果：79 passed, 1 warning**