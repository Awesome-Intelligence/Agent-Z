# -*- coding: utf-8 -*-
"""
Checkpoint 模块

提供透明的文件系统快照和回滚功能。

注意：此模块统一使用 tools.checkpoint_manager 中的实现，
避免代码重复。所有功能由 tools.checkpoint_manager 提供。

使用示例：
```python
from agent.checkpoint import CheckpointManager, get_checkpoint_manager

# 直接创建实例
mgr = CheckpointManager(enabled=True)

# 或使用全局单例
mgr = get_checkpoint_manager()
```
"""

# 从 tools.checkpoint_manager 导入核心功能
from tools.checkpoint_manager import (
    CheckpointManager,
    format_checkpoint_list,
    prune_checkpoints,
    maybe_auto_prune_checkpoints,
    store_status,
    clear_all,
)

# 保留 agent.checkpoint 中常用的别名和工具函数
# 需要创建快照的工具
SNAPSHOT_TOOLS = {"write_file", "patch", "terminal", "str_replace_editor"}

# 危险命令模式
DESTRUCTIVE_TERMINAL_PATTERNS = [
    r"rm\s+-rf",
    r"rm\s+-r",
    r"rm\s+-f",
    r"del\s+/",
    r"format\s+",
    r"mkfs\.",
    r"dd\s+if=",
    r"shred\s+",
    r">\s*/dev/",
]

# ---------------------------------------------------------------------------
# 全局单例管理
# ---------------------------------------------------------------------------

_checkpoint_manager: CheckpointManager | None = None


def get_checkpoint_manager(
    enabled: bool = True,
    max_snapshots: int = 20,
    max_total_size_mb: int = 500,
    max_file_size_mb: int = 10,
) -> CheckpointManager:
    """获取全局 CheckpointManager 单例

    Args:
        enabled: 是否启用检查点
        max_snapshots: 最大快照数
        max_total_size_mb: 最大存储大小（MB）
        max_file_size_mb: 单个文件最大大小（MB）

    Returns:
        CheckpointManager 单例实例
    """
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager(
            enabled=enabled,
            max_snapshots=max_snapshots,
            max_total_size_mb=max_total_size_mb,
            max_file_size_mb=max_file_size_mb,
        )
    return _checkpoint_manager


def reset_checkpoint_manager() -> None:
    """重置全局 CheckpointManager 单例（用于测试）"""
    global _checkpoint_manager
    _checkpoint_manager = None


# ---------------------------------------------------------------------------
# CheckpointManager 方法扩展
# ---------------------------------------------------------------------------
# 为 CheckpointManager 添加缺失的方法，使 CheckpointRail 可以正常工作

_original_checkpoint_manager_class = CheckpointManager


class CheckpointManager(_original_checkpoint_manager_class):
    """扩展的 CheckpointManager，添加 agent 层需要的辅助方法"""

    def is_enabled(self) -> bool:
        """检查是否启用（兼容旧 API）"""
        return self.enabled

    def should_snapshot_tool(self, tool_name: str) -> bool:
        """检查工具是否需要快照"""
        return tool_name in SNAPSHOT_TOOLS

    def is_destructive_command(self, command: str) -> bool:
        """检查终端命令是否为危险命令"""
        import re
        for pattern in DESTRUCTIVE_TERMINAL_PATTERNS:
            if re.search(pattern, command.lower()):
                return True
        return False


__all__ = [
    # 核心类
    "CheckpointManager",
    # 工具函数
    "get_checkpoint_manager",
    "reset_checkpoint_manager",
    "format_checkpoint_list",
    "prune_checkpoints",
    "maybe_auto_prune_checkpoints",
    "store_status",
    "clear_all",
    # 常量
    "SNAPSHOT_TOOLS",
    "DESTRUCTIVE_TERMINAL_PATTERNS",
]