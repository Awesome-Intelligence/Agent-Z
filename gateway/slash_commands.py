"""
Slash Commands Module for Agent-Z GatewayRunner.

提供 /new, /reset, /model, /stop, /help 等斜杠命令支持。
"""

from typing import Optional, Tuple

from common.logging_manager import get_logger

logger = get_logger("gateway.slash")

# 斜杠命令前缀
COMMAND_PREFIX = "/"


def _is_slash_command(text: str) -> bool:
    """
    检查消息是否为斜杠命令。

    Args:
        text: 消息文本

    Returns:
        True if the message starts with / or !
    """
    if not text:
        return False
    return text.startswith(COMMAND_PREFIX)


def _parse_slash_command(text: str) -> Tuple[str, str]:
    """
    解析斜杠命令文本。

    Args:
        text: 完整的命令文本，如 "/new" 或 "/model gpt-4" 或 "!help"

    Returns:
        (command, args) 元组，command 为小写命令名，args 为参数字符串
    """
    if not text:
        return "", ""

    # 支持 / 和 ! 两种前缀
    if text.startswith("!"):
        parts = text[1:].split(None, 1)
    elif text.startswith("/"):
        parts = text[1:].split(None, 1)
    else:
        return "", text

    command = parts[0].lower() if parts else ""
    args = parts[1] if len(parts) > 1 else ""

    return command, args


class GatewaySlashCommandsMixin:
    """
    斜杠命令处理 Mixin。

    继承此 Mixin 的 GatewayRunner 将支持以下命令:
    - /new, /reset: 开始新对话
    - /model: 切换或查看模型
    - /stop: 停止当前生成
    - /help: 显示帮助信息
    """

    async def _handle_message(self, event) -> Optional[bool]:
        """
        拦截消息，检查是否为斜杠命令。

        如果是斜杠命令则分发处理，否则传递给父类的 _handle_message。

        Args:
            event: 消息事件对象

        Returns:
            True if command was handled, None to fall through to parent
        """
        text = getattr(event, "text", "") or ""

        if not _is_slash_command(text):
            return await super()._handle_message(event)

        command, args = _parse_slash_command(text)
        logger.info(f"收到斜杠命令: /{command} args={args!r}")

        try:
            # 根据命令名分发到对应的处理方法
            handler_map = {
                "help": self._handle_help_command,
                "new": self._handle_new_command,
                "reset": self._handle_reset_command,
                "model": self._handle_model_command,
                "stop": self._handle_stop_command,
            }

            handler = handler_map.get(command)
            if handler:
                result = await handler(event, args)
            else:
                result = f"❓ 未知命令: /{command}，发送 /help 查看可用命令。"

            # 发送命令响应
            adapter = self.adapters.get(event.source.platform)
            reply_to = event.message_id if hasattr(event, "message_id") else None
            await self._safe_send(adapter, event.source.chat_id, result, reply_to=reply_to)
            return True

        except Exception as e:
            logger.error(f"处理斜杠命令 /{command} 时出错: {e}", exc_info=True)
            error_msg = f"⚠️ 命令处理出错: {str(e)}"
            adapter = self.adapters.get(event.source.platform)
            await self._safe_send(adapter, event.source.chat_id, error_msg)
            return True

    async def _handle_help_command(self, event, args: str) -> str:
        """
        处理 /help 命令，返回帮助文本。

        Args:
            event: 消息事件对象
            args: 命令参数（未使用）

        Returns:
            格式化的帮助文本
        """
        help_text = """```
可用斜杠命令:

/help
    显示此帮助信息

/new, /reset
    开始新对话，清除当前对话历史

/model [provider/model]
    查看或切换模型
    - /model          显示可用模型列表
    - /model list     同上
    - /model default  重置为默认模型
    - /model clear    同上
    - /model <name>   切换到指定模型

/stop
    停止当前正在进行的生成

示例:
    /new
    /model gpt-4
    /model claude-3-opus
    /model default
```"""
        return help_text

    async def _handle_new_command(self, event, args: str) -> str:
        """
        处理 /new 命令，开始新对话。

        Args:
            event: 消息事件对象
            args: 命令参数（未使用）

        Returns:
            成功消息
        """
        from gateway.session import build_session_key

        try:
            session_key = build_session_key(event.source)

            # 使当前运行中的生成失效
            await self._invalidate_session_run_generation(session_key, reason="session_reset")

            # 释放运行中的 Agent 状态
            await self._release_running_agent_state(session_key)

            # 重置 session_store 中的会话
            if hasattr(self, "session_store") and self.session_store:
                self.session_store.reset_session(session_key)

            # 从缓存中清除 Agent
            with self._agent_cache_lock:
                self._agent_cache.pop(session_key, None)

            logger.info(f"已为 {session_key} 开始新对话")
            return "✅ 已开始新对话。"

        except Exception as e:
            logger.error(f"处理 /new 命令时出错: {e}", exc_info=True)
            return f"⚠️ 重置会话时出错: {str(e)}"

    async def _handle_reset_command(self, event, args: str) -> str:
        """
        处理 /reset 命令，功能同 /new。

        Args:
            event: 消息事件对象
            args: 命令参数（未使用）

        Returns:
            成功消息
        """
        return await self._handle_new_command(event, args)

    async def _handle_model_command(self, event, args: str) -> str:
        """
        处理 /model 命令，查看或切换模型。

        Args:
            event: 消息事件对象
            args: 可能是空、"list"、"default"、"clear" 或 "provider/model"

        Returns:
            操作结果文本
        """
        from gateway.session import build_session_key

        try:
            session_key = build_session_key(event.source)
            args_lower = args.strip().lower()

            # 获取配置中的模型信息
            providers = self._gateway_cfg.get("providers", {})
            default_model = self._gateway_cfg.get("model", {}).get("default", "")

            # 无参数或 list：显示可用模型列表
            if not args_lower or args_lower == "list":
                provider_list = "\n".join(f"  - {name}" for name in providers.keys())
                response = f"""```
可用模型:

默认模型: {default_model}

可用的 Provider:
{provider_list}
```"""
                return response

            # default 或 clear：重置为默认模型
            if args_lower == "default" or args_lower == "clear":
                if hasattr(self, "session_store") and self.session_store:
                    self.session_store.set_model_override(session_key, None)
                logger.info(f"已为 {session_key} 重置模型为默认")
                return "✅ 模型已重置为默认。"

            # 指定模型：设置模型覆盖
            model_override = {"model": args.strip()}
            if hasattr(self, "session_store") and self.session_store:
                self.session_store.set_model_override(session_key, model_override)

            logger.info(f"已为 {session_key} 切换模型至 {args}")
            return f"✅ 模型已切换至 {args}"

        except Exception as e:
            logger.error(f"处理 /model 命令时出错: {e}", exc_info=True)
            return f"⚠️ 切换模型时出错: {str(e)}"

    async def _handle_stop_command(self, event, args: str) -> str:
        """
        处理 /stop 命令，停止当前生成。

        Args:
            event: 消息事件对象
            args: 命令参数（未使用）

        Returns:
            操作结果文本
        """
        from gateway.session import build_session_key

        try:
            session_key = build_session_key(event.source)

            # 从缓存中获取 Agent
            with self._agent_cache_lock:
                agent = self._agent_cache.get(session_key)

            if agent and hasattr(agent, "stop"):
                agent.stop()
                logger.info(f"已为 {session_key} 停止生成")
                return "🛑 已停止生成。"
            else:
                return "ℹ️ 当前没有正在进行的生成。"

        except Exception as e:
            logger.error(f"处理 /stop 命令时出错: {e}", exc_info=True)
            return f"⚠️ 停止生成时出错: {str(e)}"
