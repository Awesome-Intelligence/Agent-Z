"""agent.llm - LLM Integration Module"""
from .base import BaseLLMProvider, LLMResponse, LLMConfig
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider
from .factory import LLMFactory
from common.logging_manager import get_llm_logger
import json
import urllib.request

logger = get_llm_logger("LLMModule")


def get_all_providers() -> list[dict]:
    """获取所有可用的 LLM Provider"""
    return [
        {
            "id": "openai",
            "name": "OpenAI",
            "description": "OpenAI GPT 系列模型",
            "base_url": "https://api.openai.com/v1",
            "models_url": "",
            "fallback_models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "default_model": "gpt-4",
        },
        {
            "id": "claude",
            "name": "Claude (Anthropic)",
            "description": "Anthropic Claude 系列模型",
            "base_url": "https://api.anthropic.com",
            "models_url": "https://api.anthropic.com/v1/models",
            "fallback_models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "default_model": "claude-3-sonnet",
        },
        {
            "id": "nvidia",
            "name": "NVIDIA NIM",
            "description": "NVIDIA NIM — accelerated inference",
            "base_url": "https://integrate.api.nvidia.com/v1",
            "models_url": "",
            "fallback_models": ["nvidia/llama-3.1-nemotron-70b-instruct", "nvidia/llama-3.3-70b-instruct"],
            "default_model": "nvidia/llama-3.3-70b-instruct",
        },
        {
            "id": "deepseek",
            "name": "DeepSeek",
            "description": "DeepSeek — native DeepSeek API",
            "base_url": "https://api.deepseek.com/v1",
            "models_url": "",
            "fallback_models": ["deepseek-v4-flash", "deepseek-v4-pro"],
            "default_model": "deepseek-v4-pro",
        },
        {
            "id": "gemini",
            "name": "Google Gemini",
            "description": "Google AI Studio (API key)",
            "base_url": "https://generativelanguage.googleapis.com/v1beta",
            "models_url": "",
            "fallback_models": ["gemini-3-flash-preview", "gemini-3-pro-preview"],
            "default_model": "gemini-3-flash-preview",
        },
        {
            "id": "kimi",
            "name": "Kimi (Moonshot)",
            "description": "Kimi/Moonshot — long context models",
            "base_url": "https://api.moonshot.ai/v1",
            "models_url": "",
            "fallback_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            "default_model": "moonshot-v1-32k",
        },
        {
            "id": "kimi-cn",
            "name": "Kimi (China)",
            "description": "Kimi/Moonshot China — long context models",
            "base_url": "https://api.moonshot.cn/v1",
            "models_url": "",
            "fallback_models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            "default_model": "moonshot-v1-32k",
        },
        {
            "id": "alibaba",
            "name": "Alibaba DashScope",
            "description": "Alibaba Cloud DashScope (Qwen)",
            "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            "models_url": "",
            "fallback_models": ["qwen-plus", "qwen2-7b", "qwen2-72b"],
            "default_model": "qwen-plus",
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "description": "OpenRouter — unified API for 200+ models",
            "base_url": "https://openrouter.ai/api/v1",
            "models_url": "https://openrouter.ai/api/v1/models",
            "fallback_models": ["anthropic/claude-sonnet-4.6", "openai/gpt-5.4", "deepseek/deepseek-chat", "google/gemini-3-flash-preview"],
            "default_model": "anthropic/claude-sonnet-4.6",
        },
        {
            "id": "minimax",
            "name": "MiniMax",
            "description": "MiniMax — Anthropic-compatible API",
            "base_url": "https://api.minimax.io/anthropic",
            "models_url": "",
            "fallback_models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
            "default_model": "MiniMax-M2.7",
        },
        {
            "id": "minimax-cn",
            "name": "MiniMax (China)",
            "description": "MiniMax China — Anthropic-compatible API",
            "base_url": "https://api.minimaxi.com/anthropic",
            "models_url": "",
            "fallback_models": ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
            "default_model": "MiniMax-M2.7",
        },
        {
            "id": "xai",
            "name": "xAI Grok",
            "description": "xAI Grok — Elon Musk's AI",
            "base_url": "https://api.x.ai/v1",
            "models_url": "",
            "fallback_models": ["grok-beta", "grok-2"],
            "default_model": "grok-2",
        },
        {
            "id": "nous",
            "name": "Nous Research",
            "description": "Nous Research open models",
            "base_url": "https://api.nousresearch.com/v1",
            "models_url": "",
            "fallback_models": ["nous-hermes-3-mixtral-8x7b"],
            "default_model": "nous-hermes-3-mixtral-8x7b",
        },
        {
            "id": "custom",
            "name": "Custom API",
            "description": "Custom OpenAI-compatible API endpoint",
            "base_url": "",
            "models_url": "",
            "fallback_models": [],
            "default_model": "",
        },
    ]


def _fetch_models_from_api(provider_info: dict, api_key: str | None = None, timeout: float = 8.0) -> list[str] | None:
    """从 API 动态获取模型列表
    
    Args:
        provider_info: 提供商信息字典
        api_key: API 密钥（可选）
        timeout: 请求超时时间
        
    Returns:
        模型ID列表，如果获取失败则返回None
    """
    url = (provider_info.get("models_url") or "").strip()
    if not url:
        if not provider_info.get("base_url"):
            return None
        url = provider_info["base_url"].rstrip("/") + "/models"
    
    try:
        req = urllib.request.Request(url)
        if api_key:
            req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Accept", "application/json")
        req.add_header("User-Agent", "handsome-agent/1.0")
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        
        items = data if isinstance(data, list) else data.get("data", [])
        models = [m["id"] for m in items if isinstance(m, dict) and "id" in m]
        
        if models:
            logger.debug(f"Fetched {len(models)} models from {provider_info['id']} API")
            return models
        
    except Exception as exc:
        logger.debug(f"Failed to fetch models from {provider_info['id']} API: {exc}")
    
    return None


def get_provider_models(provider: str, api_key: str | None = None) -> list[str]:
    """获取指定 Provider 支持的模型
    
    优先尝试从 API 动态获取，如果失败则使用备用列表
    
    Args:
        provider: 提供商ID
        api_key: API 密钥（可选，用于动态获取）
        
    Returns:
        模型列表
    """
    providers = get_all_providers()
    for p in providers:
        if p["id"] == provider:
            if p["id"] != "custom":
                live_models = _fetch_models_from_api(p, api_key)
                if live_models:
                    return live_models
            return p["fallback_models"]
    return LLMFactory.list_models(provider)


__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMConfig",
    "OpenAIProvider",
    "ClaudeProvider",
    "LLMFactory",
    "get_all_providers",
    "get_provider_models",
]
