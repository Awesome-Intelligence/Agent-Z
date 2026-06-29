#!/usr/bin/env python3
"""
Trajectory 单元测试

测试 Trajectory 和 TrajectoryManager 的核心功能
"""

import pytest
import json
import os
import tempfile
from unittest.mock import MagicMock

from agent.curator.trajectory import (
    Trajectory,
    ExecutionStep,
    TrajectoryManager,
    TrajectoryStatus,
)
from agent.session import Message


class TestExecutionStep:
    """测试 ExecutionStep 类"""

    def test_from_message(self):
        """测试从 Message 对象创建 ExecutionStep"""
        msg = Message(
            role="user",
            content="test message",
            timestamp=1234567890.0,
            metadata={"key": "value"},
        )

        step = ExecutionStep.from_message(msg)

        assert step.step_type == "user"
        assert step.content == "test message"
        assert step.timestamp == 1234567890.0
        assert step.metadata == {"key": "value"}
        assert step.tool_name is None
        assert step.tool_result is None

    def test_to_hermes_entry(self):
        """测试转换为 Hermes 格式"""
        step = ExecutionStep(
            step_type="assistant",
            content="Hello, world!",
            timestamp=1234567890.0,
        )

        entry = step.to_hermes_entry()

        assert entry == {"from": "assistant", "value": "Hello, world!"}


class TestTrajectory:
    """测试 Trajectory 类"""

    def test_from_session(self):
        """测试从 Session 创建 Trajectory"""
        session = MagicMock()
        session.session_id = "test_session_12345678"
        session.get_history.return_value = [
            Message(role="user", content="Hello", timestamp=1234567890.0),
            Message(role="assistant", content="Hi there!", timestamp=1234567891.0),
        ]

        trajectory = Trajectory.from_session(session, metadata={"model": "test-model"})

        assert trajectory.id.startswith("traj_")
        assert trajectory.session_id == "test_session_12345678"
        assert len(trajectory.messages) == 2
        assert trajectory.messages[0] == {"from": "user", "value": "Hello"}
        assert trajectory.messages[1] == {"from": "assistant", "value": "Hi there!"}
        assert trajectory.metadata == {"model": "test-model"}

    def test_to_hermes_format(self):
        """测试转换为 Hermes 标准格式"""
        trajectory = Trajectory(
            id="test_traj_123",
            session_id="test_session",
            messages=[
                {"from": "system", "value": "You are a helpful assistant"},
                {"from": "user", "value": "Hello"},
            ],
            start_time=1234567890.0,
            metadata={"model": "gpt-4", "completed": True},
        )

        hermes_format = trajectory.to_hermes_format()

        assert hermes_format["conversations"] == trajectory.messages
        assert "2009-02-14" in hermes_format["timestamp"]
        assert hermes_format["model"] == "gpt-4"
        assert hermes_format["completed"] == True

    def test_to_dict_and_from_dict(self):
        """测试序列化和反序列化"""
        trajectory = Trajectory(
            id="test_traj_123",
            session_id="test_session",
            messages=[
                {"from": "user", "value": "Hello"},
                {"from": "assistant", "value": "Hi!"},
            ],
            start_time=1234567890.0,
            metadata={"model": "test"},
        )

        # 序列化
        data = trajectory.to_dict()

        assert data["id"] == "test_traj_123"
        assert data["session_id"] == "test_session"
        assert data["messages"] == trajectory.messages
        assert data["metadata"] == {"model": "test"}

        # 反序列化
        restored = Trajectory.from_dict(data)

        assert restored.id == "test_traj_123"
        assert restored.session_id == "test_session"
        assert restored.messages == trajectory.messages


class TestTrajectoryManager:
    """测试 TrajectoryManager 类"""

    def setup_method(self):
        """创建临时目录用于测试"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = TrajectoryManager(base_path=self.temp_dir)

    def teardown_method(self):
        """清理临时目录"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load(self):
        """测试保存和加载轨迹"""
        trajectory = Trajectory(
            id="test_traj_save_load",
            session_id="test_session",
            messages=[
                {"from": "user", "value": "Save test"},
                {"from": "assistant", "value": "Saved!"},
            ],
            metadata={"model": "test-model"},
        )

        # 保存
        save_path = self.manager.save(trajectory)

        assert os.path.exists(save_path)
        assert save_path.endswith(".jsonl")

        # 加载
        loaded = self.manager.load("test_traj_save_load")

        assert loaded is not None
        assert loaded.id == "test_traj_save_load"
        assert loaded.session_id == "test_session"
        assert loaded.messages == trajectory.messages

    def test_list(self):
        """测试列出轨迹"""
        # 创建多个轨迹
        for i in range(3):
            trajectory = Trajectory(
                id=f"test_traj_{i}",
                session_id="test_session",
                messages=[],
            )
            self.manager.save(trajectory)

        # 列出所有轨迹
        trajectories = self.manager.list()

        assert len(trajectories) == 3
        assert "test_traj_0" in trajectories
        assert "test_traj_1" in trajectories
        assert "test_traj_2" in trajectories

    def test_list_with_filter(self):
        """测试按 session_id 过滤"""
        # 创建不同会话的轨迹
        trajectory1 = Trajectory(
            id="traj_session1_1",
            session_id="session1",
            messages=[],
        )
        trajectory2 = Trajectory(
            id="traj_session2_1",
            session_id="session2",
            messages=[],
        )

        self.manager.save(trajectory1)
        self.manager.save(trajectory2)

        # 过滤 session1
        session1_traj = self.manager.list(session_id="session1")

        assert len(session1_traj) == 1
        assert "traj_session1_1" in session1_traj

        # 过滤 session2
        session2_traj = self.manager.list(session_id="session2")

        assert len(session2_traj) == 1
        assert "traj_session2_1" in session2_traj

    def test_load_nonexistent(self):
        """测试加载不存在的轨迹"""
        loaded = self.manager.load("nonexistent_traj")

        assert loaded is None