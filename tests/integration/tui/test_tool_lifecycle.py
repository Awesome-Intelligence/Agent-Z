#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具调用生命周期集成测试

测试工具调用的完整生命周期：
1. 工具请求发送
2. 工具结果接收
3. 工具状态显示（running/completed/failed）

使用 mock_llm_server fixture 模拟 LLM 响应
使用 sample_tool_result fixture 测试工具结果解析

日志子层：🔧 Tools
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from enum import Enum
import asyncio


class ToolStatus(Enum):
    """工具执行状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ToolCall:
    """模拟工具调用对象"""
    id: str
    name: str
    arguments: Dict[str, Any]
    status: ToolStatus = ToolStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None


class TestToolRequestSending:
    """测试工具请求发送"""

    def test_tool_call_request_creation(self, mock_llm_server):
        """
        测试创建工具调用请求
        
        场景：LLM 返回需要调用的工具时，验证工具请求的创建
        """
        # 模拟 LLM 返回工具调用
        tool_call_response = mock_llm_server["tool_call"](
            tool_name="list_files",
            tool_input={"path": "/home", "recursive": False}
        )
        
        assert tool_call_response.tool_calls is not None
        assert len(tool_call_response.tool_calls) == 1
        
        call = tool_call_response.tool_calls[0]
        assert call["id"] == "call_123"
        assert call["function"]["name"] == "list_files"
        assert call["function"]["arguments"]["path"] == "/home"

    def test_multiple_tool_calls_request(self, mock_llm_server):
        """
        测试创建多个工具调用请求
        
        场景：单次 LLM 响应包含多个工具调用
        """
        # 创建模拟的多工具响应
        multi_tool_response = MagicMock()
        multi_tool_response.tool_calls = [
            {
                "id": "call_001",
                "type": "function",
                "function": {"name": "read_file", "arguments": {"path": "a.txt"}}
            },
            {
                "id": "call_002",
                "type": "function",
                "function": {"name": "write_file", "arguments": {"path": "b.txt", "content": "test"}}
            },
            {
                "id": "call_003",
                "type": "function",
                "function": {"name": "execute_command", "arguments": {"cmd": "ls"}}
            }
        ]
        
        assert len(multi_tool_response.tool_calls) == 3
        assert all(tc["type"] == "function" for tc in multi_tool_response.tool_calls)

    def test_tool_request_with_complex_arguments(self, mock_llm_server):
        """
        测试复杂参数的工具调用请求
        
        场景：工具参数包含嵌套对象和数组
        """
        complex_args = {
            "filter": {"type": "file", "size_min": 1024},
            "patterns": ["*.py", "*.txt"],
            "recursive": True,
            "max_results": 100
        }
        
        tool_call_response = mock_llm_server["tool_call"](
            tool_name="search_files",
            tool_input=complex_args
        )
        
        call = tool_call_response.tool_calls[0]
        assert call["function"]["arguments"]["filter"]["type"] == "file"
        assert len(call["function"]["arguments"]["patterns"]) == 2


class TestToolResultReceiving:
    """测试工具结果接收"""

    def test_tool_result_parsing(self, sample_tool_result):
        """
        测试解析工具返回结果
        
        场景：接收工具执行结果并解析为可用数据
        """
        assert sample_tool_result["tool_call_id"] == "call_123"
        assert sample_tool_result["tool_name"] == "list_dir"
        assert sample_tool_result["status"] == "success"
        assert len(sample_tool_result["output"]) == 3

    def test_tool_result_with_file_list(self, sample_tool_result):
        """
        测试文件列表工具结果解析
        
        场景：list_dir 工具返回的文件列表包含目录和文件
        """
        output = sample_tool_result["output"]
        
        files = [item for item in output if not item["is_dir"]]
        dirs = [item for item in output if item["is_dir"]]
        
        assert len(files) == 1
        assert len(dirs) == 2
        assert files[0]["name"] == "README.md"

    def test_tool_result_error_handling(self):
        """
        测试工具错误结果处理
        
        场景：工具执行失败时返回错误信息
        """
        error_result = {
            "tool_call_id": "call_error",
            "tool_name": "read_file",
            "status": "error",
            "error": "File not found: /nonexistent/file.txt",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        assert error_result["status"] == "error"
        assert "not found" in error_result["error"]

    def test_tool_result_with_large_output(self):
        """
        测试大型输出结果的解析
        
        场景：工具返回大量数据时正确处理
        """
        large_result = {
            "tool_call_id": "call_large",
            "tool_name": "search",
            "status": "success",
            "output": [{"path": f"file_{i}.txt", "line": i} for i in range(1000)],
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        assert len(large_result["output"]) == 1000
        assert large_result["output"][0]["line"] == 0
        assert large_result["output"][-1]["line"] == 999


class TestToolStatusDisplay:
    """测试工具状态显示"""

    def test_tool_status_pending(self):
        """
        测试待处理状态
        
        场景：工具调用刚创建，尚未开始执行
        """
        tool_call = ToolCall(
            id="call_1",
            name="test_tool",
            arguments={},
            status=ToolStatus.PENDING
        )
        
        assert tool_call.status == ToolStatus.PENDING
        assert tool_call.result is None
        assert tool_call.error is None

    def test_tool_status_running(self):
        """
        测试运行中状态
        
        场景：工具正在执行中
        """
        tool_call = ToolCall(
            id="call_2",
            name="test_tool",
            arguments={},
            status=ToolStatus.RUNNING
        )
        
        assert tool_call.status == ToolStatus.RUNNING
        assert tool_call.result is None

    def test_tool_status_completed(self, sample_tool_result):
        """
        测试完成状态
        
        场景：工具成功执行完成
        """
        tool_call = ToolCall(
            id=sample_tool_result["tool_call_id"],
            name=sample_tool_result["tool_name"],
            arguments={},
            status=ToolStatus.COMPLETED,
            result=sample_tool_result["output"]
        )
        
        assert tool_call.status == ToolStatus.COMPLETED
        assert tool_call.result == sample_tool_result["output"]
        assert tool_call.error is None

    def test_tool_status_failed(self):
        """
        测试失败状态
        
        场景：工具执行失败
        """
        tool_call = ToolCall(
            id="call_fail",
            name="test_tool",
            arguments={},
            status=ToolStatus.FAILED,
            error="Connection timeout"
        )
        
        assert tool_call.status == ToolStatus.FAILED
        assert tool_call.result is None
        assert tool_call.error == "Connection timeout"

    def test_tool_status_transitions(self):
        """
        测试状态转换
        
        场景：工具从 pending -> running -> completed 的完整生命周期
        """
        tool_call = ToolCall(
            id="call_lifecycle",
            name="test_tool",
            arguments={}
        )
        
        # 初始状态
        assert tool_call.status == ToolStatus.PENDING
        
        # 开始执行
        tool_call.status = ToolStatus.RUNNING
        assert tool_call.status == ToolStatus.RUNNING
        
        # 执行完成
        tool_call.status = ToolStatus.COMPLETED
        tool_call.result = {"status": "ok"}
        assert tool_call.status == ToolStatus.COMPLETED


class TestToolLifecycleIntegration:
    """测试工具完整生命周期集成"""

    @pytest.fixture
    def tool_manager(self, mock_llm_server, sample_tool_result):
        """创建工具管理器模拟"""
        class ToolManager:
            def __init__(self):
                self.pending_calls: List[ToolCall] = []
                self.completed_calls: List[ToolCall] = []
            
            def create_tool_call(self, response) -> ToolCall:
                """从 LLM 响应创建工具调用"""
                if not response.tool_calls:
                    return None
                
                call_data = response.tool_calls[0]
                tool_call = ToolCall(
                    id=call_data["id"],
                    name=call_data["function"]["name"],
                    arguments=call_data["function"]["arguments"]
                )
                self.pending_calls.append(tool_call)
                return tool_call
            
            def start_execution(self, call_id: str):
                """开始执行工具"""
                for call in self.pending_calls:
                    if call.id == call_id:
                        call.status = ToolStatus.RUNNING
                        return call
                return None
            
            def complete_execution(self, call_id: str, result: Any):
                """完成工具执行"""
                for call in self.pending_calls:
                    if call.id == call_id:
                        call.status = ToolStatus.COMPLETED
                        call.result = result
                        self.completed_calls.append(call)
                        self.pending_calls.remove(call)
                        return call
                return None
            
            def fail_execution(self, call_id: str, error: str):
                """标记工具执行失败"""
                for call in self.pending_calls:
                    if call.id == call_id:
                        call.status = ToolStatus.FAILED
                        call.error = error
                        self.completed_calls.append(call)
                        self.pending_calls.remove(call)
                        return call
                return None
            
            def get_call_by_id(self, call_id: str) -> Optional[ToolCall]:
                """根据 ID 获取工具调用"""
                for call in self.pending_calls + self.completed_calls:
                    if call.id == call_id:
                        return call
                return None
        
        return ToolManager()

    def test_full_lifecycle_success(self, mock_llm_server, sample_tool_result, tool_manager):
        """
        测试完整的成功生命周期
        
        场景：
        1. LLM 返回工具调用请求
        2. 创建工具调用
        3. 开始执行
        4. 接收结果
        5. 标记完成
        """
        # 1. 模拟 LLM 返回工具调用
        llm_response = mock_llm_server["tool_call"](
            tool_name="list_dir",
            tool_input={"path": "."}
        )
        
        # 2. 创建工具调用
        tool_call = tool_manager.create_tool_call(llm_response)
        assert tool_call is not None
        assert tool_call.status == ToolStatus.PENDING
        assert len(tool_manager.pending_calls) == 1
        
        # 3. 开始执行
        started_call = tool_manager.start_execution(tool_call.id)
        assert started_call.status == ToolStatus.RUNNING
        
        # 4-5. 接收结果并完成
        completed_call = tool_manager.complete_execution(
            tool_call.id,
            sample_tool_result["output"]
        )
        assert completed_call.status == ToolStatus.COMPLETED
        assert completed_call.result == sample_tool_result["output"]
        assert len(tool_manager.pending_calls) == 0
        assert len(tool_manager.completed_calls) == 1

    def test_full_lifecycle_failure(self, mock_llm_server, tool_manager):
        """
        测试完整的失败生命周期
        
        场景：
        1. LLM 返回工具调用请求
        2. 创建工具调用
        3. 开始执行
        4. 执行失败
        5. 标记失败状态
        """
        # 1. 模拟 LLM 返回工具调用
        llm_response = mock_llm_server["tool_call"](
            tool_name="read_file",
            tool_input={"path": "/nonexistent"}
        )
        
        # 2. 创建工具调用
        tool_call = tool_manager.create_tool_call(llm_response)
        assert tool_call is not None
        
        # 3. 开始执行
        tool_manager.start_execution(tool_call.id)
        assert tool_call.status == ToolStatus.RUNNING
        
        # 4-5. 执行失败
        failed_call = tool_manager.fail_execution(
            tool_call.id,
            "File not found"
        )
        assert failed_call.status == ToolStatus.FAILED
        assert failed_call.error == "File not found"

    def test_multiple_tools_lifecycle(self, mock_llm_server, tool_manager):
        """
        测试多个工具的并行执行生命周期
        
        场景：同时执行多个工具调用
        """
        # 创建多个工具调用（手动创建不同的tool_calls来避免ID冲突）
        mock_response_1 = MagicMock()
        mock_response_1.tool_calls = [{
            "id": "call_001", "type": "function",
            "function": {"name": "tool_a", "arguments": {"param": 1}}
        }]
        mock_response_2 = MagicMock()
        mock_response_2.tool_calls = [{
            "id": "call_002", "type": "function",
            "function": {"name": "tool_b", "arguments": {"param": 2}}
        }]
        mock_response_3 = MagicMock()
        mock_response_3.tool_calls = [{
            "id": "call_003", "type": "function",
            "function": {"name": "tool_c", "arguments": {"param": 3}}
        }]
        
        responses = [mock_response_1, mock_response_2, mock_response_3]
        
        calls = [tool_manager.create_tool_call(r) for r in responses]
        assert len(calls) == 3
        
        # 启动所有工具
        for call in calls:
            tool_manager.start_execution(call.id)
        
        # 验证所有工具都在运行
        for call in calls:
            assert call.status == ToolStatus.RUNNING
        
        # 完成部分工具
        tool_manager.complete_execution(calls[0].id, {"result": "a"})
        assert calls[0].status == ToolStatus.COMPLETED
        assert calls[1].status == ToolStatus.RUNNING
        assert calls[2].status == ToolStatus.RUNNING

    def test_get_call_status(self, mock_llm_server, tool_manager):
        """
        测试查询工具调用状态
        
        场景：根据 ID 查询工具调用的当前状态
        """
        # 创建工具调用
        llm_response = mock_llm_server["tool_call"]("test_tool", {})
        tool_call = tool_manager.create_tool_call(llm_response)
        
        # 查询状态
        found = tool_manager.get_call_by_id(tool_call.id)
        assert found is not None
        assert found.status == ToolStatus.PENDING
        
        # 查询不存在的 ID
        not_found = tool_manager.get_call_by_id("nonexistent_id")
        assert not_found is None


class TestToolStreamingResults:
    """测试工具流式结果处理"""

    def test_streaming_tool_result_chunks(self):
        """
        测试流式工具结果的分块处理
        
        场景：工具结果通过流式方式返回
        """
        large_output = "x" * 10000
        chunk_size = 100
        chunks = []
        
        for i in range(0, len(large_output), chunk_size):
            chunk = large_output[i:i + chunk_size]
            chunks.append(chunk)
        
        assert len(chunks) == 100
        assert all(len(c) <= chunk_size for c in chunks)
        assert "".join(chunks) == large_output

    @pytest.mark.asyncio
    async def test_async_tool_streaming(self, mock_llm_stream):
        """
        测试异步流式工具结果
        
        场景：使用异步迭代器处理流式结果
        """
        full_result = ""
        chunk_count = 0
        
        async for chunk in mock_llm_stream("test streaming result", chunk_size=5):
            full_result += chunk
            chunk_count += 1
        
        assert full_result == "test streaming result"
        assert chunk_count > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
