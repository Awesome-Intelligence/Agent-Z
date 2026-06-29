#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the modern_agent module.

Tests cover:
- Agent initialization
- Chat functionality
- Tool integration
- Response generation
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock
from dataclasses import asdict


class TestAgent:
    """Test suite for Agent."""

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        assert agent is not None
        assert hasattr(agent, 'engine')
        assert hasattr(agent, '_session')

    def test_agent_with_llm_provider(self):
        """Test agent initialization with LLM provider."""
        from agent.agent import Agent
        
        mock_llm = MagicMock()
        agent = Agent(llm_provider=mock_llm)
        
        assert agent.llm_provider is mock_llm

    def test_agent_without_session(self):
        """Test agent initialization without session."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=False)
        
        assert agent._session is None


class TestAgentChat:
    """Test chat functionality."""

    @pytest.mark.asyncio
    async def test_chat_returns_response(self):
        """Test that chat returns a response."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("打开计算器")
        
        assert response is not None
        assert hasattr(response, 'content')
        assert hasattr(response, 'tool_used')
        assert hasattr(response, 'confidence_score')

    @pytest.mark.asyncio
    async def test_chat_with_tool_execution(self):
        """Test chat with tool execution."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("打开计算器")
        
        # Should have executed a tool
        assert response.tool_used is not None or len(response.content) > 0

    @pytest.mark.asyncio
    async def test_chat_empty_input(self):
        """Test chat with empty input."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        # Should handle empty input gracefully
        response = await agent.chat("")
        
        assert response is not None

    @pytest.mark.asyncio
    async def test_chat_records_to_session(self):
        """Test that chat records to session."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=True)
        
        await agent.chat("打开计算器")
        
        # Session should have messages
        if agent._session:
            assert len(agent._session.messages) > 0


class TestAgentToolList:
    """Test tool listing functionality."""

    def test_get_tool_list(self):
        """Test getting list of tools."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        tools = agent.get_tool_list()
        
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_tool_list_has_required_fields(self):
        """Test that tool list has required fields."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        tools = agent.get_tool_list()
        
        for tool in tools:
            assert 'name' in tool
            assert 'description' in tool


class TestAgentResponse:
    """Test response structure."""

    def test_response_has_required_fields(self):
        """Test that response has required fields."""
        from agent.agent import AgentResponse
        
        response = AgentResponse(
            content="Test response",
            tool_used="open_calculator",
            confidence_score=0.9
        )
        
        assert response.content == "Test response"
        assert response.tool_used == "open_calculator"
        assert response.confidence_score == 0.9

    def test_response_defaults(self):
        """Test response default values."""
        from agent.agent import AgentResponse
        
        response = AgentResponse(content="Test")
        
        assert response.tool_used is None
        assert response.tool_result is None
        assert response.confidence_score == 1.0


class TestAgentIntegration:
    """Test integration with other modules."""

    def test_agent_uses_integrated_engine(self):
        """Test that agent uses integrated engine."""
        from agent.agent import Agent
        from tools.integrated_tools import get_integrated_engine

        agent = Agent(llm_provider=None)

        # Agent should have the integrated engine
        assert agent.engine is not None

        # Engine should be the same as get_integrated_engine
        expected_engine = get_integrated_engine()
        assert agent.engine is expected_engine

    def test_agent_initializes_tools(self):
        """Test that agent initializes tools."""
        from agent.agent import Agent
        from tools.integrated_tools import initialize_tools

        initialize_tools()

        agent = Agent(llm_provider=None)

        # Should have tools registered
        assert len(agent.engine.tool_selector.tools) > 0


class TestIsComplexTask:
    """Test _is_complex_task method for task complexity detection."""

    def test_empty_input(self):
        """Test that empty input returns False."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent._is_complex_task("") is False
        assert agent._is_complex_task(None) is False

    def test_short_greeting(self):
        """Test that short greeting returns False."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent._is_complex_task("你好") is False
        assert agent._is_complex_task("hi") is False

    def test_simple_question(self):
        """Test that simple question returns False."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent._is_complex_task("今天天气怎么样?") is False
        assert agent._is_complex_task("什么是 Python?") is False
        assert agent._is_complex_task("你好吗?") is False

    def test_complex_task_keywords(self):
        """Test that complex task keywords return True."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)

        # Writing tasks
        assert agent._is_complex_task("帮我写一个博客系统") is True
        assert agent._is_complex_task("请帮我写一段代码") is True
        assert agent._is_complex_task("写代码实现快速排序") is True

        # Building tasks
        assert agent._is_complex_task("实现一个用户认证系统") is True
        assert agent._is_complex_task("创建一个项目管理系统") is True
        assert agent._is_complex_task("开发一个博客应用") is True

        # Analysis tasks
        assert agent._is_complex_task("分析这段代码有什么问题") is True
        assert agent._is_complex_task("帮我优化一下这段代码") is True

    def test_long_text(self):
        """Test that very long text returns True."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        long_text = "a" * 250
        assert agent._is_complex_task(long_text) is True

    def test_question_with_action(self):
        """Test that question with action keywords returns True."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent._is_complex_task("能不能帮我分析一下这个问题") is True
        assert agent._is_complex_task("请帮我修改这段代码") is True

    def test_only_question_mark(self):
        """Test that single question mark returns False."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        assert agent._is_complex_task("?") is False


class TestGoalCommand:
    """Test /goal command detection."""

    def test_goal_command_with_text(self):
        """Test /goal command with text returns 'new' and goal text."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        cmd_type, goal_text = agent._is_goal_command("/goal 帮我写一个博客系统")

        assert cmd_type == "new"
        assert goal_text == "帮我写一个博客系统"

    def test_goal_command_with_long_text(self):
        """Test /goal command with long text."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        long_goal = "/goal " + "实现一个" + "用户认证" * 50
        cmd_type, goal_text = agent._is_goal_command(long_goal)

        assert cmd_type == "new"
        assert goal_text.startswith("实现一个用户认证")

    def test_goal_command_empty_no_last_goal(self):
        """Test /goal command without text and no last goal returns 'continue' with None."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        agent._last_goal = None
        cmd_type, goal_text = agent._is_goal_command("/goal")

        assert cmd_type == "continue"
        assert goal_text is None

    def test_goal_command_empty_with_last_goal(self):
        """Test /goal command without text but with last goal returns 'continue' with goal text."""
        from agent.agent import Agent
        from agent.agent import GoalState

        agent = Agent(llm_provider=None)
        agent._last_goal = GoalState(goal_text="上次的目标", turns=5)
        cmd_type, goal_text = agent._is_goal_command("/goal")

        assert cmd_type == "continue"
        assert goal_text == "上次的目标"

    def test_goal_command_with_extra_spaces(self):
        """Test /goal command with extra spaces."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        cmd_type, goal_text = agent._is_goal_command("/goal   帮我写代码  ")

        assert cmd_type == "new"
        assert goal_text == "帮我写代码"

    def test_regular_input_not_goal(self):
        """Test that regular input is not detected as goal command."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        cmd_type, goal_text = agent._is_goal_command("帮我写一个博客系统")

        assert cmd_type == ""
        assert goal_text is None

    def test_goal_with_prefix(self):
        """Test /goal at middle of text is not detected."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        cmd_type, goal_text = agent._is_goal_command("请使用 /goal 帮我完成任务")

        assert cmd_type == ""
        assert goal_text is None

    def test_empty_input(self):
        """Test that empty input returns empty string."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        cmd_type, goal_text = agent._is_goal_command("")

        assert cmd_type == ""
        assert goal_text is None


class TestSubgoalCommand:
    """Test /subgoal command detection."""

    def test_subgoal_command_with_text(self):
        """Test /subgoal command with text returns True and subgoal text."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("/subgoal 需要支持用户登录")

        assert is_subgoal is True
        assert subgoal_text == "需要支持用户登录"

    def test_subgoal_command_with_long_text(self):
        """Test /subgoal command with long text."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        long_subgoal = "/subgoal " + "这是一个很长的子目标描述" * 20
        is_subgoal, subgoal_text = agent._is_subgoal_command(long_subgoal)

        assert is_subgoal is True
        assert "这是一个很长的子目标描述" in subgoal_text

    def test_subgoal_command_empty(self):
        """Test /subgoal command without text returns True with None."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("/subgoal")

        assert is_subgoal is True
        assert subgoal_text is None

    def test_subgoal_command_with_extra_spaces(self):
        """Test /subgoal command with extra spaces."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("/subgoal   需要支持用户登录  ")

        assert is_subgoal is True
        assert subgoal_text == "需要支持用户登录"

    def test_regular_input_not_subgoal(self):
        """Test that regular input is not detected as subgoal command."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("需要支持用户登录")

        assert is_subgoal is False
        assert subgoal_text is None

    def test_goal_command_not_subgoal(self):
        """Test that /goal is not detected as /subgoal."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("/goal 需要支持用户登录")

        assert is_subgoal is False
        assert subgoal_text is None

    def test_empty_input(self):
        """Test that empty input returns False."""
        from agent.agent import Agent

        agent = Agent(llm_provider=None)
        is_subgoal, subgoal_text = agent._is_subgoal_command("")

        assert is_subgoal is False
        assert subgoal_text is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
