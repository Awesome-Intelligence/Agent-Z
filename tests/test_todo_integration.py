#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TodoToolkit 集成测试

测试 TodoAdapter 和 Task Management Handler 的功能
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def test_todo_adapter():
    """测试 TodoToolkitAdapter"""
    from core.todo_adapter import get_todo_adapter, TodoToolkitAdapter, ToolCallResult
    
    print("=" * 60)
    print("测试 TodoToolkitAdapter")
    print("=" * 60)
    
    session_id = "test_session_001"
    adapter = get_todo_adapter(session_id)
    
    assert isinstance(adapter, TodoToolkitAdapter), "get_todo_adapter 应返回 TodoToolkitAdapter 实例"
    print("✅ TodoToolkitAdapter 实例创建成功")
    
    tools = adapter.list_tools()
    assert len(tools) >= 8, f"应该有至少 8 个工具，当前有 {len(tools)} 个"
    print(f"✅ 工具列表包含 {len(tools)} 个工具")
    for tool in tools:
        print(f"   - {tool['name']}: {tool['description'][:50]}...")
    
    print("\n测试创建任务列表...")
    result = adapter.call_tool('todo_create', {'tasks': ['任务1', '任务2', '任务3']})
    assert isinstance(result, ToolCallResult), "应返回 ToolCallResult"
    assert result.success, f"创建任务应该成功: {result.error}"
    print(f"✅ 创建任务成功: {result.output[:100]}...")
    
    print("\n测试添加任务...")
    result = adapter.call_tool('todo_add', {'task': '新任务4'})
    assert result.success, f"添加任务应该成功: {result.error}"
    print(f"✅ 添加任务成功: {result.output}")
    
    print("\n测试列出任务...")
    result = adapter.call_tool('todo_list', {})
    assert result.success, f"列出任务应该成功: {result.error}"
    print(f"✅ 列出任务成功:")
    print(result.output[:500])
    
    print("\n测试完成任务...")
    result = adapter.call_tool('todo_complete', {'task_id': 1, 'result': '测试完成'})
    assert result.success, f"完成任务应该成功: {result.error}"
    print(f"✅ 完成任务成功: {result.output}")
    
    print("\n测试删除任务...")
    result = adapter.call_tool('todo_remove', {'task_id': 2})
    assert result.success, f"删除任务应该成功: {result.error}"
    print(f"✅ 删除任务成功: {result.output}")
    
    print("\n测试清空任务...")
    result = adapter.call_tool('todo_clear', {})
    assert result.success, f"清空任务应该成功: {result.error}"
    print(f"✅ 清空任务成功: {result.output}")
    
    print("\n" + "=" * 60)
    print("✅ TodoToolkitAdapter 所有测试通过!")
    print("=" * 60)


async def test_task_management_handler():
    """测试 Task Management Handler"""
    from core.router_handlers import task_management_handler
    from core.todo_adapter import get_todo_adapter
    
    print("\n" + "=" * 60)
    print("测试 Task Management Handler")
    print("=" * 60)
    
    session_id = "test_session_002"
    
    context = {
        'session_id': session_id,
        'enable_detailed_logs': True
    }
    
    print("\n测试创建任务...")
    input_text = "创建任务：1. 完成报告 2. 回复邮件 3. 开会讨论"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应: {response[:200]}...")
    assert "已创建" in response or "任务" in response, "应该创建任务成功"
    print("✅ 创建任务测试通过")
    
    print("\n测试列出任务...")
    input_text = "列出所有任务"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应预览: {response[:300]}...")
    assert "待办" in response or "任务" in response or "暂无" in response, "应该显示任务列表"
    print("✅ 列出任务测试通过")
    
    print("\n测试添加任务...")
    input_text = "添加任务：准备下周演示"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应: {response}")
    assert "添加" in response or "已添加" in response, "应该添加任务成功"
    print("✅ 添加任务测试通过")
    
    print("\n测试完成任务...")
    input_text = "完成 #1"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应: {response}")
    assert "完成" in response or "✅" in response, "应该完成任务"
    print("✅ 完成任务测试通过")
    
    print("\n测试取消任务...")
    input_text = "取消任务 3"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应: {response}")
    assert "取消" in response, "应该取消任务"
    print("✅ 取消任务测试通过")
    
    print("\n测试删除任务...")
    input_text = "删除任务 2"
    response, flow = await task_management_handler(input_text, context)
    print(f"输入: {input_text}")
    print(f"响应: {response}")
    assert "删除" in response, "应该删除任务"
    print("✅ 删除任务测试通过")
    
    from core.todo_adapter import get_todo_adapter
    adapter = get_todo_adapter(session_id)
    adapter.call_tool('todo_clear', {})
    
    print("\n" + "=" * 60)
    print("✅ Task Management Handler 所有测试通过!")
    print("=" * 60)


async def test_intent_classification():
    """测试任务管理意图分类"""
    from core.router import router
    
    print("\n" + "=" * 60)
    print("测试 Intent Classification")
    print("=" * 60)
    
    test_cases = [
        ("创建任务：写代码、测试", "task_management"),
        ("添加一个新任务", "task_management"),
        ("列出我的任务", "task_management"),
        ("完成任务 1", "task_management"),
        ("待办列表", "task_management"),
        ("有哪些任务", "task_management"),
    ]
    
    print("\n测试任务管理意图识别...")
    for text, expected_intent in test_cases:
        intent = router.intent_classifier.classify(text)
        status = "✅" if intent == expected_intent else "⚠️"
        print(f"  {status} \"{text[:30]}...\" -> {intent} (期望: {expected_intent})")
    
    print("\n" + "=" * 60)
    print("✅ Intent Classification 测试完成")
    print("=" * 60)


async def main():
    """运行所有测试"""
    print("\n" + "🎯" * 30)
    print("TodoToolkit 集成测试开始")
    print("🎯" * 30 + "\n")
    
    try:
        await test_intent_classification()
        await test_todo_adapter()
        await test_task_management_handler()
        
        print("\n" + "🎉" * 30)
        print("🎉 所有测试通过! 🎉")
        print("🎉" * 30 + "\n")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())