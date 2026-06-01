# Handsome Agent

> Hermes-Brain + OpenClaw-Body 双核驱动的模块化 AI 智能助手

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

***

## 🎯 项目概述

Handsome Agent 是一个企业级 AI Agent 系统，融合了：

- **OpenClaw** 的多渠道接入能力和工具抽象
- **Hermes** 的智能决策和自我进化能力

**核心特性**：LLM 驱动的意图识别 + 工具选择、自动学习进化、技能生命周期管理。

***

## 🏛️ Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    🚪 Access Layer                          │
│  CLI │ Gateway │ HTTP Adapter │ WebSocket                   │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🧠 Decision Layer                        │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🤖 LLMDrivenDecisionEngine                           │  │
│  │  LLM directly understands intent + selects tools      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 💾 Memory    │  │ 📋 Skills    │  │ 📝 Trajectory│      │
│  │              │  │              │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  🔬 Curator (Async Post-Processing)                   │  │
│  │  Trajectory Evaluation → Skill Synthesis → Evolution  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    🏃 Execution Layer                       │
│  Shell Executor │ Docker Executor │ Tool Executor           │
└─────────────────────────────────────────────────────────────┘
```

***

## 📁 项目目录结构

```
Handsome-Agent/
│
├── agent/                    # 🤖 Agent 核心
│   ├── agent_loop.py        #   Agent Loop（ReAct 模式）
│   ├── schemas.py           #   数据模型
│   ├── trajectory.py        #   轨迹记录
│   ├── memory.py            #   记忆管理
│   ├── context_engine.py    #   上下文引擎
│   ├── prompt_builder.py    #   提示词构建
│   ├── modern_agent.py      #   现代 Agent 实现
│   ├── llm_tool_selector.py #   LLM 驱动的工具选择器
│   ├── workspace.py         #   工作空间管理
│   ├── curator/             #   Curator（自我进化）
│   ├── llm/                 #   LLM Provider (OpenAI/Claude/DeepSeek等)
│   └── templates/           #   Agent 模板
│
├── skills/                   # 🛠️ 技能系统
│   ├── matcher.py           #   技能匹配
│   ├── loader.py            #   技能加载
│   ├── registry.py          #   技能注册
│   ├── system/             #   系统内置技能
│   └── user/               #   用户技能
│
├── gateway/                  # 🚪 网关
│   ├── server.py           #   HTTP 服务器
│   ├── middleware.py       #   中间件（认证/限流）
│   └── adapters/           #   渠道适配器
│
├── executor/                 # 🏃 执行层
│   ├── shell.py            #   Shell 执行器
│   └── docker.py          #   Docker 执行器
│
├── tools/                    # 🛠️ 工具定义
│   ├── registry.py          #   注册表
│   ├── integrated_tools.py #   集成工具
│   └── file_tools.py       #   文件工具
│
├── common/                   # 📦 基础设施
│   ├── config.py           #   配置
│   ├── logging_manager.py  #   日志管理（统一 LayerLogger）
│   ├── exceptions.py       #   异常
│   └── logging.py          #   简化日志配置
│
├── cli/                      # 💬 CLI
│   ├── main.py             #   主入口
│   ├── modern_cli.py       #   现代 CLI 实现
│   └── setup_wizard.py     #   配置向导
│
├── tests/                    # 🧪 测试套件
│   ├── unit/               #   单元测试
│   ├── integration/        #   集成测试
│   └── performance/        #   性能测试
│
├── docs/                     # 📚 文档系统
│   ├── index.md            #   文档索引
│   ├── architecture/       #   架构文档
│   ├── guides/             #   使用指南
│   ├── modules/            #   模块文档
│   └── references/         #   参考资料
│
├── api/                      # 📋 OpenAPI 规范
│   └── brain_service.yaml  #   网关 HTTP API 的 OpenAPI 规范
│
└── workspace/                # 💾 工作空间
    ├── logs/               #   日志目录
    └── sessions/           #   会话目录
```

***

## 🔑 核心特性

### 1. LLM 驱动的意图识别（无预定义意图）

```python
# 旧架构：预定义意图 → 工具选择
# 新架构：LLM 直接理解 + 选择工具
result = await engine.process(
    user_input="打开 agent.md 看看内容",
    available_tools=["read_file", "open_file", "launch_app"]
)
# → LLM 直接决定使用 read_file
```

### 2. 技能系统 (Skills)

- 技能加载、匹配、执行
- 技能使用追踪（use/view/patch 事件）
- 生命周期管理（active → stale → archived）
- 技能合并（相似技能自动聚合）

### 3. 自我进化 (Self-Evolution)

```
用户对话 → 轨迹记录 → Curator 评估 → 技能合成 → 自动学习
                                                      ↓
                                           越聊越好用 ✨
```

### 4. 完整工具生态

| 类别    | 工具                                                      |
| ----- | ------------------------------------------------------- |
| 📁 文件 | read\_file, write\_file, list\_directory, search\_files |
| 🚀 应用 | launch\_app, open\_calculator, open\_notepad            |
| 💻 终端 | terminal, run\_python                                   |
| 🔍 网络 | web\_search, web\_extract                               |
| 🧠 记忆 | memory\_save, memory\_search                            |

***

## 🚀 快速开始

### 方式一：CLI 交互

```bash
# 安装依赖
pip install -r requirements.txt

# 配置 LLM（首次运行会提示）
python -m cli.main setup

# 启动交互式对话
python -m cli.main chat

# 运行测试
pytest tests/unit/ -v
```

### 方式二：Docker

```bash
docker-compose up -d
```

***

## 📚 文档导航

> 完整文档系统位于 [docs/index.md](docs/index.md)

### 新手入门

| 文档                                   | 内容      | 预计时间  |
| ------------------------------------ | ------- | ----- |
| [快速开始](docs/guides/quick-start.md)   | 5分钟快速上手 | 5min  |
| [系统设计](docs/guides/system-design.md) | 设计文档    | 10min |

### 架构与设计

| 文档                                            | 内容             |
| --------------------------------------------- | -------------- |
| [架构设计](docs/architecture/architecture.md)     | 三层架构详解         |
| [重构计划](docs/architecture/restructure-plan.md) | 目录结构重构计划       |
| [迁移指南](docs/guides/migration-guide.md)        | 意图识别层迁移 ⚠️ 已废弃 |

### 模块文档

| 模块                                        | 文档       |
| ----------------------------------------- | -------- |
| [Agent](docs/modules/agent/README.md)     | Agent 核心 |
| [Skills](docs/modules/skills/README.md)   | 技能系统     |
| [Gateway](docs/modules/gateway/README.md) | 网关       |
| [Tools](docs/modules/tools/README.md)     | 工具定义     |
| [CLI](docs/modules/cli/README.md)         | 命令行界面    |
| [Common](docs/modules/common/README.md)   | 基础设施     |

### 参考资料

| 文档                                               | 内容          |
| ------------------------------------------------ | ----------- |
| [LLM 集成](docs/references/llm-integration.md)     | 25+ LLM 提供商 |
| [能力清单](docs/references/capabilities-overview.md) | Agent 能力矩阵  |
| [编码规范](.trae/rules/rule.md)                      | 开发规范        |

***

## 🧪 Testing

```bash
# Run all tests
pytest tests/unit/ -v

# With coverage
pytest tests/unit/ --cov=. --cov-report=term-missing

# Specific modules
pytest tests/unit/curator/ -v
pytest tests/unit/tools/ -v
```

***

## 📄 License

MIT License

***

*Handsome Agent - Making AI smarter with use* ✨
*Last updated: 2026-06-01*
*Version: v3.0.0 - Architecture restructuring complete, unified logging system online*
