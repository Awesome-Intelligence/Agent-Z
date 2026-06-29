# -*- coding: utf-8 -*-
# 🔧 System - Tool Executor - 类型定义

"""
Tool Executor Types - 工具执行器类型定义

定义工具调用相关的统一类型，避免与现有类型冲突。
命名规则：
- ToolInvokeResult: 调用结果（统一格式）
- ToolInvokeRequest: 调用请求
- ToolInvokeError: 调用错误信息
"""

from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List, Callable
from enum import Enum


@dataclass
class ToolInvokeResult:
    """
    工具调用结果（统一格式）

    用于 ToolExecutor 所有工具调用的返回值，
    替代各模块中分散的 Result 定义。
    """
    tool_name: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    error_type: Optional[str] = None
    is_retryable: bool = False
    is_blocked: bool = False
    block_reason: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "is_retryable": self.is_retryable,
            "is_blocked": self.is_blocked,
            "block_reason": self.block_reason,
            "execution_time": self.execution_time,
        }

    def get_output(self) -> Any:
        """获取输出，自动处理格式"""
        if self.is_blocked:
            return {"error": self.block_reason}
        if not self.success:
            return {"error": self.error}
        return self.output


@dataclass
class ToolInvokeRequest:
    """
    工具调用请求

    封装工具名称和参数，用于批量调用。
    """
    tool_name: str
    arguments: Dict[str, Any]
    context: Optional[Any] = None  # 传递给 Rail 的上下文

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "arguments": self.arguments,
        }


@dataclass
class ToolInvokeError:
    """
    工具调用错误信息

    用于结构化错误分类，不抛异常。
    """
    error_type: str
    message: str
    is_retryable: bool = False
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "is_retryable": self.is_retryable,
            "details": self.details,
        }


class ExecuteMode(Enum):
    """执行模式"""
    SEQUENTIAL = "sequential"  # 顺序执行
    CONCURRENT = "concurrent"  # 并发执行


@dataclass
class ExecuteOptions:
    """执行选项"""
    mode: ExecuteMode = ExecuteMode.SEQUENTIAL
    max_concurrent: int = 1
    stop_on_error: bool = False  # 遇到错误是否停止
    context: Optional[Any] = None  # 传递给 Rail 的上下文
