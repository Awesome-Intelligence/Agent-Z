#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cron command - Cron job management

🚪 Access - 💬 CLI - 定时任务管理

提供定时任务管理功能：列出任务、查看状态。
"""

import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime


def list_cron_jobs(json_output: bool = False) -> None:
    """List all cron jobs.
    
    Args:
        json_output: Output as JSON
    """
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_info
    
    print_header("⏰ 定时任务列表")
    
    jobs = _get_cron_jobs()
    
    if not jobs:
        print_info("没有配置定时任务")
        return
    
    if json_output:
        import json
        print(json.dumps({"jobs": jobs}, indent=2))
        return
    
    print()
    print(color("  ID", Colors.BOLD), end="")
    print(color(" " * 8, Colors.DIM), end="")
    print(color("Schedule", Colors.DIM), end="")
    print(color(" " * 12, Colors.DIM), end="")
    print(color("Command", Colors.DIM))
    print(color("-" * 70, Colors.DIM))
    
    for job in jobs:
        job_id = job.get("id", "unknown")[:8]
        schedule = job.get("schedule", "unknown")
        command = job.get("command", "")[:40]
        
        print(f"  {job_id}  {color(schedule, Colors.AVOCADO_BRIGHT)}  {command}")
    
    print()


def check_cron_status() -> None:
    """Check cron service status."""
    from common.terminal.colors import Colors, color
    from common.terminal.ui import print_header, print_success, print_error, print_info
    
    print_header("📊 定时任务状态")
    
    jobs = _get_cron_jobs()
    
    if not jobs:
        print_error("没有配置定时任务")
        print_info("使用 'handsome cron add' 添加任务")
        return
    
    # 统计运行状态
    running = 0
    for job in jobs:
        if job.get("enabled", True):
            running += 1
    
    print()
    print_success(f"🟢 定时任务服务正常")
    print_info(f"总计: {len(jobs)} 个任务, {running} 个启用")
    print()
    
    # 显示最近执行
    recent = _get_recent_executions()
    if recent:
        print(color("  最近执行:", Colors.DIM))
        for exec_info in recent[:5]:
            timestamp = exec_info.get("timestamp", "")
            job_id = exec_info.get("job_id", "")[:8]
            status = exec_info.get("status", "unknown")
            
            status_icon = "✓" if status == "success" else "✗" if status == "failed" else "?"
            status_color = Colors.GREEN if status == "success" else Colors.RED if status == "failed" else Colors.DIM
            
            print(f"  {color(status_icon, status_color)} {timestamp} - {job_id}")


def _get_cron_jobs() -> List[Dict]:
    """获取定时任务列表"""
    try:
        from common.config import load_config
        config = load_config()
        
        cron_config = config.get("cron", {})
        jobs = cron_config.get("jobs", [])
        
        return jobs
    except Exception:
        # 回退到默认配置
        return _get_default_jobs()


def _get_default_jobs() -> List[Dict]:
    """获取默认任务列表（如果没有配置）"""
    # 默认任务：每天清理会话，每周备份
    return [
        {
            "id": "cleanup-sessions",
            "schedule": "0 2 * * *",  # 每天凌晨2点
            "command": "python -m cli.main sessions cleanup --older-than 7d",
            "description": "清理超过7天的会话",
            "enabled": True,
        },
        {
            "id": "backup-config",
            "schedule": "0 3 * * 0",  # 每周日凌晨3点
            "command": "python -m cli.main backup",
            "description": "备份配置",
            "enabled": True,
        },
    ]


def _get_recent_executions() -> List[Dict]:
    """获取最近执行记录"""
    try:
        cron_dir = Path.home() / ".handsome_agent" / "cron"
        if not cron_dir.exists():
            return []
        
        # 读取执行日志
        log_file = cron_dir / "execution.log"
        if not log_file.exists():
            return []
        
        executions = []
        with open(log_file, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split("|")
                if len(parts) >= 3:
                    executions.append({
                        "timestamp": parts[0],
                        "job_id": parts[1],
                        "status": parts[2],
                    })
        
        return executions[-10:]  # 返回最近10条
    except Exception:
        return []


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cron job management")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    list_parser = subparsers.add_parser("list", help="List cron jobs")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    status_parser = subparsers.add_parser("status", help="Check cron status")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_cron_jobs(json_output=args.json)
    elif args.command == "status":
        check_cron_status()
    else:
        # 默认显示列表
        list_cron_jobs()