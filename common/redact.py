# 🔧 System - 敏感信息脱敏模块

"""
Redact Module - 敏感信息脱敏工具

提供敏感信息检测和脱敏功能：
1. API keys (OpenAI, GitHub, Anthropic, etc.)
2. Tokens 和 Bearer tokens
3. Passwords 和 credentials
4. Private keys
5. 数据库连接字符串

Usage:
    from common.redact import redact_sensitive_text, redact_messages

    # 单个文本脱敏
    safe_text = redact_sensitive_text(text)

    # 批量消息脱敏
    safe_messages = redact_messages(messages)
"""

import re
from typing import Any, Dict, List, Optional, Tuple

# 正则表达式模式
REDACTION_PATTERNS: List[Tuple[str, str]] = [
    # API Keys - 通用格式
    (r'(?i)(api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', r'\1: [REDACTED]'),

    # Bearer Tokens
    (r'(?i)(bearer|token|auth)\s+([a-zA-Z0-9_\-\.]{20,})', r'\1: [REDACTED]'),

    # Passwords
    (r'password\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?', r'password: [REDACTED]'),
    (r'(?i)passwd\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?', r'passwd: [REDACTED]'),

    # Private Keys
    (r'-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----[\s\S]+?-----END\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----', '[PRIVATE KEY REDACTED]'),
    (r'-----BEGIN\s+PRIVATE\s+KEY-----[\s\S]+?-----END\s+PRIVATE\s+KEY-----', '[PRIVATE KEY REDACTED]'),

    # AWS Keys
    (r'AKIA[0-9A-Z]{16}', '[AWS_KEY REDACTED]'),
    (r'(?i)aws[_-]?access[_-]?key[_-]?id\s*[:=]\s*["\']?([A-Z0-9]{20})["\']?', r'aws_access_key_id: [REDACTED]'),
    (r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?', r'aws_secret_access_key: [REDACTED]'),

    # GitHub Tokens
    (r'ghp_[a-zA-Z0-9]{36}', '[GITHUB_TOKEN REDACTED]'),
    (r'gho_[a-zA-Z0-9]{36}', '[GITHUB_TOKEN REDACTED]'),
    (r'github_pat_[a-zA-Z0-9_]{22,255}', '[GITHUB_PAT REDACTED]'),

    # OpenAI Keys
    (r'sk-[a-zA-Z0-9]{48}', '[OPENAI_KEY REDACTED]'),
    (r'sk-proj-[a-zA-Z0-9_-]{48,}', '[OPENAI_PROJECT_KEY REDACTED]'),

    # Anthropic Keys
    (r'sk-ant-[a-zA-Z0-9]{48}', '[ANTHROPIC_KEY REDACTED]'),
    (r'sk-ant-api[0-9a-f]{32}', '[ANTHROPIC_KEY REDACTED]'),

    # Google API Keys
    (r'AIza[0-9A-Za-z_-]{35}', '[GOOGLE_API_KEY REDACTED]'),

    # Stripe Keys
    (r'sk_live_[0-9a-zA-Z]{24}', '[STRIPE_LIVE_KEY REDACTED]'),
    (r'sk_test_[0-9a-zA-Z]{24}', '[STRIPE_TEST_KEY REDACTED]'),
    (r'rk_live_[0-9a-zA-Z]{24}', '[STRIPE_RESTRICTED_KEY REDACTED]'),

    # Database Connection Strings
    (r'(?i)mysql\+pymysql:\/\/[^:]+:[^@]+@', 'mysql+pymysql://[USER]:[REDACTED]@'),
    (r'(?i)postgres:\/\/[^:]+:[^@]+@', 'postgres://[USER]:[REDACTED]@'),
    (r'(?i)mongodb(\+srv)?:\/\/[^:]+:[^@]+@', 'mongodb+srv://[USER]:[REDACTED]@'),
    (r'(?i)redis:\/\/[^:]+:[^@]+@', 'redis://[REDACTED]:[REDACTED]@'),

    # Slack Tokens
    (r'xox[baprs]-[0-9]{10,12}-[0-9]{10,12}-[a-zA-Z0-9]{24}', '[SLACK_TOKEN REDACTED]'),

    # JWT Tokens
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[JWT REDACTED]'),

    # Generic Secret Patterns
    (r'(?i)(secret|token|credential|password|passwd|pwd)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?', r'\1: [REDACTED]'),
]

# URL 参数中的敏感字段
SENSITIVE_URL_PARAMS = {
    'api_key', 'apikey', 'api-key', 'secret', 'token', 'password', 'passwd',
    'access_token', 'access-token', 'auth_token', 'auth-token', 'private_key',
    'private-key', 'credentials', 'client_secret', 'client-secret',
}

# JSON 字段中的敏感字段
SENSITIVE_JSON_FIELDS = {
    'api_key', 'apiKey', 'api-key', 'secret_key', 'secretKey', 'secret-key',
    'password', 'passwd', 'pwd', 'token', 'access_token', 'accessToken',
    'auth_token', 'authToken', 'private_key', 'privateKey', 'private-key',
    'client_secret', 'clientSecret', 'client-secret', 'credentials',
    'aws_access_key', 'aws_secret_key', 'github_token', 'slack_token',
}


def redact_sensitive_text(text: str, replacement: str = "[REDACTED]") -> str:
    """
    脱敏单个文本中的敏感信息

    Args:
        text: 输入文本
        replacement: 替换文本（默认 [REDACTED]）

    Returns:
        脱敏后的文本
    """
    if not text:
        return text

    result = text

    for pattern, _ in REDACTION_PATTERNS:
        result = re.sub(pattern, replacement, result)

    return result


def redact_url(url: str) -> str:
    """
    脱敏 URL 中的敏感参数

    Args:
        url: 输入 URL

    Returns:
        脱敏后的 URL
    """
    if not url:
        return url

    try:
        from urllib.parse import urlparse, parse_qs, urlencode

        parsed = urlparse(url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        redacted_params = {}
        for key, values in query_params.items():
            if key.lower() in SENSITIVE_URL_PARAMS:
                redacted_params[key] = ['[REDACTED]']
            else:
                redacted_params[key] = values

        new_query = urlencode(redacted_params, doseq=True)
        return parsed._replace(query=new_query).geturl()

    except Exception:
        return url


def redact_json_value(key: str, value: Any) -> Any:
    """
    脱敏 JSON 中的敏感值

    Args:
        key: JSON 字段名
        value: 字段值

    Returns:
        脱敏后的值
    """
    key_lower = key.lower()

    if key_lower in SENSITIVE_JSON_FIELDS:
        if isinstance(value, str) and len(value) > 4:
            return "[REDACTED]"
        return value

    if isinstance(value, str):
        return redact_sensitive_text(value)

    return value


def redact_json(obj: Any, _seen: Optional[set] = None) -> Any:
    """
    递归脱敏 JSON 对象

    Args:
        obj: JSON 对象（dict, list, str, int, float, bool, None）
        _seen: 内部使用，防止循环引用

    Returns:
        脱敏后的对象
    """
    if _seen is None:
        _seen = set()

    obj_id = id(obj)
    if obj_id in _seen:
        return obj
    _seen.add(obj_id)

    if isinstance(obj, dict):
        return {
            k: redact_json_value(k, redact_json(v, _seen))
            for k, v in obj.items()
        }

    if isinstance(obj, list):
        return [redact_json(item, _seen) for item in obj]

    if isinstance(obj, str):
        return redact_sensitive_text(obj)

    return obj


def redact_message(message: Dict[str, Any], _seen: Optional[set] = None) -> Dict[str, Any]:
    """
    脱敏单个消息

    Args:
        message: 消息字典（包含 role, content, tool_calls 等）
        _seen: 内部使用，防止循环引用

    Returns:
        脱敏后的消息
    """
    if not isinstance(message, dict):
        return message

    if _seen is None:
        _seen = set()

    result = {}

    for key, value in message.items():
        if key == 'content':
            if isinstance(value, str):
                result[key] = redact_sensitive_text(value)
            elif isinstance(value, list):
                result[key] = [
                    redact_message_part(part, _seen) for part in value
                ]
            else:
                result[key] = value
        elif key == 'tool_calls':
            if isinstance(value, list):
                result[key] = [
                    redact_tool_call(tc, _seen) for tc in value
                ]
            else:
                result[key] = value
        elif key in ('tool_call_id', 'call_id'):
            result[key] = value
        else:
            result[key] = redact_json(value, _seen)

    return result


def redact_message_part(part: Any, _seen: Optional[set] = None) -> Any:
    """
    脱敏消息内容块

    Args:
        part: 消息部分（可能包含 text, image_url 等）
        _seen: 内部使用，防止循环引用

    Returns:
        脱敏后的部分
    """
    if not isinstance(part, dict):
        return part

    if _seen is None:
        _seen = set()

    ptype = part.get('type')

    if ptype == 'text':
        return {
            'type': 'text',
            'text': redact_sensitive_text(part.get('text', ''))
        }

    if ptype in ('image_url', 'input_image', 'image'):
        return part

    if 'text' in part:
        return {
            **part,
            'text': redact_sensitive_text(part.get('text', ''))
        }

    return part


def redact_tool_call(tool_call: Dict[str, Any], _seen: Optional[set] = None) -> Dict[str, Any]:
    """
    脱敏工具调用

    Args:
        tool_call: 工具调用字典
        _seen: 内部使用，防止循环引用

    Returns:
        脱敏后的工具调用
    """
    if not isinstance(tool_call, dict):
        return tool_call

    if _seen is None:
        _seen = set()

    result = {}

    for key, value in tool_call.items():
        if key == 'function':
            if isinstance(value, dict):
                fn = {}
                for fn_key, fn_value in value.items():
                    if fn_key == 'arguments':
                        if isinstance(fn_value, str):
                            redacted_args = redact_sensitive_text(fn_value)
                            try:
                                import json
                                parsed = json.loads(fn_value)
                                redacted_parsed = redact_json(parsed, _seen)
                                fn[fn_key] = json.dumps(redacted_parsed, ensure_ascii=False)
                            except Exception:
                                fn[fn_key] = redacted_args
                        else:
                            fn[fn_key] = redact_json(fn_value, _seen)
                    else:
                        fn[fn_key] = redact_sensitive_text(str(fn_value)) if isinstance(fn_value, str) else fn_value
                result[key] = fn
            else:
                result[key] = value
        else:
            result[key] = redact_json(value, _seen)

    return result


def redact_messages(messages: List[Dict[str, Any]], include_tool_calls: bool = True) -> List[Dict[str, Any]]:
    """
    批量脱敏消息列表

    Args:
        messages: 消息列表
        include_tool_calls: 是否脱敏工具调用（默认 True）

    Returns:
        脱敏后的消息列表
    """
    if not messages:
        return messages

    seen: set = set()

    return [
        redact_message(msg, seen) for msg in messages
    ]


def redact_summarizer_input(text: str) -> str:
    """
    脱敏用于摘要生成的内容

    与 redact_sensitive_text 不同，这个函数专门用于摘要生成场景，
    会保留更多的上下文信息，只移除真正敏感的部分。

    Args:
        text: 输入文本

    Returns:
        脱敏后的文本
    """
    if not text:
        return text

    result = text

    # 只移除最敏感的密钥格式
    critical_patterns = [
        (r'sk-[a-zA-Z0-9]{48}', '[API_KEY]'),
        (r'sk-ant-[a-zA-Z0-9]{48}', '[API_KEY]'),
        (r'ghp_[a-zA-Z0-9]{36}', '[TOKEN]'),
        (r'-----BEGIN\s+PRIVATE\s+KEY-----[\s\S]+?-----END\s+PRIVATE\s+KEY-----', '[PRIVATE_KEY]'),
        (r'AKIA[0-9A-Z]{16}', '[AWS_KEY]'),
        (r'AIza[0-9A-Za-z_-]{35}', '[GOOGLE_KEY]'),
    ]

    for pattern, replacement in critical_patterns:
        result = re.sub(pattern, replacement, result)

    return result


def check_has_sensitive(text: str) -> Tuple[bool, List[str]]:
    """
    检查文本是否包含敏感信息

    Args:
        text: 输入文本

    Returns:
        (是否包含敏感信息, 敏感信息类型列表)
    """
    if not text:
        return False, []

    found_types = []

    type_patterns = [
        (r'sk-[a-zA-Z0-9]{48}', 'openai_key'),
        (r'sk-ant-[a-zA-Z0-9]{48}', 'anthropic_key'),
        (r'ghp_[a-zA-Z0-9]{36}', 'github_token'),
        (r'-----BEGIN\s+.*PRIVATE\s+KEY-----', 'private_key'),
        (r'AKIA[0-9A-Z]{16}', 'aws_key'),
        (r'AIza[0-9A-Za-z_-]{35}', 'google_api_key'),
        (r'xox[baprs]-[0-9]{10,12}-[0-9]{10,12}', 'slack_token'),
        (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.', 'jwt_token'),
    ]

    for pattern, secret_type in type_patterns:
        if re.search(pattern, text):
            found_types.append(secret_type)

    return len(found_types) > 0, found_types


__all__ = [
    "redact_sensitive_text",
    "redact_url",
    "redact_json",
    "redact_message",
    "redact_messages",
    "redact_summarizer_input",
    "check_has_sensitive",
    "REDACTION_PATTERNS",
]