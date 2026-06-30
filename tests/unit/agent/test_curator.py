#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Curator module.

Tests cover:
- CuratorState: state persistence and loading
- Curator initialization and configuration
- Trajectory evaluation logic
- Skill synthesis from successful trajectories
- Auto-learning functionality
- Periodic review mechanism
- Conditional execution (idle gating)
- Global instance management
"""

import pytest
import asyncio
import json
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

from agent.curator.curator import Curator, CuratorState, get_curator
from agent.curator.types import (
    EvaluationResult,
    EvaluationReport,
    EvaluationStep,
    SynthesizedSkill,
)


class TestCuratorState:
    """Test CuratorState class."""

    def test_initial_state(self):
        """Test initial state values."""
        state = CuratorState()

        assert state.last_run_at is None
        assert state.last_run_duration_seconds is None
        assert state.last_run_summary is None
        assert state.paused is False
        assert state.run_count == 0

    def test_state_persistence(self):
        """Test state saving and loading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state = CuratorState(state_file=state_file)

            state.last_run_at = "2024-01-01T00:00:00+00:00"
            state.last_run_duration_seconds = 120.5
            state.last_run_summary = "test run"
            state.paused = False
            state.run_count = 5
            state.save()

            new_state = CuratorState(state_file=state_file)

            assert new_state.last_run_at == "2024-01-01T00:00:00+00:00"
            assert new_state.last_run_duration_seconds == 120.5
            assert new_state.last_run_summary == "test run"
            assert new_state.paused is False
            assert new_state.run_count == 5

    def test_state_update_run(self):
        """Test update_run method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state = CuratorState(state_file=state_file)

            state.update_run(duration=45.2, summary="test update")

            assert state.last_run_at is not None
            assert state.last_run_duration_seconds == 45.2
            assert state.last_run_summary == "test update"
            assert state.run_count == 1

    def test_state_should_run(self):
        """Test should_run method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state = CuratorState(state_file=state_file)

            assert state.should_run(interval_hours=24) is False

            state.last_run_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            assert state.should_run(interval_hours=24) is True

            state.last_run_at = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            assert state.should_run(interval_hours=24) is False

    def test_state_paused_should_not_run(self):
        """Test that paused state prevents running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state = CuratorState(state_file=state_file)

            state.last_run_at = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
            state.set_paused(True)

            assert state.should_run(interval_hours=24) is False

    def test_state_reset(self):
        """Test reset method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state = CuratorState(state_file=state_file)

            state.last_run_at = "2024-01-01T00:00:00+00:00"
            state.last_run_duration_seconds = 120.5
            state.run_count = 5
            state._reset()

            assert state.last_run_at is None
            assert state.last_run_duration_seconds is None
            assert state.run_count == 0

    def test_state_load_corrupted_file(self):
        """Test loading corrupted state file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "curator_state.json"
            state_file.write_text("not valid json", encoding="utf-8")

            state = CuratorState(state_file=state_file)

            assert state.last_run_at is None
            assert state.run_count == 0


class TestCuratorInitialization:
    """Test Curator initialization."""

    def test_curator_default_init(self):
        """Test default initialization."""
        curator = Curator()

        assert curator.skill_writer is None
        assert curator.enable_auto_learn is True
        assert curator.min_confidence_threshold == 0.7
        assert curator.interval_hours == 24 * 7
        assert curator.min_idle_hours == 2
        assert curator._state is not None
        assert curator._running is False

    def test_curator_custom_init(self):
        """Test custom initialization parameters."""
        mock_writer = MagicMock()
        mock_state = MagicMock()

        curator = Curator(
            skill_writer=mock_writer,
            enable_auto_learn=False,
            min_confidence_threshold=0.8,
            interval_hours=12,
            min_idle_hours=1,
            curator_state=mock_state,
        )

        assert curator.skill_writer is mock_writer
        assert curator.enable_auto_learn is False
        assert curator.min_confidence_threshold == 0.8
        assert curator.interval_hours == 12
        assert curator.min_idle_hours == 1
        assert curator._state is mock_state

    def test_curator_learning_methods(self):
        """Test enable/disable learning methods."""
        curator = Curator()

        assert curator._learning_enabled is True

        curator.disable_learning()
        assert curator._learning_enabled is False

        curator.enable_learning()
        assert curator._learning_enabled is True


class TestCuratorEvaluation:
    """Test trajectory evaluation logic."""

    @pytest.mark.asyncio
    async def test_evaluate_success(self):
        """Test evaluation with successful tool calls."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "test_1",
            "messages": [
                {"role": "user", "content": "打开计算器"},
                {"role": "assistant", "content": "<tool_call>open_calculator</tool_call>"},
                {"role": "tool", "content": "Calculator opened successfully"},
            ],
        }

        report = await curator.evaluate(trajectory)

        assert report.trajectory_id == "test_1"
        assert report.overall_result == EvaluationResult.SUCCESS
        assert report.success_rate == 1.0
        assert report.metrics["total_tool_calls"] == 1
        assert report.metrics["total_tool_responses"] == 1
        assert report.metrics["errors"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_partial_success(self):
        """Test evaluation with partial success."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "test_2",
            "messages": [
                {"role": "user", "content": "执行多个操作"},
                {"role": "assistant", "content": "<tool_call>tool1</tool_call>"},
                {"role": "tool", "content": "success"},
                {"role": "assistant", "content": "<tool_call>tool2</tool_call>"},
                {"role": "tool", "content": "error: failed"},
            ],
        }

        report = await curator.evaluate(trajectory)

        assert report.overall_result == EvaluationResult.PARTIAL_SUCCESS
        assert report.success_rate == 0.5

    @pytest.mark.asyncio
    async def test_evaluate_failure(self):
        """Test evaluation with failure."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "test_3",
            "messages": [
                {"role": "user", "content": "测试"},
                {"role": "assistant", "content": "<tool_call>test_tool</tool_call>"},
                {"role": "tool", "content": "error: exception occurred"},
            ],
        }

        report = await curator.evaluate(trajectory)

        assert report.overall_result == EvaluationResult.FAILURE
        assert report.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_evaluate_unknown_no_tool_calls(self):
        """Test evaluation with no tool calls."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "test_4",
            "messages": [
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"},
            ],
        }

        report = await curator.evaluate(trajectory)

        assert report.overall_result == EvaluationResult.UNKNOWN
        assert report.metrics["total_tool_calls"] == 0

    @pytest.mark.asyncio
    async def test_evaluate_with_conversations_format(self):
        """Test evaluation with conversations format."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "test_5",
            "conversations": [
                {"role": "user", "content": "打开计算器"},
                {"role": "assistant", "content": "<tool_call>open_calculator</tool_call>"},
                {"role": "tool", "content": "success"},
            ],
        }

        report = await curator.evaluate(trajectory)

        assert report.overall_result == EvaluationResult.SUCCESS

    @pytest.mark.asyncio
    async def test_evaluate_empty_messages(self):
        """Test evaluation with empty messages."""
        curator = Curator()

        trajectory = {"trajectory_id": "test_6", "messages": []}

        report = await curator.evaluate(trajectory)

        assert report.overall_result == EvaluationResult.UNKNOWN


class TestCuratorSkillSynthesis:
    """Test skill synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_skill(self):
        """Test skill synthesis from successful trajectory."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "skill_test_1",
            "user_input": "查询天气并记录",
            "steps": [
                {"type": "action", "data": {"tool_name": "get_weather", "parameters": {"city": "Beijing"}}},
                {"type": "observation", "data": {"weather": "sunny"}},
                {"type": "action", "data": {"tool_name": "save_note", "parameters": {"content": "sunny"}}},
            ],
        }

        report = EvaluationReport(
            trajectory_id="skill_test_1",
            overall_result=EvaluationResult.SUCCESS,
            success_rate=1.0,
            steps=[],
            suggestions=[],
            metrics={},
        )

        skill = await curator.synthesize_skill(trajectory, report)

        assert skill is not None
        assert skill.name.startswith("auto_")
        assert "查询天气" in skill.description
        assert "get_weather" in skill.action_template
        assert "save_note" in skill.action_template
        assert skill.confidence == 1.0

    @pytest.mark.asyncio
    async def test_synthesize_skill_low_confidence(self):
        """Test skill synthesis with low confidence."""
        curator = Curator(min_confidence_threshold=0.9)

        trajectory = {
            "trajectory_id": "skill_test_2",
            "user_input": "测试",
            "steps": [
                {"type": "action", "data": {"tool_name": "test_tool", "parameters": {}}},
            ],
        }

        report = EvaluationReport(
            trajectory_id="skill_test_2",
            overall_result=EvaluationResult.PARTIAL_SUCCESS,
            success_rate=0.5,
            steps=[],
            suggestions=[],
            metrics={},
        )

        skill = await curator.synthesize_skill(trajectory, report)

        assert skill is None

    @pytest.mark.asyncio
    async def test_synthesize_skill_not_candidate(self):
        """Test skill synthesis when trajectory is not a candidate."""
        curator = Curator()

        trajectory = {
            "trajectory_id": "skill_test_3",
            "user_input": "测试",
            "steps": [
                {"type": "thought", "data": {"content": "thinking"}},
            ],
        }

        report = EvaluationReport(
            trajectory_id="skill_test_3",
            overall_result=EvaluationResult.SUCCESS,
            success_rate=1.0,
            steps=[],
            suggestions=[],
            metrics={},
        )

        skill = await curator.synthesize_skill(trajectory, report)

        assert skill is None

    def test_get_learned_skills(self):
        """Test get_learned_skills method."""
        curator = Curator()

        assert len(curator.get_learned_skills()) == 0

        curator._learned_skills["test_skill"] = SynthesizedSkill(
            name="test_skill",
            description="test",
            trigger_patterns=[],
            action_template="",
            confidence=1.0,
        )

        skills = curator.get_learned_skills()
        assert len(skills) == 1
        assert skills[0].name == "test_skill"

    def test_get_skill_by_name(self):
        """Test get_skill_by_name method."""
        curator = Curator()

        assert curator.get_skill_by_name("nonexistent") is None

        curator._learned_skills["test_skill"] = SynthesizedSkill(
            name="test_skill",
            description="test",
            trigger_patterns=[],
            action_template="",
            confidence=1.0,
        )

        skill = curator.get_skill_by_name("test_skill")
        assert skill is not None
        assert skill.name == "test_skill"


class TestCuratorProcessTrajectory:
    """Test process_trajectory method."""

    @pytest.mark.asyncio
    async def test_process_trajectory_success(self):
        """Test processing successful trajectory."""
        curator = Curator(enable_auto_learn=False)

        trajectory = {
            "trajectory_id": "process_test_1",
            "user_input": "查询天气",
            "messages": [
                {"role": "user", "content": "查询天气"},
                {"role": "assistant", "content": "<tool_call>get_weather</tool_call>"},
                {"role": "tool", "content": "sunny"},
            ],
            "steps": [
                {"type": "action", "data": {"tool_name": "get_weather", "parameters": {}}},
            ],
        }

        result = await curator.process_trajectory(trajectory)

        assert "evaluation" in result
        assert "skills" in result
        assert result["evaluation"].overall_result == EvaluationResult.SUCCESS

    @pytest.mark.asyncio
    async def test_process_trajectory_with_callback(self):
        """Test processing trajectory with evaluation callback."""
        curator = Curator(enable_auto_learn=False)
        callback = MagicMock()

        curator.add_evaluation_callback(callback)

        trajectory = {
            "trajectory_id": "process_test_2",
            "messages": [
                {"role": "user", "content": "测试"},
                {"role": "assistant", "content": "<tool_call>test</tool_call>"},
                {"role": "tool", "content": "success"},
            ],
            "steps": [
                {"type": "action", "data": {"tool_name": "test", "parameters": {}}},
            ],
        }

        await curator.process_trajectory(trajectory)

        callback.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_trajectory_with_async_callback(self):
        """Test processing trajectory with async callback."""
        curator = Curator(enable_auto_learn=False)
        callback = AsyncMock()

        curator.add_evaluation_callback(callback)

        trajectory = {
            "trajectory_id": "process_test_3",
            "messages": [
                {"role": "user", "content": "测试"},
                {"role": "assistant", "content": "<tool_call>test</tool_call>"},
                {"role": "tool", "content": "success"},
            ],
            "steps": [
                {"type": "action", "data": {"tool_name": "test", "parameters": {}}},
            ],
        }

        await curator.process_trajectory(trajectory)

        callback.assert_awaited_once()


class TestCuratorAutoLearn:
    """Test auto-learning functionality."""

    @pytest.mark.asyncio
    async def test_learn_skill_with_writer(self):
        """Test learning skill with skill writer."""
        mock_writer = AsyncMock()
        curator = Curator(skill_writer=mock_writer, enable_auto_learn=True)

        skill = SynthesizedSkill(
            name="test_skill",
            description="test",
            trigger_patterns=[],
            action_template="",
            confidence=1.0,
        )

        result = await curator.learn_skill(skill)

        assert result is True
        mock_writer.write.assert_awaited_once_with(skill)

    @pytest.mark.asyncio
    async def test_learn_skill_disabled(self):
        """Test learning when auto-learn is disabled."""
        mock_writer = AsyncMock()
        curator = Curator(skill_writer=mock_writer, enable_auto_learn=False)

        skill = SynthesizedSkill(
            name="test_skill",
            description="test",
            trigger_patterns=[],
            action_template="",
            confidence=1.0,
        )

        result = await curator.learn_skill(skill)

        assert result is False
        mock_writer.write.assert_not_called()

    @pytest.mark.asyncio
    async def test_learn_skill_no_writer(self):
        """Test learning without skill writer."""
        curator = Curator(enable_auto_learn=True)

        skill = SynthesizedSkill(
            name="test_skill",
            description="test",
            trigger_patterns=[],
            action_template="",
            confidence=1.0,
        )

        result = await curator.learn_skill(skill)

        assert result is False

    @pytest.mark.asyncio
    async def test_learn_from_feedback(self):
        """Test learn_from_feedback method."""
        curator = Curator()

        result = await curator.learn_from_feedback("traj_1", "good")

        assert result is None


class TestCuratorPeriodicReview:
    """Test periodic review mechanism."""

    @pytest.mark.asyncio
    async def test_start_stop_periodic_review(self):
        """Test starting and stopping periodic review."""
        curator = Curator(interval_hours=0.001)

        await curator.start_periodic_review()
        assert curator._running is True

        await curator.stop_periodic_review()
        assert curator._running is False

    @pytest.mark.asyncio
    async def test_run_review(self):
        """Test running a review."""
        curator = Curator()

        result = await curator.run_review()

        assert "started_at" in result
        assert "duration_seconds" in result
        assert "summary" in result
        assert result["dry_run"] is False

    @pytest.mark.asyncio
    async def test_run_review_dry_run(self):
        """Test running a dry run review."""
        curator = Curator()

        result = await curator.run_review(dry_run=True)

        assert result["dry_run"] is True
        assert result["summary"].startswith("[DRY RUN]")

    @pytest.mark.asyncio
    async def test_run_review_with_callback(self):
        """Test running review with callback."""
        curator = Curator()
        callback = MagicMock()

        await curator.run_review(on_summary=callback)

        callback.assert_called_once()


class TestCuratorConditionalRun:
    """Test conditional execution (idle gating)."""

    @pytest.mark.asyncio
    async def test_maybe_run_paused(self):
        """Test maybe_run when curator is paused."""
        curator = Curator()
        curator._state.set_paused(True)

        result = await curator.maybe_run(idle_for_seconds=3600)

        assert result is None

    @pytest.mark.asyncio
    async def test_maybe_run_not_enough_idle(self):
        """Test maybe_run when idle time is insufficient."""
        curator = Curator(min_idle_hours=5)

        result = await curator.maybe_run(idle_for_seconds=3600)

        assert result is None

    @pytest.mark.asyncio
    async def test_maybe_run_not_time_yet(self):
        """Test maybe_run when interval not reached."""
        curator = Curator(interval_hours=24)
        curator._state.last_run_at = datetime.now(timezone.utc).isoformat()

        result = await curator.maybe_run(idle_for_seconds=86400)

        assert result is None


class TestCuratorStatus:
    """Test status methods."""

    def test_pause_resume(self):
        """Test pause and resume methods."""
        curator = Curator()

        assert curator._state.paused is False

        curator.pause()
        assert curator._state.paused is True

        curator.resume()
        assert curator._state.paused is False

    def test_get_status(self):
        """Test get_status method."""
        curator = Curator()

        status = curator.get_status()

        assert "running" in status
        assert "paused" in status
        assert "interval_hours" in status
        assert "min_idle_hours" in status
        assert "run_count" in status


class TestCuratorGlobalInstance:
    """Test global curator instance."""

    def test_get_curator_singleton(self):
        """Test get_curator returns same instance."""
        curator1 = get_curator()
        curator2 = get_curator()

        assert curator1 is curator2

    def test_global_curator_has_default_config(self):
        """Test global curator has default configuration."""
        curator = get_curator()

        assert curator.enable_auto_learn is True
        assert curator.interval_hours == 24 * 7


if __name__ == "__main__":
    pytest.main([__file__, "-v"])