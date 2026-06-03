#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Builder - 独立的上下文构建器

将上下文拼装逻辑从 LLMToolSelector 中分离出来，职责更清晰。

参考 Hermes 的 system_prompt.py 和 prompt_builder.py 实现。

架构：
- ContextBuilder: 专门负责构建完整的系统提示词
- LLMToolSelector: 只负责工具选择 + 执行

功能：
1. 加载 Agent 定义文件 (agent.md, capabilities.md, user.md 等)
2. 构建工具 Schema
3. 收集对话历史
4. 组装完整的系统提示词

日志子层：💾 Context
"""

import json
from typing import Dict, List, Optional, Any
from pathlib import Path

from common.logging_manager import get_decision_logger
from agent.workspace import get_workspace_manager


class AgentDefinitionLoader:
    """
    Agent 定义加载器
    
    从 workspace 加载 Agent 的身份、性格、能力边界和用户信息
    """
    
    def __init__(self):
        self.workspace_manager = get_workspace_manager()
        self._definitions: Dict[str, str] = {}
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self._load_definitions()
    
    def _load_definitions(self):
        """加载所有 agent 定义文件"""
        definition_files = {
            'identity': 'agent.md',
            'capabilities': 'capabilities.md',
            'memory': 'memory.md',
            'user': 'user.md',
            'tools': 'tools.md'
        }
        
        for section_name, filename in definition_files.items():
            content = self._load_file(filename)
            if content:
                self._definitions[section_name] = content
    
    def _load_file(self, filename: str) -> Optional[str]:
        """加载单个定义文件"""
        # 尝试工作空间目录
        workspace_dir = self.workspace_manager.workspace_dir
        if workspace_dir:
            file_path = Path(workspace_dir) / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self.logger.info(f"Loaded agent definition from workspace: {filename}")
                    return content
                except Exception as e:
                    self.logger.error(f"Failed to load {filename}: {e}")
                    return None
        
        # 尝试 agent 模板目录
        agent_dir = Path(__file__).parent.parent
        file_path = agent_dir / filename
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self.logger.info(f"Loaded agent definition: {filename}")
                return content
            except Exception:
                return None
        
        return None
    
    def get_identity_summary(self) -> str:
        """获取身份定义摘要"""
        if 'identity' not in self._definitions:
            return "You are a helpful AI assistant."
        
        content = self._definitions['identity']
        lines = content.split('\n')
        summary_lines = []
        
        for line in lines:
            if line.startswith('#') or line.startswith('>'):
                continue
            if '## ' in line or line.strip():
                summary_lines.append(line)
        
        return '\n'.join(summary_lines[:50])
    
    def get_capabilities_summary(self) -> str:
        """获取能力摘要"""
        if 'capabilities' not in self._definitions:
            return ""
        
        content = self._definitions['capabilities']
        lines = content.split('\n')
        summary_lines = []
        
        for line in lines:
            if '## ' in line or line.strip():
                summary_lines.append(line)
        
        return '\n'.join(summary_lines[:30])
    
    def get_user_summary(self) -> str:
        """获取用户信息摘要"""
        if 'user' not in self._definitions:
            return ""
        
        content = self._definitions['user']
        lines = content.split('\n')
        summary_lines = []
        
        for i, line in enumerate(lines):
            if '## ' in line:
                summary_lines.append(line)
                for j in range(i+1, min(i+10, len(lines))):
                    if lines[j].startswith('##'):
                        break
                    if lines[j].strip():
                        summary_lines.append(lines[j])
        
        if summary_lines:
            return '\n'.join(summary_lines)
        return ""
    
    def get_all_definitions(self) -> Dict[str, str]:
        """获取所有定义"""
        return self._definitions.copy()


class ContextBuilder:
    """
    上下文构建器 - 专门负责构建完整的系统提示词
    
    职责：
    1. 加载 Agent 定义（身份、能力、用户信息）
    2. 构建工具 Schema
    3. 收集对话历史
    4. 组装完整的系统提示词
    
    日志子层：💾 Context
    """
    
    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        enable_guidance: bool = True
    ):
        """
        Args:
            tools: 工具字典 {name: ToolDefinition}
            enable_guidance: 是否添加指导性文本（memory, skills 等）
        """
        self.logger = get_decision_logger(self.__class__.__name__, sublayer="context")
        self.tools = tools or {}
        self.enable_guidance = enable_guidance
        
        self.agent_loader = AgentDefinitionLoader()
        
        # 🧠 Decision - 💾 Context - 上下文构建器初始化
        self.logger.info("ContextBuilder initialized")
    
    def set_tools(self, tools: Dict[str, Any]) -> None:
        """设置工具字典"""
        self.tools = tools
        self.logger.info(f"Tools set: {len(tools)} tools available")
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取工具 Schema（用于 LLM）"""
        schema = []
        for tool_name, tool in self.tools.items():
            schema.append({
                'name': tool.name if hasattr(tool, 'name') else tool_name,
                'description': tool.description if hasattr(tool, 'description') else '',
                'parameters': tool.parameters if hasattr(tool, 'parameters') else {}
            })
        return schema
    
    def build_system_prompt(
        self,
        conversation_history: Optional[List[Dict]] = None,
        include_tools: bool = True
    ) -> str:
        """
        构建完整的系统提示词
        
        Args:
            conversation_history: 对话历史
            include_tools: 是否包含工具列表
            
        Returns:
            完整的系统提示词
        """
        # 🧠 Decision - 💾 Context - 开始构建上下文
        self.logger.info("Context Assembly: Starting prompt building")
        
        # 加载 Agent 定义
        identity_summary = self.agent_loader.get_identity_summary()
        capabilities_summary = self.agent_loader.get_capabilities_summary()
        user_summary = self.agent_loader.get_user_summary()
        
        # 🧠 Decision - 💾 Context - 记录各部分长度
        self.logger.info(
            f"Context Assembly: identity={len(identity_summary)} chars, "
            f"capabilities={len(capabilities_summary)} chars, "
            f"user_profile={len(user_summary)} chars"
        )
        
        # 构建对话历史上下文
        history_context = ""
        history_msg_count = 0
        if conversation_history:
            recent = conversation_history[-6:]
            history_msg_count = len(recent)
            history_context = "\n\nRecent conversation:\n"
            for msg in recent:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')[:200]
                history_context += f"- {role}: {content}\n"
        
        # 🧠 Decision - 💾 Context - 构建工具列表
        tools_schema = ""
        tools_schema_len = 0
        if include_tools and self.tools:
            tools_schema = json.dumps(self.get_tools_schema(), ensure_ascii=False, indent=2)
            tools_schema_len = len(tools_schema)
        
        self.logger.info(
            f"Context Assembly: tools_schema={tools_schema_len} chars, "
            f"history={history_msg_count} messages"
        )
        
        # 组装提示词
        prompt_parts = []
        
        # 1. 身份定义
        if identity_summary:
            prompt_parts.append(identity_summary)
        
        # 2. 能力摘要
        if capabilities_summary:
            prompt_parts.append(capabilities_summary)
        
        # 3. 用户信息
        prompt_parts.append(f"User Profile:\n{user_summary if user_summary else 'User information not configured. Provide general assistance.'}")
        
        # 4. 指导性文本（参考 Hermes）
        if self.enable_guidance:
            guidance = self._build_guidance()
            if guidance:
                prompt_parts.append(guidance)
        
        # 5. 工具列表
        if include_tools and self.tools:
            prompt_parts.append(f"Available tools:\n{tools_schema}")
            prompt_parts.append(self._build_tool_usage_instruction())
        
        # 6. 对话历史
        if history_context:
            prompt_parts.append(history_context)
        
        prompt = "\n\n".join(prompt_parts)
        
        # 🧠 Decision - 💾 Context - 上下文构建完成
        self.logger.info(
            f"Context Assembly complete: total={len(prompt)} chars, "
            f"tools_count={len(self.tools)}"
        )
        
        return prompt
    
    def _build_guidance(self) -> str:
        """
        构建指导性文本（参考 Hermes 的 MEMORY_GUIDANCE, SKILLS_GUIDANCE 等）
        
        这些文本帮助 LLM 更好地使用记忆、技能等功能
        
        借鉴 Hermes 的设计：
        1. 分层组织：stable (稳定) / context (上下文) / volatile (可变)
        2. 工具感知：只有当工具可用时才添加相关指导
        3. 模型特定：不同模型有不同的执行指导
        """
        guidance_parts = []
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 1. 记忆使用指导 (参考 Hermes MEMORY_GUIDANCE)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        guidance_parts.append("""
## Memory Usage
You have persistent memory across sessions. Save durable facts using the memory tool: user preferences, environment details, tool quirks, and stable conventions.
Memory is injected into every turn, so keep it compact and focused on facts that will still matter later.

**Prioritize what reduces future user steering** — the most valuable memory is one that prevents the user from having to correct or remind you again.
User preferences and recurring corrections matter more than procedural task details.

**What to save:**
- User preferences (e.g., "User prefers concise responses")
- Environment details (e.g., "Project uses pytest with xdist")
- Tool quirks and conventions

**What NOT to save:**
- Task progress or session outcomes
- Completed-work logs or temporary TODO state
- PR numbers, issue numbers, commit SHAs, or any artifact that will be stale in 7 days

**How to write:**
- Write memories as declarative facts, not instructions
  ✓ "User prefers concise responses"
  ✗ "Always respond concisely"
  ✓ "Project uses pytest"
  ✗ "Run tests with pytest -n 4"
""")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 2. 跨会话搜索指导 (参考 Hermes SESSION_SEARCH_GUIDANCE)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        guidance_parts.append("""
## Session Search
When the user references something from a past conversation or you suspect relevant cross-session context exists, use session_search to recall it before asking them to repeat themselves.
""")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 3. 技能保存指导 (参考 Hermes SKILLS_GUIDANCE)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        guidance_parts.append("""
## Skills
After completing a complex task (5+ tool calls), fixing a tricky error, or discovering a non-trivial workflow, save the approach as a skill with skill_manage so you can reuse it next time.
When using a skill and finding it outdated, incomplete, or wrong, patch it immediately with skill_manage(action='patch') — don't wait to be asked.
Skills that aren't maintained become liabilities.
""")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 4. 工具使用执行纪律 (参考 Hermes TOOL_USE_ENFORCEMENT_GUIDANCE)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        guidance_parts.append("""
## Tool-Use Enforcement
You MUST use your tools to take action — do not describe what you would do or plan to do without actually doing it.

**Execution rules:**
- When you say you will perform an action (e.g., 'I will run the tests'), you MUST immediately make the corresponding tool call
- Never end your turn with a promise of future action — execute it now
- Keep working until the task is actually complete

**When to use tools (never answer from memory):**
- Arithmetic, math, calculations → use terminal or execute_code
- Current time, date, timezone → use terminal
- System state (OS, CPU, memory, disk, ports, processes) → use terminal
- File contents, sizes, line counts → use read_file, search_files, or terminal
- Current facts (weather, news, versions) → use web_search

**Verification before completion:**
- Correctness: does the output satisfy every stated requirement?
- Grounding: are factual claims backed by tool outputs?
- Formatting: does the output match the requested format?

**If information is missing:**
- Do NOT guess or hallucinate an answer
- Use the appropriate lookup tool when missing information is retrievable
- Ask a clarifying question only when the information cannot be retrieved by tools
""")
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # 5. 主动行动原则 (参考 Hermes act_dont_ask)
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        guidance_parts.append("""
## Act Without Asking
When a question has an obvious default interpretation, act on it immediately instead of asking for clarification:

- 'Is port 443 open?' → check THIS machine (don't ask 'open where?')
- 'What OS am I running?' → check the live system (don't use user profile)
- 'What time is it?' → run `date` (don't guess)

Only ask for clarification when the ambiguity genuinely changes what tool you would call.
""")
        
        return "\n".join(guidance_parts)
    
    def _build_tool_usage_instruction(self) -> str:
        """构建工具使用说明"""
        return """
## Tool Usage
When you need to use a tool, format your response as XML tags.
IMPORTANT: Always wrap tool calls in the XML tags exactly as shown above.
"""


__all__ = ["ContextBuilder", "AgentDefinitionLoader"]