#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the process_registry module.

Tests cover:
- Process spawning
- Process verification
- Process polling
- Process listing
- Process killing
"""

import json
import pytest
import time
import platform
from unittest.mock import patch, MagicMock

_IS_WINDOWS = platform.system() == "Windows"


class TestProcessRegistry:
    """Test suite for ProcessRegistry."""

    @patch("subprocess.Popen")
    def test_spawn_success(self, mock_popen):
        """Test successful process spawning."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        assert session.id.startswith("proc_")
        assert session.app_name == "calculator"
        assert session.pid == 12345
        assert session.exited is False
        assert session.verified is False

    @patch("subprocess.Popen")
    def test_spawn_failure(self, mock_popen):
        """Test process spawning failure."""
        from tools.process_registry import ProcessRegistry

        mock_popen.side_effect = Exception("Failed to start")

        registry = ProcessRegistry()
        session = registry.spawn(["nonexistent.exe"], "nonexistent")

        assert session.exited is True
        assert session.exit_code == -1

    def test_verify_not_found(self):
        """Test verify for non-existent session."""
        from tools.process_registry import ProcessRegistry

        registry = ProcessRegistry()
        result = registry.verify("nonexistent_session")
        assert result is False

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_verify_success(self, mock_pid_exists, mock_popen):
        """Test successful process verification."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = True

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        result = registry.verify(session.id, timeout=0.5)
        assert result is True
        assert session.verified is True

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_verify_failure(self, mock_pid_exists, mock_popen):
        """Test process verification failure when process doesn't exist."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = False

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        result = registry.verify(session.id, timeout=0.5)
        assert result is False
        assert session.exited is True

    def test_poll_not_found(self):
        """Test poll for non-existent session."""
        from tools.process_registry import ProcessRegistry

        registry = ProcessRegistry()
        result = registry.poll("nonexistent")

        assert result["status"] == "not_found"
        assert "error" in result

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_poll_running(self, mock_pid_exists, mock_popen):
        """Test poll for running process."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = True

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        # 手动验证以设置 verified 标志
        registry.verify(session.id, timeout=0.1)

        result = registry.poll(session.id)

        assert result["status"] == "running"
        assert result["app_name"] == "calculator"
        assert result["pid"] == 12345
        assert result["verified"] is True

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_poll_exited(self, mock_pid_exists, mock_popen):
        """Test poll for exited process."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = False

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        result = registry.poll(session.id)

        assert result["status"] == "exited"
        assert result["exit_code"] == -1

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_list_sessions(self, mock_pid_exists, mock_popen):
        """Test listing all sessions."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = True

        registry = ProcessRegistry()
        session1 = registry.spawn(["calc.exe"], "calculator")
        session2 = registry.spawn(["notepad.exe"], "notepad")

        sessions = registry.list_sessions()

        assert len(sessions) == 2
        session_ids = [s["session_id"] for s in sessions]
        assert session1.id in session_ids
        assert session2.id in session_ids

    @patch("subprocess.Popen")
    @patch("subprocess.run")
    @patch("tools.process_registry._pid_exists")
    def test_kill_running(self, mock_pid_exists, mock_run, mock_popen):
        """Test killing a running process."""
        from tools.process_registry import ProcessRegistry

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = True
        mock_run.return_value = MagicMock(returncode=0)

        registry = ProcessRegistry()
        session = registry.spawn(["calc.exe"], "calculator")

        result = registry.kill(session.id)

        assert result["status"] == "killed"

    def test_kill_not_found(self):
        """Test killing non-existent process."""
        from tools.process_registry import ProcessRegistry

        registry = ProcessRegistry()
        result = registry.kill("nonexistent")

        assert result["status"] == "not_found"


class TestPidExists:
    """Test suite for _pid_exists function."""

    def test_invalid_pid(self):
        """Test with invalid PIDs."""
        from tools.process_registry import _pid_exists

        assert _pid_exists(0) is False
        assert _pid_exists(-1) is False

    def test_current_process(self):
        """Test with current process PID."""
        import os
        from tools.process_registry import _pid_exists

        assert _pid_exists(os.getpid()) is True


class TestProcessTool:
    """Test suite for process tool handler."""

    def test_list_action(self):
        """Test list action."""
        from tools.process_registry import handle_process

        result = json.loads(handle_process({"action": "list"}))
        assert result["success"] is True
        assert "sessions" in result

    def test_poll_missing_session_id(self):
        """Test poll without session_id."""
        from tools.process_registry import handle_process

        result = json.loads(handle_process({"action": "poll"}))
        assert result["success"] is False
        assert "error" in result

    def test_unknown_action(self):
        """Test unknown action."""
        from tools.process_registry import handle_process

        result = json.loads(handle_process({"action": "unknown"}))
        assert result["success"] is False
        assert "error" in result

    @patch("subprocess.Popen")
    @patch("tools.process_registry._pid_exists")
    def test_verify_action(self, mock_pid_exists, mock_popen):
        """Test verify action."""
        from tools.process_registry import handle_process, process_registry

        # 清空单例中的会话
        process_registry._running.clear()
        process_registry._finished.clear()

        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_popen.return_value = mock_proc
        mock_pid_exists.return_value = True

        # 使用模块级单例
        session = process_registry.spawn(["calc.exe"], "calculator")

        # 先手动验证
        process_registry.verify(session.id, timeout=0.1)

        result = json.loads(handle_process({
            "action": "verify",
            "session_id": session.id,
        }))

        assert result["success"] is True
        assert result["session_id"] == session.id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])