"""Tests for Enhanced Memory System"""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path

from core.memory_system import (
    EnhancedMemorySystem,
    MemoryType,
    MemoryItem
)
from core.markdown_memory import (
    MarkdownMemoryStore,
    MemoryCurator,
    MemoryEntry
)
from core.memory_retrieval import (
    KeywordRetriever,
    HybridRetriever,
    UnifiedMemoryRetriever
)


class TestMarkdownMemoryStore:
    """测试 Markdown 记忆存储"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_dir):
        """创建存储实例"""
        return MarkdownMemoryStore(base_path=temp_dir)

    def test_init(self, store, temp_dir):
        """测试初始化"""
        assert store.base_path == Path(temp_dir)
        assert store.sessions_path.exists()

        # 检查默认文件是否创建
        for file_path in store.files.values():
            assert file_path.exists()

    def test_store_and_retrieve(self, store):
        """测试存储和检索"""
        entry = MemoryEntry(
            id="test_1",
            content="This is a test memory",
            category="general",
            importance=0.8
        )

        # 存储
        result = store.store(entry)
        assert result is True

        # 检索
        results = store.retrieve("test memory")
        assert len(results) > 0
        assert any("test memory" in r[0].content.lower() for r in results)

    def test_update(self, store):
        """测试更新"""
        entry = MemoryEntry(
            id="test_1",
            content="Original content",
            category="general"
        )

        store.store(entry)

        # 更新
        result = store.update("test_1", "Updated content")
        assert result is True

        # 验证更新
        entries = store.get_all("general")
        assert any("Updated content" in e.content for e in entries)

    def test_delete(self, store):
        """测试删除"""
        entry = MemoryEntry(
            id="test_1",
            content="To be deleted",
            category="general"
        )

        store.store(entry)
        result = store.delete("test_1")
        assert result is True

    def test_save_and_list_sessions(self, store):
        """测试会话保存"""
        session_id = "test_session_001"
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi there!'}
        ]

        store.save_session(session_id, messages)
        sessions = store.list_sessions()

        assert session_id in sessions

    def test_cleanup_old_sessions(self, store, temp_dir):
        """测试清理旧会话"""
        # 创建一些旧的会话文件
        old_session = store.sessions_path / "old_session.md"
        old_session.write_text("# Old Session\n\nContent")

        # 修改文件时间为过去
        import time
        old_time = time.time() - (31 * 24 * 3600)  # 31 天前
        import os
        os.utime(old_session, (old_time, old_time))

        # 清理 30 天前的会话
        deleted = store.cleanup_old_sessions(days=30)
        assert deleted == 1
        assert not old_session.exists()


class TestMemoryCurator:
    """测试记忆整理器"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def curator(self, temp_dir):
        """创建整理器实例"""
        store = MarkdownMemoryStore(base_path=temp_dir)
        return MemoryCurator(store, min_importance=0.5, max_entries_per_category=5)

    def test_curate_removes_low_importance(self, curator):
        """测试移除低重要性条目"""
        # 添加一些条目
        for i in range(10):
            entry = MemoryEntry(
                id=f"test_{i}",
                content=f"Memory {i}",
                importance=0.3 if i < 5 else 0.7  # 前5个低重要性
            )
            curator.store.store(entry)

        # 整理
        stats = curator.curate()

        assert stats['entries_removed'] >= 5

    def test_curate_dry_run(self, curator):
        """测试预览模式"""
        for i in range(10):
            entry = MemoryEntry(
                id=f"test_{i}",
                content=f"Memory {i}",
                importance=0.6
            )
            curator.store.store(entry)

        # 预览模式 - 应该返回预估的清理数量
        stats = curator.curate(dry_run=True)
        entries_after = curator.store.get_all("general")

        # 预览模式应该返回预估数量（不是0），但实际数据没有被修改
        assert stats['categories_curated'] > 0
        # 数据没有被修改
        assert len(entries_after) == 10


class TestHybridRetriever:
    """测试混合检索器"""

    @pytest.fixture
    def retriever(self):
        """创建检索器实例"""
        return HybridRetriever(use_vector=True)

    @pytest.mark.asyncio
    async def test_add_and_retrieve(self, retriever):
        """测试添加和检索"""
        # 添加文档
        await retriever.add(
            "Python is a great programming language",
            metadata={'source': 'test'}
        )
        await retriever.add(
            "JavaScript is used for web development",
            metadata={'source': 'test'}
        )

        # 检索
        results = await retriever.retrieve("Python programming")

        assert len(results) > 0
        assert any("Python" in r.content for r in results)

    @pytest.mark.asyncio
    async def test_keyword_only(self):
        """测试纯关键词检索"""
        retriever = HybridRetriever(use_vector=False)

        await retriever.add("Machine learning is AI", metadata={'source': 'test'})

        results = await retriever.retrieve("machine")

        assert len(results) > 0


class TestUnifiedMemoryRetriever:
    """测试统一检索器"""

    @pytest.fixture
    def retriever(self):
        """创建检索器实例"""
        return UnifiedMemoryRetriever()

    @pytest.mark.asyncio
    async def test_register_and_retrieve(self, retriever):
        """测试注册和检索"""
        keyword_retriever = KeywordRetriever()
        retriever.register_retriever('keyword', keyword_retriever)

        await keyword_retriever.add(
            "Test content",
            metadata={'source': 'keyword'}
        )

        results = await retriever.retrieve("test", sources=['keyword'])

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_multiple_sources(self, retriever):
        """测试多源检索"""
        # 注册多个检索器
        retriever1 = KeywordRetriever()
        retriever2 = KeywordRetriever()

        retriever.register_retriever('source1', retriever1)
        retriever.register_retriever('source2', retriever2)

        await retriever1.add("Content from source 1")
        await retriever2.add("Content from source 2")

        # 检索所有源
        results = await retriever.retrieve("content")

        assert len(results) >= 2


class TestEnhancedMemorySystem:
    """测试增强记忆系统"""

    @pytest.fixture
    def memory_system(self):
        """创建记忆系统实例"""
        return EnhancedMemorySystem(
            session_id="test_session",
            enable_vector_search=True,
            enable_auto_curation=True
        )

    def test_init(self, memory_system):
        """测试初始化"""
        assert memory_system.session_id == "test_session"
        assert memory_system.enable_vector_search is True
        assert len(memory_system.working_memory) == 0
        assert len(memory_system.session_memory) == 0

    def test_add_working_memory(self, memory_system):
        """测试添加工作记忆"""
        memory_id = memory_system.add_working_memory(
            content="Test working memory",
            importance=0.8
        )

        assert memory_id.startswith("working_")
        assert len(memory_system.working_memory) == 1

    def test_add_session_memory(self, memory_system):
        """测试添加会话记忆"""
        memory_id = memory_system.add_session_memory(
            content="Test session memory",
            importance=0.7
        )

        assert memory_id.startswith("session_")
        assert len(memory_system.session_memory) == 1

    def test_add_persistent_memory(self, memory_system):
        """测试添加持久记忆"""
        memory_id = memory_system.add_persistent_memory(
            content="Important fact",
            category="facts",
            importance=0.9
        )

        assert memory_id.startswith("persistent_")

    def test_working_memory_consolidation(self, memory_system):
        """测试工作记忆整合"""
        # 添加超过限制的记忆
        for i in range(25):
            memory_system.add_working_memory(
                content=f"Memory {i}",
                importance=0.3 + (i % 10) * 0.05
            )

        # 应该触发整合
        assert len(memory_system.working_memory) <= memory_system.max_working_items

    def test_get_context_for_prompt(self, memory_system):
        """测试生成 Prompt 上下文"""
        # 添加一些记忆
        memory_system.add_working_memory("Recent task 1")
        memory_system.add_working_memory("Recent task 2")
        memory_system.add_session_memory("Historical task")

        context = memory_system.get_context_for_prompt()

        assert "Recent Context" in context or "Session History" in context

    def test_get_memory_stats(self, memory_system):
        """测试获取记忆统计"""
        memory_system.add_working_memory("Working memory 1")
        memory_system.add_session_memory("Session memory 1")

        stats = memory_system.get_memory_stats()

        assert stats['working_memory']['count'] == 1
        assert stats['session_memory']['count'] == 1
        assert 'compression_stats' in stats
