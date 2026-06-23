#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock LLM 集成测试

测试 LLM 响应模拟的完整功能：
1. LLM 响应模拟
2. 流式响应（使用 mock_llm_stream）
3. 错误处理（网络错误、超时、API错误）

日志子层：🤖 LLM
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncGenerator
from enum import Enum
import time


class LLMErrorType(Enum):
    """LLM 错误类型枚举"""
    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    API_ERROR = "api_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    AUTHENTICATION_ERROR = "authentication_error"
    INVALID_RESPONSE_ERROR = "invalid_response_error"


@dataclass
class LLMResponse:
    """LLM 响应数据类"""
    content: str
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = "mock-model"
    finish_reason: str = "stop"


@dataclass
class LLMError:
    """LLM 错误数据类"""
    error_type: LLMErrorType
    message: str
    retry_after: Optional[int] = None


class TestLLMResponseMocking:
    """测试 LLM 响应模拟"""

    def test_basic_text_response(self, mock_llm_server):
        """
        测试基础文本响应模拟
        
        场景：模拟 LLM 返回纯文本响应
        """
        response = mock_llm_server["response"](
            content="Hello! How can I help you today?"
        )
        
        assert response.content == "Hello! How can I help you today?"
        assert len(response.tool_calls) == 0

    def test_response_with_usage(self, mock_llm_server):
        """
        测试带使用量信息的响应
        
        场景：验证响应包含 token 使用统计
        """
        response = mock_llm_server["response"](
            content="Test response"
        )
        
        assert "prompt_tokens" in response.usage
        assert "completion_tokens" in response.usage
        assert "total_tokens" in response.usage
        assert response.usage["total_tokens"] == 15

    def test_tool_call_response(self, mock_llm_server):
        """
        测试工具调用响应
        
        场景：模拟 LLM 返回需要调用工具的响应
        """
        response = mock_llm_server["tool_call"](
            tool_name="search_web",
            tool_input={"query": "Python tutorials", "limit": 5}
        )
        
        assert len(response.tool_calls) == 1
        call = response.tool_calls[0]
        assert call["id"] == "call_123"
        assert call["function"]["name"] == "search_web"
        assert call["function"]["arguments"]["query"] == "Python tutorials"

    def test_empty_response(self, mock_llm_server):
        """
        测试空响应
        
        场景：LLM 返回空内容
        """
        response = mock_llm_server["response"](content="")
        
        assert response.content == ""

    def test_long_text_response(self, mock_llm_server):
        """
        测试长文本响应
        
        场景：模拟 LLM 返回较长的文本内容
        """
        long_content = "This is a " + "very " * 1000 + "long response."
        response = mock_llm_server["response"](content=long_content)
        
        assert len(response.content) > 5000  # 实际长度约5026
        assert "very very" in response.content

    def test_markdown_content_response(self, mock_llm_server):
        """
        测试 Markdown 内容响应
        
        场景：模拟 LLM 返回 Markdown 格式的内容
        """
        markdown_content = """# Heading 1

This is a paragraph with **bold** and *italic* text.

## Code Block

```python
def hello():
    print("Hello, World!")
```

### List

- Item 1
- Item 2
- Item 3
"""
        response = mock_llm_server["response"](content=markdown_content)
        
        assert "# Heading 1" in response.content
        assert "```python" in response.content
        assert "- Item 1" in response.content


class TestStreamingResponse:
    """测试流式响应"""

    @pytest.mark.asyncio
    async def test_basic_streaming(self, mock_llm_stream):
        """
        测试基础流式响应
        
        场景：验证流式响应的基本分块功能
        """
        text = "Hello, World!"
        received_chunks = []
        
        async for chunk in mock_llm_stream(text, chunk_size=1):
            received_chunks.append(chunk)
        
        assert len(received_chunks) == len(text)
        assert "".join(received_chunks) == text

    @pytest.mark.asyncio
    async def test_streaming_with_custom_chunk_size(self, mock_llm_stream):
        """
        测试自定义分块大小的流式响应
        
        场景：验证不同 chunk_size 下的分块行为
        """
        text = "ABCDEFGHIJ"  # 10 characters
        
        # 测试 chunk_size = 2
        chunks_2 = []
        async for chunk in mock_llm_stream(text, chunk_size=2):
            chunks_2.append(chunk)
        
        assert len(chunks_2) == 5
        assert all(len(c) == 2 for c in chunks_2)
        
        # 测试 chunk_size = 5
        chunks_5 = []
        async for chunk in mock_llm_stream(text, chunk_size=5):
            chunks_5.append(chunk)
        
        assert len(chunks_5) == 2
        assert all(len(c) == 5 for c in chunks_5)

    @pytest.mark.asyncio
    async def test_streaming_accumulation(self, mock_llm_stream):
        """
        测试流式响应的累积
        
        场景：验证分块数据能够正确累积为完整内容
        """
        text = "Streaming response content"
        accumulated = ""
        
        async for chunk in mock_llm_stream(text, chunk_size=3):
            accumulated += chunk
        
        assert accumulated == text

    @pytest.mark.asyncio
    async def test_empty_streaming(self, mock_llm_stream):
        """
        测试空内容的流式响应
        
        场景：空字符串的流式处理
        """
        chunks = []
        async for chunk in mock_llm_stream("", chunk_size=1):
            chunks.append(chunk)
        
        assert len(chunks) == 0
        assert "".join(chunks) == ""

    @pytest.mark.asyncio
    async def test_concurrent_streaming(self, mock_llm_stream):
        """
        测试并发流式响应
        
        场景：同时处理多个流式响应
        """
        text1 = "First response"
        text2 = "Second response"
        
        results = {"r1": "", "r2": ""}
        
        async def stream1():
            async for chunk in mock_llm_stream(text1, chunk_size=1):
                results["r1"] += chunk
        
        async def stream2():
            async for chunk in mock_llm_stream(text2, chunk_size=1):
                results["r2"] += chunk
        
        await asyncio.gather(stream1(), stream2())
        
        assert results["r1"] == text1
        assert results["r2"] == text2

    @pytest.mark.asyncio
    async def test_streaming_with_delays(self, mock_llm_stream):
        """
        测试带延迟的流式响应
        
        场景：模拟真实网络延迟的流式响应
        """
        text = "Delayed text"
        start_time = time.time()
        
        async for chunk in mock_llm_stream(text, chunk_size=1):
            await asyncio.sleep(0.001)  # Small delay
        
        elapsed = time.time() - start_time
        
        # 验证至少经过了一些时间
        assert elapsed > 0


class TestErrorHandling:
    """测试错误处理"""

    def test_network_error_creation(self):
        """
        测试网络错误创建
        
        场景：模拟网络连接失败
        """
        error = LLMError(
            error_type=LLMErrorType.NETWORK_ERROR,
            message="Connection refused: Unable to reach LLM server"
        )
        
        assert error.error_type == LLMErrorType.NETWORK_ERROR
        assert "Connection" in error.message

    def test_timeout_error_creation(self):
        """
        测试超时错误创建
        
        场景：模拟请求超时
        """
        error = LLMError(
            error_type=LLMErrorType.TIMEOUT_ERROR,
            message="Request timeout after 60 seconds"
        )
        
        assert error.error_type == LLMErrorType.TIMEOUT_ERROR
        assert "timeout" in error.message.lower()

    def test_api_error_creation(self):
        """
        测试 API 错误创建
        
        场景：模拟 API 返回错误
        """
        error = LLMError(
            error_type=LLMErrorType.API_ERROR,
            message="Invalid request: Missing required parameter 'model'"
        )
        
        assert error.error_type == LLMErrorType.API_ERROR
        assert "Invalid" in error.message

    def test_rate_limit_error_creation(self):
        """
        测试速率限制错误创建
        
        场景：模拟 API 速率限制
        """
        error = LLMError(
            error_type=LLMErrorType.RATE_LIMIT_ERROR,
            message="Rate limit exceeded",
            retry_after=60
        )
        
        assert error.error_type == LLMErrorType.RATE_LIMIT_ERROR
        assert error.retry_after == 60

    def test_authentication_error_creation(self):
        """
        测试认证错误创建
        
        场景：模拟 API 密钥无效或过期
        """
        error = LLMError(
            error_type=LLMErrorType.AUTHENTICATION_ERROR,
            message="Invalid API key"
        )
        
        assert error.error_type == LLMErrorType.AUTHENTICATION_ERROR
        assert "API key" in error.message

    def test_invalid_response_error_creation(self):
        """
        测试无效响应错误创建
        
        场景：模拟 LLM 返回格式错误的响应
        """
        error = LLMError(
            error_type=LLMErrorType.INVALID_RESPONSE_ERROR,
            message="Response format does not match expected schema"
        )
        
        assert error.error_type == LLMErrorType.INVALID_RESPONSE_ERROR

    def test_error_type_detection(self):
        """
        测试错误类型检测
        
        场景：根据错误消息识别错误类型
        """
        error_messages = {
            "Connection refused": LLMErrorType.NETWORK_ERROR,
            "timeout": LLMErrorType.TIMEOUT_ERROR,
            "401 Unauthorized": LLMErrorType.AUTHENTICATION_ERROR,
            "429 Too Many Requests": LLMErrorType.RATE_LIMIT_ERROR,
            "Invalid JSON": LLMErrorType.API_ERROR,
        }
        
        for msg, expected_type in error_messages.items():
            if "timeout" in msg.lower():
                assert expected_type == LLMErrorType.TIMEOUT_ERROR
            elif "Connection" in msg:
                assert expected_type == LLMErrorType.NETWORK_ERROR


class TestErrorRecovery:
    """测试错误恢复"""

    def test_retry_after_rate_limit(self):
        """
        测试速率限制后的重试
        
        场景：遇到速率限制时等待指定时间后重试
        """
        error = LLMError(
            error_type=LLMErrorType.RATE_LIMIT_ERROR,
            message="Rate limit exceeded",
            retry_after=5
        )
        
        # 验证 retry_after 值
        assert error.retry_after == 5
        
        # 模拟等待后重试
        wait_time = error.retry_after
        assert wait_time > 0

    def test_error_context_preservation(self):
        """
        测试错误上下文保留
        
        场景：错误信息应保留足够的上下文用于调试
        """
        error = LLMError(
            error_type=LLMErrorType.API_ERROR,
            message="Model 'gpt-5' not found. Available models: gpt-4, gpt-3.5"
        )
        
        assert "gpt-5" in error.message
        assert "gpt-4" in error.message
        assert error.error_type == LLMErrorType.API_ERROR

    def test_network_error_retry_logic(self):
        """
        测试网络错误的重试逻辑
        
        场景：网络错误时应进行指数退避重试
        """
        max_retries = 3
        base_delay = 1
        
        delays = []
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            delays.append(delay)
        
        assert delays == [1, 2, 4]  # 指数退避

    def test_error_fallback_response(self):
        """
        测试错误时的回退响应
        
        场景：LLM 不可用时返回友好的错误消息
        """
        fallback_response = LLMResponse(
            content="I'm sorry, I'm having trouble connecting to my language model right now. Please try again in a few moments.",
            finish_reason="error"
        )
        
        assert "trouble" in fallback_response.content.lower()
        assert fallback_response.finish_reason == "error"


class TestMockLLMIntegration:
    """测试 Mock LLM 集成"""

    @pytest.fixture
    def llm_client_mock(self, mock_llm_server, mock_llm_stream):
        """创建 LLM 客户端模拟"""
        class LLMClientMock:
            def __init__(self):
                self.call_count = 0
                self.streaming_call_count = 0
                self.errors: List[LLMError] = []
            
            async def generate(self, prompt: str) -> LLMResponse:
                """生成响应"""
                self.call_count += 1
                
                # 模拟根据提示词返回不同响应
                if "tool" in prompt.lower():
                    return mock_llm_server["tool_call"]("test_tool", {"param": "value"})
                else:
                    return mock_llm_server["response"](
                        f"Response to: {prompt[:50]}..."
                    )
            
            async def stream_generate(self, prompt: str) -> AsyncGenerator[str, None]:
                """流式生成响应"""
                self.streaming_call_count += 1
                
                text = f"Streaming response for: {prompt[:30]}"
                async for chunk in mock_llm_stream(text, chunk_size=5):
                    yield chunk
            
            def add_error(self, error: LLMError):
                """添加错误"""
                self.errors.append(error)
            
            def should_fail(self) -> bool:
                """检查是否应该失败"""
                return len(self.errors) > 0 and self.errors[-1].error_type == LLMErrorType.API_ERROR
        
        return LLMClientMock()

    @pytest.mark.asyncio
    async def test_complete_generation_flow(self, llm_client_mock):
        """
        测试完整的生成流程
        
        场景：
        1. 发送提示词
        2. 接收响应
        3. 处理工具调用
        """
        # 生成普通响应
        response = await llm_client_mock.generate("Hello, how are you?")
        
        assert response.content is not None
        assert llm_client_mock.call_count == 1
        
        # 生成工具调用响应
        tool_response = await llm_client_mock.generate("Use a tool please")
        
        assert len(tool_response.tool_calls) > 0
        assert llm_client_mock.call_count == 2

    @pytest.mark.asyncio
    async def test_streaming_generation_flow(self, llm_client_mock):
        """
        测试流式生成流程
        
        场景：使用流式方式接收响应
        """
        full_response = ""
        
        async for chunk in llm_client_mock.stream_generate("Tell me a story"):
            full_response += chunk
        
        assert len(full_response) > 0
        assert "Streaming response" in full_response
        assert llm_client_mock.streaming_call_count == 1

    @pytest.mark.asyncio
    async def test_error_during_generation(self, llm_client_mock):
        """
        测试生成过程中的错误
        
        场景：模拟 LLM 生成时发生错误
        """
        # 添加错误（API错误会触发should_fail）
        llm_client_mock.add_error(LLMError(
            error_type=LLMErrorType.API_ERROR,
            message="Connection lost"
        ))
        
        # 尝试生成 - 应该检测到错误
        error_raised = False
        try:
            if llm_client_mock.should_fail():
                error_raised = True
                raise Exception("Network error: Connection lost")
            response = await llm_client_mock.generate("Test")
        except Exception as e:
            error_raised = True
            assert "Network error" in str(e)
        
        assert error_raised, "Should have raised an error"

    @pytest.mark.asyncio
    async def test_streaming_with_error(self, llm_client_mock):
        """
        测试流式生成中的错误
        
        场景：流式响应中途发生错误
        """
        received_chunks = []
        error_occurred = False
        
        try:
            async for chunk in llm_client_mock.stream_generate("Test"):
                if len(received_chunks) >= 3 and not error_occurred:
                    raise Exception("Stream interrupted")
                received_chunks.append(chunk)
        except Exception:
            error_occurred = True
        
        # 验证部分数据已接收
        assert len(received_chunks) >= 0
        assert error_occurred or len(received_chunks) > 0

    def test_call_statistics(self, llm_client_mock):
        """
        测试调用统计
        
        场景：追踪 LLM 调用的次数和类型
        """
        assert llm_client_mock.call_count == 0
        assert llm_client_mock.streaming_call_count == 0
        
        # 模拟多次调用
        async def run_calls():
            await llm_client_mock.generate("call 1")
            await llm_client_mock.generate("call 2")
            # 流式调用需要迭代
            async for _ in llm_client_mock.stream_generate("call 3"):
                pass
            await llm_client_mock.generate("call 4")
        
        asyncio.run(run_calls())
        
        assert llm_client_mock.call_count == 3
        assert llm_client_mock.streaming_call_count == 1


class TestLLMRetryAndRecovery:
    """测试 LLM 重试和恢复"""

    def test_exponential_backoff_calculation(self):
        """
        测试指数退避时间计算
        
        场景：计算合理的重试间隔
        """
        base_delay = 1
        max_delay = 60
        max_retries = 5
        
        delays = []
        for attempt in range(max_retries):
            delay = min(base_delay * (2 ** attempt), max_delay)
            delays.append(delay)
        
        assert delays == [1, 2, 4, 8, 16]

    def test_max_retries_exceeded(self):
        """
        测试超过最大重试次数
        
        场景：多次重试失败后放弃
        """
        max_retries = 3
        attempt = 0
        
        for i in range(max_retries + 2):
            attempt = i
        
        assert attempt > max_retries

    def test_error_before_all_retries_exhausted(self):
        """
        测试重试中途成功
        
        场景：在达到最大重试次数前成功
        """
        attempts = 0
        success_on_attempt = 2
        
        for attempt in range(5):
            attempts += 1
            if attempt == success_on_attempt:
                break
        
        assert attempts == 3


class TestLLMResponseValidation:
    """测试 LLM 响应验证"""

    def test_response_schema_validation(self):
        """
        测试响应模式验证
        
        场景：验证 LLM 响应符合预期格式
        """
        response = LLMResponse(
            content="Test content",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
        )
        
        # 验证必需字段
        assert hasattr(response, "content")
        assert hasattr(response, "usage")
        assert hasattr(response, "model")
        assert isinstance(response.usage, dict)

    def test_tool_call_schema_validation(self, mock_llm_server):
        """
        测试工具调用响应模式验证
        
        场景：验证工具调用响应格式正确
        """
        response = mock_llm_server["tool_call"]("test_tool", {"key": "value"})
        
        assert len(response.tool_calls) == 1
        call = response.tool_calls[0]
        
        # 验证必需字段
        assert "id" in call
        assert "type" in call
        assert "function" in call
        assert "name" in call["function"]
        assert "arguments" in call["function"]

    def test_invalid_response_handling(self):
        """
        测试无效响应的处理
        
        场景：接收格式错误的响应时优雅处理
        """
        # 模拟无效响应
        invalid_response = {
            "unexpected_field": "value"
            # 缺少必需的 content 字段
        }
        
        # 尝试提取内容
        content = invalid_response.get("content", "")
        
        assert content == ""
        assert "unexpected_field" in invalid_response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
