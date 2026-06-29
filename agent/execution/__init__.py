# -*- coding: utf-8 -*-
"""
Agent Execution - Agent 循环执行引擎

核心设计：
1. LLM 自主决策：是否调用工具、调用哪些工具、何时结束
2. 单轨模式：LLM 返回直接响应时自动结束
3. 可选增强：Todo 工具等作为可选组件

设计原则：
- 意图理解使用 LLM 动态判断，禁止硬编码关键词
- 任务完成由 LLM 自主判断何时结束
- 无显式的 Goal 模式，简化处理流程

使用方式：
```python
from agent.execution import AgentLoop, ExecutionContext

context = ExecutionContext(
    task_description="帮我做一个博客系统",
    tools=tools_schema,
    tool_handlers=tool_handlers
)

loop = AgentLoop(
    llm_provider=llm,
    session_id=session_id,
    rails=[TaskEventRail(session_id)]
)

result = await loop.run(context)
```

子层标识：✅ Task（循环执行任务相关逻辑时使用）
主层：🧠 Decision
"""

from agent.execution.context import (
    ExecutionContext,
    Message,
    ToolCallRecord,
    ToolDefinition,
    ToolCallInfo,
)
from agent.execution.loop import AgentLoop, LoopState, LoopStepResult, Decision

__all__ = [
    "AgentLoop",
    "LoopState",
    "LoopStepResult",
    "Decision",
    "ExecutionContext",
    "Message",
    "ToolCallRecord",
    "ToolDefinition",
    "ToolCallInfo",
]