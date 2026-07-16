#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tui.services.project_info and tui.textual_app mixins

🚪 Access - 💬 Tests - TUI - Services + Mixins

覆盖：
- project_info 工具/技能/路径查询
- PANEL_ORDER 侧边栏面板循环顺序
- ApprovalMixin 工具预览脱敏逻辑
- NotificationType get_icon
"""

from __future__ import annotations


class TestProjectInfo:
    """tui.services.project_info 跨端共享服务."""

    def test_get_tools_count_returns_int(self):
        from tui.services.project_info import get_tools_count

        n = get_tools_count()
        assert isinstance(n, int)
        assert n >= 0

    def test_get_skills_count_returns_int(self):
        from tui.services.project_info import get_skills_count

        n = get_skills_count()
        assert isinstance(n, int)
        assert n >= 0

    def test_paths_are_absolute_strings(self):
        from tui.services.project_info import (
            get_project_path,
            get_skills_path,
            get_tools_path,
        )

        for path in (get_project_path(), get_skills_path(), get_tools_path()):
            assert isinstance(path, str)
            # 绝对路径（在 Windows 上含盘符，在 POSIX 上含 /）
            assert path[0] in ("/", "C", "D", "E", "F", "G") or ":" in path

    def test_paths_under_project_root(self):
        """skills/tools 路径必须是 project 路径的子目录."""
        from tui.services.project_info import (
            get_project_path,
            get_skills_path,
            get_tools_path,
        )

        project = get_project_path()
        assert get_skills_path().startswith(project)
        assert get_tools_path().startswith(project)


class TestNotificationType:
    """通知类型 icon 映射."""

    def test_get_icon_each_type(self):
        from tui.textual_app.notifications import NotificationType

        for t in ("info", "success", "warning", "error", "loading"):
            icon = NotificationType.get_icon(t)
            assert icon  # 非空字符串

    def test_get_icon_unknown_returns_default(self):
        from tui.textual_app.notifications import NotificationType

        assert NotificationType.get_icon("nonexistent_type") == "ℹ️"

    def test_notification_animation_manager_is_constructible(self):
        """向后兼容占位类仍能构造."""
        from tui.textual_app.notifications import NotificationAnimationManager

        mgr = NotificationAnimationManager()
        assert mgr is not None
        mgr.animate("test")  # 不抛
        mgr.stop()


class TestSidebarPanelOrder:
    """侧边栏面板循环顺序."""

    def test_panel_order_contains_expected_panels(self):
        from tui.textual_app.sidebar_panels import PANEL_ORDER

        assert isinstance(PANEL_ORDER, tuple)
        assert "goal" in PANEL_ORDER
        assert "file_tree" in PANEL_ORDER
        assert "skills" in PANEL_ORDER
        assert "cron" in PANEL_ORDER

    def test_panel_order_unique(self):
        from tui.textual_app.sidebar_panels import PANEL_ORDER

        assert len(PANEL_ORDER) == len(set(PANEL_ORDER))


class TestApprovalMixin:
    """ApprovalMixin 工具预览脱敏."""

    def _make_isolated_app(self):
        """构造一个不依赖 Textual 完整运行的裸对象，混入 ApprovalMixin."""
        from tui.textual_app.approval import ApprovalMixin

        class _App(ApprovalMixin):
            pass

        app = _App()
        app._logger = type("L", (), {
            "debug": lambda *a, **k: None,
            "info": lambda *a, **k: None,
            "warning": lambda *a, **k: None,
            "error": lambda *a, **k: None,
        })()
        return app

    def test_masks_password_field(self):
        app = self._make_isolated_app()
        preview = app._generate_tool_preview(
            "write_file",
            {"path": "/tmp/x", "password": "supersecret123"},
        )
        assert "password=***" in preview
        assert "supersecret123" not in preview

    def test_masks_api_key_field(self):
        app = self._make_isolated_app()
        preview = app._generate_tool_preview(
            "http_call",
            {"url": "https://api.example.com", "api_key": "sk-abc123"},
        )
        assert "api_key=***" in preview
        assert "sk-abc123" not in preview

    def test_truncates_long_values(self):
        app = self._make_isolated_app()
        long_value = "x" * 100
        preview = app._generate_tool_preview(
            "tool", {"field": long_value}
        )
        assert "..." in preview
        assert "x" * 50 not in preview  # 已截断

    def test_truncates_long_preview(self):
        app = self._make_isolated_app()
        # 构造总长 >100 的参数
        args = {f"k{i}": f"value_{i}" for i in range(20)}
        preview = app._generate_tool_preview("tool", args)
        assert len(preview) <= 100


class TestMixinsInheritance:
    """Mixin 类定义完整性."""

    def test_all_d_mixins_subclassable(self):
        """所有 D 阶段 mixin 都应能裸混入一个简单 class."""
        from tui.textual_app.loading import LoadingMixin
        from tui.textual_app.notifications import NotifyMixin
        from tui.textual_app.actions import ActionsMixin
        from tui.textual_app.slash_completion_bind import SlashCompletionMixin
        from tui.textual_app.model_selector import ModelSelectorMixin
        from tui.textual_app.status_bar import StatusBarMixin
        from tui.textual_app.sidebar_panels import SidebarPanelMixin
        from tui.textual_app.approval import ApprovalMixin
        from tui.textual_app.session import SessionMixin
        from tui.textual_app.agent_runner import AgentRunnerMixin
        from tui.textual_app.banner import BannerMixin

        for mixin in (
            LoadingMixin, NotifyMixin, ActionsMixin, SlashCompletionMixin,
            ModelSelectorMixin, StatusBarMixin, SidebarPanelMixin,
            ApprovalMixin, SessionMixin, AgentRunnerMixin, BannerMixin,
        ):
            class _App(mixin):
                pass

            assert _App is not None

    def test_wisdom_consumer_constructible(self):
        from tui.consumers.wisdom_consumer import WisdomConsumer

        consumer = WisdomConsumer(
            agent_getter=lambda: None,
            on_wisdom=lambda text: None,
        )
        assert consumer is not None
        # 不抛
        consumer.start()