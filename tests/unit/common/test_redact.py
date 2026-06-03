"""Tests for Redact Module - 敏感信息脱敏模块测试"""

import pytest
from common.redact import (
    redact_sensitive_text,
    redact_url,
    redact_json,
    redact_message,
    redact_messages,
    redact_summarizer_input,
    check_has_sensitive,
)


class TestRedactSensitiveText:
    """测试 redact_sensitive_text 函数"""

    def test_no_sensitive(self):
        """测试无敏感信息文本"""
        text = "Hello, how are you today?"
        result = redact_sensitive_text(text)
        assert result == text

    def test_api_key_format(self):
        """测试通用 API Key 格式脱敏"""
        text = "api_key: sk-1234567890abcdefghijklmnop"
        result = redact_sensitive_text(text)
        assert "sk-" not in result

    def test_password(self):
        """测试密码脱敏"""
        text = "password: MySecretPassword123"
        result = redact_sensitive_text(text)
        assert "MySecretPassword123" not in result
        assert "[REDACTED]" in result

    def test_github_token(self):
        """测试 GitHub Token 脱敏"""
        text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456"
        result = redact_sensitive_text(text)
        assert "ghp_" not in result

    def test_empty_text(self):
        """测试空文本"""
        assert redact_sensitive_text("") == ""
        assert redact_sensitive_text(None) is None


class TestRedactUrl:
    """测试 redact_url 函数"""

    def test_normal_url(self):
        """测试普通 URL"""
        url = "https://api.example.com/users?id=123"
        result = redact_url(url)
        assert "123" in result

    def test_url_with_api_key(self):
        """测试带 API Key 的 URL"""
        url = "https://api.example.com?api_key=secret1234567890"
        result = redact_url(url)
        assert "api_key=secret1234567890" not in result


class TestRedactJson:
    """测试 redact_json 函数"""

    def test_simple_dict(self):
        """测试简单字典脱敏"""
        data = {
            "name": "John",
            "secret_key": "secret123456789",
            "value": 42
        }
        result = redact_json(data)
        assert result["name"] == "John"
        assert result["secret_key"] == "[REDACTED]"
        assert result["value"] == 42

    def test_empty(self):
        """测试空对象"""
        assert redact_json({}) == {}
        assert redact_json([]) == []


class TestRedactMessage:
    """测试 redact_message 函数"""

    def test_simple_message(self):
        """测试简单消息脱敏"""
        message = {
            "role": "user",
            "content": "Hello, this is a test"
        }
        result = redact_message(message)
        assert result["role"] == "user"
        assert result["content"] == "Hello, this is a test"

    def test_message_with_tool_calls(self):
        """测试包含工具调用的消息"""
        message = {
            "role": "assistant",
            "content": "I'll help you",
            "tool_calls": [
                {
                    "id": "call_123",
                    "function": {
                        "name": "search",
                        "arguments": '{"query": "test"}'
                    }
                }
            ]
        }
        result = redact_message(message)
        assert result["tool_calls"][0]["function"]["name"] == "search"


class TestRedactMessages:
    """测试 redact_messages 函数"""

    def test_multiple_messages(self):
        """测试批量消息脱敏"""
        messages = [
            {"role": "user", "content": "Hello world"},
            {"role": "assistant", "content": "I see"},
            {"role": "user", "content": "Test message"},
        ]
        result = redact_messages(messages)
        assert len(result) == 3
        assert result[0]["content"] == "Hello world"

    def test_empty_messages(self):
        """测试空消息列表"""
        assert redact_messages([]) == []
        assert redact_messages(None) is None


class TestRedactSummarizerInput:
    """测试 redact_summarizer_input 函数"""

    def test_preserves_context(self):
        """测试保留上下文信息"""
        text = "User asked me to help with Python coding."
        result = redact_summarizer_input(text)
        assert "Python" in result
        assert "coding" in result


class TestCheckHasSensitive:
    """测试 check_has_sensitive 函数"""

    def test_no_sensitive(self):
        """测试无敏感信息"""
        has_sensitive, types = check_has_sensitive("Hello, how are you?")
        assert has_sensitive is False
        assert len(types) == 0

    def test_github_token(self):
        """测试检测 GitHub Token"""
        text = "ghp_1234567890abcdefghijklmnopqrstuvwxyz123456"
        has_sensitive, types = check_has_sensitive(text)
        assert has_sensitive is True
        assert "github_token" in types