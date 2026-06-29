#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一的数据类型定义 - Curator 模块共享类型

此文件定义了 curator 模块中多个文件需要使用的共享数据类型，
避免重复定义导致的不一致问题。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class EvaluationResult(str, Enum):
    """评估结果枚举"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass
class EvaluationReport:
    """评估报告 - 用于记录轨迹评估结果"""
    trajectory_id: str
    overall_result: EvaluationResult
    success_rate: float
    steps: List["EvaluationStep"]  # 使用字符串引用避免循环导入
    suggestions: List[str]
    metrics: Dict[str, Any]
    created_at: str = field(default_factory=lambda: "")


@dataclass
class EvaluationStep:
    """评估步骤 - 用于评估过程中的步骤记录

    与 TrajectoryStep 不同，EvaluationStep 是评估器内部使用的数据结构，
    记录评估时的详细信息。
    """
    step_id: int
    thought: str
    action: str
    observation: str
    result: str
    success: bool


# 同步 EvaluationReport 中的 steps 类型注解
EvaluationReport.__annotations__["steps"] = List[EvaluationStep]


@dataclass
class SynthesizedSkill:
    """合成的技能 - 存储从轨迹中提取的可复用技能"""
    name: str
    description: str
    trigger_patterns: List[str]
    action_template: str
    confidence: float
    source_trajectory: str = ""
    quality_score: float = 0.0
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: "")


# 向后兼容别名
TrajectoryStep = EvaluationStep


__all__ = [
    "EvaluationResult",
    "EvaluationReport",
    "EvaluationStep",
    "EvaluationStep",  # 别名也导出
    "SynthesizedSkill",
    "TrajectoryStep",  # 向后兼容别名
]