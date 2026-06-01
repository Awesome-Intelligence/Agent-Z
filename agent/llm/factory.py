"""
LLM Factory - LLM Provider 工厂
"""

from typing import Optional, Dict
from .base import BaseLLMProvider, LLMConfig
from .openai_provider import OpenAIProvider
from .claude_provider import ClaudeProvider


class LLMFactory:
    """LLM Provider 工厂"""
    
    _providers: Dict[str, type] = {
        "openai": OpenAIProvider,
        "gpt": OpenAIProvider,
        "claude": ClaudeProvider,
        "anthropic": ClaudeProvider,
        "nvidia": OpenAIProvider,
        "deepseek": OpenAIProvider,
        "gemini": OpenAIProvider,
        "kimi": OpenAIProvider,
        "kimi-cn": OpenAIProvider,
        "alibaba": OpenAIProvider,
        "openrouter": OpenAIProvider,
        "minimax": ClaudeProvider,
        "minimax-cn": ClaudeProvider,
        "xai": OpenAIProvider,
        "nous": OpenAIProvider,
        "custom": OpenAIProvider,
    }
    
    _default_models: Dict[str, str] = {
        "openai": "gpt-4",
        "gpt": "gpt-4",
        "claude": "claude-3-sonnet",
        "anthropic": "claude-3-sonnet",
        "nvidia": "nvidia/llama-3.3-70b-instruct",
        "deepseek": "deepseek-chat",
        "gemini": "gemini-3-flash-preview",
        "kimi": "moonshot-v1-32k",
        "kimi-cn": "moonshot-v1-32k",
        "alibaba": "qwen-plus",
        "openrouter": "anthropic/claude-sonnet-4.6",
        "minimax": "MiniMax-M2.7",
        "minimax-cn": "MiniMax-M2.7",
        "xai": "grok-2",
        "nous": "nous-hermes-3-mixtral-8x7b",
        "custom": "",
    }
    
    @classmethod
    def create(
        cls,
        provider: str,
        api_key: str,
        model: Optional[str] = None,
        **kwargs
    ) -> BaseLLMProvider:
        """
        创建 LLM Provider
        
        Args:
            provider: 提供商名称
            api_key: API 密钥
            model: 模型名称（可选）
            **kwargs: 其他配置参数
            
        Returns:
            BaseLLMProvider: LLM Provider 实例
        """
        provider_lower = provider.lower()
        
        if provider_lower not in cls._providers:
            raise ValueError(
                f"Unknown provider: {provider}. "
                f"Available: {list(cls._providers.keys())}"
            )
        
        provider_class = cls._providers[provider_lower]
        
        config_kwargs = {}
        for k, v in kwargs.items():
            if hasattr(LLMConfig, '__dataclass_fields__') and k in LLMConfig.__dataclass_fields__:
                config_kwargs[k] = v
            elif hasattr(LLMConfig, 'model_fields') and k in LLMConfig.model_fields:
                config_kwargs[k] = v
        
        config = LLMConfig(
            provider=provider_lower,
            api_key=api_key,
            model=model or cls._default_models.get(provider_lower, "gpt-4"),
            **config_kwargs
        )
        
        return provider_class(config)
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """列出支持的提供商"""
        return list(cls._providers.keys())
    
    @classmethod
    def list_models(cls, provider: str) -> list[str]:
        """列出提供商支持的模型"""
        from . import get_all_providers
        providers = get_all_providers()
        for p in providers:
            if p["id"] == provider.lower():
                return p["models"]
        return []
    
    @classmethod
    def register_provider(cls, name: str, provider_class: type) -> None:
        """注册新的 Provider"""
        cls._providers[name.lower()] = provider_class
