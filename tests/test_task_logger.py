#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task Logger 演示脚本

展示任务规划和执行的直观可视化输出
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.task_logger import TaskLogger, TaskTreeLogger, LogStyle


def demo_basic_tree():
    """演示基础树形结构"""
    print("\n" + "=" * 60)
    print("演示 1: 基础树形任务列表")
    print("=" * 60 + "\n")
    
    tree = TaskTreeLogger("开发用户注册功能")
    
    tree.add_task(1, "需求分析", [])
    tree.add_task(2, "数据库设计", [1])
    tree.add_task(3, "后端API开发", [2])
    tree.add_task(4, "前端表单开发", [3])
    tree.add_task(5, "单元测试", [3])
    tree.add_task(6, "集成测试", [4, 5])
    
    tree.update_task_status(1, "completed", "已完成需求文档")
    tree.update_task_status(2, "completed", "设计了用户表结构")
    tree.update_task_status(3, "running")
    tree.update_task_status(4, "pending")
    tree.update_task_status(5, "pending")
    tree.update_task_status(6, "pending")
    
    print(tree.render())


def demo_progress_bar():
    """演示进度条"""
    print("\n" + "=" * 60)
    print("演示 2: 进度条显示")
    print("=" * 60 + "\n")
    
    tree = TaskTreeLogger()
    
    for i in range(1, 6):
        tree.add_task(i, f"任务 {i}")
    
    print("进度变化演示:")
    print("-" * 40)
    
    tree.update_task_status(1, "completed")
    print(f"完成 1/5: {tree._render_progress_bar(1, 5)}")
    
    tree.update_task_status(2, "completed")
    print(f"完成 2/5: {tree._render_progress_bar(2, 5)}")
    
    tree.update_task_status(3, "running")
    print(f"完成 2/5: {tree._render_progress_bar(2, 5)} (正在执行任务3)")
    
    for i in range(4, 6):
        tree.update_task_status(i, "completed")
    print(f"完成 5/5: {tree._render_progress_bar(5, 5)}")


def demo_task_logger():
    """演示完整的任务日志器"""
    print("\n" + "=" * 60)
    print("演示 3: 完整任务日志流程")
    print("=" * 60 + "\n")
    
    logger = TaskLogger("DemoLogger")
    
    print(logger.plan_start("帮我开发一个用户注册功能，包括前端、后端、数据库"))
    
    subtasks = [
        {"id": 1, "title": "需求分析", "depends_on": []},
        {"id": 2, "title": "数据库设计", "depends_on": [1]},
        {"id": 3, "title": "后端API开发", "depends_on": [2]},
        {"id": 4, "title": "前端表单开发", "depends_on": [3]},
        {"id": 5, "title": "测试验证", "depends_on": [4]},
    ]
    
    print(logger.plan_complete("complex", subtasks, "从分析到测试的完整开发流程"))
    
    print(logger.execute_start(1, 5, "需求分析"))
    print(logger.execute_complete(1, "需求分析", "输出了需求文档"))
    
    print(logger.execute_start(2, 5, "数据库设计"))
    print(logger.execute_complete(2, "数据库设计", "设计了 users 表"))
    
    print(logger.execute_start(3, 5, "后端API开发"))
    print(logger.execute_complete(3, "后端API开发", "实现了注册和登录接口"))
    
    print(logger.final_summary())


def demo_execution_flow():
    """演示执行流程"""
    print("\n" + "=" * 60)
    print("演示 4: 实时执行流程")
    print("=" * 60 + "\n")
    
    logger = TaskLogger("ExecutionDemo")
    
    subtasks = [
        {"id": 1, "title": "环境搭建", "depends_on": []},
        {"id": 2, "title": "代码编写", "depends_on": [1]},
        {"id": 3, "title": "功能测试", "depends_on": [2]},
        {"id": 4, "title": "部署上线", "depends_on": [3]},
    ]
    
    print(logger.plan_start("完成项目交付"))
    print(logger.plan_complete("moderate", subtasks, "项目四阶段交付"))
    
    for i, task in enumerate(subtasks):
        print(logger.execute_start(task['id'], len(subtasks), task['title']))
        
        if task['id'] == 3:
            print(logger.execute_failed(task['id'], task['title'], "测试环境连接超时"))
        else:
            print(logger.execute_complete(task['id'], task['title'], f"第{i+1}步完成"))
    
    print(logger.final_summary())


def demo_colors():
    """演示颜色输出"""
    print("\n" + "=" * 60)
    print("演示 5: 状态颜色")
    print("=" * 60 + "\n")
    
    statuses = ['pending', 'running', 'completed', 'failed']
    
    print("任务状态颜色:")
    print("-" * 40)
    
    for status in statuses:
        color = {
            'pending': LogStyle.GRAY,
            'running': LogStyle.CYAN,
            'completed': LogStyle.GREEN,
            'failed': LogStyle.RED,
        }[status]
        
        icon = {
            'pending': '⏳',
            'running': '🔄',
            'completed': '✅',
            'failed': '❌',
        }[status]
        
        print(f"{color.value}{icon} {status.upper():12} {LogStyle.RESET.value}", end="  ")
    
    print("\n")


if __name__ == "__main__":
    print("\n" + "🎯" * 30)
    print("🎯 任务可视化日志系统演示 🎯")
    print("🎯" * 30)
    
    demo_colors()
    demo_basic_tree()
    demo_progress_bar()
    demo_task_logger()
    demo_execution_flow()
    
    print("\n" + "🎉" * 30)
    print("🎉 演示完成! 🎉")
    print("🎉" * 30 + "\n")