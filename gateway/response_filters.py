#!/usr/bin/env python3
# 🚪 Response Filters - Gateway response sanitization and policy enforcement.

"""
Response filters operate at the gateway boundary: they decide whether and how
a completed agent turn should be delivered to the chat (not what gets persisted
in conversation history).

Provides:
- API key / sensitive credential redaction
- Provider error sanitization (429 rate limits, 401 auth, 500 server errors)
- Intentional silence marker detection
- Text policy filters
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from common.logging_manager import get_logger

logger = get_logger("gateway.response_filters")

# ── API Key / Credential Redaction ───────────────────────────────────────────

# Patterns for sensitive credentials that must never be exposed to users.
_API_KEY_PATTERNS = [
    # OpenAI / generic API keys
    (re.compile(r'\b(sk-[A-Za-z0-9_-]{20,})(?:\b|$)', re.IGNORECASE), "[REDACTED_API_KEY]"),
    # Bearer tokens in Authorization headers
    (re.compile(r'(?i)(Bearer\s+)[A-Za-z0-9_\-\.]+'), r"\1[REDACTED_TOKEN]"),
    # Anthropic API keys
    (re.compile(r'\b(sk-ant-[A-Za-z0-9_-]{50,})(?:\b|$)', re.IGNORECASE), "[REDACTED_API_KEY]"),
    # Google API keys
    (re.compile(r'\b(AIza[A-Za-z0-9_-]{30,})(?:\b|$)', re.IGNORECASE), "[REDACTED_API_KEY]"),
    # Generic secret= / token= patterns
    (re.compile(r'(?i)(secret|token|api_key|apikey|password)\s*[=:]\s*["\']?([A-Za-z0-9_\-]{16,})["\']?', re.IGNORECASE),
     r"\1=[REDACTED]"),
    # URL-embedded credentials
    (re.compile(r'https?://[^:]+:[^@]+@(?:localhost|[\w.-]+\.[a-z]{2,})/\S*', re.IGNORECASE),
     "https://[REDACTED_CREDENTIALS]@..."),
    # AWS keys
    (re.compile(r'\b(AKIA[A-Z0-9]{16})\b', re.IGNORECASE), "[REDACTED_AWS_KEY]"),
    # GitHub tokens (lowercase only; ghp_ is always lowercase)
    (re.compile(r'(?:^|[^A-Za-z0-9])(ghp_[A-Za-z0-9]{20,})(?:^|[^A-Za-z0-9]|$)', re.IGNORECASE),
     "[REDACTED_GITHUB_TOKEN]"),
]


def redact_credentials(text: str) -> str:
    """Redact API keys, tokens, and other sensitive credentials from text.

    Uses multiple regex patterns to catch various credential formats.
    Runs in a single pass for efficiency.

    Args:
        text: The text to sanitize.

    Returns:
        Sanitized text with credentials replaced by placeholders.
    """
    if not text:
        return text

    for pattern, replacement in _API_KEY_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


# ── Provider Error Sanitization ───────────────────────────────────────────────

# HTTP status patterns and their user-friendly replacements.
_ERROR_STATUS_PATTERNS = [
    # 429 Rate limit
    (re.compile(r'(?i)(429|rate\s*limit|RateLimitExceeded|too\s*many\s*requests)', re.IGNORECASE),
     "⚠️ 请求过于频繁，请稍后再试。"),
    # 401 / 403 Auth errors
    (re.compile(r'(?i)(401|403|Unauthorized|Forbidden|invalid\s*api\s*key|authentication\s*failed)',
                re.IGNORECASE),
     "⚠️ 身份验证失败，请检查 API 配置。"),
    # 500 / 502 / 503 Server errors
    (re.compile(r'(?i)(500|502|503|Internal\s*Server\s*Error|Service\s*Unavailable|bad\s*gateway)',
                re.IGNORECASE),
     "⚠️ 服务端出现问题，请稍后再试。"),
    # Model not found / context length
    (re.compile(r'(?i)(context_length_exceeded|Maximum\s*context\s*length|model_not_found|model\s*does\s*not\s*exist)',
                re.IGNORECASE),
     "⚠️ 请求超出模型限制，请尝试更短的消息或切换模型。"),
    # Quota exceeded
    (re.compile(r'(?i)(quota\s*exceeded|insufficient\s*quota|billing\s*limit|out\s*of\s*credits)',
                re.IGNORECASE),
     "⚠️ API 配额已用尽，请检查账号余额或等待重置。"),
    # Connection timeout
    (re.compile(r'(?i)(connection\s*(?:timeout|error)|ConnectionTimeout|ConnectError|ReadTimeout)',
                re.IGNORECASE),
     "⚠️ 连接超时，请检查网络后重试。"),
]


def sanitize_provider_error(text: str) -> str:
    """Replace raw provider error messages with user-friendly Chinese text.

    Prevents leaking technical error details (status codes, stack traces)
    to end users through the chat.

    Args:
        text: The response text that may contain provider errors.

    Returns:
        Sanitized text with technical errors replaced by friendly messages.
    """
    if not text:
        return text

    for pattern, replacement in _ERROR_STATUS_PATTERNS:
        text = pattern.sub(replacement, text)

    return text


# ── Intentional Silence Detection ─────────────────────────────────────────────

# Exact whole-response markers that mean "the agent intentionally chose not to reply".
_LIVE_GATEWAY_SILENT_MARKERS = frozenset({
    "[SILENT]",
    "SILENT",
    "NO_REPLY",
    "NO REPLY",
    "(silent)",
    "[NO_REPLY]",
})


def _canonical_silence_candidate(text: str) -> str:
    return " ".join(text.strip().upper().split())


def _strip_edge_silence_punctuation(text: str) -> str:
    """Strip stray punctuation from edges without erasing marker structure."""
    start = 0
    end = len(text)
    while start < end and text[start] not in "[]" and unicodedata.category(text[start]).startswith("P"):
        start += 1
    while end > start and text[end - 1] not in "[]" and unicodedata.category(text[end - 1]).startswith("P"):
        end -= 1
    return text[start:end].strip()


def is_intentional_silence_response(response: Any) -> bool:
    """Return True only when ``response`` is exactly a silence marker.

    Substantive prose that merely mentions ``NO_REPLY`` must be delivered
    normally. A blank response is an error path, not silence.
    """
    if not isinstance(response, str):
        return False
    stripped = response.strip()
    if not stripped or len(stripped) > 64:
        return False
    exact = _canonical_silence_candidate(stripped)
    stripped2 = _strip_edge_silence_punctuation(stripped)
    fallback = _canonical_silence_candidate(stripped2) if stripped2 != stripped else None
    candidates = (exact,) if fallback is None else (exact, fallback)
    return any(c in _LIVE_GATEWAY_SILENT_MARKERS for c in candidates)


# ── Full Filter Pipeline ───────────────────────────────────────────────────────

# Controls whether to apply full sanitization or just critical redaction.
_SANITIZE_ALL = True  # Set to False to disable error-status rewriting (debug mode)


def filter_response(text: str, *, full_sanitize: bool = True) -> str:
    """Apply the full response filter pipeline.

    Order of operations:
    1. Redact API keys / credentials (always, never configurable)
    2. Sanitize provider errors (if full_sanitize=True)
    3. Return sanitized text

    Args:
        text: The raw agent response text.
        full_sanitize: If True, also apply error-status rewriting.

    Returns:
        Filtered, sanitized response text safe to deliver to users.
    """
    if not text:
        return text

    # Step 1: Credential redaction — always applied, never optional
    result = redact_credentials(text)

    # Step 2: Provider error sanitization
    if full_sanitize and _SANITIZE_ALL:
        result = sanitize_provider_error(result)

    # Step 3: Detect intentional silence (don't deliver empty-looking responses)
    if is_intentional_silence_response(result):
        # Return a sentinel that tells the caller to suppress delivery
        return ""

    return result


def filter_and_maybe_suppress(text: str) -> tuple[str, bool]:
    """Filter a response and return (filtered_text, should_suppress).

    Convenience wrapper for the gateway message handler.

    Args:
        text: The raw response text.

    Returns:
        A (filtered_text, should_suppress) tuple.
        ``should_suppress`` is True when the response is an intentional silence marker.
    """
    if not text:
        return text, False

    filtered = filter_response(text)
    should_suppress = is_intentional_silence_response(text)
    return filtered, should_suppress
