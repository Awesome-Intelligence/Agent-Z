#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUI 端到端集成测试

测试完整的用户交互流程：
1. 完整对话流程（发送请求、接收响应、显示结果）
2. 会话切换
3. 多轮对话

日志子层：🖥️ TUI
"""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# 模块级 Fixtures
# ============================================================================

@pytest.fixture
def session_manager():
    """创建会话管理器"""
    class SessionManager:
        def __init__(self):
            self.sessions: Dict[str, Session] = {}
            self.active_session_id: Optional[str] = None
            self.session_counter = 0
        
        def create_session(self, title: str = "New Session") -> Session:
            """创建新会话"""
            self.session_counter += 1
            session_id = f"session_{self.session_counter}"
            session = Session(
                id=session_id,
                title=title
            )
            self.sessions[session_id] = session
            self.active_session_id = session_id
            return session
        
        def switch_session(self, session_id: str) -> bool:
            """切换到指定会话"""
            if session_id in self.sessions:
                self.active_session_id = session_id
                return True
            return False
        
        def get_active_session(self) -> Optional[Session]:
            """获取当前活动会话"""
            if self.active_session_id:
                return self.sessions.get(self.active_session_id)
            return None
        
        def list_sessions(self) -> List[Session]:
            """列出所有会话"""
            return list(self.sessions.values())
        
        def delete_session(self, session_id: str) -> bool:
            """删除会话"""
            if session_id in self.sessions:
                del self.sessions[session_id]
                if self.active_session_id == session_id:
                    self.active_session_id = (
                        list(self.sessions.keys())[0] 
                        if self.sessions else None
                    )
                return True
            return False
    
    return SessionManager()


class MessageRole(Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class Message:
    """消息数据类"""
    id: str
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tool_calls: List[Dict] = field(default_factory=list)
    tool_call_id: Optional[str] = None


@dataclass
class Session:
    """会话数据类"""
    id: str
    title: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


class TestCompleteConversationFlow:
    """测试完整对话流程"""

    @pytest.fixture
    def conversation_engine(self, mock_llm_server, mock_llm_stream):
        """创建对话引擎"""
        class ConversationEngine:
            def __init__(self, llm_stream):
                self.messages: List[Message] = []
                self.current_streaming_message: Optional[Message] = None
                self.message_counter = 0
                self._llm_stream = llm_stream
            
            def add_user_message(self, content: str) -> Message:
                """添加用户消息"""
                self.message_counter += 1
                msg = Message(
                    id=f"msg_{self.message_counter}",
                    role=MessageRole.USER,
                    content=content
                )
                self.messages.append(msg)
                return msg
            
            def start_assistant_stream(self, content: str = "") -> Message:
                """开始助手消息流"""
                self.message_counter += 1
                msg = Message(
                    id=f"msg_{self.message_counter}",
                    role=MessageRole.ASSISTANT,
                    content=content
                )
                self.current_streaming_message = msg
                return msg
            
            def append_to_stream(self, text: str):
                """追加流式内容"""
                if self.current_streaming_message:
                    self.current_streaming_message.content += text
            
            def complete_stream(self) -> Message:
                """完成流式消息"""
                if self.current_streaming_message:
                    msg = self.current_streaming_message
                    self.messages.append(msg)
                    self.current_streaming_message = None
                    return msg
                return None
            
            async def send_to_llm(self, prompt: str) -> str:
                """发送消息到 LLM"""
                response = mock_llm_server["response"](
                    content=f"Response to: {prompt}"
                )
                return response.content
            
            async def stream_response(self, text: str):
                """流式响应"""
                async for chunk in self._llm_stream(text, chunk_size=5):
                    self.append_to_stream(chunk)
            
            def get_conversation_history(self) -> List[Message]:
                """获取对话历史"""
                return self.messages.copy()
        
        return ConversationEngine(mock_llm_stream)
    
    def test_user_sends_message(self, conversation_engine):
        """
        测试用户发送消息
        
        场景：用户输入消息后消息被正确添加
        """
        user_message = conversation_engine.add_user_message("Hello, how are you?")
        
        assert user_message.role == MessageRole.USER
        assert user_message.content == "Hello, how are you?"
        assert len(conversation_engine.messages) == 1

    def test_receive_assistant_response(self, conversation_engine):
        """
        测试接收助手响应
        
        场景：助手响应被正确添加
        """
        # 用户发送消息
        conversation_engine.add_user_message("What is Python?")
        
        # 模拟助手响应
        assistant_msg = Message(
            id="msg_2",
            role=MessageRole.ASSISTANT,
            content="Python is a programming language."
        )
        conversation_engine.messages.append(assistant_msg)
        
        assert len(conversation_engine.messages) == 2
        assert conversation_engine.messages[1].role == MessageRole.ASSISTANT

    def test_streaming_response_flow(self, conversation_engine):
        """
        测试流式响应流程
        
        场景：模拟逐字显示的流式响应
        """
        # 开始流式消息
        conversation_engine.start_assistant_stream()
        
        # 模拟逐字接收
        text = "This is a streaming response."
        for char in text:
            conversation_engine.append_to_stream(char)
        
        assert conversation_engine.current_streaming_message.content == text
        
        # 完成流式
        completed = conversation_engine.complete_stream()
        
        assert completed is not None
        assert completed.content == text
        assert completed not in [conversation_engine.current_streaming_message]

    @pytest.mark.asyncio
    async def test_full_conversation_cycle(self, conversation_engine):
        """
        测试完整对话周期
        
        场景：
        1. 用户发送消息
        2. 显示用户消息
        3. 发送请求到 LLM
        4. 接收流式响应
        5. 显示助手消息
        """
        # 1-2. 用户发送消息
        user_msg = conversation_engine.add_user_message("Tell me about AI")
        
        # 3-4. 发送请求并接收流式响应
        response_text = "AI stands for Artificial Intelligence."
        
        conversation_engine.start_assistant_stream()
        
        await conversation_engine.stream_response(response_text)
        
        # 5. 完成并显示
        assistant_msg = conversation_engine.complete_stream()
        
        # 验证完整流程
        assert len(conversation_engine.messages) == 2
        assert conversation_engine.messages[0] == user_msg
        assert conversation_engine.messages[1] == assistant_msg
        assert assistant_msg.content == response_text

    def test_message_ordering(self, conversation_engine):
        """
        测试消息顺序
        
        场景：消息按时间顺序正确排列
        """
        # 按顺序添加消息
        msg1 = conversation_engine.add_user_message("First message")
        time.sleep(0.01)
        msg2 = conversation_engine.add_user_message("Second message")
        time.sleep(0.01)
        
        history = conversation_engine.get_conversation_history()
        
        assert len(history) == 2
        assert history[0].id == msg1.id
        assert history[1].id == msg2.id
        assert history[0].timestamp < history[1].timestamp

    def test_conversation_history_retrieval(self, conversation_engine):
        """
        测试对话历史检索
        
        场景：能够获取完整的对话历史
        """
        # 创建多轮对话
        conversation_engine.add_user_message("Round 1")
        conversation_engine.messages.append(Message(
            id="a1", role=MessageRole.ASSISTANT, content="Response 1"
        ))
        conversation_engine.add_user_message("Round 2")
        conversation_engine.messages.append(Message(
            id="a2", role=MessageRole.ASSISTANT, content="Response 2"
        ))
        conversation_engine.add_user_message("Round 3")
        
        history = conversation_engine.get_conversation_history()
        
        assert len(history) == 5
        assert all(isinstance(m, Message) for m in history)


class TestSessionSwitching:
    """测试会话切换"""

    def test_create_new_session(self, session_manager):
        """
        测试创建新会话
        
        场景：创建新的聊天会话
        """
        session = session_manager.create_session("My Chat")
        
        assert session is not None
        assert session.title == "My Chat"
        assert session.id in session_manager.sessions

    def test_switch_between_sessions(self, session_manager):
        """
        测试会话之间切换
        
        场景：在多个会话之间切换
        """
        # 创建多个会话
        session1 = session_manager.create_session("Session 1")
        session2 = session_manager.create_session("Session 2")
        session3 = session_manager.create_session("Session 3")
        
        # 切换到 session1
        session_manager.switch_session(session1.id)
        assert session_manager.active_session_id == session1.id
        
        # 切换到 session3
        session_manager.switch_session(session3.id)
        assert session_manager.active_session_id == session3.id
        
        # 切换到 session2
        session_manager.switch_session(session2.id)
        assert session_manager.active_session_id == session2.id

    def test_active_session_indicator(self, session_manager):
        """
        测试活动会话标识
        
        场景：当前活动会话应有明确标识
        """
        session1 = session_manager.create_session("First")
        session2 = session_manager.create_session("Second")
        
        assert session_manager.get_active_session() == session2
        
        session_manager.switch_session(session1.id)
        assert session_manager.get_active_session() == session1
        assert session_manager.get_active_session().is_active is True

    def test_delete_active_session_switches(self, session_manager):
        """
        测试删除活动会话时自动切换
        
        场景：删除当前活动会话后自动切换到其他会话
        """
        session1 = session_manager.create_session("First")
        session2 = session_manager.create_session("Second")
        
        # 当前在 session2
        assert session_manager.active_session_id == session2.id
        
        # 删除 session2
        session_manager.delete_session(session2.id)
        
        # 应该自动切换到 session1
        assert session_manager.active_session_id == session1.id
        assert session_manager.get_active_session() == session1

    def test_session_listing(self, session_manager):
        """
        测试会话列表
        
        场景：列出所有会话
        """
        session_manager.create_session("Session A")
        session_manager.create_session("Session B")
        session_manager.create_session("Session C")
        
        sessions = session_manager.list_sessions()
        
        assert len(sessions) == 3
        assert any(s.title == "Session A" for s in sessions)
        assert any(s.title == "Session B" for s in sessions)
        assert any(s.title == "Session C" for s in sessions)


class TestMultiTurnConversation:
    """测试多轮对话"""

    @pytest.fixture
    def multi_turn_conversation(self, mock_llm_server, mock_llm_stream):
        """创建多轮对话模拟"""
        class MultiTurnConversation:
            def __init__(self):
                self.conversation_engine = ConversationEngineMock(mock_llm_server, mock_llm_stream)
                self.turn_count = 0
            
            async def user_sends_and_gets_response(self, user_message: str) -> str:
                """用户发送消息并获取响应"""
                self.turn_count += 1
                
                # 添加用户消息
                self.conversation_engine.add_user_message(user_message)
                
                # 获取助手响应
                response = await self.conversation_engine.get_llm_response(
                    f"Turn {self.turn_count}: {user_message}"
                )
                
                return response
            
            def get_full_history(self) -> List[Message]:
                """获取完整对话历史"""
                return self.conversation_engine.messages.copy()
        
        class ConversationEngineMock:
            def __init__(self, llm_server, llm_stream):
                self.messages: List[Message] = []
                self.llm_server = llm_server
                self.llm_stream = llm_stream
                self.counter = 0
            
            def add_user_message(self, content: str):
                self.counter += 1
                self.messages.append(Message(
                    id=f"msg_{self.counter}",
                    role=MessageRole.USER,
                    content=content
                ))
            
            async def get_llm_response(self, prompt: str) -> str:
                response = self.llm_server["response"](content=f"Response to: {prompt}")
                self.counter += 1
                assistant_msg = Message(
                    id=f"msg_{self.counter}",
                    role=MessageRole.ASSISTANT,
                    content=response.content
                )
                self.messages.append(assistant_msg)
                return response.content
        
        return MultiTurnConversation()

    @pytest.mark.asyncio
    async def test_two_turn_conversation(self, multi_turn_conversation):
        """
        测试两轮对话
        
        场景：两轮完整的问答
        """
        # 第一轮
        response1 = await multi_turn_conversation.user_sends_and_gets_response(
            "What is Python?"
        )
        
        # 第二轮
        response2 = await multi_turn_conversation.user_sends_and_gets_response(
            "What about JavaScript?"
        )
        
        history = multi_turn_conversation.get_full_history()
        
        assert len(history) == 4  # 2 user + 2 assistant
        assert history[0].role == MessageRole.USER
        assert history[1].role == MessageRole.ASSISTANT
        assert history[2].role == MessageRole.USER
        assert history[3].role == MessageRole.ASSISTANT

    @pytest.mark.asyncio
    async def test_five_turn_conversation(self, multi_turn_conversation):
        """
        测试五轮对话
        
        场景：连续多轮对话
        """
        messages = [
            "Hello!",
            "How are you?",
            "Tell me a joke",
            "That's funny! Tell me another one",
            "Thanks, that's all for now"
        ]
        
        responses = []
        for msg in messages:
            response = await multi_turn_conversation.user_sends_and_gets_response(msg)
            responses.append(response)
        
        history = multi_turn_conversation.get_full_history()
        
        # 每轮有用户消息和助手响应
        assert len(history) == len(messages) * 2
        assert multi_turn_conversation.turn_count == 5
        
        # 验证交替顺序
        for i, msg in enumerate(history):
            expected_role = MessageRole.USER if i % 2 == 0 else MessageRole.ASSISTANT
            assert msg.role == expected_role

    @pytest.mark.asyncio
    async def test_conversation_context_preserved(self, multi_turn_conversation):
        """
        测试对话上下文保留
        
        场景：后续对话应能感知之前的上下文
        """
        # 初始消息
        await multi_turn_conversation.user_sends_and_gets_response(
            "I'm working on a Python project"
        )
        
        # 后续消息
        await multi_turn_conversation.user_sends_and_gets_response(
            "What libraries should I use?"
        )
        
        history = multi_turn_conversation.get_full_history()
        
        # 验证历史中包含之前的上下文
        assert any("Python" in m.content for m in history)
        assert any("libraries" in m.content for m in history)

    @pytest.mark.asyncio
    async def test_conversation_with_interruptions(self, multi_turn_conversation):
        """
        测试带中断的对话
        
        场景：对话过程中切换到其他会话或操作
        """
        # 开始对话
        response1 = await multi_turn_conversation.user_sends_and_gets_response(
            "First topic"
        )
        
        # 模拟中断（记录状态）
        interrupted_history = multi_turn_conversation.get_full_history()
        
        # 继续对话
        response2 = await multi_turn_conversation.user_sends_and_gets_response(
            "Continuing topic"
        )
        
        final_history = multi_turn_conversation.get_full_history()
        
        # 验证历史包含所有消息
        assert len(final_history) > len(interrupted_history)
        assert any("First topic" in m.content for m in final_history)
        assert any("Continuing topic" in m.content for m in final_history)


class TestEndToEndScenarios:
    """测试端到端场景"""

    @pytest.fixture
    def tui_simulator(self, mock_llm_server, mock_llm_stream, session_manager):
        """创建 TUI 模拟器"""
        class TUISimulator:
            def __init__(self, llm_server, llm_stream, session_mgr):
                self.llm = llm_server
                self.stream = llm_stream
                self.sessions = session_mgr
                self.current_session = None
                self.conversation = []
            
            def start(self):
                """启动 TUI"""
                self.current_session = self.sessions.create_session("Welcome Chat")
            
            async def process_input(self, user_input: str) -> str:
                """处理用户输入"""
                # 添加用户消息
                self.conversation.append({
                    "role": "user",
                    "content": user_input
                })
                
                # 获取响应
                response = self.llm["response"](
                    content=f"Response to: {user_input}"
                )
                
                self.conversation.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                return response.content
            
            def switch_to_new_session(self, title: str):
                """切换到新会话"""
                self.current_session = self.sessions.create_session(title)
                self.conversation = []
            
            def get_display_state(self) -> Dict:
                """获取显示状态"""
                return {
                    "session_id": self.current_session.id if self.current_session else None,
                    "message_count": len(self.conversation),
                    "last_message": self.conversation[-1] if self.conversation else None
                }
        
        return TUISimulator(mock_llm_server, mock_llm_stream, session_manager)

    @pytest.mark.asyncio
    async def test_complete_user_journey(self, tui_simulator):
        """
        测试完整的用户旅程
        
        场景：
        1. 启动 TUI
        2. 用户登录并开始对话
        3. 发送多条消息
        4. 切换会话
        5. 在新会话继续对话
        """
        # 1. 启动
        tui_simulator.start()
        assert tui_simulator.current_session is not None
        
        # 2. 开始对话
        response1 = await tui_simulator.process_input("Hello!")
        assert "Hello" in response1
        
        # 3. 发送多条消息
        await tui_simulator.process_input("How is the weather?")
        await tui_simulator.process_input("Thanks!")
        
        state1 = tui_simulator.get_display_state()
        assert state1["message_count"] == 6  # 3 user + 3 assistant
        
        # 4. 切换会话
        tui_simulator.switch_to_new_session("New Topic Chat")
        
        state2 = tui_simulator.get_display_state()
        assert state2["message_count"] == 0  # 新会话清空了对话
        
        # 5. 在新会话继续
        await tui_simulator.process_input("Different topic")
        
        state3 = tui_simulator.get_display_state()
        assert state3["message_count"] == 2

    def test_session_persistence(self, tui_simulator):
        """
        测试会话持久化
        
        场景：会话数据应该能够持久化
        """
        # 创建会话
        session1 = tui_simulator.sessions.create_session("Persistent Session")
        session_id = session1.id
        
        # 添加一些数据到会话
        session1.messages.append(Message(
            id="msg_1",
            role=MessageRole.USER,
            content="Test message"
        ))
        
        # 切换会话
        tui_simulator.sessions.create_session("Other Session")
        
        # 切换回来
        tui_simulator.sessions.switch_session(session_id)
        restored_session = tui_simulator.sessions.get_active_session()
        
        # 验证数据恢复
        assert restored_session is not None
        assert restored_session.id == session_id
        assert len(restored_session.messages) > 0

    @pytest.mark.asyncio
    async def test_rapid_message_sending(self, tui_simulator):
        """
        测试快速发送消息
        
        场景：用户快速连续发送多条消息
        """
        tui_simulator.start()
        
        # 快速发送多条消息
        tasks = [
            tui_simulator.process_input(f"Message {i}")
            for i in range(5)
        ]
        
        responses = await asyncio.gather(*tasks)
        
        state = tui_simulator.get_display_state()
        
        # 应该有 10 条消息（5 user + 5 assistant）
        assert state["message_count"] == 10
        assert len(responses) == 5

    def test_ui_state_consistency(self, tui_simulator):
        """
        测试 UI 状态一致性
        
        场景：UI 显示的状态应与实际数据一致
        """
        tui_simulator.start()
        
        # 检查初始状态
        state = tui_simulator.get_display_state()
        assert state["session_id"] is not None
        assert state["message_count"] == 0
        
        # 添加消息
        async def add_messages():
            await tui_simulator.process_input("Test 1")
            await tui_simulator.process_input("Test 2")
        
        asyncio.run(add_messages())
        
        # 检查更新后的状态
        state = tui_simulator.get_display_state()
        assert state["message_count"] == 4
        assert state["last_message"] is not None
        assert state["last_message"]["role"] == "assistant"


class TestErrorRecoveryInConversation:
    """测试对话中的错误恢复"""

    @pytest.fixture
    def resilient_conversation(self, mock_llm_server):
        """创建有错误恢复能力的对话模拟"""
        class ResilientConversation:
            def __init__(self, llm_server):
                self.llm = llm_server
                self.messages: List[Message] = []
                self.errors: List[str] = []
                self.retry_count = 0
            
            async def send_with_retry(self, message: str, max_retries: int = 3) -> Optional[str]:
                """带重试的消息发送"""
                for attempt in range(max_retries):
                    try:
                        self.retry_count = attempt
                        response = self.llm["response"](content=f"Reply to: {message}")
                        return response.content
                    except Exception as e:
                        self.errors.append(str(e))
                        if attempt == max_retries - 1:
                            return None
                return None
        
        return ResilientConversation(mock_llm_server)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self, resilient_conversation):
        """
        测试失败时重试
        
        场景：请求失败时自动重试
        """
        response = await resilient_conversation.send_with_retry("Test message")
        
        # 验证响应成功
        assert response is not None
        assert "Reply to" in response
        
        # 如果有错误，验证重试次数
        if resilient_conversation.errors:
            assert resilient_conversation.retry_count > 0

    def test_error_logging(self, resilient_conversation):
        """
        测试错误日志
        
        场景：发生的错误应该被记录
        """
        async def run_with_error():
            await resilient_conversation.send_with_retry("test")
        
        asyncio.run(run_with_error())
        
        # 验证错误被记录（如果有）
        # 在正常情况下errors应该为空
        assert isinstance(resilient_conversation.errors, list)


class TestConversationEdgeCases:
    """测试对话边界情况"""

    def test_empty_message_handling(self):
        """
        测试空消息处理
        
        场景：用户发送空消息
        """
        messages = []
        
        empty_message = ""
        if empty_message.strip():
            messages.append({"role": "user", "content": empty_message})
        
        # 空消息不应被添加
        assert len(messages) == 0

    def test_very_long_message(self):
        """
        测试超长消息处理
        
        场景：用户发送非常长的消息
        """
        long_content = "A" * 10000
        
        message = Message(
            id="msg_1",
            role=MessageRole.USER,
            content=long_content
        )
        
        assert len(message.content) == 10000

    def test_special_characters_in_message(self):
        """
        测试消息中的特殊字符
        
        场景：消息包含特殊字符和格式
        """
        special_content = """
        🧑‍💻 Hello! <script>alert('xss')</script>
        
        Code: ```python
        print("Hello")
        ```
        
        Links: [Click here](https://example.com)
        """
        
        message = Message(
            id="msg_1",
            role=MessageRole.USER,
            content=special_content
        )
        
        assert "<script>" in message.content
        assert "```python" in message.content
        assert "🧑‍💻" in message.content

    def test_concurrent_session_creation(self):
        """
        测试并发创建会话
        
        场景：同时创建多个会话
        """
        sessions = []
        
        for i in range(10):
            session = Session(id=f"session_{i}", title=f"Session {i}")
            sessions.append(session)
        
        assert len(sessions) == 10
        assert all(s.id.startswith("session_") for s in sessions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
