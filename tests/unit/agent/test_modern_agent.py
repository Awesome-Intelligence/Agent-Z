#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the modern_agent module.

Tests cover:
- Agent initialization
- Chat functionality
- Tool integration
- Response generation
- Interrupt handling
- State management
- Session management
- Goal commands
"""

import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
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
        assert hasattr(agent, '_state')
        assert hasattr(agent, '_goal_manager')
        assert hasattr(agent, '_context_manager')
        assert hasattr(agent, '_context_compressor')

    def test_agent_with_llm_provider(self):
        """Test agent initialization with LLM provider."""
        from agent.agent import Agent
        
        mock_llm = MagicMock()
        mock_llm.model = "gpt-4o"
        agent = Agent(llm_provider=mock_llm)
        
        assert agent.llm_provider is mock_llm
        assert agent._context_compressor.model == "gpt-4o"

    def test_agent_without_session(self):
        """Test agent initialization without session."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=False)
        
        assert agent._session is None

    def test_agent_with_custom_session_id(self):
        """Test agent initialization with custom session ID."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, session_id="test_session_123")
        
        assert agent._session is not None
        assert agent._session.session_id == "test_session_123"

    def test_agent_with_force_new_session(self):
        """Test agent initialization with force_new_session."""
        from agent.agent import Agent
        
        agent1 = Agent(llm_provider=None)
        session_id1 = agent1._session.session_id
        
        agent2 = Agent(llm_provider=None, force_new_session=True)
        session_id2 = agent2._session.session_id
        
        assert session_id1 != session_id2

    def test_agent_interrupt_methods(self):
        """Test interrupt methods."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        assert agent.is_interrupted() is False
        
        agent.interrupt()
        assert agent.is_interrupted() is True
        
        agent.clear_interrupt()
        assert agent.is_interrupted() is False

    def test_agent_state_property(self):
        """Test state property returns AgentState."""
        from agent.agent import Agent
        from agent.state import AgentState
        
        agent = Agent(llm_provider=None)
        
        assert isinstance(agent.state, AgentState)
        assert agent.state is agent._state


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
        assert hasattr(response, 'execution_time')
        assert hasattr(response, 'metadata')

    @pytest.mark.asyncio
    async def test_chat_with_tool_execution(self):
        """Test chat with tool execution."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("打开计算器")
        
        assert response.tool_used is not None or len(response.content) > 0

    @pytest.mark.asyncio
    async def test_chat_empty_input(self):
        """Test chat with empty input."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("")
        
        assert response is not None
        assert response.content is not None

    @pytest.mark.asyncio
    async def test_chat_records_to_session(self):
        """Test that chat records to session."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=True)
        
        await agent.chat("打开计算器")
        
        if agent._session:
            assert len(agent._session.messages) > 0

    @pytest.mark.asyncio
    async def test_chat_with_conversation_history(self):
        """Test chat with provided conversation history."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=False)
        
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好！我是你的助手。"}
        ]
        
        response = await agent.chat("今天天气怎么样?", conversation_history=history)
        
        assert response is not None

    @pytest.mark.asyncio
    async def test_chat_execution_time(self):
        """Test that chat tracks execution time."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("你好")
        
        assert response.execution_time > 0


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
            assert 'category' in tool


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
        assert response.metadata == {}
        assert response.execution_time == 0.0

    def test_response_with_metadata(self):
        """Test response with custom metadata."""
        from agent.agent import AgentResponse
        
        response = AgentResponse(
            content="Test",
            metadata={"iterations": 5, "final_action": "direct_response"}
        )
        
        assert response.metadata["iterations"] == 5
        assert response.metadata["final_action"] == "direct_response"


class TestAgentIntegration:
    """Test integration with other modules."""

    def test_agent_uses_integrated_engine(self):
        """Test that agent uses integrated engine."""
        from agent.agent import Agent
        from tools.integrated_tools import get_integrated_engine

        agent = Agent(llm_provider=None)

        assert agent.engine is not None
        expected_engine = get_integrated_engine()
        assert agent.engine is expected_engine

    def test_agent_initializes_tools(self):
        """Test that agent initializes tools."""
        from agent.agent import Agent
        from tools.integrated_tools import initialize_tools

        initialize_tools()

        agent = Agent(llm_provider=None)

        assert len(agent.engine.tool_selector.tools) > 0

    def test_agent_initializes_context_components(self):
        """Test that agent initializes context components."""
        from agent.agent import Agent
        from agent.context.context_builder import ContextBuilder
        from agent.context.context_compressor import ContextCompressor
        from agent.context.context_manager import ContextManager

        agent = Agent(llm_provider=None)

        assert isinstance(agent._context_builder, ContextBuilder)
        assert isinstance(agent._context_compressor, ContextCompressor)
        assert isinstance(agent._context_manager, ContextManager)


class TestAgentSessionMessages:
    """Test _get_session_messages method."""

    def test_get_session_messages_with_session(self):
        """Test getting messages from session."""
        from agent.agent import Agent
        from agent.session import Session, SessionConfig
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(history_path=tmpdir, enable_persistence=False)
            session = Session("test_session", config=config)
            session.add_message("user", "Hello")
            session.add_message("assistant", "Hi!")

            agent = Agent(llm_provider=None, enable_session=False)
            agent._session = session

            messages = agent._get_session_messages()

            assert len(messages) == 2
            assert messages[0]["role"] == "user"
            assert messages[0]["content"] == "Hello"
            assert messages[1]["role"] == "assistant"
            assert messages[1]["content"] == "Hi!"

    def test_get_session_messages_with_tool_calls(self):
        """Test getting messages with tool calls from session."""
        from agent.agent import Agent
        from agent.session import Session, SessionConfig
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            config = SessionConfig(history_path=tmpdir, enable_persistence=False)
            session = Session("test_session", config=config)
            session.add_message(
                "assistant",
                "",
                tool_calls=[{"id": "call_1", "type": "function", "function": {"name": "test_tool", "arguments": "{}"}}],
                tool_call_id=None
            )
            session.add_message("tool", "result", tool_call_id="call_1")

            agent = Agent(llm_provider=None, enable_session=False)
            agent._session = session

            messages = agent._get_session_messages()

            assert len(messages) == 2
            assert "tool_calls" in messages[0]
            assert messages[1]["tool_call_id"] == "call_1"

    def test_get_session_messages_without_session(self):
        """Test getting messages when no session."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None, enable_session=False)
        
        messages = agent._get_session_messages()
        
        assert messages == []


class TestGoalCommand:
    """Test /goal command handling in Agent."""

    @pytest.mark.asyncio
    async def test_goal_command_create(self):
        """Test /goal command creates goal."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        response = await agent.chat("/goal 帮我写一个博客系统")
        
        assert response is not None
        assert agent._goal_manager.is_active() is True
        assert agent._goal_manager.state.goal == "帮我写一个博客系统"

    @pytest.mark.asyncio
    async def test_goal_command_resume(self):
        """Test /goal resume command."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        await agent.chat("/goal 测试目标")
        agent._goal_manager.pause()
        
        response = await agent.chat("/goal resume")
        
        assert response is not None
        assert agent._goal_manager.is_active() is True

    @pytest.mark.asyncio
    async def test_goal_command_clear(self):
        """Test /goal clear command."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        await agent.chat("/goal 测试目标")
        
        response = await agent.chat("/goal clear")
        
        assert response is not None
        assert agent._goal_manager.is_active() is False

    @pytest.mark.asyncio
    async def test_goal_command_pause(self):
        """Test /goal pause command."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        await agent.chat("/goal 测试目标")
        
        response = await agent.chat("/goal pause")
        
        assert response is not None
        assert agent._goal_manager.state.status == "paused"


class TestAgentStreamCallbacks:
    """Test stream callback functionality."""

    def test_set_stream_callback(self):
        """Test setting stream callback."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        callback = MagicMock()
        
        agent.set_stream_callback(callback)
        
        assert agent._stream_callback is callback

    def test_set_thinking_callback(self):
        """Test setting thinking callback."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        callback = MagicMock()
        
        agent.set_thinking_callback(callback)
        
        assert agent._thinking_callback is callback

    def test_set_stream_emitter(self):
        """Test setting stream emitter."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        emitter = MagicMock()
        
        agent.set_stream_emitter(emitter)
        
        assert agent._stream_emitter is emitter

    def test_emit_stream(self):
        """Test emitting stream data."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        callback = MagicMock()
        emitter = MagicMock()
        
        agent.set_stream_callback(callback)
        agent.set_stream_emitter(emitter)
        
        agent._emit_stream("test text")
        
        callback.assert_called_once_with("test text")
        emitter.emit_delta.assert_called_once_with("test text")


class TestAgentRails:
    """Test Rails registration."""

    def test_ensure_rails_registered(self):
        """Test that rails are registered."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        session_id = "test_session"
        agent._ensure_rails_registered(session_id)
        
        assert session_id in agent._rails_registered_sessions

    def test_ensure_rails_registered_idempotent(self):
        """Test that rails registration is idempotent."""
        from agent.agent import Agent
        
        agent = Agent(llm_provider=None)
        
        session_id = "test_session"
        agent._ensure_rails_registered(session_id)
        agent._ensure_rails_registered(session_id)
        
        assert len(agent._rails_registered_sessions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])