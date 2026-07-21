#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GreetingMixin — 个性化问候语生成

🚪 Access - 💬 TUI - Textual App - Greeting

依赖主类的 ``self._agent`` / ``self._logger``。
"""

from __future__ import annotations

import asyncio
import logging
import random

from common.logging_manager import get_access_logger


_DEFAULT_GREETINGS = {
    "zh": [
        "你好！有什么我可以帮你的吗？",
        "嗨！准备好开始工作了吗？",
        "你好！很高兴见到你。",
    ],
    "en": [
        "Hello! How can I help you today?",
        "Hi! Ready to get started?",
        "Hello! Nice to see you.",
    ],
    "ko": [
        "안녕하세요! 어떻게 도와드릴까요?",
        "안녕! 오늘도 좋은 하루 되세요.",
        "안녕하세요! 반갑습니다.",
    ],
    "ja": [
        "こんにちは！何かお手伝いできますか？",
        "こんにちは！始めましょうか？",
        "こんにちは！お会いできて嬉しいです。",
    ],
}


class GreetingMixin:
    """个性化问候语 Mixin."""

    _logger = get_access_logger("greeting")

    # ------------------------------------------------------------------
    # 欢迎消息
    # ------------------------------------------------------------------

    def _send_welcome_message(self) -> None:
        """发送欢迎消息到聊天区域."""
        self._logger.info("Sending welcome message to chat area")

        try:
            greeting = self._generate_welcome_greeting()
            if greeting:
                self._append_message("assistant", greeting)
                self._logger.info(f"Welcome message sent: {greeting[:50]}...")
        except Exception as e:
            self._logger.warning(f"Failed to send welcome message: {e}")

    def _generate_welcome_greeting(self) -> str | None:
        """根据 workspace 配置生成个性化问候语.

        读取 agent.md（Agent 身份）和 memory.md（记忆）文件，
        使用 LLM 生成符合 Agent 性格的问候语。

        Returns:
            生成的问候语，如果生成失败则返回 None
        """
        agent_content = ""
        memory_content = ""

        try:
            from agent.workspace import get_workspace_manager

            workspace_manager = get_workspace_manager()

            agent_content = workspace_manager.load_workspace_file("agent.md") or ""
            memory_content = workspace_manager.load_workspace_file("memory.md") or ""

            self._logger.debug(f"Loaded agent.md: {len(agent_content)} chars")
            self._logger.debug(f"Loaded memory.md: {len(memory_content)} chars")
        except Exception as e:
            self._logger.debug(f"Failed to load workspace files: {e}")

        agent = self._get_agent()
        if not agent or not agent.llm_provider:
            self._logger.debug("Agent not available, using default greeting")
            return self._get_default_greeting()

        try:
            from common.i18n import get_language

            lang = get_language()
            lang_prompt = {"zh": "中文", "en": "English"}.get(lang, "English")

            context_info = []
            if agent_content.strip():
                context_info.append(f"Agent 身份描述:\n{agent_content.strip()}")
            if memory_content.strip():
                context_info.append(f"Agent 记忆:\n{memory_content.strip()}")

            context_str = "\n\n".join(context_info) if context_info else "无特殊配置"

            prompt = f"""你是一个 AI 助手，请根据以下配置信息生成一句问候语（不超过60个字符）：

{context_str}

要求：
1. 使用 {lang_prompt} 回复
2. 问候语要符合 Agent 的性格设定
3. 如果有记忆信息，适当提及（如项目背景、之前的对话等）
4. 保持友好，自然，不要太正式
5. 不要包含任何 Markdown 格式或特殊符号
6. 不要超过60个字符

只返回问候语本身，不要其他内容。"""

            loop = asyncio.new_event_loop()
            try:
                response = loop.run_until_complete(
                    agent.llm_provider.generate(
                        prompt=prompt,
                        max_tokens=60,
                        temperature=0.8,
                    )
                )
                greeting = (
                    response.content.strip() if response and response.content else None
                )
            finally:
                loop.close()

            if greeting:
                return greeting

        except Exception as e:
            self._logger.debug(f"Failed to generate greeting via LLM: {e}")

        return self._get_default_greeting()

    def _get_default_greeting(self) -> str:
        """获取默认问候语（降级方案）.

        当 LLM 不可用或生成失败时使用。

        Returns:
            默认问候语字符串
        """
        from common.i18n import get_language

        lang = get_language()

        return random.choice(_DEFAULT_GREETINGS.get(lang, _DEFAULT_GREETINGS["en"]))


__all__ = ["GreetingMixin"]
