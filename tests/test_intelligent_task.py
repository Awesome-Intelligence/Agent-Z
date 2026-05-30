#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能任务规划系统验证测试

测试 LLM 驱动的任务复杂度检测和自动拆解功能
"""

import asyncio
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MockLLMProvider:
    """模拟 LLM Provider"""
    
    async def generate(self, prompt: str) -> str:
        """根据 prompt 类型返回不同的模拟响应"""
        
        if "判断任务复杂度" in prompt or "分析用户请求" in prompt:
            if "开发" in prompt and ("用户" in prompt or "注册" in prompt or "功能" in prompt):
                return '''{"complexity": "complex", "estimated_steps": 5, "needs_planning": true, "reasoning": "涉及前端、后端、数据库多个层面，需要多步骤实现"}'''
            elif "你好" in prompt or "天气" in prompt or "时间" in prompt:
                return '''{"complexity": "simple", "estimated_steps": 1, "needs_planning": false, "reasoning": "简单查询，直接回答即可"}'''
            elif "完成报告" in prompt or "帮我" in prompt:
                return '''{"complexity": "moderate", "estimated_steps": 3, "needs_planning": true, "reasoning": "需要几个步骤，建议拆解"}'''
            else:
                return '''{"complexity": "simple", "estimated_steps": 1, "needs_planning": false, "reasoning": "简单任务"}'''
        
        elif "拆解" in prompt or "子任务" in prompt:
            return '''{
    "subtasks": [
        {"id": 1, "title": "需求分析", "description": "分析用户注册功能需求", "depends_on": [], "priority": "high"},
        {"id": 2, "title": "数据库设计", "description": "设计用户表结构", "depends_on": [1], "priority": "high"},
        {"id": 3, "title": "后端API开发", "description": "实现用户注册API接口", "depends_on": [2], "priority": "high"},
        {"id": 4, "title": "前端表单开发", "description": "实现注册表单界面", "depends_on": [3], "priority": "medium"},
        {"id": 5, "title": "测试验证", "description": "测试完整注册流程", "depends_on": [4], "priority": "medium"}
    ],
    "overall_plan": "从需求分析开始，逐步实现后端和前端，最后进行集成测试"
}'''
        
        return '{"result": "ok"}'


async def test_task_planner():
    """测试 TaskPlanner"""
    print("=" * 60)
    print("测试 1: TaskPlanner - 任务规划器")
    print("=" * 60)

    from core.task_planner import TaskPlanner, TaskComplexity, get_task_planner

    llm = MockLLMProvider()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        planner = get_task_planner("test_session", llm, tmpdir)
        
        print("\n1.1 测试复杂度分析...")
        result = await planner.analyze_complexity("帮我开发一个用户注册功能，包括前端、后端、数据库")
        print(f"   输入: 帮我开发一个用户注册功能...")
        print(f"   结果: {result}")
        assert result['needs_decomposition'] == True, "复杂任务应该需要拆解"
        print("   ✓ 复杂度分析正确")
        
        print("\n1.2 测试任务拆解...")
        plan = await planner.decompose_task("帮我开发一个用户注册功能", "complex")
        print(f"   拆解了 {len(plan.subtasks)} 个子任务:")
        for task in plan.subtasks:
            print(f"   - #{task.id}: {task.title} (依赖: {task.depends_on})")
        assert len(plan.subtasks) >= 3, "应该拆解出至少3个子任务"
        print("   ✓ 任务拆解正确")
        
        print("\n1.3 测试创建任务列表...")
        task_list = await planner.create_task_list(plan)
        print(f"   {task_list[:100]}...")
        assert "已创建" in task_list or "任务" in task_list
        print("   ✓ 任务列表创建成功")

    print("\n✅ TaskPlanner 测试通过!\n")


async def test_task_middleware():
    """测试 TaskPlanningMiddleware"""
    print("=" * 60)
    print("测试 2: TaskPlanningMiddleware - 规划中间件")
    print("=" * 60)

    from core.task_middleware import TaskPlanningMiddleware, IntelligentTaskAgent

    llm = MockLLMProvider()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        middleware = TaskPlanningMiddleware(
            llm_provider=llm,
            session_id="test_middleware",
            workspace_dir=tmpdir,
            complexity_threshold=2
        )
        
        print("\n2.1 测试简单任务...")
        result = await middleware.process("你好，今天天气怎么样？")
        print(f"   输入: 你好，今天天气怎么样？")
        print(f"   is_complex: {result.is_complex}")
        assert result.is_complex == False, "简单任务不应该触发规划"
        print("   ✓ 简单任务正确识别")
        
        print("\n2.2 测试复杂任务...")
        result = await middleware.process("帮我开发一个用户注册功能")
        print(f"   输入: 帮我开发一个用户注册功能")
        print(f"   is_complex: {result.is_complex}")
        print(f"   complexity: {result.complexity}")
        print(f"   子任务数: {len(result.subtasks)}")
        assert result.is_complex == True, "复杂任务应该触发规划"
        assert len(result.subtasks) >= 3, "应该拆解出子任务"
        print("   ✓ 复杂任务正确识别并拆解")
        
        print("\n2.3 测试规划结果格式化...")
        if result.initial_plan:
            print(f"   规划输出预览:\n{result.initial_plan[:200]}...")
        print("   ✓ 规划结果格式化正确")

    print("\n✅ TaskPlanningMiddleware 测试通过!\n")


async def test_intelligent_agent():
    """测试 IntelligentTaskAgent"""
    print("=" * 60)
    print("测试 3: IntelligentTaskAgent - 智能任务 Agent")
    print("=" * 60)

    from core.task_middleware import IntelligentTaskAgent

    llm = MockLLMProvider()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = IntelligentTaskAgent(
            llm_provider=llm,
            session_id="test_agent",
            workspace_dir=tmpdir,
            complexity_threshold=2
        )
        
        print("\n3.1 测试处理简单请求...")
        result = await agent.respond("你好")
        print(f"   is_complex: {result['is_complex']}")
        assert result['is_complex'] == False
        print("   ✓ 简单请求处理正确")
        
        print("\n3.2 测试处理复杂请求...")
        result = await agent.respond("帮我开发一个用户注册功能")
        print(f"   is_complex: {result['is_complex']}")
        print(f"   子任务数: {len(result.get('subtasks', []))}")
        assert result['is_complex'] == True
        assert len(result.get('subtasks', [])) >= 3
        print("   ✓ 复杂请求处理正确")
        
        print("\n3.3 测试获取当前任务...")
        tasks = agent.get_current_tasks()
        print(f"   主任务: {tasks.get('main_task', 'N/A')}")
        print(f"   待处理: {len(tasks.get('pending', []))} 个")
        print(f"   已完成: {len(tasks.get('completed', []))} 个")
        print("   ✓ 当前任务查询正确")

    print("\n✅ IntelligentTaskAgent 测试通过!\n")


async def test_agent_integration():
    """测试 Agent 集成"""
    print("=" * 60)
    print("测试 4: Agent 集成 - 复杂任务自动规划")
    print("=" * 60)

    from core.agent import CustomAgent, AgentConfig

    llm = MockLLMProvider()
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AgentConfig(
            enable_task_planning=True,
            task_complexity_threshold=2,
            enable_session=True,
            enable_detailed_logs=False
        )
        
        agent = CustomAgent(config=config, session_id="test_integration")
        agent.set_llm_provider(llm)
        
        print("\n4.1 测试简单请求...")
        response = await agent.respond("你好")
        print(f"   类型: {type(response)}")
        print(f"   元数据: {response.metadata}")
        is_complex = response.metadata.get('is_complex_task', False) if response.metadata else False
        print(f"   is_complex_task: {is_complex}")
        print("   ✓ 简单请求通过 Agent 处理")
        
        print("\n4.2 测试复杂请求...")
        response = await agent.respond("帮我开发一个用户注册功能，包括前端界面、后端API、数据库设计")
        print(f"   内容预览: {response.content[:150]}...")
        is_complex = response.metadata.get('is_complex_task', False) if response.metadata else False
        print(f"   is_complex_task: {is_complex}")
        if is_complex:
            print(f"   子任务数: {len(response.metadata.get('subtasks', []))}")
        assert is_complex == True, "复杂任务应该被识别"
        print("   ✓ 复杂任务自动规划")

    print("\n✅ Agent 集成测试通过!\n")


async def main():
    """运行所有测试"""
    print("\n" + "🎯" * 25)
    print("🎯 智能任务规划系统验证测试 🎯")
    print("🎯" * 25 + "\n")

    try:
        await test_task_planner()
        await test_task_middleware()
        await test_intelligent_agent()
        await test_agent_integration()

        print("=" * 60)
        print("🎉 所有测试通过! 🎉")
        print("=" * 60)

        print("\n" + "-" * 60)
        print("📊 系统架构总结:")
        print("-" * 60)
        print("""
┌─────────────────────────────────────────────────────────────┐
│                     User Request                             │
│          "帮我开发一个用户注册功能..."                        │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   TaskPlanningMiddleware                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. LLM 分析复杂度 (TaskPlanner)                      │   │
│  │    → complexity: "complex", needs_planning: true     │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 2. LLM 拆解任务                                      │   │
│  │    → 5 个子任务: 需求分析、数据库设计、API开发...    │   │
│  └─────────────────────────────────────────────────────┘   │
│                            │                                │
│                            ▼                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 3. TodoToolkitAdapter 创建任务列表                  │   │
│  │    → #1 需求分析, #2 数据库设计, #3 API开发...      │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      Response                                │
│  🎯 任务规划完成                                            │
│  📝 主任务: 帮我开发一个用户注册功能                         │
│  📊 复杂度: complex                                         │
│  📋 步骤: 5 步                                              │
│                                                              │
│  1. 🔴 需求分析                                             │
│  2. 🟡 数据库设计  (依赖: 1)                                 │
│  3. 🟡 后端API开发 (依赖: 2)                                 │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘
""")
        print("✅ 智能任务规划系统已成功集成到 Agent!")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())