# Tasks - CLI 命令完整实现

## 阶段 1: logs 命令

- [x] Task 1.1: 创建 `cli/cli_commands/logs.py`
  - [x] 实现 `show_logs()` 函数
  - [x] 支持 `--lines` 参数（默认 50）
  - [x] 支持 `--level` 参数（debug/info/warning/error）
  - [x] 支持 `--search` 参数（关键字搜索）

## 阶段 2: gateway 命令

- [x] Task 2.1: 创建 `cli/cli_commands/gateway.py`
  - [x] 实现 `start_gateway()` - 启动服务
  - [x] 实现 `stop_gateway()` - 停止服务
  - [x] 实现 `check_gateway_status()` - 查看状态
  - [x] 实现 `restart_gateway()` - 重启服务

## 阶段 3: cron 命令

- [x] Task 3.1: 创建 `cli/cli_commands/cron.py`
  - [x] 实现 `list_cron_jobs()` - 列出定时任务
  - [x] 实现 `check_cron_status()` - 查看运行状态

## 阶段 4: acp 命令

- [x] Task 4.1: 创建 `cli/cli_commands/acp.py`
  - [x] 实现 `start_acp_server()` - 启动 ACP 服务器
  - [x] 实现 `stop_acp_server()` - 停止 ACP 服务器
  - [x] 实现 `check_acp_status()` - 查看状态

## 阶段 5: sessions recap 命令

- [x] Task 5.1: 创建 `cli/cli_commands/session_recap.py`
  - [x] 实现 `generate_session_recap()` - 生成会话摘要
  - [x] 支持 Markdown 格式输出

## 阶段 6: uninstall 命令

- [x] Task 6.1: 创建 `cli/cli_commands/uninstall.py`
  - [x] 实现 `uninstall_agent()` - 卸载功能
  - [x] 添加确认提示
  - [x] 添加备份选项

## 阶段 7: 命令注册

- [x] Task 7.1: 更新 `cli/_parser.py`
  - [x] 注册 logs 命令
  - [x] 注册 gateway 子命令
  - [x] 注册 cron 子命令
  - [x] 注册 acp 子命令
  - [x] 注册 sessions recap 子命令
  - [x] 注册 uninstall 命令
  - [x] 注册 doctor 命令

- [x] Task 7.2: 更新 `cli/main.py`
  - [x] 添加命令处理器映射
  - [x] 实现命令分发逻辑

## 阶段 8: 向后兼容

- [x] Task 8.1: 更新 `cli/compat.py`
  - [x] 导出新命令函数

- [x] Task 8.2: 更新 `cli/cli_commands/__init__.py`
  - [x] 导出所有命令函数

## Task Dependencies

- 所有任务已完成