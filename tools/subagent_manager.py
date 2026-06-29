#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SubagentManager - 子代理生命周期管理器

参考 Hermes 的 delegate_tool.py 实现，管理子代理的创建、运行、监控和销毁。

核心功能：
1. 子代理创建和隔离执行
2. 并发执行多个子代理（ThreadPoolExecutor）
3. 子代理进度和状态追踪
4. 中断和取消支持
5. 资源清理

子层标识：🔧 Tools
主层：✅ Task
"""

import asyncio
import concurrent.futures
import json
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from common.logging_manager import get_execution_logger

logger = get_execution_logger("SubagentManager")


class SubagentStatus(str, Enum):
    """子代理状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class SubagentRole(str, Enum):
    """子代理角色"""
    LEAF = "leaf"  # 不能进一步委托
    ORCHESTRATOR = "orchestrator"  # 可以委托更多子代理


# 默认配置
DEFAULT_MAX_CONCURRENT = 3
DEFAULT_MAX_ITERATIONS = 50
DEFAULT_TIMEOUT_SECONDS = 600  # 10 分钟
MAX_SPAWN_DEPTH = 1  # 默认不允许嵌套委托

# 子代理被禁止使用的工具
BLOCKED_TOOLS = frozenset([
    "delegate_subtask",  # 禁止递归委托
    "delegate_batch",    # 禁止递归委托
    "clarify",           # 禁止用户交互
    "memory",            # 禁止写入共享记忆
])


@dataclass
class SubagentRecord:
    """子代理记录"""
    subagent_id: str
    parent_id: Optional[str]
    depth: int
    goal: str
    context: Optional[str]
    role: SubagentRole
    status: SubagentStatus
    model: Optional[str] = None
    toolsets: Optional[List[str]] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    tool_count: int = 0
    last_tool: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subagent_id": self.subagent_id,
            "parent_id": self.parent_id,
            "depth": self.depth,
            "goal": self.goal[:100] + "..." if len(self.goal) > 100 else self.goal,
            "status": self.status.value,
            "role": self.role.value,
            "tool_count": self.tool_count,
            "duration_seconds": (
                round(self.completed_at - self.started_at, 2)
                if self.started_at and self.completed_at
                else None
            ),
        }


@dataclass
class SubagentResult:
    """子代理执行结果"""
    subagent_id: str
    task_index: int
    status: SubagentStatus
    summary: Optional[str] = None
    error: Optional[str] = None
    exit_reason: str = "unknown"
    api_calls: int = 0
    duration_seconds: float = 0.0
    tool_trace: List[Dict[str, Any]] = field(default_factory=list)
    tokens: Dict[str, int] = field(default_factory=dict)
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)


class SubagentManager:
    """
    子代理生命周期管理器

    设计原则：
    1. 单一实例：全局管理所有子代理
    2. 线程安全：使用锁保护共享状态
    3. 资源隔离：每个子代理有独立的执行环境
    4. 进度追踪：支持回调通知进度变化

    使用示例：
    ```python
    manager = SubagentManager()

    # 单任务委托
    result = await manager.delegate_task(
        goal="分析这个代码库",
        context="路径: /path/to/code",
        parent_agent=agent,
    )

    # 批量委托
    results = await manager.delegate_batch(
        tasks=[
            {"goal": "任务1", "context": "..."},
            {"goal": "任务2", "context": "..."},
        ],
        max_concurrent=3,
        parent_agent=agent,
    )
    ```
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        """初始化内部状态"""
        self._active_subagents: Dict[str, SubagentRecord] = {}
        self._active_subagents_lock = threading.Lock()
        self._progress_callbacks: List[Callable] = []
        self._spawn_paused = False
        self._spawn_pause_lock = threading.Lock()

    # ─────────────────────────────────────────────────────────────────
    # 单例管理
    # ─────────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> "SubagentManager":
        """获取单例实例"""
        return cls()

    @classmethod
    def reset(cls) -> None:
        """重置单例（主要用于测试）"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance._active_subagents.clear()
                cls._instance._progress_callbacks.clear()
                cls._instance._spawn_paused = False
            cls._instance = None

    # ─────────────────────────────────────────────────────────────────
    # 进度回调
    # ─────────────────────────────────────────────────────────────────

    def on_progress(self, callback: Callable) -> None:
        """注册进度回调"""
        self._progress_callbacks.append(callback)

    def off_progress(self, callback: Callable) -> None:
        """取消进度回调"""
        if callback in self._progress_callbacks:
            self._progress_callbacks.remove(callback)

    def _emit_progress(
        self,
        event: str,
        subagent_id: str,
        goal: str,
        **kwargs
    ) -> None:
        """发射进度事件"""
        payload = {
            "event": event,
            "subagent_id": subagent_id,
            "goal": goal,
            **kwargs
        }
        for callback in self._progress_callbacks:
            try:
                callback(payload)
            except Exception as e:
                logger.debug(f"进度回调失败: {e}")

    # ─────────────────────────────────────────────────────────────────
    # Spawn 控制
    # ─────────────────────────────────────────────────────────────────

    def pause_spawn(self) -> bool:
        """暂停新的子代理生成"""
        with self._spawn_pause_lock:
            self._spawn_paused = True
            return self._spawn_paused

    def resume_spawn(self) -> bool:
        """恢复子代理生成"""
        with self._spawn_pause_lock:
            self._spawn_paused = False
            return not self._spawn_paused

    def is_spawn_paused(self) -> bool:
        """检查是否暂停生成"""
        with self._spawn_pause_lock:
            return self._spawn_paused

    # ─────────────────────────────────────────────────────────────────
    # 子代理注册
    # ─────────────────────────────────────────────────────────────────

    def _register(self, record: SubagentRecord) -> None:
        """注册子代理"""
        with self._active_subagents_lock:
            self._active_subagents[record.subagent_id] = record

    def _unregister(self, subagent_id: str) -> None:
        """取消注册子代理"""
        with self._active_subagents_lock:
            self._active_subagents.pop(subagent_id, None)

    def _update(self, subagent_id: str, **kwargs) -> None:
        """更新子代理记录"""
        with self._active_subagents_lock:
            if subagent_id in self._active_subagents:
                record = self._active_subagents[subagent_id]
                for key, value in kwargs.items():
                    if hasattr(record, key):
                        setattr(record, key, value)

    def get_subagent(self, subagent_id: str) -> Optional[SubagentRecord]:
        """获取子代理记录"""
        with self._active_subagents_lock:
            return self._active_subagents.get(subagent_id)

    def list_active(self) -> List[SubagentRecord]:
        """列出所有活跃子代理"""
        with self._active_subagents_lock:
            return list(self._active_subagents.values())

    # ─────────────────────────────────────────────────────────────────
    # 核心委托方法
    # ─────────────────────────────────────────────────────────────────

    def _build_child_system_prompt(
        self,
        goal: str,
        context: Optional[str] = None,
        role: SubagentRole = SubagentRole.LEAF,
        child_depth: int = 1,
    ) -> str:
        """构建子代理系统提示"""
        parts = [
            "You are a focused subagent working on a specific delegated task.",
            "",
            f"YOUR TASK:\n{goal}",
        ]

        if context and context.strip():
            parts.append(f"\nCONTEXT:\n{context}")

        parts.append(
            "\nComplete this task using the tools available to you. "
            "When finished, provide a clear, concise summary of:\n"
            "- What you did\n"
            "- What you found or accomplished\n"
            "- Any files you created or modified\n"
            "- Any issues encountered\n\n"
            "Be thorough but concise -- your response is returned to the "
            "parent agent as a summary."
        )

        if role == SubagentRole.ORCHESTRATOR:
            parts.append(
                "\n## Subagent Spawning (Orchestrator Role)\n"
                "You have access to the `delegate_subtask` tool and CAN spawn "
                "your own subagents to parallelize independent work.\n\n"
                "WHEN to delegate:\n"
                "- The goal decomposes into 2+ independent subtasks that can "
                "run in parallel.\n"
                "- A subtask is reasoning-heavy.\n\n"
                "WHEN NOT to delegate:\n"
                "- Single-step mechanical work.\n"
                "- Trivial tasks you can execute in one or two tool calls.\n"
            )

        return "\n".join(parts)

    def _create_subagent(
        self,
        task_index: int,
        goal: str,
        context: Optional[str] = None,
        toolsets: Optional[List[str]] = None,
        role: SubagentRole = SubagentRole.LEAF,
        parent_agent: Any = None,
        parent_subagent_id: Optional[str] = None,
        child_depth: int = 1,
    ) -> tuple[str, SubagentRecord]:
        """创建子代理实例"""
        subagent_id = f"sa-{task_index}-{uuid.uuid4().hex[:8]}"

        record = SubagentRecord(
            subagent_id=subagent_id,
            parent_id=parent_subagent_id,
            depth=child_depth,
            goal=goal,
            context=context,
            role=role,
            status=SubagentStatus.PENDING,
            toolsets=toolsets,
            model=getattr(parent_agent, "model", None) if parent_agent else None,
        )

        return subagent_id, record

    def _run_single_child(
        self,
        task_index: int,
        goal: str,
        context: Optional[str],
        toolsets: Optional[List[str]],
        role: SubagentRole,
        parent_agent: Any,
        subagent_id: str,
        parent_subagent_id: Optional[str],
        child_depth: int,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> SubagentResult:
        """在独立线程中运行子代理"""
        start_time = time.monotonic()

        # 注册子代理
        record = SubagentRecord(
            subagent_id=subagent_id,
            parent_id=parent_subagent_id,
            depth=child_depth,
            goal=goal,
            context=context,
            role=role,
            status=SubagentStatus.RUNNING,
            toolsets=toolsets,
            model=getattr(parent_agent, "model", None),
            started_at=start_time,
        )
        self._register(record)
        self._emit_progress("subagent.start", subagent_id, goal)

        try:
            # 构建子代理的系统提示
            system_prompt = self._build_child_system_prompt(
                goal=goal,
                context=context,
                role=role,
                child_depth=child_depth,
            )

            # 在线程池中运行子代理
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._execute_subagent_sync,
                    goal=goal,
                    context=context,
                    toolsets=toolsets,
                    system_prompt=system_prompt,
                    parent_agent=parent_agent,
                    subagent_id=subagent_id,
                )

                try:
                    result = future.result(timeout=timeout_seconds)
                except FuturesTimeoutError:
                    result = {
                        "status": "timeout",
                        "error": f"Subagent timed out after {timeout_seconds}s",
                        "summary": None,
                    }

            # 处理结果
            status = result.get("status", "completed")
            summary = result.get("summary")
            error = result.get("error")

            end_time = time.monotonic()
            duration = round(end_time - start_time, 2)

            if status == "timeout":
                subagent_status = SubagentStatus.TIMEOUT
            elif status == "error" or status == "failed":
                subagent_status = SubagentStatus.FAILED
            elif summary:
                subagent_status = SubagentStatus.COMPLETED
            else:
                subagent_status = SubagentStatus.FAILED

            subagent_result = SubagentResult(
                subagent_id=subagent_id,
                task_index=task_index,
                status=subagent_status,
                summary=summary,
                error=error,
                duration_seconds=duration,
                api_calls=result.get("api_calls", 0),
                tool_trace=result.get("tool_trace", []),
                tokens=result.get("tokens", {}),
                files_read=result.get("files_read", []),
                files_written=result.get("files_written", []),
            )

            # 更新记录
            self._update(
                subagent_id,
                status=subagent_status,
                completed_at=end_time,
                result=subagent_result.__dict__,
            )

            self._emit_progress(
                "subagent.complete",
                subagent_id,
                goal,
                status=subagent_status.value,
                duration_seconds=duration,
                summary=summary,
            )

            return subagent_result

        except Exception as e:
            end_time = time.monotonic()
            logger.exception(f"子代理 {subagent_id} 执行失败")

            self._update(
                subagent_id,
                status=SubagentStatus.FAILED,
                completed_at=end_time,
                error=str(e),
            )

            return SubagentResult(
                subagent_id=subagent_id,
                task_index=task_index,
                status=SubagentStatus.FAILED,
                error=str(e),
                duration_seconds=round(end_time - start_time, 2),
            )

        finally:
            self._unregister(subagent_id)

    def _execute_subagent_sync(
        self,
        goal: str,
        context: Optional[str],
        toolsets: Optional[List[str]],
        system_prompt: str,
        parent_agent: Any,
        subagent_id: str,
    ) -> Dict[str, Any]:
        """
        同步执行子代理（在新线程中运行）

        注意：这是简化实现，实际需要创建新的 Agent 实例
        """
        from agent.agent import Agent

        # 创建子代理实例
        # 注意：这里需要传递正确的配置
        try:
            # 使用父代理的 LLM 提供者
            llm_provider = getattr(parent_agent, "llm_provider", None)

            child_agent = Agent(
                llm_provider=llm_provider,
                enable_session=False,
                enable_curator=False,
            )

            # 运行对话
            response = asyncio.run(child_agent.chat(
                user_input=goal,
                conversation_history=[],
            ))

            return {
                "status": "completed",
                "summary": response.content if response else None,
                "api_calls": 1,
            }

        except Exception as e:
            logger.debug(f"子代理执行异常: {e}")
            return {
                "status": "error",
                "error": str(e),
                "summary": None,
            }

    async def delegate_task(
        self,
        goal: str,
        context: Optional[str] = None,
        toolsets: Optional[List[str]] = None,
        role: str = "leaf",
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        parent_agent: Any = None,
        parent_subagent_id: Optional[str] = None,
    ) -> SubagentResult:
        """
        委托单个子任务

        Args:
            goal: 子任务描述
            context: 上下文信息
            toolsets: 工具集列表
            role: 子代理角色 ("leaf" 或 "orchestrator")
            max_iterations: 最大迭代次数
            parent_agent: 父代理实例
            parent_subagent_id: 父代理 ID

        Returns:
            SubagentResult: 执行结果
        """
        if self.is_spawn_paused():
            return SubagentResult(
                subagent_id="",
                task_index=0,
                status=SubagentStatus.FAILED,
                error="子代理生成已暂停",
            )

        # 解析角色
        effective_role = SubagentRole.ORCHESTRATOR if role == "orchestrator" else SubagentRole.LEAF

        # 检查深度限制
        parent_depth = 0
        if parent_subagent_id:
            parent_record = self.get_subagent(parent_subagent_id)
            if parent_record:
                parent_depth = parent_record.depth

        child_depth = parent_depth + 1
        if child_depth >= MAX_SPAWN_DEPTH and effective_role == SubagentRole.ORCHESTRATOR:
            effective_role = SubagentRole.LEAF

        # 创建子代理
        subagent_id, _ = self._create_subagent(
            task_index=0,
            goal=goal,
            context=context,
            toolsets=toolsets,
            role=effective_role,
            parent_agent=parent_agent,
            parent_subagent_id=parent_subagent_id,
            child_depth=child_depth,
        )

        # 运行子代理
        result = self._run_single_child(
            task_index=0,
            goal=goal,
            context=context,
            toolsets=toolsets,
            role=effective_role,
            parent_agent=parent_agent,
            subagent_id=subagent_id,
            parent_subagent_id=parent_subagent_id,
            child_depth=child_depth,
            timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
        )

        return result

    async def delegate_batch(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        parent_agent: Any = None,
        parent_subagent_id: Optional[str] = None,
    ) -> List[SubagentResult]:
        """
        批量委托子任务（并发执行）

        Args:
            tasks: 任务列表，每个任务包含 goal, context, toolsets, role
            max_concurrent: 最大并发数
            parent_agent: 父代理实例
            parent_subagent_id: 父代理 ID

        Returns:
            List[SubagentResult]: 执行结果列表
        """
        if self.is_spawn_paused():
            return [
                SubagentResult(
                    subagent_id="",
                    task_index=i,
                    status=SubagentStatus.FAILED,
                    error="子代理生成已暂停",
                )
                for i in range(len(tasks))
            ]

        # 限制并发数
        max_concurrent = min(max_concurrent, DEFAULT_MAX_CONCURRENT)

        # 获取父代理深度
        parent_depth = 0
        if parent_subagent_id:
            parent_record = self.get_subagent(parent_subagent_id)
            if parent_record:
                parent_depth = parent_record.depth

        child_depth = parent_depth + 1

        # 创建所有子代理
        children = []
        for i, task_info in enumerate(tasks):
            goal = task_info.get("goal", "")
            context = task_info.get("context")
            toolsets = task_info.get("toolsets")
            role_str = task_info.get("role", "leaf")
            effective_role = SubagentRole.ORCHESTRATOR if role_str == "orchestrator" else SubagentRole.LEAF

            # 检查深度限制
            if child_depth >= MAX_SPAWN_DEPTH and effective_role == SubagentRole.ORCHESTRATOR:
                effective_role = SubagentRole.LEAF

            subagent_id, _ = self._create_subagent(
                task_index=i,
                goal=goal,
                context=context,
                toolsets=toolsets,
                role=effective_role,
                parent_agent=parent_agent,
                parent_subagent_id=parent_subagent_id,
                child_depth=child_depth,
            )

            children.append({
                "task_index": i,
                "goal": goal,
                "context": context,
                "toolsets": toolsets,
                "role": effective_role,
                "subagent_id": subagent_id,
            })

        # 并发执行
        results = []
        completed_count = 0

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {}

            for child in children:
                future = executor.submit(
                    self._run_single_child,
                    task_index=child["task_index"],
                    goal=child["goal"],
                    context=child["context"],
                    toolsets=child["toolsets"],
                    role=child["role"],
                    parent_agent=parent_agent,
                    subagent_id=child["subagent_id"],
                    parent_subagent_id=parent_subagent_id,
                    child_depth=child_depth,
                )
                futures[future] = child["task_index"]

            # 等待完成
            from concurrent.futures import wait as cf_wait, FIRST_COMPLETED

            pending = set(futures.keys())
            while pending:
                done, pending = cf_wait(pending, timeout=0.5, return_when=FIRST_COMPLETED)

                for future in done:
                    task_index = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = SubagentResult(
                            subagent_id=children[task_index]["subagent_id"],
                            task_index=task_index,
                            status=SubagentStatus.FAILED,
                            error=str(e),
                        )

                    results.append(result)
                    completed_count += 1

                    # 发射进度
                    child = children[task_index]
                    self._emit_progress(
                        "subagent.progress",
                        child["subagent_id"],
                        child["goal"],
                        completed=completed_count,
                        total=len(children),
                    )

        # 按任务索引排序
        results.sort(key=lambda r: r.task_index)
        return results


# 全局单例
_subagent_manager: Optional[SubagentManager] = None


def get_subagent_manager() -> SubagentManager:
    """获取 SubagentManager 单例"""
    global _subagent_manager
    if _subagent_manager is None:
        _subagent_manager = SubagentManager.get_instance()
    return _subagent_manager


def reset_subagent_manager() -> None:
    """重置 SubagentManager（主要用于测试）"""
    global _subagent_manager
    SubagentManager.reset()
    _subagent_manager = None


__all__ = [
    "SubagentManager",
    "SubagentRecord",
    "SubagentResult",
    "SubagentStatus",
    "SubagentRole",
    "get_subagent_manager",
    "reset_subagent_manager",
    "BLOCKED_TOOLS",
    "DEFAULT_MAX_CONCURRENT",
    "DEFAULT_MAX_ITERATIONS",
    "DEFAULT_TIMEOUT_SECONDS",
]