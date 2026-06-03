"""Tests for Context Compressor Module - 新压缩引擎测试"""

import pytest
import asyncio
from agent.context.context_compressor import (
    ContextCompressor,
    estimate_messages_tokens_rough,
    redact_sensitive_text,
)


class TestContextCompressor:
    """测试 ContextCompressor 类"""

    @pytest.fixture
    def compressor(self):
        """创建压缩器实例"""
        return ContextCompressor(
            model="gpt-4o",
            threshold_percent=0.50,
            protect_first_n=3,
            protect_last_n=10,
            quiet_mode=True,
        )

    @pytest.fixture
    def sample_messages(self):
        """示例消息"""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I am fine, thank you!"},
            {"role": "user", "content": "Can you help me with Python?"},
            {"role": "assistant", "content": "Of course! What do you need?"},
            {"role": "user", "content": "I want to learn about async programming"},
            {"role": "assistant", "content": "Async programming is great for I/O operations."},
            {"role": "user", "content": "Tell me more about asyncio"},
            {"role": "assistant", "content": "asyncio is a standard library for async Python."},
            {"role": "user", "content": "How do I use await?"},
            {"role": "assistant", "content": "You use await to pause async function execution."},
            {"role": "user", "content": "Can you show me an example?"},
            {"role": "assistant", "content": "Here is an example: async def main(): await asyncio.sleep(1)"},
            {"role": "user", "content": "Thanks! What about tasks?"},
            {"role": "assistant", "content": "You can use asyncio.create_task() to run tasks concurrently."},
        ]

    def test_init(self, compressor):
        """测试初始化"""
        assert compressor.model == "gpt-4o"
        assert compressor.threshold_percent == 0.50
        assert compressor.protect_first_n == 3
        assert compressor.protect_last_n == 10
        assert compressor.quiet_mode is True

    def test_context_length(self, compressor):
        """测试上下文长度设置"""
        assert compressor.context_length == 128000
        assert compressor.threshold_tokens > 0

    def test_should_compress_small(self, compressor):
        """测试不需要压缩的情况"""
        assert compressor.should_compress(1000) is False

    def test_should_compress_large(self, compressor):
        """测试需要压缩的情况"""
        assert compressor.should_compress(100000) is True

    def test_compress_small_messages(self, compressor, sample_messages):
        """测试小消息列表不压缩"""
        # 只使用前几条消息，不超过阈值
        messages = sample_messages[:5]
        result = compressor.compress(messages)
        assert len(result) == len(messages)

    def test_compress_large_messages(self, compressor, sample_messages):
        """测试大消息列表压缩"""
        result = compressor.compress(sample_messages)
        # 压缩后消息数量应该减少
        assert len(result) < len(sample_messages)

    def test_compress_simple(self, compressor, sample_messages):
        """测试简单压缩（无 LLM）"""
        result = compressor.compress_simple(sample_messages)
        assert len(result) > 0
        assert len(result) <= len(sample_messages)


class TestCompressIntegration:
    """测试压缩集成"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_token_estimation(self):
        """测试 Token 估算"""
        messages = [
            {"role": "user", "content": "Hello, this is a test message."},
            {"role": "assistant", "content": "Hi! This is a response."},
        ]
        tokens = estimate_messages_tokens_rough(messages)
        assert tokens > 0

    def test_redact_sensitive(self):
        """测试敏感信息脱敏"""
        text = "API Key: sk-1234567890abcdefghijklmnopqrstuvwxyz123456"
        result = redact_sensitive_text(text)
        assert "sk-" not in result
        assert "[REDACTED]" in result


class TestCompressionEdgeCases:
    """测试压缩边界情况"""

    @pytest.fixture
    def compressor(self):
        return ContextCompressor(model="gpt-4o", quiet_mode=True)

    def test_empty_messages(self, compressor):
        """测试空消息列表"""
        result = compressor.compress([])
        assert result == []

    def test_single_message(self, compressor):
        """测试单条消息"""
        messages = [{"role": "user", "content": "Hello"}]
        result = compressor.compress(messages)
        assert len(result) == 1

    def test_system_message_preserved(self, compressor):
        """测试系统消息被保留"""
        messages = [
            {"role": "system", "content": "You are an assistant."},
            {"role": "user", "content": "Hello" * 1000},
        ]
        result = compressor.compress(messages)
        assert result[0]["role"] == "system"

    def test_last_user_message_in_tail(self, compressor):
        """测试最后一条用户消息在尾部保护区域"""
        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Last user message"},
        ]
        result = compressor.compress(messages)
        # 应该在结果中找到 "Last user message"
        content = " ".join(str(m.get("content", "")) for m in result)
        assert "Last user message" in content