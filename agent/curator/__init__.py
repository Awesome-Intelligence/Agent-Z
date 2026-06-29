"""brain.curator - 后处理层模块

统一导出：
- EvaluationResult: 评估结果枚举
- EvaluationReport: 评估报告
- EvaluationStep: 评估步骤（用于评估器内部）
- SynthesizedSkill: 合成的技能
- TrajectoryStatus: 轨迹状态枚举
- Trajectory: 完整轨迹数据
- TrajectoryStep: 评估步骤别名（向后兼容）
- ExecutionStep: 执行步骤（用于轨迹持久化）
- TrajectoryManager: 轨迹管理器
- SkillSynthesizer: 技能合成器
- SkillWriter: 技能写入器
- Curator: 自我进化核心
- CuratorState: Curator 状态管理
"""

from .types import (
    EvaluationResult,
    EvaluationReport,
    EvaluationStep,
    SynthesizedSkill,
    TrajectoryStep,  # 向后兼容别名
)
from .trajectory import (
    TrajectoryStatus,
    Trajectory,
    TrajectoryManager,
    ExecutionStep,
    TrajectoryStep as ExecutionTrajectoryStep,  # 向后兼容别名
)
from .synthesizer import SkillSynthesizer
from .writer import SkillWriter
from .curator import Curator, CuratorState, get_curator


__all__ = [
    # 类型定义
    "EvaluationResult",
    "EvaluationReport",
    "EvaluationStep",
    "SynthesizedSkill",
    # 轨迹相关
    "TrajectoryStatus",
    "Trajectory",
    "TrajectoryManager",
    "ExecutionStep",
    "TrajectoryStep",  # 向后兼容别名
    # 合成
    "SkillSynthesizer",
    "SkillWriter",
    # 核心
    "Curator",
    "CuratorState",
    "get_curator",
]
