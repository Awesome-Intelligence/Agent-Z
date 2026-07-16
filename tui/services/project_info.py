#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目元信息服务（工具/技能/路径读取）

🚪 Access - 💬 TUI - Services - 项目信息

v8.x 从 ``tui/textual_app/app.py`` 抽出：
- ``_get_tools_count`` / ``_get_skills_count`` / ``_get_project_path`` /
  ``_get_skills_path`` / ``_get_tools_path``

**所有函数均无 Textual 依赖**，可在 cli/agent 等场景复用；
失败时返回合理的默认值（0 / str），保证调用方不会崩溃。
"""

from __future__ import annotations

from pathlib import Path


# ============================================================================
# 计数查询
# ============================================================================


def get_tools_count() -> int:
    """获取已注册的工具数量。

    Returns:
        工具数量；注册表不可用时返回 0
    """
    try:
        from tools.tool_registry import get_tool_registry

        registry = get_tool_registry()
        if registry:
            return len(registry._tools) if hasattr(registry, "_tools") else 0
    except ImportError:
        pass
    return 0


def get_skills_count() -> int:
    """获取已加载的 Skill 数量。

    Returns:
        Skill 数量；管理器不可用时返回 0
    """
    try:
        from agent.skills.skill_manager import skill_manager

        return len(skill_manager.skills)
    except ImportError:
        pass
    return 0


# ============================================================================
# 路径查询
# ============================================================================

# 当前文件 → tui/services/project_info.py
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parent.parent.parent  # tui/services → tui → project_root


def get_project_path() -> str:
    """获取项目根目录字符串。

    Returns:
        项目根目录绝对路径字符串
    """
    return str(_PROJECT_ROOT)


def get_skills_path() -> str:
    """获取 skills 目录路径。

    Returns:
        skills 目录绝对路径字符串
    """
    return str(_PROJECT_ROOT / "skills")


def get_tools_path() -> str:
    """获取 tools 目录路径。

    Returns:
        tools 目录绝对路径字符串
    """
    return str(_PROJECT_ROOT / "tools")


__all__ = [
    "get_tools_count",
    "get_skills_count",
    "get_project_path",
    "get_skills_path",
    "get_tools_path",
]