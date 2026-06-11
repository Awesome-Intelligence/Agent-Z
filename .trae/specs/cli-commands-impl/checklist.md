# Checklist - CLI 命令完整实现

## logs 命令

- [x] `cli/cli_commands/logs.py` 创建成功
- [x] `show_logs()` 函数实现
- [x] `--lines` 参数支持
- [x] `--level` 参数支持
- [x] `--search` 参数支持

## gateway 命令

- [x] `cli/cli_commands/gateway.py` 创建成功
- [x] `start_gateway()` 实现
- [x] `stop_gateway()` 实现
- [x] `check_gateway_status()` 实现

## cron 命令

- [x] `cli/cli_commands/cron.py` 创建成功
- [x] `list_cron_jobs()` 实现
- [x] `check_cron_status()` 实现

## acp 命令

- [x] `cli/cli_commands/acp.py` 创建成功
- [x] `start_acp_server()` 实现
- [x] `stop_acp_server()` 实现
- [x] `check_acp_status()` 实现

## sessions recap 命令

- [x] `cli/cli_commands/session_recap.py` 创建成功
- [x] `generate_session_recap()` 实现
- [x] Markdown 格式输出支持

## uninstall 命令

- [x] `cli/cli_commands/uninstall.py` 创建成功
- [x] `uninstall_agent()` 实现
- [x] 确认提示
- [x] 备份选项

## 命令注册

- [x] `cli/_parser.py` 更新完成
- [x] `cli/main.py` 更新完成

## 向后兼容

- [x] `cli/compat.py` 更新完成
- [x] `cli/cli_commands/__init__.py` 更新完成

## 功能验证

- [x] `python -m cli.main --help` 显示所有命令
- [x] `python -m cli.main logs --help` 正常工作
- [x] `python -m cli.main gateway --help` 正常工作
- [x] `python -m cli.main cron --help` 正常工作
- [x] `python -m cli.main acp --help` 正常工作
- [x] `python -m cli.main sessions --help` 正常工作
- [x] `python -m cli.main uninstall --help` 正常工作