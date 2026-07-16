#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BannerMixin — 欢迎横幅 + 个性化问候

🚪 Access - 💬 TUI - Textual App - Banner

v8.x 从 ``tui/textual_app/app.py`` L1233–1576 抽出：
- ``_init_banner_cache``        缓存项目元信息
- ``_get_theme_banner_color``   从主题读 banner 颜色
- ``_render_welcome_banner``    渲染 ASCII 横幅 + 右侧信息
- ``_generate_wisdom_async``    后台生成 wisdom
- ``_send_welcome_message``     发送欢迎语到聊天
- ``_generate_welcome_greeting`` 个性化问候
- ``_get_default_greeting``     默认 fallback

依赖主类的 ``self._banner_cache`` / ``self._widget_cache` /
``self._theme_manager`` / ``self._agent`` / ``self.cwd`` / ``self._logger``。
"""

from __future__ import annotations

import asyncio
import logging
import random

from tui.services.project_info import (
    get_project_path,
    get_skills_count,
    get_skills_path,
    get_tools_count,
    get_tools_path,
)

from .imports import RichText

logger = logging.getLogger(__name__)


# ASCII Art 常量
_BANNER_LINES = (
    "░█░█░█▀█░█▀█░█▀▄░█▀▀░█▀█░█▄█░█▀▀",
    "░█▀█░█▀█░█░█░█░█░▀▀█░█░█░█░█░█▀▀",
    "░▀░▀░▀░▀░▀░▀░▀▀░░▀▀▀░▀▀▀░▀░▀░▀▀▀",
)

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


class BannerMixin:
    """欢迎横幅 + greeting Mixin."""

    _logger = logging.getLogger(__name__)
    _widget_cache: dict = {}
    _banner_cache: dict = {}
    _banner_cache_initialized: bool = False
    _theme_manager = None
    cwd: str = ""
    _agent = None

    # ------------------------------------------------------------------
    # 缓存初始化
    # ------------------------------------------------------------------

    def _init_banner_cache(self) -> None:
        """初始化 Banner 缓存（在后台线程中调用）."""
        if self._banner_cache_initialized:
            return

        try:
            # 缓存项目路径（来自 tui.services.project_info，跨 tui/cli 共享）
            self._banner_cache["project_path"] = get_project_path()
            self._banner_cache["skills_path"] = get_skills_path()
            self._banner_cache["tools_path"] = get_tools_path()
            # 缓存数量
            self._banner_cache["skills_count"] = get_skills_count()
            self._banner_cache["tools_count"] = get_tools_count()
            # 缓存版本
            try:
                from cli import __version__ as app_version

                self._banner_cache["version"] = app_version
            except ImportError:
                self._banner_cache["version"] = "unknown"
            self._banner_cache_initialized = True
            self._logger.debug("Banner cache initialized")
        except Exception as e:
            self._logger.error(f"Failed to initialize banner cache: {e}")

    def _get_theme_banner_color(self) -> str:
        """从当前 Theme 对象获取 banner 颜色."""
        if self._theme_manager:
            theme = self._theme_manager.get_current_theme()
            return theme.banner_color
        return "#C9A0E0"  # 默认紫色

    # ------------------------------------------------------------------
    # 渲染
    # ------------------------------------------------------------------

    def _render_welcome_banner(self) -> None:
        """渲染欢迎 Banner 和右侧信息."""
        # 初始化缓存（首次调用时）
        if not self._banner_cache_initialized:
            self._init_banner_cache()

        # 从 CSS 主题文件读取 Banner 颜色
        banner_color = self._get_theme_banner_color()

        # 渲染左侧 ASCII Banner
        welcome_lines = [
            f"[bold {banner_color}]{line}[/]" for line in _BANNER_LINES
        ]

        # 使用缓存的 widgets
        welcome_widget = self._widget_cache.get("welcome_banner")
        if welcome_widget:
            welcome_text = RichText.from_markup("\n".join(welcome_lines))
            welcome_widget.update(welcome_text)

        # 获取随机问候语（先显示 fallback，LLM 生成后再更新）
        try:
            from common.i18n import get_random_greeting

            greeting = get_random_greeting()
        except Exception:
            greeting = "存在先于本质。"

        # 渲染右侧信息栏
        # 尝试获取当前模式
        current_mode = "Agent"  # 默认模式
        try:
            if (
                hasattr(self, "_agent")
                and self._agent
                and hasattr(self._agent, "get_mode")
            ):
                current_mode = self._agent.get_mode()
        except Exception:
            pass

        # 获取工作目录（绝对路径）
        cwd_path = self.cwd or "unknown"

        # 路径太长时截断显示（单行）
        max_chars = 40
        if len(cwd_path) > max_chars:
            half = max_chars - 3  # 留3位给 "..."
            cwd_path = cwd_path[:half] + "..."

        # 第1行：版本号 + 俏皮话（不要引号）
        version_widget = self._widget_cache.get("version_info")
        if version_widget and self._banner_cache.get("version"):
            version_text = RichText.from_markup(
                f"[dim]{self._banner_cache['version']}[/] [dim]·[/] [italic dim]{greeting}[/]"
            )
            version_widget.update(version_text)

        # 第2行：工作目录（单行显示）
        mode_widget = self._widget_cache.get("skills_info")
        if mode_widget:
            mode_text = RichText.from_markup(f"[bright_black]{cwd_path}[/]")
            mode_widget.update(mode_text)

        # 第3行：留空（不再使用）
        greeting_widget = self._widget_cache.get("tools_info")
        if greeting_widget:
            greeting_widget.update("")

    # ------------------------------------------------------------------
    # Wisdom（异步生成）
    # ------------------------------------------------------------------

    def _generate_wisdom_async(self) -> None:
        """后台异步生成哲学语录并更新 Banner 显示."""
        try:
            agent = self._get_agent()
            if not agent or not agent.llm_provider:
                return

            from common.i18n import get_language

            lang = get_language()
            lang_prompt = {"zh": "中文", "en": "English"}.get(lang, "English")

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # ponytail: 一次简单 LLM 调用，timeout 15s
                response = loop.run_until_complete(
                    agent.llm_provider.generate(
                        prompt=(
                            f"Give me one short philosophical quote "
                            f"(max 25 characters) in {lang_prompt} about life, "
                            f"existence, or wisdom. Only return the quote, nothing else."
                        ),
                        max_tokens=60,
                        temperature=1.0,
                    )
                )
                wisdom = (
                    response.content.strip() if response and response.content else None
                )
            finally:
                loop.close()

            if wisdom:
                version_widget = self._widget_cache.get("version_info")
                if version_widget and self._banner_cache.get("version"):
                    version_text = RichText.from_markup(
                        f"[dim]{self._banner_cache['version']}[/] "
                        f"[dim]·[/] [italic dim]{wisdom}[/]"
                    )
                    version_widget.update(version_text)
        except Exception:
            pass  # 静默失败，用户看到的是 fallback

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
4. 保持友好、自然，不要太正式
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


__all__ = ["BannerMixin"]