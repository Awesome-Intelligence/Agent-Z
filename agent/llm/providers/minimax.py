"""
MiniMax Provider 实现
🧠 Decision - 🤖 LLM - MiniMax 海螺AI
"""

import os
import httpx
import json
import time
from typing import Optional, List, AsyncIterator
from .base import BaseProvider, ProviderConfig, ProviderResponse, Message, StreamChunk
from common.logging_manager import get_llm_logger
from common.config import DEFAULT_LLM_BASE_URLS
from common.streaming.think_scrubber import StreamingThinkScrubber


class MiniMaxProvider(BaseProvider):
    """MiniMax LLM Provider

    支持 MiniMax 海螺AI服务
    """

    provider_name = "minimax"
    provider_display_name = "MiniMax"
    supported_models = [
        "MiniMax-M2.7",
        "MiniMax-M2.5",
        "MiniMax-M2.1",
        "MiniMax-M2",
    ]
    default_model = "MiniMax-M2.7"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # 优先级: 配置 > 环境变量 > Provider默认URL
        self.base_url = (
            config.base_url
            or os.getenv("MINIMAX_BASE_URL")
            or DEFAULT_LLM_BASE_URLS.get("minimax")
        )
        self.api_key = config.api_key
        self._client: Optional[httpx.AsyncClient] = None
        self.logger = get_llm_logger(self.__class__.__name__)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.config.timeout,
                limits=self._get_default_limits(),
            )
        return self._client

    async def close(self) -> None:
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _validate_api_key(self):
        """验证 API Key 是否配置"""
        if not self.api_key:
            return False, (
                "MiniMax API Key 未配置。请设置环境变量 MINIMAX_API_KEY 或在配置中指定。\n"
                "获取方式: https://platform.minimaxi.com/"
            )
        return True, None

    def _get_request_body_extra(self, kwargs):
        """获取额外的请求体参数"""
        tools = kwargs.get("tools")
        if tools:
            return {"tools": tools}
        return {}

    def _should_handle_function_call(self, message):
        """检查是否有 tool_calls 或 function_call"""
        return message.get("tool_calls") or message.get("function_call")

    async def generate(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> ProviderResponse:
        """生成文本响应"""
        is_valid, error_msg = self._validate_api_key()
        if not is_valid:
            raise Exception(error_msg)

        start_time = time.time()
        self._log_request_started()

        system, msg_list, prompt_meta = self._build_messages(prompt, messages, system_prompt)
        if system:
            system_msg = {"role": "system", "content": system}
            if prompt_meta:
                system_msg["_prompt_meta"] = prompt_meta
            msg_list.insert(0, system_msg)

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }
        request_body.update(self._get_request_body_extra(kwargs))

        try:
            client = await self._get_client()
            self._log_request_body(request_body)
            self._log_input_messages(msg_list, prompt_meta)
            response = await client.post("/chat/completions", json=request_body)


            self._raise_for_status(response)

            data = response.json()
            latency_ms = (time.time() - start_time) * 1000

            message = data["choices"][0]["message"]
            raw_content = message.get("content", "")

            # MiniMax-M3 embeds thinking in content as <think>...[/think]\n\n\n{answer}
            import re as minimax_re
            thinking_blocks = minimax_re.findall(r"<think>(.*?)\[/think]", raw_content, minimax_re.DOTALL)
            reasoning_content = "\n".join(b.strip() for b in thinking_blocks if b.strip())
            output_content = minimax_re.sub(r"<think>.*?\[/think]\n+", "", raw_content, flags=minimax_re.DOTALL).strip()

            function_call = self._should_handle_function_call(message)
            if function_call:
                self._log_output_content(json.dumps(function_call))
                self._log_response_debug(message, function_call)
                self._log_request_completed(latency_ms)
                return ProviderResponse(
                    content=json.dumps(function_call),
                    model=data.get("model", self.config.model or self.default_model),
                    finish_reason=data["choices"][0].get("finish_reason", "stop"),
                    usage=data.get("usage", {}),
                    latency_ms=latency_ms,
                    function_call=function_call[0] if isinstance(function_call, list) else function_call,
                    reasoning_content=reasoning_content,
                )

            usage = data.get("usage", {})
            self._log_output_content(output_content)
            self._log_response_debug(message, function_call)
            self._log_request_completed(latency_ms)

            return ProviderResponse(
                content=output_content,
                model=data.get("model", self.config.model or self.default_model),
                finish_reason=data["choices"][0].get("finish_reason", "stop"),
                usage=usage,
                latency_ms=latency_ms,
                reasoning_content=reasoning_content,
            )

        except httpx.HTTPError as e:
            # HTTPStatusError 会从 _raise_for_status 传播，携带 response
            # 其他 HTTP 错误（超时、连接错误等）需要包装
            if not isinstance(e, httpx.HTTPStatusError):
                self._log_request_error(e, "request")
                raise Exception(f"Failed to call {self.provider_display_name} API: {e}") from e
            raise

    async def generate_stream(
        self,
        prompt: str,
        messages: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """生成流式响应"""
        is_valid, error_msg = self._validate_api_key()
        if not is_valid:
            yield StreamChunk(content=error_msg, finish=True)
            return

        start_time = time.time()
        self._log_request_started()

        system, msg_list, _ = self._build_messages(prompt, messages, system_prompt)
        if system:
            msg_list.insert(0, {"role": "system", "content": system})

        request_body = {
            "model": self.config.model or self.default_model,
            "messages": msg_list,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
            "stream": True,
        }

        try:
            client = await self._get_client()
            async with client.stream("POST", "/chat/completions", json=request_body) as response:
                if response.status_code != 200:
                    if response.status_code == 401:
                        yield StreamChunk(
                            content="MiniMax API Key 无效或已过期。请检查环境变量 MINIMAX_API_KEY 是否正确。\n获取方式: https://platform.minimaxi.com/",
                            finish=True
                        )
                        return
                    raise Exception(f"MiniMax API error: {response.status_code}")

                accumulated_content = ""
                accumulated_reasoning = ""
                scrubber = StreamingThinkScrubber()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            remaining_visible, remaining_reasoning = scrubber.flush()
                            if remaining_visible:
                                accumulated_content += remaining_visible
                            if remaining_reasoning:
                                accumulated_reasoning += remaining_reasoning
                            yield StreamChunk(
                                content=accumulated_content,
                                finish=True,
                                reasoning_content=accumulated_reasoning,
                            )
                            break

                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0]["delta"].get("content", "")

                            visible_delta, reasoning_delta = scrubber.feed(delta)

                            if visible_delta:
                                accumulated_content += visible_delta

                            if reasoning_delta:
                                accumulated_reasoning += reasoning_delta

                            yield StreamChunk(
                                content=accumulated_content,
                                delta=visible_delta,
                                finish=False,
                                reasoning_content=reasoning_delta if reasoning_delta else None,
                            )
                        except json.JSONDecodeError:
                            continue

                latency_ms = (time.time() - start_time) * 1000
                self._log_request_completed(latency_ms)

        except Exception as e:
            detailed_error = self._log_request_error(e, "streaming")
            yield StreamChunk(content=f"Error: {detailed_error}", finish=True)

    async def count_tokens(self, text: str) -> int:
        """估算 token 数量"""
        return self._estimate_tokens(text)