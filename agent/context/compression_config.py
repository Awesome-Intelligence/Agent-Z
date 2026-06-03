# 🧠 Decision - 📊 Context - 上下文压缩配置

"""
Compression Config - 上下文压缩配置模块

提供压缩功能的配置管理：
1. 从配置文件加载压缩设置
2. 默认压缩设置
3. 配置文件 schema

Usage:
    from agent.context.compression_config import CompressionConfig, get_config

    config = CompressionConfig.from_env()
    compressor = ContextCompressor(
        model=config.model,
        threshold_percent=config.threshold_percent,
        ...
    )
"""

import os
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__, sublayer="context")


@dataclass
class CompressionConfig:
    """
    上下文压缩配置

    属性：
        enabled: 是否启用压缩
        threshold_percent: 触发压缩的阈值百分比 (0.0-1.0)
        protect_first_n: 保护前 N 条消息
        protect_last_n: 保护最近 N 条消息
        summary_target_ratio: 摘要目标 token 比例
        summary_model: 摘要模型（留空使用主模型）
        auto_compress: 是否自动压缩
        abort_on_summary_failure: 摘要失败时中止
        max_snapshots: 最大快照数（用于回滚）
        max_total_size_mb: 最大总大小 MB
    """

    enabled: bool = True
    threshold_percent: float = 0.50
    protect_first_n: int = 3
    protect_last_n: int = 10
    summary_target_ratio: float = 0.20
    summary_model: str = ""
    base_url: str = ""
    api_key: str = ""
    provider: str = ""
    auto_compress: bool = True
    abort_on_summary_failure: bool = False
    max_snapshots: int = 20
    max_total_size_mb: int = 500
    max_file_size_mb: int = 10
    quiet_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "enabled": self.enabled,
            "threshold_percent": self.threshold_percent,
            "protect_first_n": self.protect_first_n,
            "protect_last_n": self.protect_last_n,
            "summary_target_ratio": self.summary_target_ratio,
            "summary_model": self.summary_model,
            "base_url": self.base_url,
            "api_key": "[REDACTED]" if self.api_key else "",
            "provider": self.provider,
            "auto_compress": self.auto_compress,
            "abort_on_summary_failure": self.abort_on_summary_failure,
            "max_snapshots": self.max_snapshots,
            "max_total_size_mb": self.max_total_size_mb,
            "max_file_size_mb": self.max_file_size_mb,
            "quiet_mode": self.quiet_mode,
        }

    @classmethod
    def from_env(cls) -> "CompressionConfig":
        """从环境变量加载配置"""
        return cls(
            enabled=_env_bool("HANDSOME_COMPRESSION_ENABLED", True),
            threshold_percent=_env_float("HANDSOME_COMPRESSION_THRESHOLD", 0.50),
            protect_first_n=_env_int("HANDSOME_COMPRESSION_PROTECT_FIRST", 3),
            protect_last_n=_env_int("HANDSOME_COMPRESSION_PROTECT_LAST", 10),
            summary_target_ratio=_env_float("HANDSOME_COMPRESSION_SUMMARY_RATIO", 0.20),
            summary_model=_env_str("HANDSOME_COMPRESSION_MODEL", ""),
            base_url=_env_str("HANDSOME_COMPRESSION_BASE_URL", ""),
            api_key=_env_str("HANDSOME_COMPRESSION_API_KEY", ""),
            provider=_env_str("HANDSOME_COMPRESSION_PROVIDER", ""),
            auto_compress=_env_bool("HANDSOME_COMPRESSION_AUTO", True),
            abort_on_summary_failure=_env_bool("HANDSOME_COMPRESSION_ABORT_ON_FAILURE", False),
            max_snapshots=_env_int("HANDSOME_COMPRESSION_MAX_SNAPSHOTS", 20),
            max_total_size_mb=_env_int("HANDSOME_COMPRESSION_MAX_SIZE_MB", 500),
            max_file_size_mb=_env_int("HANDSOME_COMPRESSION_MAX_FILE_MB", 10),
            quiet_mode=_env_bool("HANDSOME_COMPRESSION_QUIET", False),
        )

    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> "CompressionConfig":
        """从字典加载配置"""
        return cls(
            enabled=config.get("enabled", True),
            threshold_percent=config.get("threshold_percent", 0.50),
            protect_first_n=config.get("protect_first_n", 3),
            protect_last_n=config.get("protect_last_n", 10),
            summary_target_ratio=config.get("summary_target_ratio", 0.20),
            summary_model=config.get("summary_model", ""),
            base_url=config.get("base_url", ""),
            api_key=config.get("api_key", ""),
            provider=config.get("provider", ""),
            auto_compress=config.get("auto_compress", True),
            abort_on_summary_failure=config.get("abort_on_summary_failure", False),
            max_snapshots=config.get("max_snapshots", 20),
            max_total_size_mb=config.get("max_total_size_mb", 500),
            max_file_size_mb=config.get("max_file_size_mb", 10),
            quiet_mode=config.get("quiet_mode", False),
        )

    def validate(self) -> Optional[str]:
        """验证配置有效性"""
        if not 0.0 < self.threshold_percent <= 1.0:
            return f"threshold_percent must be between 0.0 and 1.0, got {self.threshold_percent}"

        if not 0.0 < self.summary_target_ratio <= 1.0:
            return f"summary_target_ratio must be between 0.0 and 1.0, got {self.summary_target_ratio}"

        if self.protect_first_n < 0:
            return f"protect_first_n must be non-negative, got {self.protect_first_n}"

        if self.protect_last_n < 0:
            return f"protect_last_n must be non-negative, got {self.protect_last_n}"

        return None


def _env_bool(key: str, default: bool) -> bool:
    """从环境变量获取布尔值"""
    value = os.getenv(key, "").lower()
    if not value:
        return default
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    return default


def _env_int(key: str, default: int) -> int:
    """从环境变量获取整数值"""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    """从环境变量获取浮点值"""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_str(key: str, default: str) -> str:
    """从环境变量获取字符串值"""
    return os.getenv(key, default)


COMPRESSION_ENV_VARS = {
    "HANDSOME_COMPRESSION_ENABLED": "启用压缩 (default: true)",
    "HANDSOME_COMPRESSION_THRESHOLD": "压缩阈值百分比 (default: 0.50)",
    "HANDSOME_COMPRESSION_PROTECT_FIRST": "保护前 N 条消息 (default: 3)",
    "HANDSOME_COMPRESSION_PROTECT_LAST": "保护最近 N 条消息 (default: 10)",
    "HANDSOME_COMPRESSION_SUMMARY_RATIO": "摘要目标比例 (default: 0.20)",
    "HANDSOME_COMPRESSION_MODEL": "摘要专用模型 (default: 使用主模型)",
    "HANDSOME_COMPRESSION_AUTO": "自动压缩 (default: true)",
    "HANDSOME_COMPRESSION_ABORT_ON_FAILURE": "摘要失败时中止 (default: false)",
    "HANDSOME_COMPRESSION_QUIET": "静默模式 (default: false)",
}


def get_config_help() -> str:
    """获取配置帮助信息"""
    lines = [
        "Context Compression Configuration:",
        "",
        "Environment Variables:",
    ]
    for var, desc in COMPRESSION_ENV_VARS.items():
        lines.append(f"  {var}: {desc}")
    return "\n".join(lines)


_global_config: Optional[CompressionConfig] = None


def get_config() -> CompressionConfig:
    """获取全局压缩配置"""
    global _global_config
    if _global_config is None:
        _global_config = CompressionConfig.from_env()
    return _global_config


def set_config(config: CompressionConfig) -> None:
    """设置全局压缩配置"""
    global _global_config
    _global_config = config


__all__ = [
    "CompressionConfig",
    "get_config",
    "set_config",
    "get_config_help",
]