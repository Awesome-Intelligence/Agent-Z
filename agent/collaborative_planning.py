#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Collaborative Task Planning - 协作式任务规划

使用 LLM + Todo 工具进行任务规划。

设计原则:
- LLM 负责"做什么"（任务拆解），使用 todo 工具
- AdvancedReasoning 负责"为什么"（技术选型解释）
- 两者协同，提供带推理的完整执行计划

注意：
- 任务规划现在由 LLM 直接使用 todo 工具完成
- 保留此模块用于高级推理功能
"""

import json
import re
from typing import Dict, Any, Optional, List
from enum import Enum

from tools.todo_tool import (
    VALID_STATUSES,
    KANBAN_TO_TODO_STATUS,
)


class CollaborationStrategy(Enum):
    """协作策略"""
    DECOMPOSITION_ONLY = "decomposition_only"      # 仅拆解
    DECOMPOSITION_WITH_REASONING = "decomposition_with_reasoning"  # 拆解+推理
    EXECUTION_WITH_REASONING = "execution_with_reasoning"      # 执行+推理


class TechnicalDomain(Enum):
    """技术领域（需要 AdvancedReasoning 的场景）"""
    DATABASE = "database"            # 数据库选型
    AUTHENTICATION = "auth"         # 认证方式
    API_DESIGN = "api_design"      # API 设计
    ARCHITECTURE = "architecture"  # 架构设计
    SECURITY = "security"           # 安全设计
    DEPLOYMENT = "deployment"        # 部署策略
    TESTING = "testing"            # 测试策略
    FRONTEND = "frontend"         # 前端技术
    BACKEND = "backend"           # 后端技术


class CollaborativeTaskPlanner:
    """
    协作式任务规划器（简化版）

    保留此模块用于高级推理功能。
    任务拆解由 LLM 直接使用 todo 工具完成。

    ┌─────────────────────────────────────────────────────────────┐
    │  1. LLM 使用 todo 工具拆解任务                             │
    │     "帮我开发一个用户注册功能"                              │
    │     ↓                                                     │
    │  2. AdvancedReasoning 提供技术建议                         │
    │     "认证: JWT vs Session → 推荐 JWT (无状态，适合微服务)" │
    │     ↓                                                     │
    │  3. 生成带推理的执行计划                                   │
    └─────────────────────────────────────────────────────────────┘
    """

    def __init__(
        self,
        llm_provider=None,
        advanced_reasoning=None,
        enable_collaboration: bool = True
    ):
        self.llm_provider = llm_provider
        self.advanced_reasoning = advanced_reasoning
        self.enable_collaboration = enable_collaboration

        self._technical_keywords = {
            TechnicalDomain.DATABASE: [],
            TechnicalDomain.AUTHENTICATION: [],
            TechnicalDomain.API_DESIGN: [],
            TechnicalDomain.ARCHITECTURE: [],
            TechnicalDomain.SECURITY: [],
            TechnicalDomain.TESTING: [],
        }

    def _identify_technical_domains(self, task: str) -> List[TechnicalDomain]:
        """识别任务涉及的技术领域"""
        task_lower = task.lower()
        domains = []

        for domain, keywords in self._technical_keywords.items():
            if any(kw.lower() in task_lower for kw in keywords):
                domains.append(domain)

        return domains

    def _generate_reasoning_prompt(self, domain: TechnicalDomain, context: str) -> str:
        """生成推理提示"""
        prompts = {
            TechnicalDomain.DATABASE: f"""对于一个{context}的系统，请提供数据库选型建议。

考虑因素：
- 数据一致性要求
- 扩展性需求
- 事务支持
- 团队技术栈

请简洁回答：
1. 推荐方案
2. 主要理由（1-2句话）
3. 适用场景""",

            TechnicalDomain.AUTHENTICATION: f"""对于一个{context}的系统，请提供认证方案建议。

考虑因素：
- 是否需要无状态
- 微服务架构
- 安全要求
- 用户规模

请简洁回答：
1. 推荐方案（JWT/Session/OAuth）
2. 主要理由（1-2句话）
3. 实现要点""",

            TechnicalDomain.API_DESIGN: f"""对于一个{context}的API，请提供设计建议。

考虑因素：
- RESTful vs GraphQL
- 版本管理
- 错误处理
- 文档

请简洁回答：
1. 推荐方案
2. 主要理由
3. 设计要点""",

            TechnicalDomain.ARCHITECTURE: f"""对于一个{context}的系统，请提供架构建议。

考虑因素：
- 单体 vs 微服务
- 可扩展性
- 维护性
- 团队规模

请简洁回答：
1. 推荐方案
2. 主要理由
3. 演进路径""",

            TechnicalDomain.SECURITY: f"""对于一个{context}的系统，请提供安全建议。

考虑因素：
- 认证授权
- 数据加密
- 漏洞防护
- 合规要求

请简洁回答：
1. 推荐方案
2. 主要理由
3. 实现要点""",

            TechnicalDomain.TESTING: f"""对于一个{context}的系统，请提供测试建议。

考虑因素：
- 单元测试
- 集成测试
- E2E 测试
- 覆盖率目标

请简洁回答：
1. 推荐方案
2. 主要理由
3. 工具推荐""",

            TechnicalDomain.DEPLOYMENT: f"""对于一个{context}的系统，请提供部署建议。

考虑因素：
- 容器化
- CI/CD
- 监控日志
- 扩缩容

请简洁回答：
1. 推荐方案
2. 主要理由
3. 工具推荐""",
        }
        return prompts.get(domain, "")

    async def get_technical_reasoning(self, task: str) -> Dict[str, Any]:
        """
        获取技术领域推理建议

        这是一个简化版本，保留用于需要高级推理的场景。
        """
        result = {
            'success': True,
            'reasoning': {},
            'domains': []
        }

        if not self.advanced_reasoning:
            return result

        domains = self._identify_technical_domains(task)
        result['domains'] = [d.value for d in domains]

        for domain in domains:
            prompt = self._generate_reasoning_prompt(domain, task)
            if prompt and self.advanced_reasoning:
                try:
                    response = await self.advanced_reasoning.process(prompt)
                    if hasattr(response, 'content'):
                        result['reasoning'][domain.value] = response.content
                    else:
                        result['reasoning'][domain.value] = str(response)
                except Exception:
                    result['reasoning'][domain.value] = "推理生成失败"

        return result

    def format_result(self, result: Dict[str, Any]) -> str:
        """
        格式化规划结果

        兼容 todo 工具返回的格式。
        """
        lines = []

        # 技术推理
        if result.get('reasoning'):
            lines.append("💡 **技术选型建议:**")
            for domain, reasoning in result['reasoning'].items():
                lines.append(f"\n**{domain}:**")
                lines.append(f"{reasoning}")

        return "\n".join(lines) if lines else ""


def create_collaborative_planner(
    llm_provider=None,
    advanced_reasoning=None,
    enable_collaboration: bool = True
) -> CollaborativeTaskPlanner:
    """创建协作式任务规划器"""
    return CollaborativeTaskPlanner(
        llm_provider=llm_provider,
        advanced_reasoning=advanced_reasoning,
        enable_collaboration=enable_collaboration
    )
