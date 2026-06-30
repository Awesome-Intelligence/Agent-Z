#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the trajectory module.

Tests cover:
- ExecutionStep serialization and deserialization
- Trajectory creation and manipulation
- TrajectoryManager saving and loading
- Hermes format conversion
- Session integration
"""

import pytest
import json
import tempfile
import os
from datetime import datetime
from unittest.mock import MagicMock

from agent.curator.trajectory import (
    TrajectoryStatus,
    ExecutionStep,
    Trajectory,
    TrajectoryManager,
)


class TestExecutionStep:
    """Test ExecutionStep class."""

    def test_step_creation(self):
        """Test creating an execution step."""
        step = ExecutionStep(
            step_type="thought",
            content="Thinking about the problem",
            timestamp=1234567890.0,
            metadata={"key": "value"},
            tool_name="test_tool",
            tool_result={"result": "success"},
        )

        assert step.step_type == "thought"
        assert step.content == "Thinking about the problem"
        assert step.timestamp == 1234567890.0
        assert step.metadata == {"key": "value"}
        assert step.tool_name == "test_tool"
        assert step.tool_result == {"result": "success"}

    def test_step_to_dict(self):
        """Test converting step to dictionary."""
        step = ExecutionStep(
            step_type="tool_call",
            content="Calling tool",
            timestamp=1234567890.0,
            metadata={"test": "data"},
            tool_name="calculator",
            tool_result={"value": 42},
        )

        result = step.to_dict()

        assert result["step_type"] == "tool_call"
        assert result["content"] == "Calling tool"
        assert result["timestamp"] == 1234567890.0
        assert result["metadata"] == {"test": "data"}
        assert result["tool_name"] == "calculator"
        assert result["tool_result"] == {"value": 42}

    def test_step_from_dict(self):
        """Test creating step from dictionary."""
        data = {
            "step_type": "response",
            "content": "Hello",
            "timestamp": 1234567890.0,
            "metadata": {"source": "test"},
            "tool_name": None,
            "tool_result": None,
        }

        step = ExecutionStep.from_dict(data)

        assert step.step_type == "response"
        assert step.content == "Hello"
        assert step.timestamp == 1234567890.0
        assert step.metadata == {"source": "test"}

    def test_step_to_hermes_entry(self):
        """Test converting step to Hermes format."""
        step = ExecutionStep(
            step_type="user",
            content="What is the weather?",
            timestamp=1234567890.0,
        )

        entry = step.to_hermes_entry()

        assert entry["from"] == "user"
        assert entry["value"] == "What is the weather?"

    def test_step_from_message(self):
        """Test creating step from message object."""
        class MockMessage:
            role = "assistant"
            content = "I'll check the weather"
            timestamp = 1234567890.0
            metadata = {"model": "gpt-4"}

        msg = MockMessage()
        step = ExecutionStep.from_message(msg)

        assert step.step_type == "assistant"
        assert step.content == "I'll check the weather"
        assert step.timestamp == 1234567890.0
        assert step.metadata == {"model": "gpt-4"}

    def test_step_from_message_with_tool_info(self):
        """Test creating step from message with tool information."""
        class MockMessage:
            role = "assistant"
            content = "<tool_call>get_weather</tool_call>"
            timestamp = 1234567890.0
            metadata = {}
            tool_name = "get_weather"
            tool_result = {"weather": "sunny"}

        msg = MockMessage()
        step = ExecutionStep.from_message(msg)

        assert step.tool_name == "get_weather"
        assert step.tool_result == {"weather": "sunny"}


class TestTrajectory:
    """Test Trajectory class."""

    def test_trajectory_creation(self):
        """Test creating a trajectory."""
        trajectory = Trajectory(
            id="traj_123",
            session_id="session_abc",
            start_time=1234567890.0,
        )

        assert trajectory.id == "traj_123"
        assert trajectory.session_id == "session_abc"
        assert trajectory.start_time == 1234567890.0
        assert len(trajectory.steps) == 0
        assert len(trajectory.messages) == 0

    def test_add_step(self):
        """Test adding steps to trajectory."""
        trajectory = Trajectory(id="traj_1", session_id="session_1")

        step1 = ExecutionStep(
            step_type="thought",
            content="Step 1",
            timestamp=1234567890.0,
        )
        step2 = ExecutionStep(
            step_type="tool_call",
            content="Step 2",
            timestamp=1234567890.1,
        )

        trajectory.add_step(step1)
        trajectory.add_step(step2)

        assert len(trajectory.steps) == 2
        assert trajectory.steps[0].step_type == "thought"
        assert trajectory.steps[1].step_type == "tool_call"

    def test_trajectory_to_dict(self):
        """Test converting trajectory to dictionary."""
        trajectory = Trajectory(
            id="traj_1",
            session_id="session_1",
            start_time=1234567890.0,
            end_time=1234567895.0,
            metadata={"model": "test"},
            messages=[{"from": "user", "value": "hello"}],
        )

        step = ExecutionStep(
            step_type="thought",
            content="test",
            timestamp=1234567890.0,
        )
        trajectory.add_step(step)

        result = trajectory.to_dict()

        assert result["id"] == "traj_1"
        assert result["session_id"] == "session_1"
        assert result["start_time"] == 1234567890.0
        assert result["end_time"] == 1234567895.0
        assert result["metadata"] == {"model": "test"}
        assert len(result["steps"]) == 1
        assert len(result["messages"]) == 1

    def test_trajectory_from_dict(self):
        """Test creating trajectory from dictionary."""
        data = {
            "id": "traj_1",
            "session_id": "session_1",
            "start_time": 1234567890.0,
            "end_time": 1234567895.0,
            "metadata": {"model": "test"},
            "messages": [{"from": "user", "value": "hello"}],
            "steps": [
                {
                    "step_type": "thought",
                    "content": "test",
                    "timestamp": 1234567890.0,
                }
            ],
        }

        trajectory = Trajectory.from_dict(data)

        assert trajectory.id == "traj_1"
        assert trajectory.session_id == "session_1"
        assert len(trajectory.steps) == 1
        assert len(trajectory.messages) == 1

    def test_trajectory_from_session(self):
        """Test creating trajectory from session."""
        class MockMessage:
            role = "user"
            content = "Hello"
            timestamp = 1234567890.0
            metadata = {}

        class MockSession:
            session_id = "test_session_123"

            def get_history(self):
                return [MockMessage()]

        session = MockSession()
        trajectory = Trajectory.from_session(session, metadata={"test": "value"})

        assert trajectory.session_id == "test_session_123"
        assert trajectory.id.startswith("traj_")
        assert len(trajectory.messages) == 1
        assert trajectory.messages[0]["from"] == "user"
        assert trajectory.metadata == {"test": "value"}

    def test_trajectory_to_hermes_format(self):
        """Test converting trajectory to Hermes format."""
        trajectory = Trajectory(
            id="traj_1",
            session_id="session_1",
            start_time=datetime(2024, 1, 1, 0, 0, 0).timestamp(),
            messages=[
                {"from": "user", "value": "Hello"},
                {"from": "assistant", "value": "Hi!"},
            ],
            metadata={"model": "gpt-4", "completed": True},
        )

        result = trajectory.to_hermes_format()

        assert "conversations" in result
        assert len(result["conversations"]) == 2
        assert "timestamp" in result
        assert result["model"] == "gpt-4"
        assert result["completed"] is True


class TestTrajectoryManager:
    """Test TrajectoryManager class."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            assert manager.base_path == tmpdir
            assert os.path.exists(tmpdir)

    def test_manager_default_path(self):
        """Test manager with default path."""
        manager = TrajectoryManager()

        assert manager.base_path is not None
        assert "trajectories" in manager.base_path

    def test_create_trajectory(self):
        """Test creating a new trajectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory = manager.create_trajectory("session_123")

            assert trajectory is not None
            assert trajectory.id.startswith("traj_")
            assert trajectory.session_id == "session_123"

    def test_save_and_load_trajectory(self):
        """Test saving and loading a trajectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory = Trajectory(
                id="traj_test_save",
                session_id="session_test",
                start_time=1234567890.0,
                messages=[
                    {"from": "user", "value": "Hello"},
                    {"from": "assistant", "value": "Hi!"},
                ],
                metadata={"model": "test"},
            )

            filepath = manager.save(trajectory)

            assert os.path.exists(filepath)

            loaded = manager.load("traj_test_save")

            assert loaded is not None
            assert loaded.id == "traj_test_save"
            assert loaded.session_id == "session_test"
            assert len(loaded.messages) == 2

    def test_load_nonexistent_trajectory(self):
        """Test loading a non-existent trajectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            result = manager.load("nonexistent_traj")

            assert result is None

    def test_list_trajectories(self):
        """Test listing trajectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory1 = Trajectory(
                id="traj_20240101_000001",
                session_id="session_1",
                start_time=1234567890.0,
                messages=[],
            )
            trajectory2 = Trajectory(
                id="traj_20240101_000002",
                session_id="session_1",
                start_time=1234567891.0,
                messages=[],
            )

            manager.save(trajectory1)
            manager.save(trajectory2)

            traj_ids = manager.list()

            assert len(traj_ids) == 2
            assert "traj_20240101_000001" in traj_ids
            assert "traj_20240101_000002" in traj_ids

    def test_list_trajectories_filter_by_session(self):
        """Test listing trajectories filtered by session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory1 = Trajectory(
                id="traj_1",
                session_id="session_a",
                start_time=1234567890.0,
                messages=[],
            )
            trajectory2 = Trajectory(
                id="traj_2",
                session_id="session_b",
                start_time=1234567891.0,
                messages=[],
            )

            manager.save(trajectory1)
            manager.save(trajectory2)

            traj_ids = manager.list(session_id="session_a")

            assert len(traj_ids) == 1
            assert traj_ids[0] == "traj_1"

    def test_delete_trajectory(self):
        """Test deleting a trajectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory = Trajectory(
                id="traj_to_delete",
                session_id="session_test",
                start_time=1234567890.0,
                messages=[],
            )

            manager.save(trajectory)

            assert manager.delete_trajectory("traj_to_delete") is True
            assert manager.load("traj_to_delete") is None

    def test_delete_nonexistent_trajectory(self):
        """Test deleting a non-existent trajectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            result = manager.delete_trajectory("nonexistent")

            assert result is False

    def test_get_recent_trajectories(self):
        """Test getting recent trajectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            for i in range(5):
                trajectory = Trajectory(
                    id=f"traj_{i}",
                    session_id="session_1",
                    start_time=1234567890.0 + i,
                    messages=[],
                )
                manager.save(trajectory)

            recent = manager.get_recent_trajectories(limit=3)

            assert len(recent) == 3
            assert recent[0].id == "traj_4"
            assert recent[1].id == "traj_3"
            assert recent[2].id == "traj_2"

    def test_save_with_metadata(self):
        """Test saving trajectory with additional metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory = Trajectory(
                id="traj_meta",
                session_id="session_1",
                start_time=1234567890.0,
                messages=[],
                metadata={"original_key": "original_value"},
            )

            manager.save(trajectory, metadata={"new_key": "new_value"})

            loaded = manager.load("traj_meta")

            assert loaded is not None
            assert loaded.metadata["original_key"] == "original_value"
            assert loaded.metadata["new_key"] == "new_value"
            assert loaded.metadata["session_id"] == "session_1"

    def test_save_without_id(self):
        """Test saving trajectory without an ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TrajectoryManager(base_path=tmpdir)

            trajectory = Trajectory(
                id="",
                session_id="session_1",
                start_time=1234567890.0,
                messages=[],
            )

            filepath = manager.save(trajectory)

            assert os.path.exists(filepath)
            assert trajectory.id.startswith("traj_")


class TestTrajectoryStatus:
    """Test TrajectoryStatus enum."""

    def test_status_values(self):
        """Test that all status values are correct."""
        assert TrajectoryStatus.SUCCESS == "success"
        assert TrajectoryStatus.FAILURE == "failure"
        assert TrajectoryStatus.RUNNING == "running"
        assert TrajectoryStatus.CANCELLED == "cancelled"


class TestBackwardsCompatibility:
    """Test backwards compatibility aliases."""

    def test_trajectory_step_alias(self):
        """Test that TrajectoryStep is an alias for ExecutionStep."""
        from agent.curator.trajectory import TrajectoryStep

        assert TrajectoryStep is ExecutionStep


if __name__ == "__main__":
    pytest.main([__file__, "-v"])