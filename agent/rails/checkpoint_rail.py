#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CheckpointRail - 危险操作的自动快照拦截器

在文件修改和危险终端命令执行前自动创建快照，
确保可以回滚到操作前的状态。

Rail 生命周期：
- before_tool_call: 在工具调用前创建快照（针对需要快照的工具）

参考 Hermes Agent 的 CheckpointManager 集成设计。
"""

from typing import Any, Dict, Optional

from agent.rails.rail import Rail, RailResult, RailPriority
from agent.checkpoint import (
    CheckpointManager,
    get_checkpoint_manager,
    SNAPSHOT_TOOLS,
)


class CheckpointRail(Rail):
    """
    危险操作自动快照 Rail

    功能：
    1. 在 write_file、patch、terminal 等工具调用前自动创建快照
    2. 对危险终端命令（rm -rf、format 等）创建额外快照
    3. 支持配置是否启用

    使用方法：
    ```python
    # 在 agent.py 中注册
    checkpoint_rail = CheckpointRail(session_id, enabled=True)
    rail_registry.register(session_id, checkpoint_rail)
    ```
    """

    name = "checkpoint"
    description = "自动为危险操作创建快照"
    priority = RailPriority.HIGH  # 高优先级，确保在其他检查之前执行

    def __init__(
        self,
        session_id: str,
        enabled: bool = True,
        checkpoint_manager: Optional[CheckpointManager] = None,
        **kwargs
    ):
        super().__init__(session_id, **kwargs)
        self._enabled = enabled
        self._checkpoint_mgr = checkpoint_manager
        self._snapshot_created: Dict[str, bool] = {}  # 记录每轮是否已创建快照

    @property
    def enabled(self) -> bool:
        """Rail 是否启用"""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """设置 Rail 启用状态"""
        self._enabled = value

    def _get_checkpoint_manager(self) -> Optional[CheckpointManager]:
        """获取 CheckpointManager 实例"""
        if self._checkpoint_mgr is not None:
            return self._checkpoint_mgr
        return get_checkpoint_manager(enabled=self._enabled)

    def reset_round(self) -> None:
        """重置每轮状态"""
        self._snapshot_created.clear()

    async def before_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        **kwargs
    ) -> Optional[RailResult]:
        """
        工具调用前触发 - 创建快照

        检查是否需要为当前工具创建快照：
        1. 工具在 SNAPSHOT_TOOLS 中
        2. 当前轮次尚未创建快照

        Args:
            tool_name: 工具名称
            args: 工具参数

        Returns:
            RailResult: 始终返回 None（不阻止调用）
        """
        if not self._enabled:
            return None

        # 检查工具是否需要快照
        if not self._should_snapshot(tool_name, args):
            return None

        # 检查当前轮次是否已创建快照
        round_key = f"{self.session_id}:{tool_name}"
        if self._snapshot_created.get(round_key, False):
            self.logger.debug(f"Snapshot already created for this round: {tool_name}")
            return None

        # 获取工作目录
        work_dir = self._get_work_dir(tool_name, args)
        if not work_dir:
            self.logger.debug(f"Cannot determine work directory for {tool_name}")
            return None

        # 创建快照
        checkpoint_mgr = self._get_checkpoint_manager()
        if checkpoint_mgr is None or not checkpoint_mgr.is_enabled():
            return None

        message = self._build_snapshot_message(tool_name, args)
        try:
            commit_hash = checkpoint_mgr.ensure_checkpoint(work_dir, message)
            if commit_hash:
                self.logger.info(f"Created checkpoint {commit_hash[:8]} before {tool_name}")
                self._snapshot_created[round_key] = True
                # 存储快照信息供后续使用
                self._last_checkpoint = {
                    "hash": commit_hash,
                    "tool": tool_name,
                    "work_dir": work_dir,
                    "message": message,
                }
        except Exception as e:
            self.logger.warning(f"Failed to create checkpoint: {e}")

        return None

    def _should_snapshot(self, tool_name: str, args: Dict[str, Any]) -> bool:
        """判断是否应该创建快照"""
        # 检查工具是否在需要快照的列表中
        if tool_name not in SNAPSHOT_TOOLS:
            return False

        # 对于 write_file 和 patch，检查是否有有效的路径
        if tool_name in ("write_file", "patch"):
            file_path = args.get("path") or args.get("file_path")
            if not file_path:
                return False

        # 对于 terminal，检查是否为危险命令
        if tool_name == "terminal":
            command = args.get("command", "")
            if not command:
                return False
            checkpoint_mgr = self._get_checkpoint_manager()
            if checkpoint_mgr and checkpoint_mgr.is_destructive_command(command):
                self.logger.info(f"Destructive terminal command detected: {command[:50]}...")
                return True
            # 非危险命令不创建快照
            return False

        return True

    def _get_work_dir(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """获取工具执行的工作目录"""
        # 优先使用参数中的 workdir
        work_dir = args.get("workdir") or args.get("cwd")
        if work_dir:
            return work_dir

        # 对于文件操作，从文件路径推断
        if tool_name in ("write_file", "patch", "str_replace_editor"):
            file_path = args.get("path") or args.get("file_path")
            if file_path:
                checkpoint_mgr = self._get_checkpoint_manager()
                if checkpoint_mgr:
                    return checkpoint_mgr.get_working_dir_for_path(file_path)

        # 对于终端命令，尝试获取当前工作目录
        if tool_name == "terminal":
            import os
            return os.getcwd()

        return None

    def _build_snapshot_message(self, tool_name: str, args: Dict[str, Any]) -> str:
        """构建快照消息"""
        if tool_name == "write_file":
            path = args.get("path", "unknown")
            return f"Before write_file: {path}"
        elif tool_name == "patch":
            path = args.get("path", "unknown")
            return f"Before patch: {path}"
        elif tool_name == "terminal":
            command = args.get("command", "")[:60]
            return f"Before terminal: {command}..."
        elif tool_name == "str_replace_editor":
            path = args.get("path", "unknown")
            return f"Before str_replace_editor: {path}"
        else:
            return f"Before {tool_name}"

    def get_last_checkpoint(self) -> Optional[Dict[str, str]]:
        """获取最后创建的检查点信息"""
        return getattr(self, "_last_checkpoint", None)

    def rollback_to_last(self, file_path: Optional[str] = None) -> tuple:
        """
        回滚到最后创建的检查点

        Args:
            file_path: 可选，只回滚特定文件

        Returns:
            (success, message)
        """
        checkpoint_info = self.get_last_checkpoint()
        if not checkpoint_info:
            return False, "No checkpoint to rollback to"

        checkpoint_mgr = self._get_checkpoint_manager()
        if not checkpoint_mgr:
            return False, "Checkpoint manager not available"

        return checkpoint_mgr.restore_checkpoint(
            work_dir=checkpoint_info["work_dir"],
            commit_hash=checkpoint_info["hash"],
            file_path=file_path,
        )


__all__ = ["CheckpointRail"]