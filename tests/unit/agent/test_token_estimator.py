"""Tests for Token Estimator Module"""

import pytest
from agent.context.token_estimator import (
    get_model_context_length,
    get_model_family,
    estimate_tokens,
    estimate_message_tokens,
    estimate_messages_tokens_rough,
    estimate_request_tokens_rough,
    estimate_tool_schemas_tokens,
    estimate_system_prompt_tokens,
    calculate_compression_threshold,
    calculate_tail_token_budget,
    calculate_summary_budget,
    estimate_image_tokens,
    TokenBudget,
    get_model_info,
)


class TestGetModelContextLength:
    """测试 get_model_context_length 函数"""

    def test_gpt_4(self):
        """测试 GPT-4 上下文长度"""
        assert get_model_context_length("gpt-4") == 8192

    def test_gpt_4_turbo(self):
        """测试 GPT-4 Turbo 上下文长度"""
        assert get_model_context_length("gpt-4-turbo") == 128000

    def test_gpt_4o(self):
        """测试 GPT-4o 上下文长度"""
        assert get_model_context_length("gpt-4o") == 128000

    def test_gpt_3_5_turbo(self):
        """测试 GPT-3.5 Turbo 上下文长度"""
        assert get_model_context_length("gpt-3.5-turbo") == 16385

    def test_claude_3_opus(self):
        """测试 Claude 3 Opus 上下文长度"""
        assert get_model_context_length("claude-3-opus") == 200000

    def test_claude_3_5_sonnet(self):
        """测试 Claude 3.5 Sonnet 上下文长度"""
        assert get_model_context_length("claude-3.5-sonnet") == 200000

    def test_gemini_1_5_pro(self):
        """测试 Gemini 1.5 Pro 上下文长度"""
        assert get_model_context_length("gemini-1.5-pro") == 128000

    def test_unknown_model(self):
        """测试未知模型使用默认值"""
        context = get_model_context_length("xyz-unknown-model-xyz")
        assert context >= 8000


class TestGetModelFamily:
    """测试 get_model_family 函数"""

    def test_anthropic(self):
        """测试 Anthropic 模型家族"""
        assert get_model_family("claude-3-opus") == "anthropic"
        assert get_model_family("claude-3-sonnet") == "anthropic"

    def test_openai(self):
        """测试 OpenAI 模型家族"""
        assert get_model_family("gpt-4") == "openai"
        assert get_model_family("gpt-3.5-turbo") == "openai"

    def test_google(self):
        """测试 Google 模型家族"""
        assert get_model_family("gemini-1.5-pro") == "google"
        assert get_model_family("gemini-pro") == "google"

    def test_mistral(self):
        """测试 Mistral 模型家族"""
        assert get_model_family("mistral-large") == "mistral"
        assert get_model_family("mixtral-8x7b") == "mistral"

    def test_unknown(self):
        """测试未知模型家族"""
        assert get_model_family("unknown-model") == "unknown"


class TestEstimateTokens:
    """测试 estimate_tokens 函数"""

    def test_english_text(self):
        """测试英文文本 token 估算"""
        text = "Hello, how are you today?"
        tokens = estimate_tokens(text)
        assert tokens > 0
        assert tokens < len(text)

    def test_chinese_text(self):
        """测试中文文本 token 估算"""
        text = "你好，今天天气怎么样？"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_empty_text(self):
        """测试空文本"""
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0


class TestEstimateMessageTokens:
    """测试 estimate_message_tokens 函数"""

    def test_user_message(self):
        """测试用户消息"""
        message = {
            "role": "user",
            "content": "Hello, how are you?"
        }
        tokens = estimate_message_tokens(message)
        assert tokens > 0

    def test_assistant_message(self):
        """测试助手消息"""
        message = {
            "role": "assistant",
            "content": "I'm doing great, thank you!"
        }
        tokens = estimate_message_tokens(message)
        assert tokens > 0

    def test_message_with_tool_calls(self):
        """测试带工具调用的消息"""
        message = {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "test query"}'
                    }
                }
            ]
        }
        tokens = estimate_message_tokens(message)
        assert tokens > 0


class TestEstimateMessagesTokensRough:
    """测试 estimate_messages_tokens_rough 函数"""

    def test_empty_messages(self):
        """测试空消息列表"""
        assert estimate_messages_tokens_rough([]) == 0

    def test_single_message(self):
        """测试单条消息"""
        messages = [{"role": "user", "content": "Hello"}]
        tokens = estimate_messages_tokens_rough(messages)
        assert tokens > 0

    def test_multiple_messages(self):
        """测试多条消息"""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        tokens = estimate_messages_tokens_rough(messages)
        assert tokens > 0


class TestEstimateRequestTokensRough:
    """测试 estimate_request_tokens_rough 函数"""

    def test_with_system_prompt(self):
        """测试带系统提示的请求"""
        messages = [{"role": "user", "content": "Hello"}]
        system_prompt = "You are a helpful assistant."
        tokens = estimate_request_tokens_rough(messages, system_prompt)
        assert tokens > estimate_messages_tokens_rough(messages)

    def test_with_tool_schemas(self):
        """测试带工具 schema 的请求"""
        messages = [{"role": "user", "content": "Hello"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Search for information",
                    "parameters": {"type": "object"}
                }
            }
        ]
        tokens = estimate_request_tokens_rough(messages, tool_schemas=tools)
        assert tokens > estimate_messages_tokens_rough(messages)


class TestCalculateCompressionThreshold:
    """测试 calculate_compression_threshold 函数"""

    def test_default_threshold(self):
        """测试默认阈值"""
        threshold = calculate_compression_threshold("gpt-4", 0.50)
        assert threshold > 0
        assert threshold < get_model_context_length("gpt-4")

    def test_custom_threshold(self):
        """测试自定义阈值"""
        threshold = calculate_compression_threshold("gpt-4", 0.75)
        assert threshold >= 8000
        assert threshold > 6000


class TestCalculateTailTokenBudget:
    """测试 calculate_tail_token_budget 函数"""

    def test_default_budget(self):
        """测试默认预算"""
        budget = calculate_tail_token_budget("gpt-4")
        assert budget > 0

    def test_with_threshold(self):
        """测试带阈值的预算"""
        threshold = 10000
        budget = calculate_tail_token_budget("gpt-4", threshold_tokens=threshold)
        expected = int(threshold * 0.20)
        assert abs(budget - expected) <= 1


class TestTokenBudget:
    """测试 TokenBudget 类"""

    @pytest.fixture
    def budget(self):
        """创建 TokenBudget 实例"""
        return TokenBudget("gpt-4o", 0.50, 0.20)

    def test_init(self, budget):
        """测试初始化"""
        assert budget.model == "gpt-4o"
        assert budget.context_length == 128000
        assert budget.threshold_percent == 0.50

    def test_should_compress(self, budget):
        """测试压缩判断"""
        assert budget.should_compress(100000) is True
        assert budget.should_compress(10000) is False

    def test_remaining_budget(self, budget):
        """测试剩余预算"""
        remaining = budget.remaining_budget(50000)
        assert remaining >= 0

    def test_compression_ratio(self, budget):
        """测试压缩比率"""
        ratio = budget.compression_ratio(64000)
        assert 0 <= ratio <= 1.0


class TestEstimateImageTokens:
    """测试 estimate_image_tokens 函数"""

    def test_low_detail(self):
        """测试低细节级别"""
        tokens = estimate_image_tokens(2, detail="low")
        assert tokens == 170

    def test_high_detail(self):
        """测试高细节级别"""
        tokens = estimate_image_tokens(2, detail="high")
        assert tokens == 3400

    def test_auto_detail(self):
        """测试自动细节级别"""
        tokens = estimate_image_tokens(2, detail="auto")
        assert tokens == 1700


class TestGetModelInfo:
    """测试 get_model_info 函数"""

    def test_gpt_4o_info(self):
        """测试 GPT-4o 模型信息"""
        info = get_model_info("gpt-4o")
        assert info["model"] == "gpt-4o"
        assert info["context_length"] == 128000
        assert info["family"] == "openai"

    def test_claude_info(self):
        """测试 Claude 模型信息"""
        info = get_model_info("claude-3-opus")
        assert info["family"] == "anthropic"