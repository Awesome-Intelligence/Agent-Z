# 🧠 Decision - 🔧 Rail - 上下文压缩 Rail

"""
ContextCompressionRail - 基于 Rail 机制的上下文压缩

功能：
1. 在 before_llm_call 前检查 token 预算，判断是否需要压缩
2. 在 after_llm_call 后获取实际 token 使用量，触发压缩
3. 在 on_checkpoint 手动触发压缩（/compress 命令）

使用方式：
    from agent.rails.context_compression_rail import ContextCompressionRail

    rail = ContextCompressionRail(session_id="xxx")
    rail.set_compressor(compressor)  # 设置压缩引擎
    manager.register_rail(rail)
"""

import asyncio
from typing import Any, Dict, List, Optional

from common.logging_manager import get_decision_logger
from agent.rails.rail import Rail, RailPriority, RailResult


class ContextCompressionRail(Rail):
    """
    上下文压缩 Rail

    通过 Rail 机制将上下文压缩插入到 Agent 执行流程中。
    在 LLM 调用前后自动检查和触发压缩。

    优先级：HIGH（高优先级，在 LLM 调用前检查）
    """

    name: str = "context_compression"
    description: str = "Automatically compress conversation context when approaching token limits"
    priority: RailPriority = RailPriority.HIGH

    def __init__(
        self,
        session_id: str,
        enabled: bool = True,
        auto_compress: bool = True,
        threshold_percent: float = 0.50,
    ):
        super().__init__(session_id)
        self._enabled = enabled
        self._auto_compress = auto_compress
        self._threshold_percent = threshold_percent

        self._compressor = None
        self._llm_client = None
        self._last_prompt_tokens = 0
        self._last_completion_tokens = 0
        self._pending_compression = False
        self._compression_result: Optional[List[Dict[str, Any]]] = None
        self._focus_topic: Optional[str] = None

    def set_compressor(self, compressor: Any) -> None:
        """设置压缩引擎"""
        self._compressor = compressor
        self.logger.debug("Context compressor set")

    def set_llm_client(self, client: Any) -> None:
        """设置 LLM 客户端（用于摘要生成）"""
        self._llm_client = client
        if self._compressor:
            self._compressor.set_llm_client(client)

    def set_threshold_percent(self, threshold_percent: float) -> None:
        """设置压缩阈值百分比"""
        self._threshold_percent = threshold_percent
        if self._compressor:
            self._compressor.threshold_percent = threshold_percent

    def request_compression(self, focus_topic: Optional[str] = None) -> None:
        """
        请求在下次 LLM 调用前执行压缩

        Args:
            focus_topic: 可选的聚焦主题，用于引导压缩
        """
        self._pending_compression = True
        self._focus_topic = focus_topic
        self.logger.info(f"Compression requested (focus: {focus_topic or 'none'})")

    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        stats = {
            "enabled": self._enabled,
            "auto_compress": self._auto_compress,
            "threshold_percent": self._threshold_percent,
            "pending_compression": self._pending_compression,
            "last_prompt_tokens": self._last_prompt_tokens,
            "last_completion_tokens": self._last_completion_tokens,
        }

        if self._compressor:
            stats.update({
                "compression_count": self._compressor.compression_count,
                "context_length": self._compressor.context_length,
                "threshold_tokens": self._compressor.threshold_tokens,
            })

        return stats

    async def before_llm_call(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        **kwargs
    ) -> Optional[RailResult]:
        """
        LLM 调用前触发

        检查是否需要压缩，如果需要则执行压缩并返回 modified_messages。

        Returns:
            RailResult: 包含压缩后的消息列表
        """
        if not self._enabled:
            return None

        if not self._auto_compress and not self._pending_compression:
            return None

        if not self._compressor:
            self.logger.debug("No compressor configured, skipping compression check")
            return None

        try:
            from agent.context.token_estimator import estimate_messages_tokens_rough

            current_tokens = estimate_messages_tokens_rough(messages)

            should_compress = (
                self._pending_compression or
                self._compressor.should_compress(current_tokens)
            )

            if not should_compress:
                return None

            self.logger.info(
                f"Pre-LLM compression triggered: ~{current_tokens} tokens "
                f"(threshold: {self._compressor.threshold_tokens})"
            )

            compressed_messages = self._compressor.compress(
                messages,
                current_tokens=current_tokens,
                focus_topic=self._focus_topic,
            )

            self._pending_compression = False
            self._focus_topic = None

            if len(compressed_messages) < len(messages):
                new_tokens = estimate_messages_tokens_rough(compressed_messages)
                saved = current_tokens - new_tokens
                self.logger.info(
                    f"Compression complete: {len(messages)} -> {len(compressed_messages)} "
                    f"messages (~{saved} tokens saved)"
                )

                return RailResult(
                    allowed=True,
                    modified_args={"messages": compressed_messages},
                    metadata={
                        "compressed": True,
                        "original_count": len(messages),
                        "compressed_count": len(compressed_messages),
                        "tokens_saved": saved,
                    }
                )
            else:
                self.logger.debug("Compression had no effect, using original messages")
                return None

        except Exception as e:
            self.logger.error(f"Pre-LLM compression failed: {e}")
            self._pending_compression = False
            return None

    async def after_llm_call(
        self,
        messages: List[Dict[str, Any]],
        response: Any,
        **kwargs
    ) -> Optional[RailResult]:
        """
        LLM 调用后触发

        获取实际 token 使用量，更新压缩器状态。

        Returns:
            RailResult: 无（主要用于状态更新）
        """
        if not self._enabled:
            return None

        try:
            if hasattr(response, 'usage') and response.usage:
                usage = response.usage
                self._last_prompt_tokens = usage.get('prompt_tokens', 0)
                self._last_completion_tokens = usage.get('completion_tokens', 0)

                if self._compressor:
                    self._compressor.update_from_response(usage)

                self.logger.debug(
                    f"Token usage: prompt={self._last_prompt_tokens}, "
                    f"completion={self._last_completion_tokens}"
                )

            elif hasattr(response, 'last_prompt_tokens'):
                self._last_prompt_tokens = response.last_prompt_tokens
                self._last_completion_tokens = response.last_completion_tokens

        except Exception as e:
            self.logger.debug(f"Could not extract token usage from response: {e}")

        return None

    async def on_checkpoint(self, checkpoint_name: str) -> Optional[RailResult]:
        """
        Checkpoint 点触发

        在指定的 checkpoint 点触发压缩。

        Args:
            checkpoint_name: Checkpoint 名称（如 'compress', 'mid_task'）

        Returns:
            RailResult: 压缩结果
        """
        if not self._enabled:
            return None

        if checkpoint_name not in {"compress", "mid_task", "pause", "manual"}:
            return None

        if not self._compressor:
            self.logger.warning("No compressor configured for checkpoint compression")
            return RailResult(
                allowed=True,
                error="No compressor configured",
            )

        self.logger.info(f"Checkpoint compression triggered: {checkpoint_name}")

        return RailResult(
            allowed=True,
            metadata={"checkpoint_name": checkpoint_name},
        )

    def on_error(self, error: Exception, context: str = "") -> None:
        """错误处理"""
        self.logger.error(f"ContextCompressionRail error in {context}: {error}")


class CompressionRailManager:
    """
    压缩 Rail 管理器

    提供便捷的压缩 Rail 创建和管理接口。
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.logger = get_decision_logger("CompressionRailManager", sublayer="rail")
        self._compression_rail: Optional[ContextCompressionRail] = None

    def create_rail(
        self,
        compressor: Any = None,
        llm_client: Any = None,
        enabled: bool = True,
        auto_compress: bool = True,
        threshold_percent: float = 0.50,
    ) -> ContextCompressionRail:
        """创建压缩 Rail"""
        rail = ContextCompressionRail(
            session_id=self.session_id,
            enabled=enabled,
            auto_compress=auto_compress,
            threshold_percent=threshold_percent,
        )

        if compressor:
            rail.set_compressor(compressor)

        if llm_client:
            rail.set_llm_client(llm_client)

        self._compression_rail = rail
        self.logger.info(
            f"Created compression rail: auto={auto_compress}, "
            f"threshold={threshold_percent}"
        )

        return rail

    def get_rail(self) -> Optional[ContextCompressionRail]:
        """获取压缩 Rail 实例"""
        return self._compression_rail

    def request_compression(self, focus_topic: Optional[str] = None) -> bool:
        """请求压缩"""
        if self._compression_rail:
            self._compression_rail.request_compression(focus_topic)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        """获取压缩统计"""
        if self._compression_rail:
            return self._compression_rail.get_compression_stats()
        return {}


__all__ = [
    "ContextCompressionRail",
    "CompressionRailManager",
]