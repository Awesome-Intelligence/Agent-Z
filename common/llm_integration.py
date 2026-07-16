"""
兼容层 - 为旧代码提供 llm_integration 模块
"""

from agent.llm import LLMConfig, LLMFactory


def setup_llm_integration(config: LLMConfig) -> object:
    """
    设置 LLM 集成
    
    Args:
        config: LLM 配置对象
        
    Returns:
        LLM Provider 实例
    """
    if not config.provider:
        raise ValueError("Provider is required")
    
    return LLMFactory.create(
        provider=config.provider,
        api_key=config.api_key,
        model=config.model,
        base_url=config.base_url,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        timeout=config.timeout,
    )
