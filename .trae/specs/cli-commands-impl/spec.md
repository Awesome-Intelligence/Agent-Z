# CLI 命令完整实现规范

## Why
当前 `cli/` 目录相比 Hermes 缺少多个核心 CLI 命令，影响用户体验和功能完整性。需要实现所有缺失的命令以达到 Hermes 相同的功能水平。

## What Changes

### 新增 CLI 命令

| 命令 | 文件 | 说明 |
|------|------|------|
| `logs` | `cli/cli_commands/logs.py` | 日志查看 |
| `gateway` | `cli/cli_commands/gateway.py` | Gateway 服务管理 |
| `cron` | `cli/cli_commands/cron.py` | 定时任务 |
| `acp` | `cli/cli_commands/acp.py` | ACP 服务器（编辑器集成） |
| `sessions recap` | `cli/cli_commands/session_recap.py` | 会话摘要 |
| `uninstall` | `cli/cli_commands/uninstall.py` | 卸载功能增强 |

### 目录结构变更

```
cli/
├── cli_commands/            # 🆕 CLI 命令系统
│   ├── __init__.py
│   ├── doctor.py            # 已有
│   ├── sessions.py          # 已有
│   ├── logs.py              # 🆕 新增
│   ├── gateway.py           # 🆕 新增
│   ├── cron.py              # 🆕 新增
│   ├── acp.py               # 🆕 新增
│   ├── session_recap.py     # 🆕 新增
│   └── uninstall.py        # 🆕 新增（替换顶层）
│
└── ...                      # 其他模块
```

## Impact

### 影响的规格
- CLI 命令系统

### 影响的代码
- `cli/_parser.py` - 需要注册新命令
- `cli/main.py` - 需要处理新命令
- `cli/cli_commands/` - 新增命令模块

## ADDED Requirements

### Requirement: logs 命令
系统 SHALL 提供日志查看功能，支持：
- 查看最近日志条目
- 按级别过滤（debug/info/warning/error）
- 指定行数
- 搜索关键字

#### Scenario: 查看最近日志
- **WHEN** 用户执行 `python -m cli.main logs`
- **THEN** 显示最近的 50 条日志

#### Scenario: 按级别过滤
- **WHEN** 用户执行 `python -m cli.main logs --level error`
- **THEN** 仅显示 error 级别的日志

### Requirement: gateway 命令
系统 SHALL 提供 Gateway 服务管理，支持：
- `gateway start` - 启动服务
- `gateway stop` - 停止服务
- `gateway status` - 查看状态
- `gateway install` - 安装为系统服务

#### Scenario: 启动 Gateway
- **WHEN** 用户执行 `python -m cli.main gateway start`
- **THEN** Gateway 服务启动，PID 保存到文件

### Requirement: cron 命令
系统 SHALL 提供定时任务管理，支持：
- `cron list` - 列出定时任务
- `cron status` - 查看运行状态

### Requirement: acp 命令
系统 SHALL 提供 ACP 服务器（编辑器集成），支持：
- `acp start` - 启动 ACP 服务器
- `acp stop` - 停止 ACP 服务器
- `acp status` - 查看状态

### Requirement: sessions recap 命令
系统 SHALL 提供会话摘要功能，支持：
- `sessions recap [session_id]` - 生成会话摘要
- 支持 Markdown 格式输出

### Requirement: uninstall 命令
系统 SHALL 提供卸载功能，支持：
- `uninstall` - 清理所有配置和数据
- 确认提示
- 备份选项

## MODIFIED Requirements

### Requirement: _parser.py 命令注册
现有 `_parser.py` 需要扩展以支持新命令的子命令解析。

## 技术实现

### 1. 命令注册到 _parser.py

```python
# cli/_parser.py 扩展

# logs command
logs_parser = subparsers.add_parser("logs", help="View logs")

# gateway command
gateway_parser = subparsers.add_parser("gateway", help="Gateway service management")
gateway_subparsers = gateway_parser.add_subparsers(dest="gateway_command")
gateway_subparsers.add_parser("start")
gateway_subparsers.add_parser("stop")
gateway_subparsers.add_parser("status")

# cron command
cron_parser = subparsers.add_parser("cron", help="Cron job management")
cron_subparsers = cron_parser.add_subparsers(dest="cron_command")
cron_subparsers.add_parser("list")
cron_subparsers.add_parser("status")

# acp command
acp_parser = subparsers.add_parser("acp", help="ACP server management")
acp_subparsers = acp_parser.add_subparsers(dest="acp_command")
acp_subparsers.add_parser("start")
acp_subparsers.add_parser("stop")
acp_subparsers.add_parser("status")

# sessions subcommands
sessions_subparsers = sessions_parser.add_subparsers(dest="sessions_subcommand")
sessions_subparsers.add_parser("recap", help="Generate session recap")
```

### 2. 命令处理器注册到 main.py

```python
# cli/main.py 扩展

COMMAND_HANDLERS = {
    "doctor": cmd_doctor,
    "logs": cmd_logs,
    "gateway": cmd_gateway,
    "cron": cmd_cron,
    "acp": cmd_acp,
    "uninstall": cmd_uninstall,
}

GATEWAY_COMMANDS = {
    "start": cmd_gateway_start,
    "stop": cmd_gateway_stop,
    "status": cmd_gateway_status,
}
```

### 3. 文件结构

```
cli/cli_commands/
├── __init__.py
├── doctor.py           # 已有
├── sessions.py          # 已有
├── logs.py              # 🆕 日志查看
├── gateway.py           # 🆕 Gateway 服务
├── cron.py              # 🆕 定时任务
├── acp.py               # 🆕 ACP 服务器
├── session_recap.py     # 🆕 会话摘要
└── uninstall.py         # 🆕 卸载功能
```