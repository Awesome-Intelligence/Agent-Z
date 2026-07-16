#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wisdom Consumer — 后台生成哲学语录

🚪 Access - 💬 TUI - Consumers - Wisdom

v8.x 从 ``tui/textual_app/app.py::_generate_wisdom_async`` 抽出。

设计要点：
- 与 ``TUIConsumer`` 平行的后台消费者，遵循现有消费者模式
- 通过 ``ThreadPoolExecutor`` 异步执行，不阻塞 UI
- 失败时静默（用户看到的是 fallback 欢迎语）
- 回调式更新 widget（避免与 App 类的强耦合）
"""

from __future__ import annotations

import asyncio
import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    pass  # 仅用于类型提示


logger = logging.getLogger(__name__)


# ============================================================================
# Wisdom Consumer
# ============================================================================


class WisdomConsumer:
    """后台异步生成欢迎语中嵌入的哲学短句。

    Usage::

        consumer = WisdomConsumer(
            agent_getter=lambda: self._agent,
            on_wisdom=lambda text: self._apply_wisdom_to_banner(text),
        )
        consumer.start()  # 异步触发，UI 不阻塞
    """

    _executor: Optional[ThreadPoolExecutor] = None

    def __init__(
        self,
        agent_getter: Callable,
        on_wisdom: Callable[[str], None],
        *,
        max_chars: int = 25,
        max_tokens: int = 60,
        temperature: float = 1.0,
    ):
        self._agent_getter = agent_getter
        self._on_wisdom = on_wisdom
        self._max_chars = max_chars
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._future: Optional[Future] = None

    @classmethod
    def _get_executor(cls) -> ThreadPoolExecutor:
        """懒创建线程池（共享单例）。"""
        if cls._executor is None:
            cls._executor = ThreadPoolExecutor(
                max_workers=2, thread_name_prefix="wisdom"
            )
        return cls._executor

    def start(self) -> None:
        """提交后台任务。重复调用安全（会取消旧任务）。"""
        if self._future and not self._future.done():
            self._future.cancel()

        try:
            self._future = self._get_executor().submit(self._run)
        except RuntimeError as e:
            logger.debug(f"WisdomConsumer.start failed: {e}")

    def _run(self) -> None:
        """线程入口：调用 LLM、生成 wisdom、更新 widget。"""
        try:
            agent = self._agent_getter()
            if not agent or not getattr(agent, "llm_provider", None):
                return

            try:
                from common.i18n import get_language
                lang = get_language()
            except ImportError:
                lang = "en"

            lang_prompt = {"zh": "中文", "en": "English"}.get(lang, "English")
            prompt = (
                f"Give me one short philosophical quote (max {self._max_chars} characters) "
                f"in {lang_prompt} about life, existence, or wisdom. "
                f"Only return the quote, nothing else."
            )

            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                response = loop.run_until_complete(
                    agent.llm_provider.generate(
                        prompt=prompt,
                        max_tokens=self._max_tokens,
                        temperature=self._temperature,
                    )
                )
                wisdom = (
                    response.content.strip()
                    if response and response.content
                    else None
                )
            finally:
                loop.close()

            if wisdom:
                try:
                    self._on_wisdom(wisdom)
                except Exception as e:
                    logger.debug(f"Wisdom callback failed: {e}")
        except Exception as e:
            logger.debug(f"Wisdom generation failed (silent): {e}")


__all__ = ["WisdomConsumer"]