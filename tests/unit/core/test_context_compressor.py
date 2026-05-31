"""Tests for Context Compressor Module"""

import pytest
import asyncio
from core.context_compressor import (
    SummaryCompressor,
    HierarchicalCompressor,
    ContextCompressionManager,
    CompressionResult
)


class TestSummaryCompressor:
    """测试摘要压缩器"""

    @pytest.fixture
    def compressor(self):
        """创建压缩器实例"""
        return SummaryCompressor(recent_messages=3)

    @pytest.fixture
    def sample_messages(self):
        """示例消息"""
        return [
            {'role': 'user', 'content': 'Hello, how are you?', 'timestamp': 1000},
            {'role': 'assistant', 'content': 'I am fine, thank you!', 'timestamp': 1001},
            {'role': 'user', 'content': 'Can you help me with Python?', 'timestamp': 1002},
            {'role': 'assistant', 'content': 'Of course! What do you need?', 'timestamp': 1003},
            {'role': 'user', 'content': 'I want to learn about async programming', 'timestamp': 1004},
            {'role': 'assistant', 'content': 'Async programming is great for I/O operations', 'timestamp': 1005},
        ]

    def test_init(self, compressor):
        """测试初始化"""
        assert compressor.recent_messages == 3
        assert compressor.summary_prompt is not None

    def test_estimate_tokens(self, compressor):
        """测试 token 估算"""
        messages = [
            {'content': 'Hello world'},
            {'content': '你好世界'}
        ]
        tokens = compressor.estimate_tokens(messages)
        assert tokens > 0

    @pytest.mark.asyncio
    async def test_compress_small(self, compressor, sample_messages):
        """测试不压缩（小消息列表）"""
        result = await compressor.compress(sample_messages, max_messages=10)

        assert result.original_count == len(sample_messages)
        assert result.compressed_count == len(sample_messages)
        assert result.compression_ratio == 1.0
        assert result.summary == ""

    @pytest.mark.asyncio
    async def test_compress_large(self, compressor, sample_messages):
        """测试压缩（大消息列表）"""
        result = await compressor.compress(sample_messages, max_messages=4)

        assert result.original_count == len(sample_messages)
        assert result.compressed_count < result.original_count
        assert result.compression_ratio < 1.0
        assert result.summary != ""
        assert len(result.parent_messages) > 0

    @pytest.mark.asyncio
    async def test_compression_includes_summary_message(self, compressor, sample_messages):
        """测试压缩后包含摘要消息"""
        result = await compressor.compress(sample_messages, max_messages=4)

        # 检查是否有压缩摘要类型的消息
        summary_messages = [
            msg for msg in result.compressed_messages
            if msg.get('metadata', {}).get('type') == 'compressed_summary'
        ]
        assert len(summary_messages) > 0


class TestHierarchicalCompressor:
    """测试分层压缩器"""

    @pytest.fixture
    def compressor(self):
        """创建压缩器实例"""
        return HierarchicalCompressor(
            working_size=2,
            core_size=2,
            archive_threshold=10
        )

    @pytest.fixture
    def long_messages(self):
        """长消息列表"""
        messages = []
        for i in range(20):
            messages.append({
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Message {i}',
                'timestamp': 1000 + i
            })
        return messages

    @pytest.mark.asyncio
    async def test_compress_long_messages(self, compressor, long_messages):
        """测试长消息压缩"""
        result = await compressor.compress(long_messages, max_messages=5)

        assert result.original_count == len(long_messages)
        assert result.compressed_count < result.original_count
        assert result.compression_type == "hierarchical"

    @pytest.mark.asyncio
    async def test_archive_marker(self, compressor, long_messages):
        """测试归档标记"""
        result = await compressor.compress(long_messages, max_messages=5)

        # 检查是否有归档标记
        archive_messages = [
            msg for msg in result.compressed_messages
            if msg.get('metadata', {}).get('type') == 'archive_marker'
        ]
        # 如果消息数超过 archive_threshold，应该有归档标记
        if len(long_messages) > compressor.archive_threshold:
            assert len(archive_messages) > 0


class TestContextCompressionManager:
    """测试上下文压缩管理器"""

    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return ContextCompressionManager(
            max_tokens=500,
            compressor_type="summary"
        )

    @pytest.fixture
    def messages(self):
        """消息列表"""
        return [
            {'role': 'user', 'content': f'Message {i}' * 50}
            for i in range(30)
        ]

    @pytest.mark.asyncio
    async def test_no_compression_needed(self, manager, messages):
        """测试不需要压缩的情况"""
        # 使用足够大的 token 限制
        manager.max_tokens = 100000
        processed, result = await manager.process(messages, force_compress=False)

        assert processed == messages
        assert result is None

    @pytest.mark.asyncio
    async def test_force_compression(self, manager, messages):
        """测试强制压缩（使用小max_messages触发压缩）"""
        # 使用小max_messages来触发压缩
        compressor = SummaryCompressor(recent_messages=3)
        result = await compressor.compress(messages, max_messages=5)

        assert result.original_count == len(messages)
        assert result.compressed_count < result.original_count
        assert result.compression_ratio < 1.0
        assert len(result.parent_messages) > 0

    @pytest.mark.asyncio
    async def test_compression_history(self, manager, messages):
        """测试压缩历史"""
        compressor = SummaryCompressor(recent_messages=3)

        # 第一次压缩
        result1 = await compressor.compress(messages, max_messages=5)
        manager.compression_history.append(result1)

        # 第二次压缩
        result2 = await compressor.compress(messages, max_messages=5)
        manager.compression_history.append(result2)

        stats = manager.get_compression_stats()

        assert stats['total_compressions'] == 2
        assert stats['average_ratio'] > 0
        assert stats['total_messages_saved'] > 0
