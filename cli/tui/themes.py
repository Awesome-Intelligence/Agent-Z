#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Textual Theme System for Handsome Agent.

🚪 Access - 💬 CLI - Textual UI - 主题系统

基于 Textual CSS 的主题系统，支持：
- 四套预设主题（default/ares/mono/slate）
- 动态主题切换
- 与皮肤引擎（skin_engine.py）保持兼容
- i18n 主题名称
- 用户主题偏好持久化

预设主题：

| 主题 ID | 名称 | 主色 |
|---------|------|------|
| default | 牛油果绿 | #8B9A46 |
| ares | 战争之神 | #8B4513 |
| mono | 灰度单色 | #666666 |
| slate | 酷蓝开发者 | #607D8B |

Usage::

    from cli.tui.themes import ThemeManager, get_theme_manager

    manager = get_theme_manager()
    manager.set_theme("slate")
    css = manager.get_current_css()
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

# i18n 支持
try:
    from common.i18n import get_i18n, t
except ImportError:
    def get_i18n():
        class SimpleI18n:
            def t(self, key, default=None, **kwargs):
                return default or key
        return SimpleI18n()
    def t(key, default=None, **kwargs):
        return default or key

# 日志支持
try:
    from common.logging_manager import get_access_logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    def get_access_logger(*args, **kwargs):
        return logging.getLogger("HandsomeAgent")

logger = logging.getLogger(__name__)

# ============================================================================
# Theme Data Structure
# ============================================================================


@dataclass
class Theme:
    """Textual 主题配置数据类.
    
    Attributes:
        theme_id: 主题唯一标识符
        display_name_key: i18n 键，用于显示主题名称
        colors: CSS 变量名到颜色值的映射
        transparency: 透明度配置 (0.0 完全透明 - 1.0 完全不透明)
    """
    theme_id: str
    display_name_key: str
    colors: Dict[str, str] = field(default_factory=dict)
    transparency: float = 1.0  # 默认不透明


# ============================================================================
# Preset Themes
# ============================================================================


def _create_default_theme() -> Theme:
    """创建牛油果绿主题 (Avocado Green)."""
    return Theme(
        theme_id="default",
        display_name_key="tui.theme.default.name",
        colors={
            # 基础颜色
            "--primary": "#8B9A46",
            "--primary-bright": "#A0B45A",
            "--primary-dim": "#647030",
            "--primary-dark": "#465A1E",
            # 文字颜色
            "--text": "#FFFFFF",
            "--text-dim": "#888888",
            "--text-accent": "#A0B45A",
            # 背景颜色
            "--background": "#465A1E",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "--border": "#647030",
            "--border-light": "#8B9A46",
            "--border-accent": "#A0B45A",
            # UI 状态颜色
            "--success": "#4CAF50",
            "--warning": "#FF9800",
            "--error": "#F44336",
            "--info": "#2196F3",
        },
        transparency=1.0,
    )


def _create_ares_theme() -> Theme:
    """创建战争之神主题 (Ares - Crimson/Bronze)."""
    return Theme(
        theme_id="ares",
        display_name_key="tui.theme.ares.name",
        colors={
            # 基础颜色
            "--primary": "#CD7F32",
            "--primary-bright": "#FFD700",
            "--primary-dim": "#B8860B",
            "--primary-dark": "#8B4513",
            # 文字颜色
            "--text": "#FFF8DC",
            "--text-dim": "#B8860B",
            "--text-accent": "#FFD700",
            # 背景颜色
            "--background": "#8B4513",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "--border": "#B8860B",
            "--border-light": "#CD7F32",
            "--border-accent": "#FFD700",
            # UI 状态颜色
            "--success": "#4CAF50",
            "--warning": "#FFA726",
            "--error": "#EF5350",
            "--info": "#64B5F6",
        },
        transparency=1.0,
    )


def _create_mono_theme() -> Theme:
    """创建灰度单色主题 (Monochrome)."""
    return Theme(
        theme_id="mono",
        display_name_key="tui.theme.mono.name",
        colors={
            # 基础颜色
            "--primary": "#808080",
            "--primary-bright": "#FFFFFF",
            "--primary-dim": "#666666",
            "--primary-dark": "#404040",
            # 文字颜色
            "--text": "#CCCCCC",
            "--text-dim": "#666666",
            "--text-accent": "#FFFFFF",
            # 背景颜色
            "--background": "#1a1a1a",
            "--surface": "#1a1a1a",
            "--surface-light": "#2a2a2a",
            # 边框颜色
            "--border": "#404040",
            "--border-light": "#666666",
            "--border-accent": "#808080",
            # UI 状态颜色
            "--success": "#888888",
            "--warning": "#AAAAAA",
            "--error": "#CCCCCC",
            "--info": "#999999",
        },
        transparency=1.0,
    )


def _create_slate_theme() -> Theme:
    """创建酷蓝开发者主题 (Slate - Cool Blue)."""
    return Theme(
        theme_id="slate",
        display_name_key="tui.theme.slate.name",
        colors={
            # 基础颜色
            "--primary": "#607D8B",
            "--primary-bright": "#90CAF9",
            "--primary-dim": "#455A64",
            "--primary-dark": "#37474F",
            # 文字颜色
            "--text": "#E0E7FF",
            "--text-dim": "#94A3B8",
            "--text-accent": "#60A5FA",
            # 背景颜色
            "--background": "#37474F",
            "--surface": "#0F172A",
            "--surface-light": "#1E293B",
            # 边框颜色
            "--border": "#475569",
            "--border-light": "#607D8B",
            "--border-accent": "#90CAF9",
            # UI 状态颜色
            "--success": "#4ADE80",
            "--warning": "#FBBF24",
            "--error": "#F87171",
            "--info": "#38BDF8",
        },
        transparency=1.0,
    )


# 预设主题注册表
_PRESET_THEMES: Dict[str, Theme] = {
    "default": _create_default_theme(),
    "ares": _create_ares_theme(),
    "mono": _create_mono_theme(),
    "slate": _create_slate_theme(),
}


# ============================================================================
# 透明度等级常量
# ============================================================================

TRANSPARENCY_LEVELS = {
    "xs": 0.05,  # 极淡 - 背景微变
    "sm": 0.10,  # 淡 - 悬停效果
    "md": 0.15,  # 中 - 选择状态
    "lg": 0.25,  # 重 - 次要强调
    "xl": 0.50,  # 浓 - 焦点指示
}


# ============================================================================
# 半透明颜色转换函数
# ============================================================================


def transparent(color: str, opacity: float) -> str:
    """将 hex 颜色转换为 rgba 格式。

    Args:
        color: hex 颜色字符串，如 "#8B9A46"
        opacity: 透明度，0.0-1.0

    Returns:
        rgba 格式字符串，如 "rgba(139, 154, 70, 0.5)"

    Examples:
        >>> transparent("#8B9A46", 0.5)
        'rgba(139, 154, 70, 0.5)'
        >>> transparent("#FF0000", 0.25)
        'rgba(255, 0, 0, 0.25)'
    """
    # 移除 # 号
    color = color.lstrip("#")

    # 支持 3 位和 6 位 hex 格式
    if len(color) == 3:
        color = "".join(c * 2 for c in color)

    # 解析 RGB 分量
    try:
        r = int(color[0:2], 16)
        g = int(color[2:4], 16)
        b = int(color[4:6], 16)
    except ValueError:
        # 如果解析失败，返回原始颜色
        logger.warning(f"Invalid hex color: #{color}, returning original")
        return color

    # 限制 opacity 范围
    opacity = max(0.0, min(1.0, opacity))

    return f"rgba({r}, {g}, {b}, {opacity})"


# ============================================================================
# ThemeConfig - 语义化主题配置
# ============================================================================


@dataclass
class ThemeConfig:
    """语义化主题配置数据类.
    
    用于定义主题的强调色和其他样式变量。
    颜色变量通过 CSS 类（.theme-avocado 等）应用。
    """
    name: str
    accent: str
    accent_bright: str
    accent_dim: str
    accent_dark: str


# 预设主题配置
THEME_CONFIGS: Dict[str, ThemeConfig] = {
    "default": ThemeConfig(
        name="Avocado Green",
        accent="#8B9A46",
        accent_bright="#A0B45A",
        accent_dim="#647030",
        accent_dark="#465A1E",
    ),
    "ares": ThemeConfig(
        name="War God",
        accent="#CD7F32",
        accent_bright="#E8A060",
        accent_dim="#A06028",
        accent_dark="#7A4520",
    ),
    "mono": ThemeConfig(
        name="Monochrome",
        accent="#808080",
        accent_bright="#A0A0A0",
        accent_dim="#606060",
        accent_dark="#404040",
    ),
    "slate": ThemeConfig(
        name="Cool Blue",
        accent="#607D8B",
        accent_bright="#78909C",
        accent_dim="#455A64",
        accent_dark="#37474F",
    ),
}


def generate_semantic_colors(theme: ThemeConfig) -> Dict[str, str]:
    """生成 CSS 语义化颜色变量.
    
    Args:
        theme: ThemeConfig 实例
        
    Returns:
        CSS 变量名到颜色值的映射字典
    """
    return {
        "--accent": theme.accent,
        "--accent-bright": theme.accent_bright,
        "--accent-dim": theme.accent_dim,
        "--accent-dark": theme.accent_dark,
    }


def generate_theme_css(theme_id: str) -> str:
    """生成主题覆盖类 CSS 字符串.
    
    Args:
        theme_id: 主题 ID (default/ares/mono/slate)
        
    Returns:
        主题 CSS 类定义字符串
    """
    theme = THEME_CONFIGS.get(theme_id, THEME_CONFIGS["default"])
    colors = generate_semantic_colors(theme)
    css_parts = [f".theme-{theme_id} {{"]
    for var, value in colors.items():
        css_parts.append(f"    {var}: {value};")
    css_parts.append("}")
    return "\n".join(css_parts)


def get_all_theme_css() -> str:
    """生成所有主题的 CSS 字符串.
    
    Returns:
        所有主题 CSS 类定义的组合字符串
    """
    return "\n\n".join(generate_theme_css(tid) for tid in THEME_CONFIGS)


# ============================================================================
# 基础颜色常量（保持向后兼容）
# ============================================================================

# 状态颜色
STATUS_ONLINE = "#3fb950"
STATUS_BUSY = "#f0883e"
STATUS_AWAY = "#f0883e"
STATUS_OFFLINE = "#8b949e"
STATUS_ERROR = "#f85149"
STATUS_SUCCESS = "#3fb950"
STATUS_WARNING = "#d29922"
STATUS_INFO = "#58a6ff"


# ============================================================================
# 半透明颜色变量
# ============================================================================

# 基于 AVOCADO 主题的半透明版本
AVOCADO_ACCENT_10 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["sm"])
AVOCADO_ACCENT_25 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["lg"])
AVOCADO_ACCENT_50 = transparent(THEME_CONFIGS["default"].accent, TRANSPARENCY_LEVELS["xl"])

# 状态色透明版本
STATUS_ONLINE_15 = transparent(STATUS_ONLINE, TRANSPARENCY_LEVELS["md"])
STATUS_BUSY_10 = transparent(STATUS_BUSY, TRANSPARENCY_LEVELS["sm"])
STATUS_ERROR_15 = transparent(STATUS_ERROR, TRANSPARENCY_LEVELS["md"])
STATUS_WARNING_15 = transparent(STATUS_WARNING, TRANSPARENCY_LEVELS["md"])
STATUS_INFO_15 = transparent(STATUS_INFO, TRANSPARENCY_LEVELS["md"])


# ============================================================================
# 消息类型图标和颜色
# ============================================================================

# 消息类型图标
MESSAGE_ICONS = {
    "USER": "🧑",
    "ASSISTANT": "🤖",
    "SYSTEM": "⚙️",
    "TOOL": "🔧",
    "ERROR": "❌",
    "THINKING": "💭",
    "APPROVAL": "✅",
}

# 消息类型颜色
MESSAGE_COLORS = {
    "USER": "#58a6ff",  # 蓝色
    "ASSISTANT": "#3fb950",  # 绿色
    "SYSTEM": "#8b949e",  # 灰色
    "TOOL": "#a371f7",  # 紫色
    "ERROR": "#f85149",  # 红色
    "THINKING": "#f0883e",  # 橙色
    "APPROVAL": "#3fb950",  # 绿色
}


# ============================================================================
# 文件类型图标
# ============================================================================

FILE_TYPE_ICONS = {
    ".py": "🐍",  # Python
    ".rs": "🦀",  # Rust
    ".js": "📜",  # JavaScript
    ".ts": "📘",  # TypeScript
    ".jsx": "⚛️",  # React JavaScript
    ".tsx": "⚛️",  # React TypeScript
    ".vue": "💚",  # Vue
    ".svelte": "🔥",  # Svelte
    ".go": "🐹",  # Go
    ".java": "☕",  # Java
    ".c": "©",  # C
    ".cpp": "➕",  # C++
    ".h": "📎",  # Header
    ".hpp": "📎",  # C++ Header
    ".cs": "🔷",  # C#
    ".rb": "💎",  # Ruby
    ".php": "🐘",  # PHP
    ".swift": "🦅",  # Swift
    ".kt": "🎯",  # Kotlin
    ".scala": "⚡",  # Scala
    ".md": "📝",  # Markdown
    ".txt": "📄",  # Text
    ".json": "📋",  # JSON
    ".yaml": "📄",  # YAML
    ".yml": "📄",  # YAML (short)
    ".toml": "⚙️",  # TOML
    ".xml": "📰",  # XML
    ".html": "🌐",  # HTML
    ".htm": "🌐",  # HTML (short)
    ".css": "🎨",  # CSS
    ".scss": "🎨",  # SCSS
    ".sass": "🎨",  # Sass
    ".less": "🎨",  # Less
    ".sql": "🗃️",  # SQL
    ".sh": "💻",  # Shell
    ".bash": "💻",  # Bash
    ".zsh": "💻",  # Zsh
    ".ps1": "🖥️",  # PowerShell
    ".bat": "🖥️",  # Batch
    ".dockerfile": "🐳",  # Docker
    ".gitignore": "📁",  # Git
    ".env": "🔐",  # Environment
    ".cfg": "⚙️",  # Config
    ".conf": "⚙️",  # Config
    ".ini": "⚙️",  # Config
    ".png": "🖼️",  # Image
    ".jpg": "🖼️",  # Image
    ".jpeg": "🖼️",  # Image
    ".gif": "🖼️",  # Image
    ".svg": "🖼️",  # Image
    ".ico": "🖼️",  # Image
    ".pdf": "📕",  # PDF
    ".zip": "📦",  # Archive
    ".tar": "📦",  # Archive
    ".gz": "📦",  # Archive
    ".rar": "📦",  # Archive
    ".7z": "📦",  # Archive
    ".mp3": "🎵",  # Audio
    ".wav": "🎵",  # Audio
    ".mp4": "🎬",  # Video
    ".mov": "🎬",  # Video
    ".avi": "🎬",  # Video
    ".exe": "⚡",  # Executable
    ".dll": "⚙️",  # Library
    ".so": "⚙️",  # Shared Object
    ".a": "📚",  # Static Library
    ".o": "📚",  # Object File
    ".default": "📄",  # 默认
}


def get_file_icon(filename: str) -> str:
    """根据文件名获取对应的图标.
    
    Args:
        filename: 文件名（可包含路径）
        
    Returns:
        对应的 Emoji 图标
    """
    from pathlib import Path
    _, ext = Path(filename).suffix.lower()
    return FILE_TYPE_ICONS.get(ext, FILE_TYPE_ICONS[".default"])


# ============================================================================
# 任务状态图标
# ============================================================================

TASK_STATUS_ICONS = {
    "todo": "📋",  # 待办
    "pending": "⏳",  # 等待中
    "in_progress": "🔄",  # 进行中
    "done": "✅",  # 完成
    "completed": "✅",  # 完成 (别名)
    "success": "✅",  # 成功
    "failed": "❌",  # 失败
    "error": "❌",  # 错误
    "blocked": "🚫",  # 阻塞
    "cancelled": "🚪",  # 取消
    "skipped": "⏭️",  # 跳过
}


# ============================================================================
# 任务优先级图标
# ============================================================================

TASK_PRIORITY_ICONS = {
    "urgent": "🔴",  # 紧急
    "high": "🟠",  # 高
    "medium": "🟡",  # 中
    "normal": "🟡",  # 正常
    "low": "🟢",  # 低
    "lowest": "⚪",  # 最低
}


# ============================================================================
# 日志级别图标
# ============================================================================

LOG_LEVEL_ICONS = {
    "DEBUG": "🐛",  # 调试
    "INFO": "ℹ️",  # 信息
    "WARNING": "⚠️",  # 警告
    "WARN": "⚠️",  # 警告 (别名)
    "ERROR": "❌",  # 错误
    "ERR": "❌",  # 错误 (别名)
    "CRITICAL": "☠️",  # 严重
    "FATAL": "💀",  # 致命
    "SUCCESS": "✅",  # 成功
    "VERBOSE": "📣",  # 详细
}


def get_log_icon(level: str) -> str:
    """根据日志级别获取对应的图标.
    
    Args:
        level: 日志级别字符串
        
    Returns:
        对应的 Emoji 图标
    """
    return LOG_LEVEL_ICONS.get(level.upper(), "ℹ️")


# ============================================================================
# Agent 状态图标
# ============================================================================

AGENT_STATUS_ICONS = {
    "idle": "🟢",  # 空闲
    "busy": "🟠",  # 忙碌
    "thinking": "💭",  # 思考中
    "working": "⚙️",  # 工作中
    "error": "🔴",  # 错误
    "offline": "⚫",  # 离线
    "connected": "🟢",  # 已连接
    "disconnected": "⚫",  # 已断开
    "loading": "⏳",  # 加载中
}


# ============================================================================
# 面板图标
# ============================================================================

PANEL_ICONS = {
    "file_tree": "📁",  # 文件树
    "tasks": "📋",  # 任务
    "agent": "🤖",  # Agent
    "logs": "📜",  # 日志
    "search": "🔍",  # 搜索
    "settings": "⚙️",  # 设置
    "help": "❓",  # 帮助
    "terminal": "💻",  # 终端
}


# ============================================================================
# Theme Manager
# ============================================================================


class ThemeManager:
    """Textual 主题管理器.
    
    负责：
    - 管理预设和自定义主题
    - 生成动态 CSS
    - 保存/加载用户主题偏好
    - 与皮肤引擎（skin_engine.py）保持兼容
    """

    _instance: Optional["ThemeManager"] = None

    def __init__(self):
        """初始化主题管理器."""
        self._current_theme_id: str = "default"
        self._custom_themes: Dict[str, Theme] = {}
        self._logger = get_access_logger("ThemeManager", sublayer="tui")
        self._transparency_enabled: bool = False  # 透明度开关
        self._transparency_level: float = 0.85  # 透明度级别 (0.0-1.0)
        
        # 从配置文件加载用户偏好
        self._load_preference()

    @classmethod
    def get_instance(cls) -> "ThemeManager":
        """获取单例实例."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def list_themes(self) -> list[Theme]:
        """列出所有可用的主题.
        
        Returns:
            主题列表（预设主题 + 自定义主题）
        """
        themes = list(_PRESET_THEMES.values())
        themes.extend(self._custom_themes.values())
        return themes

    def list_theme_ids(self) -> list[str]:
        """列出所有主题 ID.
        
        Returns:
            主题 ID 列表
        """
        ids = list(_PRESET_THEMES.keys())
        ids.extend(self._custom_themes.keys())
        return ids

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        """获取指定主题.
        
        Args:
            theme_id: 主题 ID
            
        Returns:
            主题对象，如果不存在则返回 None
        """
        # 优先检查预设主题
        if theme_id in _PRESET_THEMES:
            return _PRESET_THEMES[theme_id]
        # 检查自定义主题
        return self._custom_themes.get(theme_id)

    def get_current_theme(self) -> Theme:
        """获取当前激活的主题.
        
        Returns:
            当前主题对象
        """
        theme = self.get_theme(self._current_theme_id)
        if theme is None:
            # 回退到默认主题
            self._logger.warning(
                f"Theme '{self._current_theme_id}' not found, falling back to 'default'"
            )
            self._current_theme_id = "default"
            theme = _PRESET_THEMES["default"]
        return theme

    def set_theme(self, theme_id: str) -> bool:
        """设置当前主题.
        
        Args:
            theme_id: 主题 ID
            
        Returns:
            True 如果设置成功，False 如果主题不存在
        """
        theme = self.get_theme(theme_id)
        if theme is None:
            self._logger.warning(f"Theme '{theme_id}' not found")
            return False
        
        self._current_theme_id = theme_id
        self._logger.info(f"Theme changed to: {theme_id}")
        
        # 保存用户偏好
        self._save_preference()
        
        return True

    # ============================================================================
    # 透明度控制方法
    # ============================================================================
    
    def is_transparency_supported(self) -> bool:
        """检查终端是否支持透明度.
        
        Returns:
            True 如果终端支持 RGBA 颜色
        """
        import os
        # 检查常见支持透明度的终端
        term = os.environ.get("TERM", "")
        term_program = os.environ.get("TERM_PROGRAM", "")
        
        # 支持透明度的终端
        transparent_terminals = [
            "iTerm.app",           # iTerm2
            "Apple_Terminal",       # macOS Terminal (部分支持)
            "vscode",               # VS Code 终端
            "Hyper",                # Hyper
            "alacritty",            # Alacritty
            "kitty",                # Kitty
            "wezterm",              # WezTerm
            "ghostty",              # Ghostty
        ]
        
        # 检查 TERM_PROGRAM
        if term_program in transparent_terminals:
            return True
        
        # 检查 TERM 变量 (部分终端会设置)
        if "256" in term or "truecolor" in term or "rgb" in term:
            return True
        
        # 默认返回 False，让用户手动启用
        return False
    
    def is_transparency_enabled(self) -> bool:
        """检查透明度是否启用.
        
        Returns:
            True 如果透明度已启用
        """
        return self._transparency_enabled
    
    def set_transparency_enabled(self, enabled: bool) -> None:
        """设置透明度启用状态.
        
        Args:
            enabled: 是否启用透明度
        """
        self._transparency_enabled = enabled
        self._logger.info(f"Transparency {'enabled' if enabled else 'disabled'}")
        self._save_preference()
    
    def toggle_transparency(self) -> bool:
        """切换透明度状态.
        
        Returns:
            切换后的透明度状态
        """
        self._transparency_enabled = not self._transparency_enabled
        self._logger.info(f"Transparency toggled: {self._transparency_enabled}")
        self._save_preference()
        return self._transparency_enabled
    
    def get_transparency_level(self) -> float:
        """获取透明度级别.
        
        Returns:
            透明度级别 (0.0 完全透明 - 1.0 完全不透明)
        """
        return self._transparency_level
    
    def set_transparency_level(self, level: float) -> None:
        """设置透明度级别.
        
        Args:
            level: 透明度级别 (0.0 完全透明 - 1.0 完全不透明)
        """
        self._transparency_level = max(0.0, min(1.0, level))
        self._logger.debug(f"Transparency level set to: {self._transparency_level}")
        self._save_preference()
    
    def generate_transparent_css(self) -> str:
        """生成支持透明度的 CSS 变量块.
        
        Returns:
            CSS 变量定义字符串
        """
        if not self._transparency_enabled:
            return ""
        
        # 计算透明度的 alpha 值
        alpha = self._transparency_level
        
        # 生成 RGBA 颜色值（使用 hex8 格式，Textual 支持）
        # hex8 格式: #RRGGBBAA (AA 是 alpha)
        alpha_hex = format(int(alpha * 255), '02X')
        
        return f"""
/* ============================================================================
   透明度配置 (Frosted Glass Effect)
   ============================================================================ */

:root {{
    --transparency-alpha: {alpha};
    --transparency-hex: {alpha_hex};
}}

/* 毛玻璃效果样式类 */
.transparent-surface {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-header {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-footer {{
    background: rgba(33, 38, 45, {alpha});
}}

.transparent-sidebar {{
    background: rgba(22, 27, 34, {alpha});
}}

.transparent-input {{
    background: rgba(13, 17, 23, {alpha});
}}

.transparent-border {{
    border: solid rgba(48, 54, 61, {alpha});
}}
"""
    
    def get_current_theme_id(self) -> str:
        """获取当前主题 ID.
        
        Returns:
            当前主题 ID
        """
        return self._current_theme_id

    def get_current_display_name(self) -> str:
        """获取当前主题的显示名称（使用 i18n）.
        
        Returns:
            主题显示名称
        """
        theme = self.get_current_theme()
        i18n = get_i18n()
        return i18n.t(theme.display_name_key, default=theme.theme_id)

    def generate_css(self, theme: Theme) -> str:
        """为主题生成完整的 CSS 样式.
        
        Args:
            theme: 主题对象
            
        Returns:
            CSS 样式字符串
        """
        colors = theme.colors
        
        # 构建 :root CSS 变量块
        var_lines = [":root {"]
        for var_name, color_value in colors.items():
            var_lines.append(f"    {var_name}: {color_value};")
        var_lines.append("}")
        
        # 构建完整 CSS
        css_template = """
/* Handsome Agent - {theme_id} Theme CSS */

/* ============================================================================
   CSS Variables (Theme Colors)
   ============================================================================ */

{var_block}

/* ============================================================================
   Base Styles
   ============================================================================ */

Screen {{
    background: $background;
}}

/* ============================================================================
   Container Styles
   ============================================================================ */

#main-container {{
    height: 100%;
    width: 100%;
    background: $surface;
}}

#tab-container {{
    height: auto;
    width: 100%;
    background: $background;
    border-bottom: solid $border;
}}

/* ============================================================================
   Tabs Styles
   ============================================================================ */

Tabs {{
    height: auto;
    background: $background;
    margin: 0;
    padding: 0 1;
}}

Tab {{
    background: $primary-dim;
    color: $text;
    padding: 0 2;
    margin: 0 1;
}}

Tab:hover {{
    background: $primary;
}}

Tab.active {{
    background: $primary;
    color: $text-accent;
    text-style: bold;
}}

/* ============================================================================
   Welcome Banner Styles
   ============================================================================ */

#welcome-banner {{
    height: auto;
    width: 100%;
    padding: 1 2;
    background: $primary-dim;
    border: solid $border-light;
}}

#welcome-title {{
    text-style: bold;
    color: $text-accent;
    height: 3;
}}

#welcome-content {{
    color: $text;
    height: auto;
    padding: 1 0;
}}

/* ============================================================================
   Status Bar Styles
   ============================================================================ */

#status-bar {{
    height: 3;
    width: 100%;
    background: $primary;
    padding: 0 2;
    dock: bottom;
}}

/* ============================================================================
   Input Area Styles
   ============================================================================ */

#input-area {{
    height: 3;
    width: 100%;
    padding: 0 2;
    background: $surface;
}}

.input-field {{
    border: solid $primary;
    background: $surface;
    color: $text;
}}

.input-field:focus {{
    border: solid $primary-bright;
}}

/* ============================================================================
   Chat Log Styles
   ============================================================================ */

#chat-log {{
    height: 100%;
    width: 100%;
    background: $surface;
    border: solid $border;
}}

/* ============================================================================
   Button Styles
   ============================================================================ */

Button {{
    background: $primary;
    color: $text;
}}

Button:hover {{
    background: $primary-bright;
}}

Button:pressed {{
    background: $primary-dim;
}}

/* ============================================================================
   Sidebar Styles
   ============================================================================ */

#sidebar {{
    width: 25;
    height: 100%;
    background: $background;
    border-right: solid $border;
}}

/* ============================================================================
   Content Area Styles
   ============================================================================ */

#content-area {{
    height: 1fr;
    width: 100%;
    background: $surface;
}}

/* ============================================================================
   ChatView Styles
   ============================================================================ */

ChatView {{
    height: 100%;
    width: 100%;
}}

/* ============================================================================
   Status Colors
   ============================================================================ */

.status-success {{
    color: $success;
}}

.status-warning {{
    color: $warning;
}}

.status-error {{
    color: $error;
}}

.status-info {{
    color: $info;
}}

/* ============================================================================
   Message Styles
   ============================================================================ */

.user-message {{
    color: $text-accent;
}}

.assistant-message {{
    color: $text;
}}

.system-message {{
    color: $text-dim;
}}
""".format(
            theme_id=theme.theme_id,
            var_block="\n".join(var_lines),
        )
        
        return css_template

    def get_current_css(self) -> str:
        """获取当前主题的 CSS 样式.
        
        Returns:
            CSS 样式字符串
        """
        theme = self.get_current_theme()
        return self.generate_css(theme)

    # ============================================================================
    # Preference Persistence
    # ============================================================================

    def _get_config_path(self) -> Path:
        """获取配置文件路径."""
        config_dir = Path.home() / ".handsome_agent"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "tui_config.json"

    def _load_preference(self) -> None:
        """从配置文件加载用户主题偏好."""
        try:
            config_path = self._get_config_path()
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
                
                # 加载主题偏好
                theme_id = config.get("theme", {}).get("active_theme")
                if theme_id and self.get_theme(theme_id):
                    self._current_theme_id = theme_id
                    self._logger.debug(f"Loaded theme preference: {theme_id}")
                
                # 加载透明度设置
                transparency = config.get("theme", {}).get("transparency", {})
                if transparency:
                    self._transparency_enabled = transparency.get("enabled", False)
                    self._transparency_level = transparency.get("level", 0.85)
                    self._logger.debug(
                        f"Loaded transparency: enabled={self._transparency_enabled}, "
                        f"level={self._transparency_level}"
                    )
        except Exception as e:
            self._logger.debug(f"Failed to load theme preference: {e}")

    def _save_preference(self) -> None:
        """保存用户主题偏好到配置文件."""
        try:
            config_path = self._get_config_path()
            
            config = {}
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = json.load(f)
            
            if "theme" not in config:
                config["theme"] = {}
            
            # 保存主题偏好
            config["theme"]["active_theme"] = self._current_theme_id
            
            # 保存透明度设置
            config["theme"]["transparency"] = {
                "enabled": self._transparency_enabled,
                "level": self._transparency_level,
            }
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            self._logger.debug(
                f"Saved theme preference: {self._current_theme_id}, "
                f"transparency: {self._transparency_enabled}"
            )
        except Exception as e:
            self._logger.warning(f"Failed to save theme preference: {e}")

    # ============================================================================
    # Skin Engine Compatibility
    # ============================================================================

    def apply_skin_colors(self, skin_config) -> bool:
        """从皮肤引擎的配置应用颜色到当前主题.
        
        Args:
            skin_config: SkinConfig 对象（来自 skin_engine.py）
            
        Returns:
            True 如果应用成功
        """
        try:
            # 构建自定义主题颜色映射
            css_colors = {
                # 基础颜色
                "--primary": skin_config.get_color("banner_border", "#8B9A46"),
                "--primary-bright": skin_config.get_color("banner_title", "#A0B45A"),
                "--primary-dim": skin_config.get_color("banner_dim", "#647030"),
                "--primary-dark": skin_config.get_color("banner_border", "#465A1E"),
                # 文字颜色
                "--text": skin_config.get_color("banner_text", "#FFFFFF"),
                "--text-dim": skin_config.get_color("banner_dim", "#888888"),
                "--text-accent": skin_config.get_color("ui_accent", "#A0B45A"),
                # 背景颜色
                "--background": skin_config.get_color("status_bar_bg", "#465A1E"),
                "--surface": "#1a1a1a",
                "--surface-light": "#2a2a2a",
                # 边框颜色
                "--border": skin_config.get_color("banner_dim", "#647030"),
                "--border-light": skin_config.get_color("banner_border", "#8B9A46"),
                "--border-accent": skin_config.get_color("ui_accent", "#A0B45A"),
                # UI 状态颜色
                "--success": skin_config.get_color("ui_ok", "#4CAF50"),
                "--warning": skin_config.get_color("ui_warn", "#FF9800"),
                "--error": skin_config.get_color("ui_error", "#F44336"),
                "--info": skin_config.get_color("ui_info", "#2196F3"),
            }
            
            # 创建自定义主题
            custom_theme = Theme(
                theme_id=f"skin_{skin_config.name}",
                display_name_key=f"tui.theme.skin.name:{skin_config.name}",
                colors=css_colors,
            )
            
            # 注册并应用自定义主题
            self._custom_themes[custom_theme.theme_id] = custom_theme
            self.set_theme(custom_theme.theme_id)
            
            self._logger.info(f"Applied skin colors from: {skin_config.name}")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to apply skin colors: {e}")
            return False

    def load_skin_from_engine(self) -> bool:
        """从皮肤引擎加载当前激活的皮肤.
        
        Returns:
            True 如果加载成功
        """
        try:
            from cli.skin_engine import get_active_skin
            skin = get_active_skin()
            return self.apply_skin_colors(skin)
        except ImportError:
            self._logger.debug("Skin engine not available")
            return False
        except Exception as e:
            self._logger.error(f"Failed to load skin from engine: {e}")
            return False


# ============================================================================
# Global Instance Access
# ============================================================================


def get_theme_manager() -> ThemeManager:
    """获取主题管理器单例.
    
    Returns:
        ThemeManager 实例
    """
    return ThemeManager.get_instance()


# ============================================================================
# Module Export
# ============================================================================

__all__ = [
    # 数据类
    "Theme",
    "ThemeConfig",
    # 主题配置
    "THEME_CONFIGS",
    "generate_semantic_colors",
    "generate_theme_css",
    "get_all_theme_css",
    # 管理器
    "ThemeManager",
    "get_theme_manager",
    # 透明度系统
    "TRANSPARENCY_LEVELS",
    "transparent",
    # 状态颜色
    "STATUS_ONLINE",
    "STATUS_BUSY",
    "STATUS_AWAY",
    "STATUS_OFFLINE",
    "STATUS_ERROR",
    "STATUS_SUCCESS",
    "STATUS_WARNING",
    "STATUS_INFO",
    # 半透明颜色
    "AVOCADO_ACCENT_10",
    "AVOCADO_ACCENT_25",
    "AVOCADO_ACCENT_50",
    "STATUS_ONLINE_15",
    "STATUS_BUSY_10",
    "STATUS_ERROR_15",
    "STATUS_WARNING_15",
    "STATUS_INFO_15",
    # 消息类型
    "MESSAGE_ICONS",
    "MESSAGE_COLORS",
    # 文件类型图标
    "FILE_TYPE_ICONS",
    "get_file_icon",
    # 任务状态图标
    "TASK_STATUS_ICONS",
    # 任务优先级图标
    "TASK_PRIORITY_ICONS",
    # 日志级别图标
    "LOG_LEVEL_ICONS",
    "get_log_icon",
    # Agent 状态图标
    "AGENT_STATUS_ICONS",
    # 面板图标
    "PANEL_ICONS",
]