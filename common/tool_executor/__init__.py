# -*- coding: utf-8 -*-
# 🔧 System - Tool Executor 模块

"""
Tool Executor - 统一工具执行器

提供：
- 单个工具执行
- 批量工具执行（顺序/并发）
- Rail 拦截支持
- 统一错误处理
- 事件发射

使用示例：
```python
from common.tool_executor import ToolExecutor

executor = ToolExecutor(
    tool_registry={"read_file": read_file_handler},
    rails=[SecurityRail()],
)

# 单个执行
result = await executor.execute("read_file", {"path": "test.py"})

# 批量执行
results = await executor.execute_batch([
    ToolInvokeRequest("read_file", {"path": "a.py"}),
    ToolInvokeRequest("write_file", {"path": "b.py", "content": "..."}),
])
```
"""

from common.tool_executor.types import (
    ToolInvokeResult,
    ToolInvokeRequest,
    ToolInvokeError,
    ExecuteMode,
    ExecuteOptions,
)
from common.tool_executor.tool_executor import ToolExecutor

__all__ = [
    "ToolInvokeResult",
    "ToolInvokeRequest",
    "ToolInvokeError",
    "ExecuteMode",
    "ExecuteOptions",
    "ToolExecutor",
]
