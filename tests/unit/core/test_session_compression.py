"""Tests for Session Compression and Lineage Tracking"""

import pytest
import tempfile
import shutil
from pathlib import Path

from core.session import (
    Session,
    SessionConfig,
    SessionManager,
    CompressionRecord,
    Message
)


class TestSessionCompression:
    """测试会话压缩功能"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def config(self, temp_dir):
        """创建配置"""
        return SessionConfig(
            max_history_length=50,
            enable_persistence=True,
            history_path=temp_dir,
            enable_compression=True,
            compression_threshold=10,
            preserve_compressed_history=True
        )

    @pytest.fixture
    def session(self, config):
        """创建会话实例"""
        return Session("test_session_compression", config)

    def test_init_with_compression_config(self, session, config):
        """测试初始化压缩配置"""
        assert session.config.enable_compression == config.enable_compression
        assert session.config.compression_threshold == config.compression_threshold
        assert session.config.preserve_compressed_history is True

    def test_record_compression(self, session):
        """测试记录压缩操作"""
        # 模拟压缩
        session.record_compression(
            original_count=50,
            compressed_count=10,
            summary="Compressed summary of 50 messages",
            parent_messages=[
                {'role': 'user', 'content': 'Message 1'},
                {'role': 'assistant', 'content': 'Response 1'}
            ],
            compression_ratio=0.2
        )

        # 验证压缩记录
        history = session.get_compression_history()
        assert len(history) == 1
        assert history[0].original_count == 50
        assert history[0].compressed_count == 10
        assert history[0].compression_ratio == 0.2

    def test_get_compression_history(self, session):
        """测试获取压缩历史"""
        # 记录多次压缩
        for i in range(3):
            session.record_compression(
                original_count=50 + i * 10,
                compressed_count=10,
                summary=f"Compression {i}",
                parent_messages=[],
                compression_ratio=0.2
            )

        history = session.get_compression_history()
        assert len(history) == 3

    def test_compression_persistence(self, session, temp_dir):
        """测试压缩记录持久化"""
        # 添加消息
        for i in range(5):
            session.add_message('user', f'Message {i}')

        # 记录压缩
        session.record_compression(
            original_count=50,
            compressed_count=10,
            summary="Test compression",
            parent_messages=[],
            compression_ratio=0.2
        )

        # 模拟重新加载会话
        session2 = Session("test_session_compression",
                           SessionConfig(history_path=temp_dir))

        # 验证压缩历史已加载
        history = session2.get_compression_history()
        assert len(history) == 1


class TestSessionLineage:
    """测试会话传承追踪"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def session(self, temp_dir):
        """创建会话实例"""
        config = SessionConfig(
            history_path=temp_dir,
            preserve_compressed_history=True
        )
        return Session("parent_session", config)

    def test_set_parent_session(self, session):
        """测试设置父会话"""
        session.set_parent_session("original_session_id")

        lineage = session.get_lineage_info()
        assert lineage['parent_session_id'] == "original_session_id"
        assert lineage['has_parent'] is True

    def test_add_child_session(self, session):
        """测试添加子会话"""
        session.add_child_session("child_session_1")
        session.add_child_session("child_session_2")

        lineage = session.get_lineage_info()
        assert "child_session_1" in lineage['child_session_ids']
        assert "child_session_2" in lineage['child_session_ids']
        assert lineage['child_count'] == 2

    def test_add_duplicate_child(self, session):
        """测试添加重复子会话"""
        session.add_child_session("child_session")
        session.add_child_session("child_session")

        lineage = session.get_lineage_info()
        assert lineage['child_count'] == 1

    def test_lineage_persistence(self, session, temp_dir):
        """测试传承信息持久化"""
        # 设置传承信息
        session.set_parent_session("original_session")
        session.add_child_session("child_1")

        # 重新加载
        session2 = Session("parent_session",
                           SessionConfig(history_path=temp_dir))

        lineage = session2.get_lineage_info()
        assert lineage['parent_session_id'] == "original_session"
        assert "child_1" in lineage['child_session_ids']

    def test_get_full_history_with_lineage(self, session):
        """测试获取完整历史（含传承）"""
        # 添加消息和压缩记录
        session.add_message('user', 'Test message')
        session.record_compression(
            original_count=20,
            compressed_count=5,
            summary="Test compression",
            parent_messages=[],
            compression_ratio=0.25
        )

        full_history = session.get_full_history_with_lineage()

        assert 'session_id' in full_history
        assert 'messages' in full_history
        assert 'lineage' in full_history
        assert 'compression_history' in full_history
        assert len(full_history['messages']) >= 1


class TestSessionCompressionInStats:
    """测试会话统计中的压缩信息"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def session(self, temp_dir):
        """创建会话实例"""
        config = SessionConfig(history_path=temp_dir)
        return Session("stats_test_session", config)

    def test_stats_include_compression(self, session):
        """测试统计包含压缩信息"""
        # 添加消息
        session.add_message('user', 'Test')
        session.add_message('assistant', 'Response')

        # 记录压缩
        session.record_compression(
            original_count=50,
            compressed_count=10,
            summary="Summary",
            parent_messages=[],
            compression_ratio=0.2
        )

        stats = session.get_stats()

        assert 'compression_enabled' in stats
        assert stats['compression_enabled'] is True
        assert 'compression_records' in stats
        assert stats['compression_records'] == 1
        assert 'lineage' in stats

    def test_stats_without_compression(self, session):
        """测试无压缩时的统计"""
        session.add_message('user', 'Test')

        stats = session.get_stats()

        assert stats['compression_enabled'] is True
        assert stats['compression_records'] == 0
        assert stats['total_messages_preserved'] == 0


class TestSessionManagerLineage:
    """测试会话管理器的传承功能"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        shutil.rmtree(temp_path, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_dir):
        """创建会话管理器"""
        config = SessionConfig(history_path=temp_dir)
        return SessionManager(config)

    def test_session_lineage_tracking(self, manager):
        """测试会话传承追踪"""
        # 创建父会话
        parent = manager.create_session("parent")
        parent.add_message('user', 'Parent message')

        # 记录压缩
        parent.record_compression(
            original_count=100,
            compressed_count=20,
            summary="Parent compressed",
            parent_messages=[],
            compression_ratio=0.2
        )

        # 创建子会话并设置父会话
        child = manager.create_session("child")
        child.set_parent_session("parent")

        # 验证传承
        child_lineage = child.get_lineage_info()
        assert child_lineage['has_parent'] is True
        assert child_lineage['parent_session_id'] == "parent"

        # 手动添加子引用到父会话（因为没有自动引用）
        parent.add_child_session("child")

        # 验证反向引用
        parent_lineage = parent.get_lineage_info()
        assert "child" in parent_lineage['child_session_ids']
        assert parent_lineage['child_count'] == 1

    def test_compression_statistics_across_sessions(self, manager):
        """测试跨会话的压缩统计"""
        # 创建多个会话并压缩
        for i in range(3):
            session = manager.create_session(f"session_{i}")
            session.add_message('user', f'Message {i}')
            session.record_compression(
                original_count=100,
                compressed_count=20,
                summary=f"Compression {i}",
                parent_messages=[],
                compression_ratio=0.2
            )

        # 统计
        total_compressions = 0
        total_preserved = 0

        for session_id in manager.list_sessions():
            session = manager.get_session(session_id)
            if session:
                stats = session.get_stats()
                total_compressions += stats['compression_records']
                total_preserved += stats['total_messages_preserved']

        assert total_compressions == 3
        assert total_preserved == 3 * (100 - 20)  # 每次压缩保留80条
