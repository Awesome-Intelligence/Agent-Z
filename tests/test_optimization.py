"""
测试优化修改后的核心组件

包含以下测试：
1. AgentState 统一状态管理器测试
2. 状态管理统一测试
3. TrajectoryRecorder 只读模式测试
4. RailRegistry 单例测试
5. 验证模块导入

注意：已删除废弃的 BudgetController, InterruptController, LoopExitChecker
请使用 agent.state.AgentState 作为统一状态管理器
"""

import time
import pytest


class TestAgentStateIteration:
    """测试 AgentState 迭代模式预算"""

    def test_iteration_mode(self):
        """测试 AgentState 迭代模式预算"""
        from agent.state import AgentState

        state = AgentState(max_iterations=5)
        assert state.can_iterate() == True
        assert state.budget_remaining == 5

        state.consume()
        assert state.budget_remaining == 4
        assert state.can_iterate() == True

        # 耗尽预算
        for _ in range(4):
            state.consume()

        assert state.can_iterate() == False
        assert state.budget_remaining == 0

        # 测试 reset
        state.reset()
        assert state.can_iterate() == True
        assert state.budget_remaining == 5


class TestAgentStateTurn:
    """测试 AgentState 轮次模式预算"""

    def test_turn_mode(self):
        """测试 AgentState 轮次模式预算（通过 GoalManager，参考 Hermes）"""
        from agent.state import AgentState, BudgetMode
        from agent.goal import GoalManager

        state = AgentState(max_iterations=20, max_turns=10)
        manager = GoalManager()
        state.set_goal_manager(manager)

        # 通过 GoalManager 设置 Goal 启用轮次模式
        manager.set("Test goal", max_turns=10)
        state.sync_from_goal_state(manager.state)

        assert state.is_goal_mode == True
        assert state.budget_mode == BudgetMode.TURN
        assert state.budget_remaining == 10

        state.consume()
        assert state.budget_remaining == 9
        assert state.can_iterate() == True

        # 耗尽预算
        for _ in range(9):
            state.consume()

        assert state.can_iterate() == False
        assert state.budget_remaining == 0

        # 清除 Goal 恢复迭代模式
        manager.clear()
        assert state.is_goal_mode == False
        assert state.budget_mode == BudgetMode.ITERATION


class TestAgentStateInterrupt:
    """测试 AgentState 中断功能"""

    def test_interrupt_controller(self):
        """测试 AgentState 中断功能"""
        from agent.state import AgentState, AgentStatus

        state = AgentState()

        # 初始状态
        assert state.is_interrupt_requested == False
        assert state.interrupt_reason is None
        assert state.status == AgentStatus.IDLE

        # 请求中断
        state.request_interrupt("test_reason")
        assert state.is_interrupt_requested == True
        assert state.interrupt_reason == "test_reason"

        # 清除中断
        state.clear_interrupt()
        assert state.is_interrupt_requested == False
        assert state.interrupt_reason is None


class TestAgentStateStateTransitions:
    """测试 AgentState 状态转换"""

    def test_state_transitions(self):
        """测试 AgentState 状态转换"""
        from agent.state import AgentState, AgentStatus

        state = AgentState()

        # 初始状态
        assert state.status == AgentStatus.IDLE

        # Start
        state.start()
        assert state.status == AgentStatus.RUNNING

        # Pause
        state.pause("user_paused")
        assert state.status == AgentStatus.PAUSED

        # Resume
        state.resume()
        assert state.status == AgentStatus.RUNNING

        # Complete
        state.complete()
        assert state.status == AgentStatus.COMPLETED

        # Reset
        state.reset()
        assert state.status == AgentStatus.IDLE


class TestAgentStateExitDecision:
    """测试 AgentState 退出决策"""

    def test_should_exit_direct_response(self):
        """测试 LLM 直接响应时退出"""
        from agent.state import AgentState, ExitReason
        from agent.execution.loop import LoopStepResult

        state = AgentState(max_iterations=10)
        state.start()

        step_result = LoopStepResult(
            step=1,
            action="direct_response",
            result="This is my answer"
        )

        decision = state.should_exit(step_result)
        assert decision.should_exit == True
        assert decision.reason == ExitReason.DIRECT_RESPONSE

    def test_should_exit_error(self):
        """测试错误时退出"""
        from agent.state import AgentState, ExitReason
        from agent.execution.loop import LoopStepResult

        state = AgentState(max_iterations=10)
        state.start()

        step_result = LoopStepResult(
            step=1,
            action="error",
            result={"error": "Something went wrong"}
        )

        decision = state.should_exit(step_result)
        assert decision.should_exit == True
        assert decision.reason == ExitReason.ERROR

    def test_should_exit_budget_exhausted(self):
        """测试预算耗尽时退出"""
        from agent.state import AgentState, ExitReason
        from agent.execution.loop import LoopStepResult

        state = AgentState(max_iterations=1)
        state.start()
        state.consume()  # 耗尽预算

        step_result = LoopStepResult(
            step=1,
            action="tool_call",
            tool_name="test_tool"
        )

        decision = state.should_exit(step_result)
        assert decision.should_exit == True
        assert decision.reason == ExitReason.BUDGET_EXHAUSTED

    def test_should_exit_interrupt(self):
        """测试中断时退出"""
        from agent.state import AgentState, ExitReason
        from agent.execution.loop import LoopStepResult

        state = AgentState(max_iterations=10)
        state.start()
        state.request_interrupt("user_cancelled")

        step_result = LoopStepResult(
            step=1,
            action="tool_call",
            tool_name="test_tool"
        )

        decision = state.should_exit(step_result)
        assert decision.should_exit == True
        assert decision.reason == ExitReason.INTERRUPTED


class TestTrajectoryRecorder:
    """测试 TrajectoryRecorder 只读模式"""

    def test_trajectory_recorder_readonly(self):
        """测试 TrajectoryRecorder 只读模式"""
        from agent.curator.trajectory_recorder import TrajectoryRecorder
        from agent.session import Session, Message

        # 创建 mock session
        class MockSession:
            def __init__(self):
                self.messages = [
                    Message(role="user", content="Hello", timestamp=time.time()),
                    Message(role="assistant", content="Hi there", timestamp=time.time()),
                ]

            def get_history(self):
                return self.messages

        mock_session = MockSession()
        recorder = TrajectoryRecorder(session=mock_session)

        # 测试从 Session 读取消息
        trajectory = recorder.get_trajectory()
        assert len(trajectory["messages"]) == 2
        assert trajectory["messages"][0]["content"] == "Hello"
        assert trajectory["messages"][1]["content"] == "Hi there"

        # 测试无 session 情况
        recorder2 = TrajectoryRecorder()
        trajectory2 = recorder2.get_trajectory()
        assert len(trajectory2["messages"]) == 0


class TestRailRegistry:
    """测试 RailRegistry 单例"""

    def test_rail_registry(self):
        """测试 RailRegistry 单例"""
        from agent.rails.registry import RailRegistry, get_rail_registry

        # 测试单例
        registry1 = RailRegistry()
        registry2 = RailRegistry()
        assert registry1 is registry2

        # 测试 get_rail_registry 函数
        registry3 = get_rail_registry()
        assert registry3 is registry1

        # 测试注册和获取
        class MockRail:
            def __init__(self, name):
                self.name = name

        rail1 = MockRail("rail1")
        rail2 = MockRail("rail2")

        registry1.register("session_123", rail1)
        rails = registry1.get_rails("session_123")
        assert len(rails) == 1
        assert rails[0] is rail1

        # 测试重复注册不会添加
        registry1.register("session_123", rail1)
        rails = registry1.get_rails("session_123")
        assert len(rails) == 1  # 仍然是 1

        # 测试取消注册
        registry1.unregister("session_123", rail1)
        rails = registry1.get_rails("session_123")
        assert len(rails) == 0

        # 测试不存在 session
        rails = registry1.get_rails("nonexistent")
        assert len(rails) == 0


class TestModuleImports:
    """验证模块导入"""

    def test_module_imports(self):
        """验证所有模块可以正确导入"""
        from agent.state import AgentState, AgentStatus, ExitDecision, ExitReason, BudgetMode
        from agent.rails.registry import RailRegistry, get_rail_registry
        from agent.curator.trajectory_recorder import TrajectoryRecorder
        from agent.execution.loop import AgentLoop, LoopState, LoopStepResult

        # 验证类存在
        assert AgentState is not None
        assert AgentStatus is not None
        assert ExitDecision is not None
        assert ExitReason is not None
        assert BudgetMode is not None
        assert RailRegistry is not None
        assert TrajectoryRecorder is not None
        assert AgentLoop is not None
        assert LoopState is not None
        assert LoopStepResult is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])