#!/usr/bin/env python3
# 🚪 Delivery - Media tag parsing and rich media delivery router for Agent-Z Gateway.

"""
Delivery router for routing agent responses (especially rich media) to the right
destination through platform adapters.

Supports parsing special tags from agent response text:
- [IMAGE:url] or [IMAGE:url|caption] or ![IMAGE](url) or ![IMAGE](url|caption)
- [AUDIO:url] or [AUDIO:url|caption]
- [FILE:url] or [FILE:url|filename]
- [VIDEO:url] or [VIDEO:url|caption]
- [MEDIA:url|type] or [MEDIA:url]
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, List, Optional

from common.logging_manager import get_logger

logger = get_logger("gateway.delivery")

# ── Regex patterns for media tag parsing ───────────────────────────────────────

# Matches: [IMAGE:url], [IMAGE:url|caption], ![IMAGE](url), ![IMAGE](url|caption)
IMAGE_PATTERN = re.compile(
    r'!?\[IMAGE(?:_URL)?:([^\]|]+)(?:\|([^\]]*))?\]|\[IMAGE\]\(([^)]+)\)'
)
# Matches: [AUDIO:url] or [AUDIO:url|caption]
AUDIO_PATTERN = re.compile(r'\[AUDIO:([^\]|]+)(?:\|([^\]]*))?\]')
# Matches: [FILE:url] or [FILE:url|filename]
FILE_PATTERN = re.compile(r'\[FILE:([^\]|]+)(?:\|([^\]]*))?\]')
# Matches: [VIDEO:url] or [VIDEO:url|caption]
VIDEO_PATTERN = re.compile(r'\[VIDEO:([^\]|]+)(?:\|([^\]]*))?\]')
# Matches: [MEDIA:url] or [MEDIA:url|type]
MEDIA_GENERIC_PATTERN = re.compile(r'\[MEDIA:([^\]|]+)(?:\|([^\]]*))?\]')

# ── Constants ──────────────────────────────────────────────────────────────────

MAX_PLATFORM_OUTPUT = 4000

# ── Dataclasses ───────────────────────────────────────────────────────────────


@dataclass
class MediaItem:
    """A single media item extracted from response text."""

    kind: str  # "image", "audio", "file", "video"
    url: str
    caption: Optional[str] = None
    raw_tag: str = ""  # The original tag text for reference


@dataclass
class ParsedContent:
    """A parsed response with separate text and media items."""

    text_parts: List[str] = field(default_factory=list)
    media_items: List[MediaItem] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Returns the text parts joined with newlines."""
        return "\n".join(self.text_parts)

    @property
    def has_media(self) -> bool:
        """Returns True if there are any media items."""
        return len(self.media_items) > 0


# ── Parsing ───────────────────────────────────────────────────────────────────

_ALL_TAG_PATTERNS: List[tuple[str, re.Pattern, str]] = [
    ("image", IMAGE_PATTERN, "IMAGE"),
    ("audio", AUDIO_PATTERN, "AUDIO"),
    ("file", FILE_PATTERN, "FILE"),
    ("video", VIDEO_PATTERN, "VIDEO"),
    ("media", MEDIA_GENERIC_PATTERN, "MEDIA"),
]


def parse_content(text: str) -> ParsedContent:
    """Parse text and extract media items and clean text parts.

    Args:
        text: The raw response text containing optional media tags.

    Returns:
        ParsedContent with stripped text_parts and extracted media_items.
    """
    if not text:
        return ParsedContent()

    # Track all matches to replace them with placeholders
    matches: List[tuple[str, str, str]] = []  # (raw_tag, kind, url, caption)

    # Find all media tags
    for kind, pattern, tag_name in _ALL_TAG_PATTERNS:
        for match in pattern.finditer(text):
            # Extract url and caption from match groups
            groups = match.groups()
            if tag_name == "IMAGE" and len(groups) >= 3:
                # IMAGE pattern has 3 groups: url1, caption1, url2
                url = (groups[0] or groups[2]) if groups[2] else groups[0]
                caption = groups[1] or ""
            else:
                url = groups[0] if groups else ""
                caption = groups[1] if len(groups) > 1 and groups[1] else ""

            url = url.strip() if url else ""
            caption = caption.strip() if caption else None

            if url:
                raw_tag = match.group(0)
                matches.append((raw_tag, kind, url, caption))

    # Replace all media tags with empty string
    cleaned = text
    for raw_tag, _, _, _ in matches:
        cleaned = cleaned.replace(raw_tag, "")

    # Normalize multiple whitespace (left by tag removal) and split into lines
    cleaned = re.sub(r" {2,}", " ", cleaned)  # collapse double spaces
    text_parts = [p.strip() for p in cleaned.split("\n") if p.strip()]

    # Build MediaItem list
    media_items = [
        MediaItem(kind=kind, url=url, caption=caption, raw_tag=raw_tag)
        for raw_tag, kind, url, caption in matches
    ]

    return ParsedContent(text_parts=text_parts, media_items=media_items)


# ── Delivery ──────────────────────────────────────────────────────────────────


def _call_adapter_method(
    adapter: Any, method_name: str, *args: Any, **kwargs: Any
) -> Any:
    """Call an adapter method, handling both sync and async functions."""
    fn = getattr(adapter, method_name, None)
    if fn is None or not callable(fn):
        return None

    # Check if it's an async function
    if asyncio.iscoroutinefunction(fn):
        # Return a coroutine that the caller should await
        return fn(*args, **kwargs)

    # Sync function - call directly
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        logger.warning(
            "Adapter method %s raised: %s", method_name, exc
        )
        return None


async def _send_text(adapter: Any, chat_id: str, text: str, **kwargs: bool) -> bool:
    """Send text through the adapter. Returns True on success."""
    # Try send() first
    fn = getattr(adapter, "send", None)
    if fn and callable(fn):
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn(chat_id, text, **kwargs)
            else:
                fn(chat_id, text, **kwargs)
            return True
        except Exception as exc:
            logger.warning("adapter.send() failed: %s", exc)

    # Fallback to send_message
    fn = getattr(adapter, "send_message", None)
    if fn and callable(fn):
        try:
            if asyncio.iscoroutinefunction(fn):
                await fn(chat_id, text, **kwargs)
            else:
                fn(chat_id, text, **kwargs)
            return True
        except Exception as exc:
            logger.warning("adapter.send_message() failed: %s", exc)

    return False


async def _send_media_item(
    adapter: Any, chat_id: str, item: MediaItem, **kwargs: Any
) -> bool:
    """Send a single media item through the adapter. Returns True on success."""
    kind = item.kind
    url = item.url
    caption = item.caption

    try:
        if kind == "image":
            # Try send_image first
            fn = getattr(adapter, "send_image", None)
            if fn and callable(fn):
                if asyncio.iscoroutinefunction(fn):
                    await fn(chat_id, url, caption=caption, **kwargs)
                else:
                    fn(chat_id, url, caption=caption, **kwargs)
                return True
            # Fallback to text with image link
            text = f"[图片]({url})" if caption else f"[图片]({url})"
            if caption:
                text = f"{caption}\n{text}"
            return await _send_text(adapter, chat_id, text, **kwargs)

        elif kind == "audio":
            fn = getattr(adapter, "send_audio", None)
            if fn and callable(fn):
                if asyncio.iscoroutinefunction(fn):
                    await fn(chat_id, url, caption=caption, **kwargs)
                else:
                    fn(chat_id, url, caption=caption, **kwargs)
                return True
            # Fallback to text
            text = f"[音频]({url})"
            if caption:
                text = f"{caption}\n{text}"
            return await _send_text(adapter, chat_id, text, **kwargs)

        elif kind == "file":
            fn = getattr(adapter, "send_file", None)
            if fn and callable(fn):
                filename = caption or "file"
                if asyncio.iscoroutinefunction(fn):
                    await fn(chat_id, url, filename=filename, **kwargs)
                else:
                    fn(chat_id, url, filename=filename, **kwargs)
                return True
            # Fallback to text
            text = f"[文件]({url})" if not caption else f"[{caption}]({url})"
            return await _send_text(adapter, chat_id, text, **kwargs)

        elif kind in ("video", "media"):
            fn = getattr(adapter, "send_video", None)
            if fn and callable(fn):
                if asyncio.iscoroutinefunction(fn):
                    await fn(chat_id, url, caption=caption, **kwargs)
                else:
                    fn(chat_id, url, caption=caption, **kwargs)
                return True
            # Fallback to text
            text = f"[视频]({url})"
            if caption:
                text = f"{caption}\n{text}"
            return await _send_text(adapter, chat_id, text, **kwargs)

        else:
            # Unknown kind, try generic send
            logger.warning("Unknown media kind: %s", kind)
            return await _send_text(adapter, chat_id, f"[媒体]({url})", **kwargs)

    except Exception as exc:
        logger.warning(
            "Failed to send %s media (%s): %s", kind, url, exc
        )
        return False


async def send_parsed_content(
    adapter: Any, chat_id: str, parsed: ParsedContent, **kwargs: Any
) -> bool:
    """Send the parsed content through the adapter.

    Args:
        adapter: The platform adapter instance.
        chat_id: The target chat/user ID.
        parsed: ParsedContent with text_parts and media_items.
        **kwargs: Additional arguments to pass to send methods.

    Returns:
        True if all sends succeeded, False otherwise.
    """
    if not parsed:
        return False

    has_text = bool(parsed.text_parts)
    has_media = parsed.has_media

    # Case 1: Text and media - send text first, then each media item
    if has_text and has_media:
        text = parsed.text
        if not await _send_text(adapter, chat_id, text, **kwargs):
            logger.warning("Failed to send text for media message")
            return False

        all_ok = True
        for item in parsed.media_items:
            if not await _send_media_item(adapter, chat_id, item, **kwargs):
                logger.warning("Failed to send media item: %s", item.url)
                all_ok = False
        return all_ok

    # Case 2: Text only
    if has_text:
        return await _send_text(adapter, chat_id, parsed.text, **kwargs)

    # Case 3: Media only (no text)
    if has_media:
        all_ok = True
        for item in parsed.media_items:
            if not await _send_media_item(adapter, chat_id, item, **kwargs):
                logger.warning("Failed to send media item: %s", item.url)
                all_ok = False
        return all_ok

    # Case 4: Nothing
    return False


async def send_with_delivery(
    adapter: Any, chat_id: str, content: str, **kwargs: Any
) -> bool:
    """Main entry point for sending content with delivery routing.

    Parses the content for media tags and routes appropriately.

    Args:
        adapter: The platform adapter instance.
        chat_id: The target chat/user ID.
        content: The raw content text (may contain media tags).
        **kwargs: Additional arguments to pass to send methods.

    Returns:
        True if send succeeded, False otherwise.
    """
    if not content:
        return False

    try:
        parsed = parse_content(content)

        if parsed.has_media:
            return await send_parsed_content(adapter, chat_id, parsed, **kwargs)
        else:
            # No media tags - just send the text
            return await _send_text(adapter, chat_id, content, **kwargs)

    except Exception as exc:
        logger.error("send_with_delivery failed: %s", exc)
        # Fallback to plain text send on parse error
        try:
            return await _send_text(adapter, chat_id, content, **kwargs)
        except Exception:
            return False


# ── Utilities ────────────────────────────────────────────────────────────────


def truncate_for_platform(
    text: str, max_length: int = MAX_PLATFORM_OUTPUT
) -> str:
    """Truncate text to max_length, appending truncation notice if needed.

    Args:
        text: The text to truncate.
        max_length: Maximum allowed length (default: MAX_PLATFORM_OUTPUT).

    Returns:
        Truncated text with "… (output truncated)" appended if it was truncated.
    """
    if not text:
        return text

    if len(text) <= max_length:
        return text

    truncation_marker = "… (output truncated)"
    # Ensure we have room for the truncation marker
    available = max_length - len(truncation_marker)
    if available < 0:
        available = max_length // 2

    return text[:available] + truncation_marker
