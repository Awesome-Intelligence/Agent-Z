#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RailRegistry - Rails 统一注册表

设计目的：
- 单一注册入口，避免重复注册
- 单例模式，确保全局唯一
- 支持按 session_id 隔离 Rails
- 集成 trigger 方法，统一管理 Rails 生命周期

重要变更 (v2.0.0)：
- 整合 RailManager 功能，统一为单一 Registry
- 移除 RailManager，简化架构
"""

import asyncio
import threading
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from common.logging_manager import get_decision_logger

if TYPE_CHECKING:
    from agent.rails.rail import Rail, RailResult, RailContext


class RailRegistry:
    """
    Rails 统一注册表（单例）

    设计原则：
    1. 单一注册入口：所有 Rails 必须通过此 Registry 注册
    2. 按 session_id 隔离：不同会话的 Rails 互不影响
    3. 统一 trigger 接口：trigger_before/after 方法统一调用 Rails

    使用示例：
    ```python
    from agent.rails import get_rail_registry

    registry = get_rail_registry()

    # 注册 Rail
    registry.register(session_id, TaskEventRail(session_id))

    # 获取 Rails
    rails = registry.get_rails(session_id)

    # 触发 before_tool_call
    result = await registry.trigger_before_tool_call(session_id, "write_file", args)

    # 清理会话
    registry.clear_session(session_id)
    ```

    废弃的 API（RailManager 兼容）：
    ```python
    # 旧代码兼容
    manager = RailManager(session_id)  # 请改用 get_rail_registry()
    manager.register_rail(rail)        # 请改用 registry.register(session_id, rail)
    manager.pause()                    # 请改用 registry.pause(session_id)
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
        self._rails: Dict[str, List["Rail"]] = {}
        self._rail_by_name: Dict[str, Dict[str, "Rail"]] = {}  # session_id -> {name: rail}
        self._pause_events: Dict[str, asyncio.Event] = {}
        self._abort_flags: Dict[str, bool] = {}
        self._current_contexts: Dict[str, "RailContext"] = {}
        self._lock = threading.Lock()
        self.logger = get_decision_logger("RailRegistry", sublayer="rail")

    # ─────────────────────────────────────────────────────────────────
    # 核心注册方法
    # ─────────────────────────────────────────────────────────────────

    def register(self, session_id: str, rail: "Rail") -> None:
        """
        注册 Rail

        Args:
            session_id: 会话 ID
            rail: Rail 实例
        """
        with self._lock:
            if session_id not in self._rails:
                self._rails[session_id] = []
                self._rail_by_name[session_id] = {}

            # 避免重复注册（按名称）
            if rail.name in self._rail_by_name[session_id]:
                self.logger.warning(f"Rail '{rail.name}' already registered for session '{session_id}', skipping")
                return

            self._rails[session_id].append(rail)
            self._rail_by_name[session_id][rail.name] = rail

            # 初始化 pause event
            if session_id not in self._pause_events:
                self._pause_events[session_id] = asyncio.Event()
                self._pause_events[session_id].set()

            self.logger.debug(f"Registered rail: {rail.name} (priority: {rail.priority})")

    def unregister(self, session_id: str, rail_name: str) -> bool:
        """
        取消注册 Rail（按名称）

        Args:
            session_id: 会话 ID
            rail_name: Rail 名称

        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if session_id not in self._rail_by_name:
                return False

            if rail_name not in self._rail_by_name[session_id]:
                return False

            rail = self._rail_by_name[session_id].pop(rail_name)
            self._rails[session_id] = [r for r in self._rails[session_id] if r.name != rail_name]
            self.logger.info(f"Unregistered rail: {rail_name}")
            return True

    def unregister_by_instance(self, session_id: str, rail: "Rail") -> None:
        """
        取消注册 Rail（按实例）

        Args:
            session_id: 会话 ID
            rail: Rail 实例
        """
        with self._lock:
            self.unregister(session_id, rail.name)

    def get_rails(self, session_id: str) -> List["Rail"]:
        """
        获取 Rails 列表（按优先级排序）

        Args:
            session_id: 会话 ID

        Returns:
            该会话的所有 Rails 列表（按优先级降序）
        """
        with self._lock:
            rails = self._rails.get(session_id, [])
            return sorted(rails, reverse=True)

    def get_rail(self, session_id: str, rail_name: str) -> Optional["Rail"]:
        """
        获取单个 Rail 实例

        Args:
            session_id: 会话 ID
            rail_name: Rail 名称

        Returns:
            Rail 实例或 None
        """
        with self._lock:
            return self._rail_by_name.get(session_id, {}).get(rail_name)

    def has_rail(self, session_id: str, rail_name: str) -> bool:
        """
        检查 Rail 是否已注册

        Args:
            session_id: 会话 ID
            rail_name: Rail 名称

        Returns:
            True if rail is registered
        """
        with self._lock:
            return rail_name in self._rail_by_name.get(session_id, {})

    def clear_session(self, session_id: str) -> None:
        """
        清除会话的所有 Rails

        Args:
            session_id: 会话 ID
        """
        with self._lock:
            if session_id in self._rails:
                rail_names = [r.name for r in self._rails[session_id]]
                self._rails[session_id] = []
                self._rail_by_name[session_id] = {}
                self._pause_events.pop(session_id, None)
                self._abort_flags.pop(session_id, None)
                self._current_contexts.pop(session_id, None)
                self.logger.info(f"Cleared session '{session_id}': removed {len(rail_names)} rails")

    # ─────────────────────────────────────────────────────────────────
    # Rail 控制方法
    # ─────────────────────────────────────────────────────────────────

    def enable_rail(self, session_id: str, rail_name: str) -> bool:
        """启用 Rail"""
        rail = self.get_rail(session_id, rail_name)
        if rail:
            rail.enabled = True
            return True
        return False

    def disable_rail(self, session_id: str, rail_name: str) -> bool:
        """禁用 Rail"""
        rail = self.get_rail(session_id, rail_name)
        if rail:
            rail.enabled = False
            return True
        return False

    def set_context(self, session_id: str, context: "RailContext") -> None:
        """设置执行上下文"""
        self._current_contexts[session_id] = context
        for rail in self.get_rails(session_id):
            rail.set_context(context)

    # ─────────────────────────────────────────────────────────────────
    # Trigger 方法（统一调用 Rails）
    # ─────────────────────────────────────────────────────────────────

    async def trigger_before_llm_call(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> Optional["RailResult"]:
        """触发所有 Rail 的 before_llm_call"""
        from agent.rails.rail import RailResult

        combined_result = RailResult()

        for rail in self.get_rails(session_id):
            if not rail.enabled:
                continue

            try:
                result = await rail.before_llm_call(messages, model, **kwargs)
                if result and not result.allowed:
                    combined_result.allowed = False
                    combined_result.error = result.error
                    self.logger.warning(f"Rail '{rail.name}' blocked LLM call: {result.error}")
                    break
                elif result and result.modified_args:
                    messages = result.modified_args
            except Exception as e:
                rail.on_error(e, "before_llm_call")

        return combined_result if not combined_result.allowed else None

    async def trigger_after_llm_call(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        response: Any,
        **kwargs
    ) -> Optional["RailResult"]:
        """触发所有 Rail 的 after_llm_call"""
        from agent.rails.rail import RailResult

        injected_messages = []

        for rail in self.get_rails(session_id):
            if not rail.enabled:
                continue

            try:
                result = await rail.after_llm_call(messages, response, **kwargs)
                if result and result.injected_content:
                    injected_messages.append(result.injected_content)
            except Exception as e:
                rail.on_error(e, "after_llm_call")

        if injected_messages:
            return RailResult(injected_content="\n".join(injected_messages))
        return None

    async def trigger_before_tool_call(
        self,
        session_id: str,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> Optional["RailResult"]:
        """触发所有 Rail 的 before_tool_call"""
        from agent.rails.rail import RailResult

        combined_result = RailResult()

        for rail in self.get_rails(session_id):
            if not rail.enabled:
                continue

            try:
                result = await rail.before_tool_call(tool_name, args, **kwargs)
                if result and not result.allowed:
                    combined_result.allowed = False
                    combined_result.error = result.error
                    self.logger.warning(f"Rail '{rail.name}' blocked tool '{tool_name}': {result.error}")
                    break
                elif result and result.modified_args:
                    args = result.modified_args
            except Exception as e:
                self.logger.error(
                    f"Rail '{rail.name}' before_tool_call({tool_name}) error - type={type(e).__name__} msg={str(e)[:200]}"
                )
                rail.on_error(e, f"before_tool_call({tool_name})")

        return combined_result if not combined_result.allowed else None

    async def trigger_after_tool_call(
        self,
        session_id: str,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        **kwargs
    ) -> Optional["RailResult"]:
        """触发所有 Rail 的 after_tool_call"""
        from agent.rails.rail import RailResult

        injected_content = []

        for rail in self.get_rails(session_id):
            if not rail.enabled:
                continue

            try:
                result = await rail.after_tool_call(tool_name, args, result, **kwargs)
                if result and result.injected_content:
                    injected_content.append(result.injected_content)
            except Exception as e:
                rail.on_error(e, f"after_tool_call({tool_name})")

        if injected_content:
            return RailResult(injected_content="\n".join(injected_content))
        return None

    async def trigger_checkpoint(self, session_id: str, checkpoint_name: str) -> None:
        """触发 checkpoint"""
        if session_id not in self._pause_events:
            return

        pause_event = self._pause_events[session_id]
        await pause_event.wait()

        if self._abort_flags.get(session_id, False):
            self.logger.warning("Abort requested, raising CancelledError")
            raise asyncio.CancelledError("Agent abort requested")

        for rail in self.get_rails(session_id):
            if not rail.enabled:
                continue

            try:
                await rail.on_checkpoint(checkpoint_name)
            except Exception as e:
                self.logger.error(
                    f"Rail '{rail.name}' checkpoint({checkpoint_name}) error - type={type(e).__name__} msg={str(e)[:200]}"
                )
                rail.on_error(e, f"checkpoint({checkpoint_name})")

    # ─────────────────────────────────────────────────────────────────
    # 会话控制方法
    # ─────────────────────────────────────────────────────────────────

    def pause(self, session_id: str) -> None:
        """暂停会话的 Rails"""
        if session_id in self._pause_events:
            self._pause_events[session_id].clear()
        self.logger.info(f"Session '{session_id}' rails paused")

    def resume(self, session_id: str) -> None:
        """恢复会话的 Rails"""
        self._abort_flags[session_id] = False
        if session_id in self._pause_events:
            self._pause_events[session_id].set()
        self.logger.info(f"Session '{session_id}' rails resumed")

    def abort(self, session_id: str) -> None:
        """中止会话的 Rails"""
        self._abort_flags[session_id] = True
        if session_id in self._pause_events:
            self._pause_events[session_id].set()
        self.logger.warning(f"Session '{session_id}' rails abort requested")

    def is_paused(self, session_id: str) -> bool:
        """检查会话是否已暂停"""
        event = self._pause_events.get(session_id)
        return event is not None and not event.is_set()

    def is_aborted(self, session_id: str) -> bool:
        """检查会话是否已中止"""
        return self._abort_flags.get(session_id, False)

    async def wait_for_checkpoint(self, session_id: str) -> None:
        """等待 checkpoint（暂停点）"""
        if session_id not in self._pause_events:
            return

        pause_event = self._pause_events[session_id]
        await pause_event.wait()

        if self._abort_flags.get(session_id, False):
            self.logger.warning("Abort requested, raising CancelledError")
            raise asyncio.CancelledError("Agent abort requested")

    # ─────────────────────────────────────────────────────────────────
    # 状态查询
    # ─────────────────────────────────────────────────────────────────

    def get_summary(self, session_id: str) -> Dict[str, Any]:
        """获取 Rails 状态摘要"""
        rails = self._rails.get(session_id, [])
        return {
            "total_rails": len(rails),
            "enabled_rails": len([r for r in rails if r.enabled]),
            "rail_names": [r.name for r in sorted(rails, reverse=True)],
            "is_paused": self.is_paused(session_id),
            "is_aborted": self.is_aborted(session_id),
        }

    def get_all_sessions(self) -> List[str]:
        """获取所有活跃的会话 ID"""
        with self._lock:
            return list(self._rails.keys())


# ─────────────────────────────────────────────────────────────────
# 全局单例访问函数
# ─────────────────────────────────────────────────────────────────

_rail_registry: Optional[RailRegistry] = None


def get_rail_registry() -> RailRegistry:
    """
    获取 RailRegistry 单例

    Returns:
        RailRegistry 单例实例
    """
    global _rail_registry
    if _rail_registry is None:
        _rail_registry = RailRegistry()
    return _rail_registry


def reset_rail_registry() -> None:
    """重置 RailRegistry（主要用于测试）"""
    global _rail_registry
    if _rail_registry is not None:
        _rail_registry._init()
    _rail_registry = None


__all__ = [
    "RailRegistry",
    "get_rail_registry",
    "reset_rail_registry",
]
