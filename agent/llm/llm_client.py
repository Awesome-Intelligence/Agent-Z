#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 🧠 Decision - 🤖 LLM - 统一 LLM 调用入口

"""
LLM Client - 统一的 LLM 调用入口

参考 Hermes 的 conversation_loop.py 和 auxiliary_client.py 设计。
提供双轨制 LLM 调用：
- main_call(): 主对话，使用完整上下文 (ContextManager)，含统一 retry/fallback
- auxiliary_call(): 辅助任务，使用轻量级上下文

Retry/Fallback 架构：
1. Provider.generate() 正常返回 ProviderResponse
2. 调用方（main_call）在 try/except 中捕获异常
3. 用 classify_api_error 分类错误
4. 根据 retryable 决定是否 backoff 重试
5. 根据 should_fallback / max_retries 耗尽 触发 fallback chain
6. 根据 should_compress 触发上下文压缩后重试
"""

import asyncio
import datetime
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from enum import Enum
from dataclasses import dataclass

from common.logging_manager import get_decision_logger, get_llm_logger
from common.config import load_config
from agent.error import classify_api_error, FailoverReason, jittered_backoff

if TYPE_CHECKING:
    from agent.context.context_manager import ContextManager
    from agent.llm.base import BaseLLMProvider


class LLMTaskType(Enum):
    """LLM 任务类型"""

    # 主对话相关
    MODE_DECISION = "mode_decision"  # 模式判断
    TOOL_SELECTION = "tool_selection"  # 工具选择
    DIRECT_RESPONSE = "direct_response"  # 直接回复
    CLARIFICATION = "clarification"  # 澄清回复
    TOOL_RESULT_SUMMARY = "tool_result_summary"  # 工具结果总结
    AGENT_LOOP = "agent_loop"  # Agent 循环

    # 辅助任务相关
    COMPRESSION = "compression"  # 上下文压缩
    TITLE_GENERATION = "title_generation"  # 标题生成
    SKILL_SYNTHESIS = "skill_synthesis"  # 技能合成
    MEMORY_SUMMARY = "memory_summary"  # 记忆摘要
    ANALYSIS = "analysis"  # 分析任务

    # 其他
    OTHER = "other"  # 其他任务


@dataclass
class LLMAuxConfig:
    """辅助任务配置"""

    # 压缩任务
    compression_model: str = "gpt-4o-mini"
    compression_timeout: int = 60

    # 标题生成
    title_model: str = "gpt-4o-mini"
    title_timeout: int = 30

    # 技能合成
    synthesis_model: str = "gpt-4o-mini"
    synthesis_timeout: int = 60

    # 记忆摘要
    memory_model: str = "gpt-4o-mini"
    memory_timeout: int = 30

    # 默认轻量级模型
    default_lightweight_model: str = "gpt-4o-mini"


class LLMClient:
    """
    统一的 LLM 调用客户端

    双轨制设计：
    - main_call(): 主对话，使用 ContextManager 构建完整上下文
    - auxiliary_call(): 辅助任务，使用轻量级模型和简化上下文

    Usage:
        client = LLMClient(llm_provider=provider)

        # 主对话
        result = await client.main_call(
            user_message="你好",
            context_manager=context_manager,
            purpose=LLMTaskType.DIRECT_RESPONSE
        )

        # 辅助任务
        result = await client.auxiliary_call(
            task=LLMTaskType.COMPRESSION,
            prompt=compression_prompt
        )

    日志子层：🤖 LLM
    """

    def __init__(
        self,
        llm_provider: "BaseLLMProvider",
        context_manager: Optional["ContextManager"] = None,
        aux_config: Optional[LLMAuxConfig] = None,
    ):
        """
        Args:
            llm_provider: LLM 提供者
            context_manager: 上下文管理器（用于主对话）
            aux_config: 辅助任务配置
        """
        self._provider = llm_provider
        self._context_manager = context_manager

        # Fallback provider chain from config
        cfg = load_config()
        self._fallback_providers: list[dict] = cfg.get("fallback_providers", [])

        # Build aux config from config file, with hardcoded defaults as fallback
        if aux_config:
            self._aux_config = aux_config
        else:
            ms = cfg.get("model_settings", {})
            self._aux_config = LLMAuxConfig(
                compression_model=ms.get("compression_model") or None,
                title_model=ms.get("title_model") or None,
                synthesis_model=ms.get("synthesis_model") or None,
                memory_model=ms.get("memory_model") or None,
                default_lightweight_model=ms.get("auxiliary_model") or None,
            )

        self._logger = get_decision_logger(self.__class__.__name__)
        self._llm_logger = get_llm_logger(self.__class__.__name__)

        # 系统提示缓存（用于主对话）
        self._system_prompt_cache: Optional[str] = None
        self._cache_version: int = 0

        self._logger.debug(
            f"LLMClient initialized with provider={type(llm_provider).__name__}, "
            f"context_manager={'yes' if context_manager else 'no'}"
        )

    # ── H1: 系统元信息构建（Base Layer）───────────────────────────────
    @staticmethod
    def _build_system_meta(
        tools: Optional[Dict[str, Any]] = None,
        provider_name: str = "auto",
        model_name: str = "Agent-Z",
    ) -> Dict[str, Any]:
        """构建注入 Base(stable) 层的 Agent 启动元信息。

        解决 Agent 不知道自己是谁的问题（G5）：Agent 启动时的真实系统信息
        被注入到系统提示的 About You 段落中，让 Agent 始终知道自己运行在
        什么环境、什么版本、有什么能力。

        Args:
            tools: 当前可用工具字典
            provider_name: LLM Provider 名称
            model_name: 模型名称

        Returns:
            system_meta dict，供 ContextBuilder.build_parts() 使用
        """
        import os
        import platform
        import sys
        from pathlib import Path

        # 版本号（从 common.config 或硬编码）
        version = "dev"
        try:
            from common.config import load_config
            cfg = load_config()
            version = cfg.get("agent", {}).get("version", "dev")
        except Exception:
            pass

        # 技能数量（扫描 skills 目录）
        skills_count = 0
        try:
            from common.config import get_skills_dir
            skills_dir = Path(get_skills_dir())
            if skills_dir.exists():
                skills_count = sum(1 for f in skills_dir.glob("*.md") if f.is_file())
        except Exception:
            pass

        return {
            "version": version,
            "os_name": platform.system(),
            "os_version": platform.release(),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "cwd": os.getcwd(),
            "provider": provider_name,
            "model": model_name,
            "tools_count": len(tools) if tools else 0,
            "skills_count": skills_count,
            "mcp_tools_count": 0,
        }

    # ── H2: 会话元信息构建（Session Layer）────────────────────────────
    def _build_session_info(self) -> Dict[str, Any]:
        """构建注入 Session(volatile) 层的当前会话元信息。

        包含：对话轮次、已使用工具列表、会话启动时间、Session ID 等。
        每次 build_messages 调用时重新构建，不参与 stable 层缓存。

        Returns:
            session_info dict，供 ContextBuilder.build_parts() 使用
        """
        import datetime

        used_tools = list(self._used_tools) if hasattr(self, "_used_tools") else []
        session_id = self._session_id if hasattr(self, "_session_id") else ""
        start_time = (
            self._session_start_time.isoformat()
            if hasattr(self, "_session_start_time") and self._session_start_time
            else datetime.datetime.now().isoformat()
        )
        rounds = self._turn_count if hasattr(self, "_turn_count") else 0
        user_lang = getattr(self, "_user_lang", "zh")

        return {
            "rounds": rounds,
            "used_tools": used_tools[-50:],  # 保留最近 50 个工具调用
            "start_time": start_time,
            "session_id": session_id,
            "language": user_lang,
        }

    def track_tool_call(self, tool_name: str) -> None:
        """记录工具调用（用于 session_info 的 used_tools）。"""
        if not hasattr(self, "_used_tools"):
            self._used_tools: list[str] = []
        self._used_tools.append(tool_name)

    def set_session_meta(
        self,
        session_id: str = "",
        start_time: Optional[datetime.datetime] = None,
        user_lang: str = "zh",
    ) -> None:
        """设置会话元信息（由 Agent 入口在创建会话时调用）。"""
        self._session_id = session_id
        self._session_start_time = start_time or datetime.datetime.now()
        self._user_lang = user_lang
        self._turn_count = 0

    def increment_turn(self) -> None:
        """递增对话轮次计数器。"""
        if not hasattr(self, "_turn_count"):
            self._turn_count = 0
        self._turn_count += 1

    @property
    def provider(self) -> "BaseLLMProvider":
        """获取 LLM 提供者"""
        return self._provider

    @property
    def context_manager(self) -> Optional["ContextManager"]:
        """获取上下文管理器"""
        return self._context_manager

    def set_context_manager(self, manager: "ContextManager") -> None:
        """设置上下文管理器"""
        self._context_manager = manager

    def set_active_model(
        self,
        provider: str,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """运行时切换主模型（无需重启 Agent）。

        重建 _provider 实例，context_manager 保持不变。
        """
        from agent.llm.factory import LLMFactory

        # 优先从 providers 字典读凭证，api_key 参数覆盖
        cfg = load_config()
        providers_cfg = cfg.get("providers", {})
        pconf = providers_cfg.get(provider, {})
        resolved_key = api_key or pconf.get("api_key") or ""
        resolved_url = base_url or pconf.get("base_url")

        self._provider = LLMFactory.create(
            provider=provider,
            api_key=resolved_key,
            model=model or pconf.get("model"),
            base_url=resolved_url,
        )
        self.invalidate_cache()
        # 切换模型时同时清除 ContextBuilder 的 stable 缓存（模型变了影响 stable 层）
        if self._context_manager is not None:
            if hasattr(self._context_manager, "invalidate_stable_cache"):
                self._context_manager.invalidate_stable_cache()
        self._logger.info(
            f"Switched to provider={provider}, " f"model={model or pconf.get('model')}"
        )

    def set_fallback_chain(self, chain: list[dict]) -> None:
        """运行时设置 fallback chain。

        Args:
            chain: [{provider, model, api_key, base_url}, ...]
        """
        self._fallback_providers = chain
        self._logger.info(
            f"Fallback chain updated: {[p.get('provider') for p in chain]}"
        )

    # ==================== 主对话调用 ====================

    async def main_call(
        self,
        user_message: str,
        purpose: LLMTaskType,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        tools: Optional[Dict[str, Any]] = None,
        include_tools: bool = None,
        model: str = None,
        **kwargs,
    ) -> str:
        """
        主对话调用（使用完整上下文），含统一 retry/fallback 逻辑

        错误处理流程（参考 Hermes conversation_loop）：
        1. 调用 provider.generate()
        2. 成功 → 直接返回
        3. 失败 → classify_api_error 分类
        4. 不可重试（billing/auth_permanent）→ 立即走 fallback chain
        5. 可重试 → jittered_backoff 等待 → 重试（最多 max_retries 次）
        6. 所有重试耗尽 → fallback chain
        7. 所有 fallback 耗尽 → 最后一个异常上抛

        Args:
            user_message: 用户消息
            purpose: 调用目的 (LLMTaskType)
            conversation_history: 对话历史
            tools: 工具字典
            include_tools: 是否包含工具列表
            model: 模型名称

        Returns:
            LLM 响应内容
        """
        from agent.context.context_manager import ContextPurpose

        # 映射 LLMTaskType 到 ContextPurpose
        purpose_mapping = {
            LLMTaskType.MODE_DECISION: ContextPurpose.MODE_DECISION,
            LLMTaskType.TOOL_SELECTION: ContextPurpose.TOOL_SELECTION,
            LLMTaskType.DIRECT_RESPONSE: ContextPurpose.DIRECT_RESPONSE,
            LLMTaskType.CLARIFICATION: ContextPurpose.CLARIFICATION,
            LLMTaskType.TOOL_RESULT_SUMMARY: ContextPurpose.TOOL_RESULT_SUMMARY,
            LLMTaskType.AGENT_LOOP: ContextPurpose.AGENT_LOOP,
        }

        context_purpose = purpose_mapping.get(purpose, ContextPurpose.DIRECT_RESPONSE)
        self._llm_logger.info(f"Main call: purpose={purpose.value}")

        # H2: 递增轮次计数器（在 retry 循环外，只计真实调用次数）
        self.increment_turn()

        # 获取配置
        cfg = load_config()
        max_retries = cfg.get("api_max_retries", 3)

        # 每次循环重新构建 messages（压缩后 messages 会变）
        attempt = 0
        messages_result = None
        last_error: Optional[Exception] = None

        while True:
            # ── 构建消息（注入 Base/Session 层元信息）────────────────────
            if self._context_manager:
                # H1: 构建 system_meta（启动时固定，影响 stable 层缓存）
                provider_name = getattr(self._provider, "provider_name", "auto")
                model_name = getattr(self._provider, "model", "Agent-Z")
                system_meta = self._build_system_meta(
                    tools=tools,
                    provider_name=provider_name,
                    model_name=model_name,
                )
                # H2: 构建 session_info（每次调用都变，不参与缓存）
                session_info = self._build_session_info()

                messages_result = await self._context_manager.build_messages(
                    user_message=user_message,
                    conversation_history=conversation_history,
                    purpose=context_purpose,
                    tools=tools,
                    include_tools=include_tools,
                    model=model,
                    system_meta=system_meta,
                    session_info=session_info,
                    **kwargs,
                )
                self._logger.debug(
                    f"Main call: messages={len(messages_result.messages)}, "
                    f"compressed={messages_result.compressed}"
                )
                messages = messages_result.messages
            else:
                messages = None

            # ── 调用 Provider ────────────────────────────────────────────
            try:
                response = await self._provider.generate(
                    prompt="",
                    messages=messages,
                    model=model,
                    **kwargs,
                )
                return (
                    response.content if hasattr(response, "content") else str(response)
                )

            except Exception as e:
                last_error = e
                classified = classify_api_error(
                    e,
                    provider=getattr(
                        self._provider, "provider_display_name", "unknown"
                    ),
                    model=model or "",
                )
                self._logger.debug(
                    f"API error classified: reason={classified.reason.value}, "
                    f"retryable={classified.retryable}, "
                    f"fallback={classified.should_fallback}, "
                    f"compress={classified.should_compress}"
                )

                # ── 不可重试：错误分类认为不该重试 → 立即 fallback ──────
                if not classified.retryable:
                    self._logger.info(
                        f"Error {classified.reason.value} is not retryable, "
                        f"activating fallback chain"
                    )
                    return await self._fallback_chain(messages, model, **kwargs)

                # ── 达到最大重试次数 → fallback ───────────────────────────
                if attempt >= max_retries:
                    self._logger.info(
                        f"Max retries ({max_retries}) exhausted for "
                        f"{classified.reason.value}, activating fallback chain"
                    )
                    return await self._fallback_chain(messages, model, **kwargs)

                # ── 可重试：jittered backoff 后重试 ───────────────────────
                attempt += 1
                wait_time = jittered_backoff(attempt)
                self._logger.info(
                    f"Retry {attempt}/{max_retries} for {classified.reason.value} "
                    f"in {wait_time:.1f}s"
                )
                await asyncio.sleep(wait_time)
                # retry_count 递增，但不压缩消息，直接重试

    async def _fallback_chain(
        self,
        messages: Optional[List[Dict[str, Any]]],
        model: Optional[str],
        **kwargs,
    ) -> str:
        """激活 fallback chain：遍历配置中的 fallback_providers，返回第一个成功的

        参考 Hermes _try_activate_fallback() 逻辑。
        每个 fallback provider 最多调用一次，不做重试（因为已经在主循环重试过了）。
        所有 fallback 都失败后，上抛最后一个异常。
        """
        last_error: Optional[Exception] = None

        for fb in self._fallback_providers:
            try:
                from agent.llm.factory import LLMFactory

                fb_provider = LLMFactory.create(
                    provider=fb.get("provider", "openai"),
                    api_key=fb.get("api_key") or "",
                    model=fb.get("model"),
                    base_url=fb.get("base_url"),
                )
                self._logger.info(f"[Fallback] Trying provider: {fb.get('provider')}")
                resp = await fb_provider.generate(
                    prompt="", messages=messages, model=model, **kwargs
                )
                content = resp.content if hasattr(resp, "content") else str(resp)
                self._logger.info(f"[Fallback] Provider {fb.get('provider')} succeeded")
                return content
            except Exception as fb_e:
                last_error = fb_e
                self._logger.warning(
                    f"[Fallback] Provider {fb.get('provider')} failed: {fb_e}"
                )
                continue

        # 所有 fallback 都失败了，上抛异常让上层处理
        if last_error is not None:
            raise last_error
        raise RuntimeError("Fallback chain exhausted with no error details")

    # ==================== 辅助任务调用 ====================

    async def auxiliary_call(
        self,
        task: LLMTaskType,
        prompt: str,
        system_prompt: str = None,
        model: str = None,
        messages: List[Dict[str, str]] = None,
        timeout: int = None,
        **kwargs,
    ) -> str:
        """
        辅助任务调用（使用轻量级上下文）

        根据任务类型自动选择轻量级模型。

        Args:
            task: 任务类型 (LLMTaskType)
            prompt: 用户提示
            system_prompt: 系统提示（可选）
            model: 模型名称（可选，优先级高于自动选择）
            messages: 消息列表（与 prompt 二选一）
            timeout: 超时时间（秒）

        Returns:
            LLM 响应内容
        """
        # 确定使用的模型
        effective_model = model or self._get_model_for_task(task)

        # 确定超时时间
        effective_timeout = timeout or self._get_timeout_for_task(task)

        self._llm_logger.info(
            f"Auxiliary call: task={task.value}, model={effective_model}"
        )

        try:
            if messages:
                response = await self._provider.generate(
                    messages=messages,
                    model=effective_model,
                    timeout=effective_timeout,
                    **kwargs,
                )
            else:
                response = await self._provider.generate(
                    prompt,
                    system_prompt=system_prompt,
                    model=effective_model,
                    timeout=effective_timeout,
                    **kwargs,
                )

            return response.content if hasattr(response, "content") else str(response)

        except Exception as e:
            self._logger.error(f"Auxiliary call failed: {e}")
            raise

    def _get_model_for_task(self, task: LLMTaskType) -> str:
        """根据任务类型获取模型"""
        model_mapping = {
            LLMTaskType.COMPRESSION: self._aux_config.compression_model,
            LLMTaskType.TITLE_GENERATION: self._aux_config.title_model,
            LLMTaskType.SKILL_SYNTHESIS: self._aux_config.synthesis_model,
            LLMTaskType.MEMORY_SUMMARY: self._aux_config.memory_model,
            LLMTaskType.ANALYSIS: self._aux_config.default_lightweight_model,
        }

        return model_mapping.get(task, self._aux_config.default_lightweight_model)

    def _get_timeout_for_task(self, task: LLMTaskType) -> int:
        """根据任务类型获取超时时间"""
        timeout_mapping = {
            LLMTaskType.COMPRESSION: self._aux_config.compression_timeout,
            LLMTaskType.TITLE_GENERATION: self._aux_config.title_timeout,
            LLMTaskType.SKILL_SYNTHESIS: self._aux_config.synthesis_timeout,
            LLMTaskType.MEMORY_SUMMARY: self._aux_config.memory_timeout,
            LLMTaskType.ANALYSIS: 30,
        }

        return timeout_mapping.get(task, 30)

    # ==================== 便捷方法 ====================

    async def compression_call(self, prompt: str, **kwargs) -> str:
        """上下文压缩调用"""
        return await self.auxiliary_call(
            task=LLMTaskType.COMPRESSION, prompt=prompt, **kwargs
        )

    async def title_call(self, prompt: str, **kwargs) -> str:
        """标题生成调用"""
        return await self.auxiliary_call(
            task=LLMTaskType.TITLE_GENERATION, prompt=prompt, **kwargs
        )

    async def synthesis_call(self, prompt: str, **kwargs) -> str:
        """技能合成调用"""
        return await self.auxiliary_call(
            task=LLMTaskType.SKILL_SYNTHESIS, prompt=prompt, **kwargs
        )

    async def memory_call(self, prompt: str, **kwargs) -> str:
        """记忆摘要调用"""
        return await self.auxiliary_call(
            task=LLMTaskType.MEMORY_SUMMARY, prompt=prompt, **kwargs
        )

    # ==================== 系统提示缓存 ====================

    def get_cached_system_prompt(self) -> Optional[str]:
        """获取缓存的系统提示"""
        return self._system_prompt_cache

    def set_cached_system_prompt(self, prompt: str) -> None:
        """设置缓存的系统提示"""
        self._system_prompt_cache = prompt
        self._cache_version += 1
        self._logger.debug(f"System prompt cached (version={self._cache_version})")

    def invalidate_cache(self) -> None:
        """使缓存失效"""
        self._system_prompt_cache = None
        self._cache_version += 1
        self._logger.debug(
            f"System prompt cache invalidated (version={self._cache_version})"
        )

    @property
    def cache_version(self) -> int:
        """获取缓存版本"""
        return self._cache_version


__all__ = ["LLMClient", "LLMTaskType", "LLMAuxConfig"]
