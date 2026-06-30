#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
# 🏃 Execution - 🛠️ ToolExec - Process Registry
# 进程注册表 - 用于追踪和管理后台进程
#
# 功能：
# - 进程启动追踪（session_id + PID）
# - 进程状态轮询
# - PID 存活检查
# - 进程终止
"""

import json
import logging
import os
import platform
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger

logger = get_execution_logger("ProcessRegistry")

_IS_WINDOWS = platform.system() == "Windows"

# 进程存活检查超时（秒）
PID_CHECK_TIMEOUT = 3


def _pid_exists(pid: int) -> bool:
    """
    检查给定 PID 的进程是否存在。

    Windows: 使用 tasklist 命令
    Unix: 使用 os.kill(pid, 0)
    """
    if pid <= 0:
        return False

    try:
        if _IS_WINDOWS:
            # Windows: 使用 os.kill 会抛异常，改用 tasklist
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                timeout=PID_CHECK_TIMEOUT,
            )
            # tasklist 输出中包含 PID 即表示进程存在
            return str(pid) in result.stdout
        else:
            # Unix: 发送信号 0，如果进程不存在会抛异常
            os.kill(pid, 0)
            return True
    except (ProcessLookupError, PermissionError):
        # 进程不存在或权限不足
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


@dataclass
class ProcessSession:
    """后台进程会话"""
    id: str                                     # 唯一会话 ID
    command: str                                # 原始命令
    app_name: str                               # 应用名称
    pid: Optional[int] = None                   # 操作系统进程 ID
    started_at: float = 0.0                     # 启动时间
    exited: bool = False                        # 是否已退出
    exit_code: Optional[int] = None             # 退出码
    verified: bool = False                      # 是否已验证启动成功
    interactive: bool = False                   # 是否为交互式终端（需要控制台）


class ProcessRegistry:
    """
    进程注册表 - 管理所有后台进程的跟踪和验证

    使用示例:
        registry = ProcessRegistry()

        # 启动进程
        session = registry.spawn("calc.exe", "calculator")

        # 验证是否启动成功
        if registry.verify(session.id):
            print("进程启动成功")

        # 查询状态
        status = registry.poll(session.id)
        print(status)
    """

    def __init__(self):
        self._running: Dict[str, ProcessSession] = {}
        self._finished: Dict[str, ProcessSession] = {}
        self._lock = threading.Lock()

        # 最大保留时间（秒）- 已结束的进程保留 30 分钟
        self._finished_ttl = 1800

    # 交互式终端程序列表（需要控制台才能正常运行）
    INTERACTIVE_TERMINALS = {"cmd.exe", "powershell.exe", "pwsh.exe", "bash.exe", "zsh.exe"}

    def spawn(
        self,
        command: List[str],
        app_name: str,
        cwd: Optional[str] = None,
    ) -> ProcessSession:
        """
        启动一个后台进程并注册到追踪表中。

        Args:
            command: 命令列表
            app_name: 应用名称（用于日志）

        Returns:
            ProcessSession 对象
        """
        # 检测是否为交互式终端
        exe_name = os.path.basename(command[0]).lower() if command else ""
        is_interactive = exe_name in self.INTERACTIVE_TERMINALS

        session = ProcessSession(
            id=f"proc_{uuid.uuid4().hex[:12]}",
            command=" ".join(command),
            app_name=app_name,
            started_at=time.time(),
            interactive=is_interactive,
        )

        try:
            if is_interactive:
                # 交互式终端：不重定向 stdin，让其使用控制台
                if _IS_WINDOWS:
                    # Windows 下使用 CREATE_NEW_CONSOLE 让终端有独立控制台
                    creation_flags = 0x00000010  # CREATE_NEW_CONSOLE
                    proc = subprocess.Popen(
                        command,
                        cwd=cwd,
                        stdout=None,
                        stderr=None,
                        stdin=None,
                        creationflags=creation_flags,
                    )
                else:
                    # Unix 系统直接启动
                    proc = subprocess.Popen(
                        command,
                        cwd=cwd,
                        stdout=None,
                        stderr=None,
                        stdin=None,
                    )
            else:
                # 非交互式程序：重定向 I/O
                proc = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )

            session.pid = proc.pid
            logger.info(f"启动进程: {app_name} (PID: {proc.pid}, interactive={is_interactive})")

            with self._lock:
                self._running[session.id] = session

            return session

        except Exception as e:
            logger.error(f"启动进程失败: {app_name}, 错误: {e}")
            session.exited = True
            session.exit_code = -1
            return session

    def verify(self, session_id: str, timeout: float = 2.0) -> bool:
        """
        验证进程是否真正启动成功。

        Args:
            session_id: 会话 ID
            timeout: 最大等待时间（秒）

        Returns:
            True 如果进程启动成功且仍在运行
        """
        session = self.get(session_id)
        if session is None:
            return False

        if session.exited:
            return False

        if session.pid is None:
            return False

        # 等待一小段时间让进程初始化
        check_interval = 0.1
        elapsed = 0.0

        while elapsed < timeout:
            time.sleep(check_interval)
            elapsed += check_interval

            if _pid_exists(session.pid):
                session.verified = True
                logger.info(f"进程验证成功: {session.app_name} (PID: {session.pid})")
                return True

        # 进程不存在或已退出
        session.exited = True
        session.exit_code = -1
        if session.interactive:
            logger.warning(f"交互式终端可能启动失败: {session.app_name} (PID: {session.pid})")
        else:
            logger.warning(f"进程验证失败: {session.app_name} (PID: {session.pid})")
        return False

    def poll(self, session_id: str) -> Dict[str, Any]:
        """
        查询进程状态。

        Args:
            session_id: 会话 ID

        Returns:
            状态字典，包含:
            - status: "running", "exited", "not_found"
            - pid: 进程 ID
            - exit_code: 退出码（如果已退出）
            - verified: 是否已验证启动
            - uptime_seconds: 运行时间
        """
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        # 检查进程是否仍然存活
        if not session.exited and session.pid is not None:
            if not _pid_exists(session.pid):
                session.exited = True
                session.exit_code = -1

        return {
            "session_id": session.id,
            "app_name": session.app_name,
            "command": session.command,
            "status": "exited" if session.exited else "running",
            "pid": session.pid,
            "verified": session.verified,
            "exit_code": session.exit_code,
            "uptime_seconds": int(time.time() - session.started_at) if not session.exited else 0,
        }

    def get(self, session_id: str) -> Optional[ProcessSession]:
        """获取会话对象"""
        with self._lock:
            return self._running.get(session_id) or self._finished.get(session_id)

    def list_sessions(self, only_running: bool = False) -> List[Dict[str, Any]]:
        """
        列出所有会话。

        Args:
            only_running: 仅返回运行中的会话

        Returns:
            会话列表
        """
        with self._lock:
            sessions = list(self._running.values())
            if not only_running:
                sessions.extend(self._finished.values())

        result = []
        for s in sessions:
            # 检查存活状态
            if not s.exited and s.pid is not None:
                if not _pid_exists(s.pid):
                    s.exited = True
                    s.exit_code = -1

            result.append({
                "session_id": s.id,
                "app_name": s.app_name,
                "command": s.command,
                "pid": s.pid,
                "status": "exited" if s.exited else "running",
                "verified": s.verified,
                "started_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(s.started_at)),
            })

        return result

    def kill(self, session_id: str) -> Dict[str, Any]:
        """
        终止进程。

        Args:
            session_id: 会话 ID

        Returns:
            结果字典
        """
        session = self.get(session_id)
        if session is None:
            return {"status": "not_found", "error": f"No process with ID {session_id}"}

        if session.exited:
            return {"status": "already_exited", "exit_code": session.exit_code}

        try:
            if session.pid is not None:
                if _IS_WINDOWS:
                    subprocess.run(
                        ["taskkill", "/PID", str(session.pid), "/T", "/F"],
                        capture_output=True,
                        timeout=10,
                    )
                else:
                    os.kill(session.pid, 9)

                session.exited = True
                session.exit_code = -9
                self._move_to_finished(session)
                logger.info(f"进程已终止: {session.app_name} (PID: {session.pid})")
                return {"status": "killed", "session_id": session.id}

        except (ProcessLookupError, PermissionError):
            session.exited = True
            session.exit_code = -1
        except Exception as e:
            logger.error(f"终止进程失败: {session.app_name}, 错误: {e}")
            return {"status": "error", "error": str(e)}

        return {"status": "killed", "session_id": session.id}

    def _move_to_finished(self, session: ProcessSession):
        """移动会话到已完成列表"""
        with self._lock:
            self._running.pop(session.id, None)
            self._finished[session.id] = session

        self._prune_if_needed()

    def _prune_if_needed(self):
        """清理过期的已完成会话"""
        now = time.time()
        expired = [
            sid for sid, s in self._finished.items()
            if (now - s.started_at) > self._finished_ttl
        ]
        for sid in expired:
            del self._finished[sid]


# 模块级单例
process_registry = ProcessRegistry()


# =============================================================================
# 工具定义
# =============================================================================

PROCESS_TOOL_SCHEMA = {
    "name": "process",
    "description": (
        "管理后台进程状态。\n"
        "操作：\n"
        "- 'verify': 验证进程是否启动成功\n"
        "- 'poll': 查询进程状态\n"
        "- 'list': 列出所有进程\n"
        "- 'kill': 终止进程"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["verify", "poll", "list", "kill"],
                "description": "操作类型"
            },
            "session_id": {
                "type": "string",
                "description": "进程会话 ID（除 list 外都需要）"
            },
            "timeout": {
                "type": "number",
                "description": "验证超时时间（秒），默认 2.0"
            },
        },
        "required": ["action"]
    },
}


def handle_process(args: dict, **kw) -> str:
    """处理 process 工具调用"""
    action = args.get("action", "")
    session_id = args.get("session_id", "")
    timeout = args.get("timeout", 2.0)

    if action == "list":
        sessions = process_registry.list_sessions()
        return json.dumps({"success": True, "sessions": sessions}, ensure_ascii=False)

    if action == "verify":
        if not session_id:
            return json.dumps({"success": False, "error": "session_id is required"}, ensure_ascii=False)
        result = process_registry.verify(session_id, timeout=timeout)
        return json.dumps({"success": result, "session_id": session_id}, ensure_ascii=False)

    if action == "poll":
        if not session_id:
            return json.dumps({"success": False, "error": "session_id is required"}, ensure_ascii=False)
        result = process_registry.poll(session_id)
        return json.dumps({"success": True, **result}, ensure_ascii=False)

    if action == "kill":
        if not session_id:
            return json.dumps({"success": False, "error": "session_id is required"}, ensure_ascii=False)
        result = process_registry.kill(session_id)
        return json.dumps({"success": result.get("status") != "error", **result}, ensure_ascii=False)

    return json.dumps({"success": False, "error": f"Unknown action: {action}"}, ensure_ascii=False)


def check_process_tool_requirements() -> bool:
    """检查进程工具需求"""
    return True