#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NotifyMixin — 通知/Toast/进度条

🚪 Access - 💬 TUI - Textual App - Notifications

v8.x 从 ``tui/textual_app/app.py`` L1739–1816 抽出：
- ``NotificationType`` 常量类（保留向后兼容）
- ``notify_animated`` / ``notify_success`` / ``notify_warning`` /
  ``notify_error`` / ``notify_info``
- ``show_loading_animation`` / ``show_progress_notification``
- ``apply_skin_from_engine``

依赖主类的 ``self.notify()`` / ``self._logger`` / ``self._theme_manager``。
"""

from __future__ import annotations

import logging

from common.logging_manager import get_access_logger

logger = get_access_logger("notifications")


# ============================================================================
# NotificationType —— 通知类型常量
# ============================================================================


class NotificationType:
    """通知类型常量与 icon 映射."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    LOADING = "loading"

    @classmethod
    def get_icon(cls, notification_type: str) -> str:
        return {
            cls.INFO: "ℹ️",
            cls.SUCCESS: "✅",
            cls.WARNING: "⚠️",
            cls.ERROR: "❌",
            cls.LOADING: "⏳",
        }.get(notification_type, "ℹ️")


class NotificationAnimationManager:
    """通知动画管理器（v8.x 兼容占位）.

    原 ``tui.textual_app.notifications.NotificationAnimationManager``
    负责通知 slide-in/fade 动画；v8.x 抽象为 ``NotifyMixin``，
    本类保留以保证外部 ``from tui.textual_app import NotificationAnimationManager``
    不破坏。
    """

    def __init__(self, *args, **kwargs):
        self._enabled = True

    def animate(self, message: str, duration: float = 3.0) -> None:
        """发送带动画的通知."""
        logger.debug(f"[NotificationAnimationManager] {message}")

    def stop(self) -> None:
        self._enabled = False


# ============================================================================
# NotifyMixin
# ============================================================================


class NotifyMixin:
    """通知与 Toast Mixin。"""

    _logger = get_access_logger("notifications")
    _theme_manager = None

    # ------------------------------------------------------------------
    # 基础 notify（带 icon 动画）
    # ------------------------------------------------------------------

    def notify_animated(
        self,
        message: str,
        notification_type: str = "info",
        duration: float = 3.0,
    ) -> None:
        icon = NotificationType.get_icon(notification_type)

        if notification_type == NotificationType.SUCCESS:
            animated_msg = f"✅ {message}"
        elif notification_type == NotificationType.WARNING:
            animated_msg = f"⚠️ {message}"
        elif notification_type == NotificationType.ERROR:
            animated_msg = f"❌ {message}"
        else:
            animated_msg = f"ℹ️ {message}"

        self.notify(
            animated_msg,
            timeout=duration,
            title=(
                notification_type.upper()
                if notification_type != NotificationType.INFO
                else "通知"
            ),
        )

        self._logger.debug(f"Animated notification: [{notification_type}] {message}")

    def notify_success(self, message: str, duration: float = 3.0) -> None:
        self.notify_animated(message, NotificationType.SUCCESS, duration)

    def notify_warning(self, message: str, duration: float = 4.0) -> None:
        self.notify_animated(message, NotificationType.WARNING, duration)

    def notify_error(self, message: str, duration: float = 5.0) -> None:
        self.notify_animated(message, NotificationType.ERROR, duration)

    def notify_info(self, message: str, duration: float = 3.0) -> None:
        self.notify_animated(message, NotificationType.INFO, duration)

    # ------------------------------------------------------------------
    # 加载与进度
    # ------------------------------------------------------------------

    def show_loading_animation(self, message: str = "加载中...") -> None:
        loading_msg = f"⏳ {message}"
        self.notify(loading_msg, timeout=None, title="LOADING")

    def show_progress_notification(
        self,
        progress: float,
        message: str = "",
        total: int = 100,
    ) -> None:
        percent = int(progress * 100)
        current = int(progress * total)

        bar_length = 20
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)

        progress_msg = f"{bar} {percent}%"
        if message:
            progress_msg = f"{message}\n{progress_msg}"

        self.notify(progress_msg, timeout=2.0, title=f"进度 ({current}/{total})")

    # ------------------------------------------------------------------
    # 主题引擎联动
    # ------------------------------------------------------------------

    def apply_skin_from_engine(self) -> bool:
        if not self._theme_manager:
            self._logger.warning("Theme manager not available")
            return False

        success = self._theme_manager.load_skin_from_engine()
        if success:
            display_name = self._theme_manager.get_current_display_name()
            self.notify(f"Applied skin: {display_name}")
            self._logger.info("Skin applied from engine")
        else:
            self._logger.debug("No skin to apply from engine")

        return success


__all__ = ["NotifyMixin"]