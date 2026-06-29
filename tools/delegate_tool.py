#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delegate Tool Module - 子任务委托工具

基于 Hermes Agent 的 delegate_tool.py 实现，支持子代理的创建、并发执行和结果聚合。

核心功能：
1. 单任务委托：delegate_task
2. 批量委托：delegate_batch（支持并发）
3. 任务状态查询：get_subtask_status, list_subtasks

工具列表：
- delegate_task: 委托单个子任务
- delegate_batch: 批量委托子任务
- get_subtask_status: 获取子任务状态
- list_subtasks: 列出所有子任务

使用示例：
```json
// 单任务委托
{
  "goal": "分析这个代码库的架构",
  "context": "代码路径: /path/to/code, 语言: Python"
}

// 批量委托
{
  "tasks": [
    {"goal": "任务1", "context": "..."},
    {"goal": "任务2", "context": "..."}
  ],
  "max_concurrent": 3
}
```

子层标识：🔧 Tools
主层：✅ Task
"""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from common.logging_manager import get_execution_logger
from tools.registry import registry
from tools.subagent_manager import (
    SubagentManager,
    SubagentResult,
    SubagentStatus,
    SubagentRole,
    get_subagent_manager,
    DEFAULT_MAX_CONCURRENT,
)

logger = get_execution_logger("DelegateTool")


def _tool_error(message: str) -> str:
    """返回工具错误结果"""
    return json.dumps({"error": message}, ensure_ascii=False)


def _run_async(coro):
    """在同步函数中安全地运行协程"""
    try:
        loop = threading.current_thread()._async_loop
        return loop.run_until_complete(coro)
    except AttributeError:
        pass

    try:
        import asyncio
        loop = asyncio.get_running_loop()
    except RuntimeError:
        import asyncio
        return asyncio.run(coro)
    else:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result()


def delegate_task(
    goal: Optional[str] = None,
    context: Optional[str] = None,
    toolsets: Optional[List[str]] = None,
    role: Optional[str] = None,
    tasks: Optional[List[Dict[str, Any]]] = None,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    parent_agent=None,
) -> str:
    """
    委托子任务给子代理

    支持两种模式：
    1. 单任务模式：提供 goal 参数
    2. 批量模式：提供 tasks 参数

    Args:
        goal: 子任务描述
        context: 上下文信息
        toolsets: 工具集列表
        role: 子代理角色 ("leaf" 或 "orchestrator")
        tasks: 批量任务列表
        max_concurrent: 最大并发数（批量模式）
        parent_agent: 父代理实例（自动传入）

    Returns:
        JSON 格式的执行结果
    """
    if parent_agent is None:
        return _tool_error("delegate_task 需要父代理上下文")

    manager = get_subagent_manager()

    # 解析任务列表
    if tasks and isinstance(tasks, list):
        # 批量模式
        if len(tasks) > max_concurrent:
            return _tool_error(
                f"任务数量 {len(tasks)} 超过最大并发数 {max_concurrent}"
            )

        # 验证任务
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                return _tool_error(f"任务 {i} 必须是对象")
            if not task.get("goal", "").strip():
                return _tool_error(f"任务 {i} 缺少 goal 字段")

        # 获取父代理的 subagent_id（如果有）
        parent_subagent_id = getattr(parent_agent, "_subagent_id", None)

        # 在线程池中运行
        def _execute_batch():
            import asyncio

            async def _run():
                results = await manager.delegate_batch(
                    tasks=tasks,
                    max_concurrent=max_concurrent,
                    parent_agent=parent_agent,
                    parent_subagent_id=parent_subagent_id,
                )
                return results

            return asyncio.run(_run())

        results = _execute_batch()

        # 格式化结果
        result_list = []
        for result in results:
            entry = {
                "task_index": result.task_index,
                "status": result.status.value,
                "summary": result.summary,
                "error": result.error,
                "duration_seconds": result.duration_seconds,
                "api_calls": result.api_calls,
            }
            if result.error:
                entry["error"] = result.error
            result_list.append(entry)

        return json.dumps(
            {
                "results": result_list,
                "total_tasks": len(result_list),
                "completed": sum(1 for r in results if r.status == SubagentStatus.COMPLETED),
                "failed": sum(1 for r in results if r.status in (SubagentStatus.FAILED, SubagentStatus.TIMEOUT)),
            },
            ensure_ascii=False,
        )

    elif goal and isinstance(goal, str) and goal.strip():
        # 单任务模式
        effective_role = role or "leaf"
        parent_subagent_id = getattr(parent_agent, "_subagent_id", None)

        def _execute_single():
            import asyncio

            async def _run():
                return await manager.delegate_task(
                    goal=goal,
                    context=context,
                    toolsets=toolsets,
                    role=effective_role,
                    parent_agent=parent_agent,
                    parent_subagent_id=parent_subagent_id,
                )

            return asyncio.run(_run())

        result = _execute_single()

        # 格式化结果
        output = {
            "task_index": result.task_index,
            "status": result.status.value,
            "summary": result.summary,
            "duration_seconds": result.duration_seconds,
            "api_calls": result.api_calls,
        }

        if result.error:
            output["error"] = result.error

        return json.dumps(output, ensure_ascii=False)

    else:
        return _tool_error("请提供 goal（单任务）或 tasks（批量）参数")


def delegate_batch(
    tasks: List[Dict[str, Any]],
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    parent_agent=None,
) -> str:
    """
    批量委托子任务（并发执行）

    这是 delegate_task 的批量模式别名，参数相同。

    Args:
        tasks: 任务列表
        max_concurrent: 最大并发数
        parent_agent: 父代理实例

    Returns:
        JSON 格式的执行结果
    """
    return delegate_task(
        tasks=tasks,
        max_concurrent=max_concurrent,
        parent_agent=parent_agent,
    )


def get_subtask_status(
    task_id: str,
    parent_agent=None,
) -> str:
    """
    获取子任务状态

    Args:
        task_id: 子任务 ID
        parent_agent: 父代理实例

    Returns:
        JSON 格式的状态信息
    """
    manager = get_subagent_manager()
    record = manager.get_subagent(task_id)

    if record:
        result = {
            "success": True,
            "task": record.to_dict(),
        }
    else:
        result = {
            "success": False,
            "error": f"任务未找到: {task_id}",
        }

    return json.dumps(result, ensure_ascii=False)


def list_subtasks(
    parent_task_id: Optional[str] = None,
    parent_agent=None,
) -> str:
    """
    列出所有子任务

    Args:
        parent_task_id: 父任务 ID（可选，用于过滤）
        parent_agent: 父代理实例

    Returns:
        JSON 格式的任务列表
    """
    manager = get_subagent_manager()
    tasks = manager.list_active()

    # 如果指定了父任务 ID，过滤
    if parent_task_id:
        tasks = [t for t in tasks if t.parent_id == parent_task_id]

    result = {
        "success": True,
        "tasks": [t.to_dict() for t in tasks],
        "total": len(tasks),
    }

    return json.dumps(result, ensure_ascii=False)


def pause_delegation() -> str:
    """
    暂停子代理生成

    Returns:
        JSON 格式的状态信息
    """
    manager = get_subagent_manager()
    manager.pause_spawn()
    return json.dumps({"success": True, "message": "子代理生成已暂停"})


def resume_delegation() -> str:
    """
    恢复子代理生成

    Returns:
        JSON 格式的状态信息
    """
    manager = get_subagent_manager()
    manager.resume_spawn()
    return json.dumps({"success": True, "message": "子代理生成已恢复"})


def check_delegate_requirements() -> bool:
    """代理工具无外部依赖，始终可用"""
    return True


# ─────────────────────────────────────────────────────────────────
# 工具定义
# ─────────────────────────────────────────────────────────────────

DELEGATE_TASK_SCHEMA = {
    "name": "delegate_task",
    "description": (
        "Spawn one or more subagents to work on tasks in isolated contexts. "
        "Each subagent gets its own conversation, toolset, and execution environment. "
        "Only the final summary is returned -- intermediate tool results "
        "never enter your context window.\n\n"
        "TWO MODES (one of 'goal' or 'tasks' is required):\n"
        "1. Single task: provide 'goal' (+ optional context, toolsets, role)\n"
        "2. Batch (parallel): provide 'tasks' array with up to {max_concurrent} "
        "items run concurrently.\n\n"
        "WHEN TO USE delegate_task:\n"
        "- Reasoning-heavy subtasks (debugging, code review, research synthesis)\n"
        "- Tasks that would flood your context with intermediate data\n"
        "- Parallel independent workstreams (research A and B simultaneously)\n\n"
        "WHEN NOT TO USE:\n"
        "- Mechanical multi-step work with no reasoning needed -> use todo tool\n"
        "- Single tool call -> just call the tool directly\n"
        "- Tasks needing user interaction -> subagents cannot use clarify\n\n"
        "IMPORTANT:\n"
        "- Subagents have NO memory of your conversation. Pass all relevant "
        "info (file paths, error messages, constraints) via the 'context' field.\n"
        "- Leaf subagents (role='leaf', the default) CANNOT delegate further.\n"
        "- Orchestrator subagents (role='orchestrator') CAN delegate to their own workers.\n"
        "- Each subagent gets its own isolated execution context.\n"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": (
                    "What the subagent should accomplish. Be specific and "
                    "self-contained -- the subagent knows nothing about your "
                    "conversation history."
                ),
            },
            "context": {
                "type": "string",
                "description": (
                    "Background information the subagent needs: file paths, "
                    "error messages, project structure, constraints. The more "
                    "specific you are, the better the subagent performs."
                ),
            },
            "toolsets": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Toolsets to enable for this subagent. "
                    "Default: inherits parent's enabled toolsets. "
                    "Available: files, terminal, web, code, system, ai."
                ),
            },
            "role": {
                "type": "string",
                "enum": ["leaf", "orchestrator"],
                "description": (
                    "Role of the child agent. 'leaf' (default) = focused "
                    "worker, cannot delegate further. 'orchestrator' = can "
                    "use delegate_task to spawn its own workers."
                ),
            },
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string", "description": "Task goal"},
                        "context": {
                            "type": "string",
                            "description": "Task-specific context",
                        },
                        "toolsets": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Toolsets for this specific task.",
                        },
                        "role": {
                            "type": "string",
                            "enum": ["leaf", "orchestrator"],
                            "description": "Per-task role override.",
                        },
                    },
                    "required": ["goal"],
                },
                "description": "Batch mode: tasks to run in parallel.",
            },
            "max_concurrent": {
                "type": "integer",
                "default": DEFAULT_MAX_CONCURRENT,
                "description": f"Maximum concurrent subagents (default: {DEFAULT_MAX_CONCURRENT}).",
            },
        },
    },
}


DELEGATE_BATCH_SCHEMA = {
    "name": "delegate_batch",
    "description": (
        "Delegate multiple subtasks at once for parallel execution. "
        "This is useful when you have multiple independent tasks that can be worked on concurrently."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "context": {"type": "string"},
                        "toolsets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "role": {
                            "type": "string",
                            "enum": ["leaf", "orchestrator"],
                        },
                    },
                    "required": ["goal"],
                },
                "description": "List of subtasks to delegate.",
            },
            "max_concurrent": {
                "type": "integer",
                "default": DEFAULT_MAX_CONCURRENT,
                "description": f"Maximum concurrent subagents (default: {DEFAULT_MAX_CONCURRENT}).",
            },
        },
        "required": ["tasks"],
    },
}


GET_SUBTASK_STATUS_SCHEMA = {
    "name": "get_subtask_status",
    "description": "Get the status and result of a subtask.",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "The ID of the subtask to check.",
            },
        },
        "required": ["task_id"],
    },
}


LIST_SUBTASKS_SCHEMA = {
    "name": "list_subtasks",
    "description": "List all active subtasks.",
    "parameters": {
        "type": "object",
        "properties": {
            "parent_task_id": {
                "type": "string",
                "description": "Optional parent task ID to filter by.",
            },
        },
    },
}


PAUSE_DELEGATION_SCHEMA = {
    "name": "pause_delegation",
    "description": "Pause new subagent spawning. Active subagents continue running.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


RESUME_DELEGATION_SCHEMA = {
    "name": "resume_delegation",
    "description": "Resume subagent spawning after a pause.",
    "parameters": {
        "type": "object",
        "properties": {},
    },
}


# ─────────────────────────────────────────────────────────────────
# 注册工具
# ─────────────────────────────────────────────────────────────────

registry.register(
    name="delegate_task",
    toolset="delegate",
    schema=DELEGATE_TASK_SCHEMA,
    handler=lambda args, **kw: delegate_task(
        goal=args.get("goal"),
        context=args.get("context"),
        toolsets=args.get("toolsets"),
        role=args.get("role"),
        tasks=args.get("tasks"),
        max_concurrent=args.get("max_concurrent", DEFAULT_MAX_CONCURRENT),
        parent_agent=kw.get("parent_agent"),
    ),
    check_fn=check_delegate_requirements,
    emoji="🔀",
)


registry.register(
    name="delegate_batch",
    toolset="delegate",
    schema=DELEGATE_BATCH_SCHEMA,
    handler=lambda args, **kw: delegate_batch(
        tasks=args.get("tasks", []),
        max_concurrent=args.get("max_concurrent", DEFAULT_MAX_CONCURRENT),
        parent_agent=kw.get("parent_agent"),
    ),
    check_fn=check_delegate_requirements,
    emoji="📦",
)


registry.register(
    name="get_subtask_status",
    toolset="delegate",
    schema=GET_SUBTASK_STATUS_SCHEMA,
    handler=lambda args, **kw: get_subtask_status(
        task_id=args.get("task_id", ""),
        parent_agent=kw.get("parent_agent"),
    ),
    check_fn=check_delegate_requirements,
    emoji="📊",
)


registry.register(
    name="list_subtasks",
    toolset="delegate",
    schema=LIST_SUBTASKS_SCHEMA,
    handler=lambda args, **kw: list_subtasks(
        parent_task_id=args.get("parent_task_id"),
        parent_agent=kw.get("parent_agent"),
    ),
    check_fn=check_delegate_requirements,
    emoji="📋",
)


registry.register(
    name="pause_delegation",
    toolset="delegate",
    schema=PAUSE_DELEGATION_SCHEMA,
    handler=lambda args, **kw: pause_delegation(),
    check_fn=check_delegate_requirements,
    emoji="⏸️",
)


registry.register(
    name="resume_delegation",
    toolset="delegate",
    schema=RESUME_DELEGATION_SCHEMA,
    handler=lambda args, **kw: resume_delegation(),
    check_fn=check_delegate_requirements,
    emoji="▶️",
)