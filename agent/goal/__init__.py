#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Goal Manager Module

参考 Hermes 的 Ralph loop，实现目标管理功能：
1. 用户发起复杂任务 → 创建 Goal
2. Agent 循环每轮执行完成后 → 调用 Judge 判断
3. Judge 认为未完成 → 生成 Continuation Prompt → 继续
4. Judge 认为完成 / 轮次耗尽 → 结束
"""

from .models import JudgeVerdict, GoalState, GoalStatus
from .manager import GoalManager

__all__ = [
    "GoalManager",
    "GoalState",
    "GoalStatus",
    "JudgeVerdict",
]