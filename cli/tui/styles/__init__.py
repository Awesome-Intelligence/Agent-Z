"""CSS 样式模块化架构

这个模块提供了 TUI 应用的样式系统，包括：
- base.css: 基础变量和设计令牌
- layout.css: 布局规则
- components.css: 组件样式
- animations.css: 动画定义
"""

from pathlib import Path
from typing import List


def get_stylesheets() -> List[str]:
    """
    获取所有样式表文件路径

    Returns:
        样式表文件路径列表，按加载顺序排列
    """
    styles_dir = Path(__file__).parent
    return [
        str(styles_dir / "base.css"),
        str(styles_dir / "layout.css"),
        str(styles_dir / "components.css"),
        str(styles_dir / "animations.css"),
    ]
