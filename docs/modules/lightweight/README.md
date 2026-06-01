# Lightweight Module - 轻量版 Agent

> 零依赖（仅标准库），<30MB，适合移动端后端、IoT、边缘计算部署

## 目录结构

```
lightweight/
├── __init__.py       # 模块导出：LightweightAgent, AgentConfig, AgentResponse, run_server
├── agent.py          # 基础 Agent（LightweightAgent）
├── agent_v2.py       # 增强版 Agent（EnhancedAgent，支持 CoT + Tool Use）
├── server.py         # HTTP REST API 服务器
├── tools.py          # 工具系统（Tool, ToolSystem）
└── DESIGN.md         # 设计文档
```

## 核心组件

### 1. LightweightAgent (agent.py)

基础版 Agent，无 LLM 依赖，基于知识库的响应生成。

```python
from lightweight import LightweightAgent

agent = LightweightAgent()
response = agent.respond("What is Python?")
print(response.content)  # 基于知识库的响应
```

### 2. EnhancedAgent (agent_v2.py)

增强版 Agent，支持 Chain of Thought 推理和 Tool Use。

```python
from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel, get_agent

# 创建 Agent
agent = EnhancedAgent(reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT)

# 异步响应
result = await agent.respond(
    "What is machine learning?",
    include_reasoning=True,
    use_tools=True
)

print(result["response"])       # 最终响应
print(result["reasoning"])       # 推理过程
print(result["tools_used"])      # 使用的工具
print(result["confidence"])      # 置信度
```

**推理级别 (ReasoningLevel)**：

| 级别 | 说明 |
|------|------|
| `DIRECT` | 直接响应 |
| `CHAIN_OF_THOUGHT` | 思维链推理 |
| `REACT` | 推理 + 行动（工具调用） |
| `SELF_REFLECT` | 自我反思 |

**内置工具**：

| 工具 | 说明 |
|------|------|
| `search` | 在线搜索 |
| `calculate` | 数学计算 |
| `code_executor` | Python 代码执行 |

### 3. HTTP Server (server.py)

REST API 服务器，适合移动端集成。

```python
from lightweight import run_server

# 启动服务器
run_server(host="0.0.0.0", port=8000)
```

**API 端点**：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/respond` | POST | 发送查询 |

**请求示例**：
```bash
curl -X POST http://localhost:8000/respond \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'
```

**响应示例**：
```json
{
  "content": "Python is a high-level...",
  "confidence": 0.85,
  "execution_time": 0.003
}
```

### 4. Tool System (tools.py)

工具系统，参考 LangChain Tool Calling 和 Claude Tool Use。

```python
from lightweight.tools import Tool, ToolSystem

# 创建自定义工具
def my_tool(query: str) -> str:
    return f"Result for: {query}"

tool_system = ToolSystem()
tool_system.register(Tool("my_tool", "My custom tool", my_tool))

# 执行工具
result = tool_system.execute("my_tool", "test query")
```

## 快速开始

### 交互模式

```bash
python -m lightweight
```

### API 服务器模式

```bash
python -m lightweight --server
```

### Python 集成

```python
from lightweight import LightweightAgent, AgentConfig

config = AgentConfig(
    name="MyAgent",
    enable_caching=True,
    max_response_length=2000
)

agent = LightweightAgent(config)
response = agent.respond("Hello, world!")
```

## 与增强版交互

```python
import asyncio
from lightweight.agent_v2 import EnhancedAgent, ReasoningLevel

async def main():
    agent = EnhancedAgent(
        name="ThinkingAgent",
        reasoning_level=ReasoningLevel.CHAIN_OF_THOUGHT,
        enable_caching=True,
        max_reasoning_steps=5
    )

    result = await agent.respond(
        "Explain how neural networks learn",
        include_reasoning=True,
        use_tools=True
    )

    print(f"Confidence: {result['confidence']}")
    print(f"Response:\n{result['response']}")

asyncio.run(main())
```

## 性能指标

| 指标 | 值 |
|------|-----|
| 内存占用 | < 30MB |
| 启动时间 | < 100ms |
| 依赖数量 | 0（仅标准库） |
| 支持平台 | Windows / macOS / Linux |

## 设计参考

本模块参考了以下项目的设计理念：

- **Claude** - Chain of Thought 推理
- **LangChain** - Tool Calling 和 Agent 架构
- **AutoGPT** - 目标分解和自主执行

详细设计文档见 [DESIGN.md](DESIGN.md)。

---

*最后更新: 2026-06-01*