# Core Module - 核心框架模块

> 控制层核心组件：会话管理、路由、工具选择、记忆系统

## 📋 概述

核心模块是整个 Agent 的**控制层**，负责协调各个组件的工作，实现任务路由、记忆管理和工具选择。

**架构位置**: Core Layer 处于用户层和推理层之间，负责编排调度。

> **核心原则**: "所有意图识别使用 LLM，NO hardcoded rules。"

## 🏛️ 架构中的 Core Layer

```
┌─────────────────────────────────────────────────────────────┐
│          Handsome Agent Architecture - Core Layer Position  │
├─────────────────────────────────────────────────────────────┤
│  1. Interface Layer                                         │
│     CLI │ Gateway                                          │
├─────────────────────────────────────────────────────────────┤
│  2. 🧠 Decision Layer (LLM-powered)                         │
│     llm_tool_selector.py                                   │
├─────────────────────────────────────────────────────────────┤
│  3. Core Layer ← YOU ARE HERE                              │
│     Session │ Cache │ Memory │ Skills                       │
├─────────────────────────────────────────────────────────────┤
│  4. Tool Abstraction Layer                                 │
│     ToolRegistry │ @register_tool                           │
├─────────────────────────────────────────────────────────────┤
│  5. LLM Provider Layer                                      │
│     25+ LLM Providers                                       │
└─────────────────────────────────────────────────────────────┘
```

## 🏗️ 模块结构

```
core/
├── __init__.py
├── agent.py                  # CustomAgent 主编排器（已废弃）
├── modern_agent.py           # 现代 Agent 实现
├── simplified_agent.py       # 简化版 Agent（展示 LLM 直接决策）
├── session.py                # SessionManager 会话管理
├── cache.py                  # LRUCache 响应缓存
├── memory_manager.py         # 记忆管理器
├── memory_provider.py        # 记忆提供者接口
├── memory_retrieval.py       # 记忆检索
├── memory_system.py          # 记忆系统
├── builtin_memory.py         # 内置记忆实现
├── markdown_memory.py         # Markdown 记忆存储
├── trajectory_recorder.py    # 轨迹记录器
├── llm_tool_selector.py      # LLM 驱动的工具选择器
├── llm_terminal_command.py   # LLM 终端命令生成
├── llm_web_search.py         # LLM 网络搜索
├── router.py                 # TaskRouter 任务路由（已废弃）
├── response_router.py        # 响应策略路由器
├── router_handlers.py        # 路由处理器（已废弃，使用 LLM）
├── skill_manager.py          # SkillManager 技能管理
├── task_planner.py           # 任务规划器
├── task_middleware.py        # 任务规划中间件
├── task_executor.py          # 子任务执行器
├── task_logger.py            # 任务日志
├── todo_adapter.py          # Todo 适配器
├── todo_toolkit.py           # Todo 工具包
├── todo_event_rail.py        # Todo 事件轨道
├── context_compressor.py    # 上下文压缩器
├── self_improvement.py      # 自我改进
├── collaborative_planning.py # 协作式任务规划
├── layer_logger.py           # 分层日志系统
├── logging_manager.py        # 日志管理器
├── i18n.py                   # 国际化
├── exceptions.py             # 异常定义
├── environment.py            # 环境变量管理
└── workspace.py              # 工作区管理
```

## 🔄 LLM 驱动的工具选择

### 旧架构（已废弃）

```python
# ❌ DEPRECATED - 硬编码关键词意图识别
INTENT_KEYWORDS = {
    'terminal': ['打开', '启动', '运行', ...]
}

# ❌ DEPRECATED - fallback 降级逻辑
try:
    result = llm_intent_recognition()
except:
    result = hardcoded_fallback()  # 已移除
```

### 新架构（LLM 直接决策）

```python
# ✅ NEW - 纯 LLM 工具选择
from core.llm_tool_selector import LLMDrivenDecisionEngine

engine = LLMDrivenDecisionEngine(llm_provider=provider)
result = await engine.process(
    user_input="帮我打开 agent.md 文件",
    context={"session_id": "sess-123"}
)
# LLM 直接返回 JSON：
# {
#     "action": "use_tool",
#     "selected_tool": "read_file",
#     "parameters": {"path": "agent.md"}
# }
```

详细文档见 [LLM Tool Selection](../../architecture/llm-tool-selection.md)。

## 🧩 核心组件

### 1. SessionManager (session.py)

会话管理，负责上下文保留和历史跟踪。

```python
from core.session import SessionManager

manager = SessionManager()
session = manager.get_or_create_session("user-123")

# 添加消息
session.add_message("user", "帮我打开文件")
session.add_message("assistant", "已为您打开文件")

# 获取历史
history = session.get_messages()
```

### 2. LLMDrivenDecisionEngine (llm_tool_selector.py)

LLM 驱动的工具选择器，替代旧的 IntentClassifier。

```python
from core.llm_tool_selector import LLMDrivenDecisionEngine

engine = LLMDrivenDecisionEngine(
    llm_provider=provider,
    enable_keyword_fallback=True  # LLM 不可用时降级
)

result = await engine.process(
    user_input="打开 agent.md",
    available_tools=["read_file", "open_file", "launch_app"]
)
```

### 3. Memory System (memory_*.py)

记忆系统，支持多种存储后端。

```python
from core.memory_manager import MemoryManager

memory = MemoryManager()

# 保存记忆
await memory.add("user_prefers_dark_mode", "dark")

# 检索记忆
context = await memory.retrieve("theme preferences")
```

### 4. TaskPlanning (task_*.py)

任务规划系统，自动拆解复杂任务。

```python
from core.task_planner import TaskPlanner

planner = TaskPlanner(llm_provider=provider)

# 分析任务
result = await planner.analyze("帮我开发一个用户注册系统")

# result.is_complex = True
# result.subtasks = [{"id": 1, "title": "需求分析"}, ...]
```

### 5. SkillManager (skill_manager.py)

技能管理，负责技能注册、发现和执行。

```python
from core.skill_manager import SkillManager

manager = SkillManager()

# 注册技能
await manager.register_skill(skill_definition)

# 发现技能
skills = await manager.discover_skills("web search")

# 执行技能
result = await manager.execute_skill("web_search", query="Python")
```

## 📊 模块协作关系

| 组件 | 上游依赖 | 下游依赖 | 职责 |
|------|----------|----------|------|
| LLMDrivenDecisionEngine | CLI/Gateway | Tools | 工具选择 |
| SessionManager | Agent | Memory | 会话管理 |
| MemoryManager | SessionManager | LLM | 记忆存储检索 |
| SkillManager | Decision Engine | Tools | 技能执行 |
| TaskPlanner | Agent | Skills | 任务规划 |

## 🎯 使用示例

### 简化版 Agent（推荐）

```python
from core.simplified_agent import SimpleAgent

agent = SimpleAgent(llm_provider=provider)

response = await agent.chat("帮我读取 config.json")
print(response)
```

### 现代 Agent

```python
from core.modern_agent import ModernAgent

agent = ModernAgent(
    llm_provider=provider,
    enable_memory=True,
    enable_skills=True,
    enable_task_planning=True
)

result = await agent.run("开发一个用户注册功能")
```

## 🔌 开源替代方案

| 组件 | 开源替代 | GitHub |
|------|----------|--------|
| 会话管理 | LangChain Memory | langchain-ai/langchain |
| 工具选择 | LangChain Agents | langchain-ai/langchain |
| 任务规划 | AutoGPT | significant/gravitas |
| 记忆系统 | MemGPT | dbhi/memgpt |

## 📚 相关文档

- [Architecture Overview](../../architecture/architecture.md) - 系统架构
- [LLM Tool Selection](../../architecture/llm-tool-selection.md) - LLM 工具选择
- [Brain Module](../brain/README.md) - Brain 模块
- [Tools Module](../tools/README.md) - 工具模块

---

*最后更新: 2026-06-01*