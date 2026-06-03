"""Tests for Compression Commands Module"""

import pytest
from unittest.mock import MagicMock
from agent.context.compression_commands import (
    CompressionCommands,
    handle_compress_command,
    handle_usage_command,
    handle_status_command,
    is_compression_command,
    parse_compression_command,
    COMMANDS,
)


class TestCompressionCommands:
    """测试 CompressionCommands 类"""

    @pytest.fixture
    def commands(self):
        """创建命令处理器实例"""
        return CompressionCommands(session_id="test_session")

    @pytest.fixture
    def mock_integration(self):
        """创建模拟的压缩集成器"""
        integration = MagicMock()
        integration.get_stats.return_value = {
            "enabled": True,
            "compression_count": 3,
            "last_prompt_tokens": 50000,
            "last_completion_tokens": 1000,
        }
        integration.get_status.return_value = {
            "enabled": True,
            "auto_compress": True,
            "initialized": True,
        }
        return integration

    def test_handle_compress_without_integration(self, commands):
        """测试无集成器时的压缩处理"""
        result = commands.handle_compress()
        assert result["success"] is False
        assert "not initialized" in result["error"]

    def test_handle_compress_with_integration(self, commands, mock_integration):
        """测试有集成器时的压缩处理"""
        commands.set_integration(mock_integration)
        result = commands.handle_compress()
        assert result is not None

    def test_handle_usage(self, commands, mock_integration):
        """测试 usage 命令"""
        commands.set_integration(mock_integration)
        result = commands.handle_usage()
        assert result["success"] is True
        assert "stats" in result
        assert "message" in result

    def test_handle_status(self, commands, mock_integration):
        """测试 status 命令"""
        commands.set_integration(mock_integration)
        result = commands.handle_status()
        assert result["success"] is True
        assert "status" in result
        assert "message" in result


class TestConvenienceFunctions:
    """测试便捷函数"""

    def test_handle_compress_command(self):
        """测试 handle_compress_command 函数"""
        result = handle_compress_command("test_session")
        # 无集成器时应返回失败
        assert result["success"] is False

    def test_handle_usage_command(self):
        """测试 handle_usage_command 函数"""
        result = handle_usage_command("test_session")
        assert result["success"] is False

    def test_handle_status_command(self):
        """测试 handle_status_command 函数"""
        result = handle_status_command("test_session")
        assert result["success"] is False


class TestCommandParsing:
    """测试命令解析"""

    @pytest.mark.parametrize("command", [
        "/compress",
        "/usage",
        "/compression-status",
    ])
    def test_is_compression_command(self, command):
        """测试命令识别"""
        assert is_compression_command(command) is True
        assert is_compression_command(command.upper()) is True

    @pytest.mark.parametrize("command", [
        "/help",
        "/quit",
        "/exit",
        "compress",
        "hello",
    ])
    def test_is_not_compression_command(self, command):
        """测试非压缩命令识别"""
        assert is_compression_command(command) is False

    def test_parse_compress_with_focus(self):
        """测试解析带 focus 参数的命令"""
        command, args = parse_compression_command("/compress --focus=python")
        assert command == "/compress"
        assert "--focus=python" in args

    def test_parse_usage_command(self):
        """测试解析 usage 命令"""
        command, args = parse_compression_command("/usage")
        assert command == "/usage"
        assert len(args) == 0

    def test_parse_status_command(self):
        """测试解析 status 命令"""
        command, args = parse_compression_command("/compression-status")
        assert command == "/compression-status"
        assert len(args) == 0

    def test_parse_unknown_command(self):
        """测试解析未知命令"""
        command, args = parse_compression_command("/unknown")
        assert command is None
        assert len(args) == 0


class TestCOMMANDS:
    """测试 COMMANDS 常量"""

    def test_commands_exist(self):
        """测试所有命令都存在"""
        assert "/compress" in COMMANDS
        assert "/usage" in COMMANDS
        assert "/compression-status" in COMMANDS

    def test_commands_have_handlers(self):
        """测试所有命令都有处理器"""
        for name, info in COMMANDS.items():
            assert "handler" in info
            assert "description" in info
            assert "help" in info

    def test_commands_have_valid_handlers(self):
        """测试所有命令处理器都是可调用的"""
        for name, info in COMMANDS.items():
            assert callable(info["handler"])