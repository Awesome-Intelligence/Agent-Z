#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Agent 集成 Advanced Reasoning
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
current_file = __file__
project_root = os.path.dirname(os.path.dirname(current_file))
sys.path.insert(0, project_root)


class MockLLMProvider:
    """模拟 LLM Provider"""
    
    async def generate(self, prompt: str) -> str:
        if "什么是" in prompt or "解释" in prompt:
            return "这是一个关于该主题的详细解释..."
        return "这是响应内容"


async def test_agent_with_advanced_reasoning():
    """测试 Agent 集成 Advanced Reasoning"""
    from agent.agent import CustomAgent, AgentConfig, ResponseStrategyRouter, ResponseStrategy
    
    print("=" * 60)
    print("测试 Agent 集成 Advanced Reasoning")
    print("=" * 60)
    
    config = AgentConfig(
        enable_task_planning=True,
        enable_advanced_reasoning=True,
        enable_session=False,
        enable_detailed_logs=False
    )
    
    agent = CustomAgent(config=config, session_id="test")
    
    llm = MockLLMProvider()
    agent.set_llm_provider(llm)
    
    print("\n1. 测试配置:")
    print(f"   enable_advanced_reasoning: {config.enable_advanced_reasoning}")
    print(f"   _advanced_reasoning_module: {agent._advanced_reasoning_module is not None}")
    print(f"   _strategy_router: {agent._strategy_router is not None}")
    
    print("\n2. 测试策略路由:")
    router = agent._strategy_router
    if router:
        test_cases = [
            ("什么是 REST API？", ResponseStrategy.ADVANCED_REASONING),
            ("帮我开发一个系统", ResponseStrategy.TASK_PLANNING),
            ("你好", ResponseStrategy.SIMPLE_RESPONSE),
        ]
        
        for text, expected in test_cases:
            strategy = router.analyze(text)
            status = "✓" if strategy == expected else "✗"
            print(f"   {status} \"{text}\" → {strategy.value}")
    
    print("\n3. 测试 Advanced Reasoning 请求:")
    response = await agent.respond("什么是 RESTful API？请详细解释")
    print(f"   响应长度: {len(response.content)}")
    print(f"   响应预览: {response.content[:50]}...")
    
    print("\n✅ 测试完成!")


if __name__ == "__main__":
    asyncio.run(test_agent_with_advanced_reasoning())
