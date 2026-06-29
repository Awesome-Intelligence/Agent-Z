#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for AgentState unified state management.

Tests cover:
- AgentState initialization
- Status transitions
- Budget management
- Goal management
- Exit decision logic
"""

import pytest
import asyncio
from unittest.mock import MagicMock


class TestAgentStatus:
    """Test suite for AgentStatus enum."""

    def test_agent_status_values(self):
        """Test AgentStatus enum values."""
        from agent.state import AgentStatus
        
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.PAUSED.value == "paused"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ABORTED.value == "aborted"

    def test_is_active(self):
        """Test is_active method."""
        from agent.state import AgentStatus
        
        assert AgentStatus.IDLE.is_active() is True
        assert AgentStatus.RUNNING.is_active() is True
        assert AgentStatus.PAUSED.is_active() is True
        assert AgentStatus.COMPLETED.is_active() is False
        assert AgentStatus.ABORTED.is_active() is False

    def test_is_terminal(self):
        """Test is_terminal method."""
        from agent.state import AgentStatus
        
        assert AgentStatus.IDLE.is_terminal() is False
        assert AgentStatus.RUNNING.is_terminal() is False
        assert AgentStatus.PAUSED.is_terminal() is False
        assert AgentStatus.COMPLETED.is_terminal() is True
        assert AgentStatus.ABORTED.is_terminal() is True


class TestAgentStateInit:
    """Test suite for AgentState initialization."""

    def test_agent_state_default_init(self):
        """Test AgentState with default values."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        
        assert state.status == AgentStatus.IDLE
        assert state.is_idle is True
        assert state.is_running is False
        assert state.is_active is True
        assert state.is_terminal is False
        assert state.goal is None
        assert state.is_goal_mode is False

    def test_agent_state_with_params(self):
        """Test AgentState with custom parameters."""
        from agent.state import AgentState
        
        state = AgentState(max_iterations=50, max_turns=30)
        
        assert state.budget_max == 50  # Default is iteration mode
        assert state.is_goal_mode is False

    def test_budget_properties(self):
        """Test budget properties."""
        from agent.state import AgentState
        
        state = AgentState(max_iterations=10)
        
        assert state.budget_used == 0
        assert state.budget_max == 10
        assert state.budget_remaining == 10
        assert state.can_iterate() is True


class TestAgentStateTransitions:
    """Test suite for AgentState transitions."""

    def test_start_transition(self):
        """Test start() transition."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        
        assert state.status == AgentStatus.RUNNING
        assert state.is_running is True

    def test_pause_resume_transition(self):
        """Test pause() and resume() transitions."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        state.pause("test_pause")
        
        assert state.status == AgentStatus.PAUSED
        assert state.is_paused is True
        
        state.resume()
        assert state.status == AgentStatus.RUNNING

    def test_complete_transition(self):
        """Test complete() transition."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        state.complete("task_done")
        
        assert state.status == AgentStatus.COMPLETED
        assert state.is_completed is True

    def test_abort_transition(self):
        """Test abort() transition."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        state.abort("error_occurred")
        
        assert state.status == AgentStatus.ABORTED
        assert state.is_aborted is True
        assert state.interrupt_reason == "error_occurred"

    def test_reset_transition(self):
        """Test reset() transition."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        state.complete("done")
        state.reset()
        
        assert state.status == AgentStatus.IDLE
        assert state.is_idle is True

    def test_status_history(self):
        """Test status history recording."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        state.start()
        state.pause("test")
        state.resume()
        
        assert len(state.status_history) == 3  # IDLE->RUNNING, RUNNING->PAUSED, PAUSED->RUNNING


class TestAgentStateBudget:
    """Test suite for AgentState budget management."""

    def test_consume_budget(self):
        """Test budget consumption."""
        from agent.state import AgentState
        
        state = AgentState(max_iterations=5)
        state.start()
        
        assert state.consume() == 1
        assert state.budget_used == 1
        assert state.budget_remaining == 4
        
        state.consume()
        state.consume()
        assert state.budget_used == 3
        assert state.budget_remaining == 2

    def test_budget_exhaustion(self):
        """Test budget exhaustion."""
        from agent.state import AgentState
        
        state = AgentState(max_iterations=3)
        state.start()
        
        state.consume()
        state.consume()
        assert state.can_iterate() is True
        
        state.consume()  # 3rd consumption
        assert state.can_iterate() is False
        assert state.budget_remaining == 0

    def test_budget_thread_safety(self):
        """Test budget is thread-safe."""
        import threading
        from agent.state import AgentState
        
        state = AgentState(max_iterations=1000)
        state.start()
        
        def consume():
            for _ in range(100):
                state.consume()
        
        threads = [threading.Thread(target=consume) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert state.budget_used == 1000

    def test_get_budget_status(self):
        """Test budget status string."""
        from agent.state import AgentState
        
        state = AgentState(max_iterations=10)
        state.start()
        
        assert state.get_budget_status() == "迭代: 0/10"
        
        state.consume()
        assert state.get_budget_status() == "迭代: 1/10"


class TestAgentStateGoal:
    """Test suite for AgentState goal management (delegated to GoalManager)."""

    def test_goal_mode_via_goal_manager(self):
        """Test goal mode through GoalManager (参考 Hermes)."""
        from agent.state import AgentState
        from agent.goal import GoalManager
        
        state = AgentState(max_turns=20)
        manager = GoalManager()
        state.set_goal_manager(manager)
        
        # 通过 GoalManager 设置 Goal
        manager.set("Complete the task")
        
        # 同步预算信息
        state.sync_from_goal_state(manager.state)
        
        # 验证状态代理
        assert state.goal is not None
        assert state.goal.goal == "Complete the task"
        assert state.is_goal_mode is True

    def test_clear_goal_via_goal_manager(self):
        """Test clearing goal through GoalManager."""
        from agent.state import AgentState
        from agent.goal import GoalManager
        
        state = AgentState()
        manager = GoalManager()
        state.set_goal_manager(manager)
        
        manager.set("Test goal")
        manager.clear()
        
        assert state.goal is None
        assert state.is_goal_mode is False

    def test_pause_resume_goal_via_goal_manager(self):
        """Test pausing and resuming goal through GoalManager."""
        from agent.state import AgentState
        from agent.goal import GoalManager
        
        state = AgentState()
        manager = GoalManager()
        state.set_goal_manager(manager)
        
        manager.set("Test goal")
        manager.pause("user_paused")
        
        assert state.goal.status == "paused"
        
        manager.resume()
        assert state.goal.status == "active"

    def test_is_goal_mode_without_goal_manager(self):
        """Test is_goal_mode when no GoalManager is set."""
        from agent.state import AgentState
        
        state = AgentState()
        
        # 没有 GoalManager 时，is_goal_mode 应返回 False
        assert state.goal is None
        assert state.is_goal_mode is False


class TestAgentStateInterrupt:
    """Test suite for AgentState interrupt handling."""

    def test_request_interrupt(self):
        """Test requesting an interrupt."""
        from agent.state import AgentState
        
        state = AgentState()
        state.request_interrupt("user_cancel")
        
        assert state.is_interrupt_requested is True
        assert state.interrupt_reason == "user_cancel"

    def test_clear_interrupt(self):
        """Test clearing an interrupt."""
        from agent.state import AgentState
        
        state = AgentState()
        state.request_interrupt("test")
        state.clear_interrupt()
        
        assert state.is_interrupt_requested is False
        assert state.interrupt_reason is None


class TestAgentStateExitDecision:
    """Test suite for AgentState exit decision logic."""

    def test_exit_on_direct_response(self):
        """Test exit decision on direct_response action."""
        from agent.state import AgentState, ExitReason
        
        state = AgentState(max_iterations=10)
        state.start()
        
        # Mock step result
        mock_result = MagicMock()
        mock_result.action = "direct_response"
        mock_result.result = "This is a response"
        
        decision = state.should_exit(mock_result)
        
        assert decision.should_exit is True
        assert decision.reason == ExitReason.DIRECT_RESPONSE

    def test_exit_on_error(self):
        """Test exit decision on error action."""
        from agent.state import AgentState, ExitReason
        
        state = AgentState(max_iterations=10)
        state.start()
        
        mock_result = MagicMock()
        mock_result.action = "error"
        mock_result.result = {"error": "Something went wrong"}
        
        decision = state.should_exit(mock_result)
        
        assert decision.should_exit is True
        assert decision.reason == ExitReason.ERROR

    def test_continue_on_tool_call(self):
        """Test continue decision on tool_call action."""
        from agent.state import AgentState, ExitReason
        
        state = AgentState(max_iterations=10)
        state.start()
        
        mock_result = MagicMock()
        mock_result.action = "tool_call"
        mock_result.result = {"success": True}
        
        decision = state.should_exit(mock_result)
        
        assert decision.should_exit is False
        assert decision.reason == ExitReason.UNKNOWN

    def test_exit_on_budget_exhausted(self):
        """Test exit decision on budget exhaustion."""
        from agent.state import AgentState, ExitReason
        
        state = AgentState(max_iterations=2)
        state.start()
        
        state.consume()
        state.consume()
        
        mock_result = MagicMock()
        mock_result.action = "tool_call"
        
        decision = state.should_exit(mock_result)
        
        assert decision.should_exit is True
        assert decision.reason == ExitReason.BUDGET_EXHAUSTED

    def test_exit_on_interrupt(self):
        """Test exit decision on interrupt."""
        from agent.state import AgentState, ExitReason
        
        state = AgentState(max_iterations=10)
        state.start()
        state.request_interrupt("user_cancel")
        
        mock_result = MagicMock()
        mock_result.action = "tool_call"
        
        decision = state.should_exit(mock_result)
        
        assert decision.should_exit is True
        assert decision.reason == ExitReason.INTERRUPTED


class TestAgentStateListener:
    """Test suite for AgentState listener functionality."""

    def test_add_remove_listener(self):
        """Test adding and removing listeners."""
        from agent.state import AgentState, AgentStatus
        
        state = AgentState()
        transitions = []
        
        def listener(old, new, reason):
            transitions.append((old, new, reason))
        
        state.add_listener(listener)
        state.start()
        state.complete("done")
        
        assert len(transitions) == 2
        assert transitions[0][0] == AgentStatus.IDLE
        assert transitions[0][1] == AgentStatus.RUNNING
        assert transitions[1][0] == AgentStatus.RUNNING
        assert transitions[1][1] == AgentStatus.COMPLETED
        
        state.remove_listener(listener)
        state.reset()
        state.start()
        
        assert len(transitions) == 2  # No new transitions


class TestAgentStateSerialization:
    """Test suite for AgentState serialization."""

    def test_to_dict(self):
        """Test serialization to dictionary."""
        from agent.state import AgentState, AgentStatus
        from agent.goal import GoalManager
        
        state = AgentState(max_iterations=10)
        manager = GoalManager()
        state.set_goal_manager(manager)
        
        # 通过 GoalManager 设置 Goal
        manager.set("Test goal", max_turns=20)
        state.sync_from_goal_state(manager.state)
        
        state.start()
        
        data = state.to_dict()
        
        assert data["status"] == "running"
        assert data["is_goal_mode"] is True
        assert data["budget_mode"] == "turn"
        assert data["budget_used"] == 0
        assert data["budget_max"] == 20  # max_turns for goal mode
        assert data["interrupt_requested"] is False
        assert data["goal"] is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])