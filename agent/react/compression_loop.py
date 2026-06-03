# 🧠 Decision - ✅ Task - ReAct 循环压缩增强

"""
ReActLoop with Compression - ReAct 循环的压缩增强版本

在 ReAct 循环中自动集成上下文压缩功能：
1. 在每次 LLM 调用前检查是否需要压缩
2. 压缩后继续循环
3. 提供压缩状态查询

Usage:
    from agent.react.compression_loop import CompressedReActLoop

    loop = CompressedReActLoop(
        llm_provider=llm,
        session_id="xxx",
        model="gpt-4o",
    )

    context = ReActContext(...)
    result = await loop.run(context)
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent.react.context import ReActContext

from common.logging_manager import get_task_logger
from agent.react.loop import ReActLoop, LoopState, StepResult, Decision
from agent.context.compression_integration import CompressionIntegration

logger = get_task_logger("CompressedReActLoop", sublayer="task")


class CompressedReActLoop(ReActLoop):
    """
    带压缩功能的 ReAct 循环

    在每次 LLM 决策前自动检查和执行上下文压缩。

    使用示例：
    ```python
    loop = CompressedReActLoop(
        llm_provider=llm,
        session_id="xxx",
        model="gpt-4o",
    )

    context = ReActContext(
        task_description="帮我重构这个模块",
        tools=tools_schema,
        tool_handlers=tool_handlers
    )

    result = await loop.run(context)
    ```
    """

    def __init__(
        self,
        llm_provider,
        session_id: str,
        model: str = "gpt-4o",
        rails: Optional[List] = None,
        max_iterations: int = 20,
        compression_integration: Optional[CompressionIntegration] = None,
    ):
        """
        Args:
            llm_provider: LLM Provider
            session_id: 会话 ID
            model: 模型名称（用于压缩阈值计算）
            rails: Rail 列表
            max_iterations: 最大迭代次数
            compression_integration: 压缩集成器（可选）
        """
        super().__init__(
            llm_provider=llm_provider,
            session_id=session_id,
            rails=rails,
            max_iterations=max_iterations,
        )

        self.model = model
        self._compression_integration = compression_integration

        if self._compression_integration is None:
            self._compression_integration = CompressionIntegration(
                session_id=session_id,
                model=model,
                llm_client=llm_provider,
            )

        self.logger = get_task_logger("CompressedReActLoop", sublayer="task")

    @property
    def compression(self) -> CompressionIntegration:
        """获取压缩集成器"""
        return self._compression_integration

    def request_compression(self, focus_topic: Optional[str] = None) -> None:
        """
        请求压缩

        Args:
            focus_topic: 聚焦主题
        """
        self._compression_integration.request_compression(focus_topic)

    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计"""
        return self._compression_integration.get_stats()

    async def _llm_decide(self, context: "ReActContext") -> Decision:
        """
        LLM 决策（带压缩检查）

        在 LLM 决策前检查并执行上下文压缩。
        """
        messages = context.get_messages()

        compressed_messages = await self._compression_integration.before_llm_call(
            messages, self.model
        )

        if compressed_messages != messages:
            context.replace_messages(compressed_messages)
            self.logger.debug(
                f"Context compressed before LLM call: "
                f"{len(messages)} -> {len(compressed_messages)} messages"
            )

        response = await self.llm.generate(self._build_decision_prompt(context))
        content = response.content if hasattr(response, 'content') else str(response)

        await self._compression_integration.after_llm_call(messages, response)

        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        try:
            import json
            result = json.loads(content)
            return Decision(
                action=result.get("action", "direct_response"),
                tool_name=result.get("tool_name"),
                parameters=result.get("parameters", {}),
                reasoning=result.get("reasoning", ""),
                content=result.get("content"),
                questions=result.get("questions", [])
            )
        except Exception as e:
            self.logger.error(f"LLM 决策解析失败: {e}")
            return Decision(
                action="direct_response",
                content=f"处理出错: {str(e)}"
            )

    def _build_decision_prompt(self, context: "ReActContext") -> str:
        """构建决策提示"""
        tools_schema = context.get_tools_schema()
        tools_str = ""
        if tools_schema:
            import json
            tools_str = json.dumps(tools_schema, ensure_ascii=False, indent=2)

        todo_guide = self._get_todo_guide()
        recent_history = context.get_recent_messages(4)

        history_str = "\n".join(
            f"- {m['role']}: {m['content']}"
            for m in recent_history
        ) if recent_history else "(无历史记录)"

        return f"""你是一个任务执行助手。当前任务是：{context.task_description}

对话历史：
{history_str}

可用工具：
{tools_str}

{todo_guide}

请根据当前任务和对话历史，决定下一步行动：

规则：
- 如果任务复杂（3+ 步骤），使用 todo_* 工具管理任务
- 如果需要多个操作，按顺序逐个完成
- 如果遇到问题，先尝试解决，解决不了再询问用户
- 完成任务后给出简洁的总结

返回 JSON 格式：
{{
    "action": "use_tool" 或 "direct_response" 或 "ask_clarification",
    "tool_name": "工具名" (仅当 action 为 use_tool 时),
    "parameters": {{}} (仅当 action 为 use_tool 时),
    "reasoning": "决策理由",
    "content": "直接回答的内容" (仅当 action 为 direct_response 时),
    "questions": ["问题1", "问题2"] (仅当 action 为 ask_clarification 时)
}}

Respond with ONLY the JSON object, no other text."""

    async def _execute_step(self, context: "ReActContext") -> StepResult:
        """执行单个步骤"""
        decision = await self._llm_decide(context)

        if decision.action == "use_tool":
            rail_result = await self._trigger_before_tool(
                decision.tool_name,
                decision.parameters
            )

            if rail_result and not rail_result.allowed:
                self.logger.warning(
                    f"Rail 阻止工具调用: {decision.tool_name}"
                )
                return StepResult(
                    step=context.current_iteration,
                    action="blocked",
                    tool_name=decision.tool_name,
                    parameters=decision.parameters,
                    result=rail_result.error or "Blocked by Rail",
                    reasoning=decision.reasoning,
                    is_blocked=True,
                    block_reason=rail_result.error
                )

            result = await self._execute_tool(
                decision.tool_name,
                decision.parameters,
                context
            )

            await self._trigger_after_tool(
                decision.tool_name,
                decision.parameters,
                result
            )

            is_error = self._is_error_result(result)

            context.add_tool_call(
                decision.tool_name,
                decision.parameters,
                result,
                is_error
            )

            return StepResult(
                step=context.current_iteration,
                action="tool_call",
                tool_name=decision.tool_name,
                parameters=decision.parameters,
                result=result,
                reasoning=decision.reasoning,
                is_error=is_error
            )

        else:
            content = decision.content or "\n".join(decision.questions)
            return StepResult(
                step=context.current_iteration,
                action=decision.action,
                result=content,
                reasoning=decision.reasoning
            )


class CompressionAwareReActLoop(CompressedReActLoop):
    """
    压缩感知的 ReAct 循环

    在每次迭代后检查压缩状态，并在需要时触发压缩。

    与 CompressedReActLoop 的区别：
    - 在每次迭代后检查 token 使用量
    - 支持手动压缩请求
    - 提供更详细的压缩日志
    """

    def __init__(
        self,
        llm_provider,
        session_id: str,
        model: str = "gpt-4o",
        rails: Optional[List] = None,
        max_iterations: int = 20,
        compression_integration: Optional[CompressionIntegration] = None,
        check_compression_each_iteration: bool = True,
    ):
        """
        Args:
            llm_provider: LLM Provider
            session_id: 会话 ID
            model: 模型名称
            rails: Rail 列表
            max_iterations: 最大迭代次数
            compression_integration: 压缩集成器
            check_compression_each_iteration: 是否在每次迭代后检查压缩
        """
        super().__init__(
            llm_provider=llm_provider,
            session_id=session_id,
            model=model,
            rails=rails,
            max_iterations=max_iterations,
            compression_integration=compression_integration,
        )

        self.check_compression_each_iteration = check_compression_each_iteration

    async def run(self, context: "ReActContext") -> Dict[str, Any]:
        """运行压缩感知的 ReAct 循环"""
        self.logger.info(f"压缩感知 ReAct 循环开始: {context.task_description[:50]}...")

        self._state = LoopState.RUNNING
        self._steps.clear()

        compression_count = 0

        while self._state == LoopState.RUNNING:
            context.increment_iteration()

            if context.remaining_iterations <= 0:
                self.logger.warning(f"达到最大迭代次数 {self.max_iterations}")
                break

            self.logger.debug(
                f"迭代 {context.current_iteration}/{self.max_iterations}"
            )

            try:
                step_result = await self._execute_step(context)
                self._steps.append(step_result)

                if self.check_compression_each_iteration:
                    messages = context.get_messages()
                    if self._compression_integration.should_compress(messages):
                        compressed = self._compression_integration.compress(messages)
                        if compressed != messages:
                            context.replace_messages(compressed)
                            compression_count += 1
                            self.logger.info(
                                f"迭代后压缩 #{compression_count}: "
                                f"{len(messages)} -> {len(compressed)} messages"
                            )

                if step_result.action in ("direct_response", "ask_clarification"):
                    self._state = LoopState.COMPLETED
                    self.logger.info(
                        f"循环完成，迭代次数: {context.current_iteration}, "
                        f"压缩次数: {compression_count}"
                    )

            except Exception as e:
                self.logger.error(f"步骤执行错误: {e}")
                self._steps.append(StepResult(
                    step=context.current_iteration,
                    action="error",
                    result={"error": str(e)},
                    is_error=True
                ))
                self._state = LoopState.ABORTED
                break

        return self._build_result(context)


__all__ = [
    "CompressedReActLoop",
    "CompressionAwareReActLoop",
]