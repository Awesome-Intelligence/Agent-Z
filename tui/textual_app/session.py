#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionMixin — 会话存储与持久化

🚪 Access - 💬 TUI - Textual App - Session

v8.x 从 ``tui/textual_app/app.py`` L1644–1966 抽出：
- ``_init_session_store``     初始化 SessionStore
- ``_restore_session``        恢复历史消息
- ``_auto_save_check``        触发自动 flush
- ``_flush_messages``         真正写入存储
- ``save_message``            单条消息保存

依赖主类的 ``self._session_store`` / ``self.session_id` / ``self._logger`` /
``self._pending_message_count`` / ``self._auto_save_interval``。
"""

from __future__ import annotations

import logging

from .imports import SessionStore

logger = logging.getLogger(__name__)


class SessionMixin:
    """会话存储 Mixin."""

    _logger = logging.getLogger(__name__)
    _session_store = None
    session_id: str | None = None
    model_name: str = ""
    provider: str = ""
    _pending_message_count: int = 0
    _auto_save_interval: int = 5

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------

    def _init_session_store(self) -> None:
        if SessionStore:
            try:
                self._session_store = SessionStore()
                self._logger.debug("SessionStore initialized")

                if not self.session_id:
                    self.session_id, is_new = self._session_store.get_or_create_session(
                        model=self.model_name or "",
                        provider=self.provider or "",
                    )
                    if is_new:
                        self._logger.info(f"Created new session: {self.session_id}")
                    else:
                        self._logger.debug(f"Using existing session: {self.session_id}")
                else:
                    self._session_store.get_or_create_session(
                        model=self.model_name or "",
                        provider=self.provider or "",
                        session_id=self.session_id,
                    )
            except Exception as e:
                self._logger.error(f"Failed to initialize SessionStore: {e}")
                self._session_store = None

    # ------------------------------------------------------------------
    # 消息持久化
    # ------------------------------------------------------------------

    def _restore_session(self, session_id: str) -> list[dict[str, str]]:
        if not self._session_store:
            return []

        try:
            messages = self._session_store.get_messages(session_id, limit=100)
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "thinking": msg.thinking_content,
                }
                for msg in messages
            ]
        except Exception as e:
            self._logger.error(f"Failed to restore session: {e}")
            return []

    def _auto_save_check(self) -> None:
        self._pending_message_count += 1
        if self._pending_message_count >= self._auto_save_interval:
            self._flush_messages()

    def _flush_messages(self) -> None:
        if self._session_store:
            try:
                count = self._session_store.flush_pending_messages()
                if count > 0:
                    self._logger.debug(f"Flushed {count} pending messages")
                self._pending_message_count = 0
            except Exception as e:
                self._logger.error(f"Failed to flush messages: {e}")

    def save_message(self, role: str, content: str, **kwargs) -> None:
        if not self._session_store or not self.session_id:
            return

        try:
            self._session_store.save_message(
                session_id=self.session_id,
                role=role,
                content=content,
                flush=False,
                **kwargs,
            )
            self._auto_save_check()
        except Exception as e:
            self._logger.error(f"Failed to save message: {e}")


__all__ = ["SessionMixin"]