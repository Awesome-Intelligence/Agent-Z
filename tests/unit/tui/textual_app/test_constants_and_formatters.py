#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for tui.textual_app constants + core formatters

🚪 Access - 💬 Tests - TUI - Textual App - 常量与格式化

覆盖：
- constants 模块导出所有 PURPLE_*/STATUS_* 颜色
- core.formatters 各种 token 数字格式化
"""

from __future__ import annotations


class TestTextualAppConstants:
    """Textual App 颜色与状态常量."""

    def test_purple_colors_exported(self):
        from tui.textual_app.constants import (
            PURPLE_PRIMARY,
            PURPLE_BRIGHT,
            PURPLE_DIM,
            PURPLE_DARK,
        )

        for c in (PURPLE_PRIMARY, PURPLE_BRIGHT, PURPLE_DIM, PURPLE_DARK):
            assert c.startswith("#")
            assert len(c) == 7

    def test_status_colors_exported(self):
        from tui.textual_app.constants import (
            STATUS_ONLINE,
            STATUS_BUSY,
            STATUS_ERROR,
        )

        for c in (STATUS_ONLINE, STATUS_BUSY, STATUS_ERROR):
            assert c.startswith("#")

    def test_constants_have_expected_default_values(self):
        """默认值稳定（主题颜色基线）."""
        from tui.textual_app.constants import PURPLE_PRIMARY, STATUS_ONLINE

        assert PURPLE_PRIMARY == "#B180D7"
        assert STATUS_ONLINE == "#3fb950"


class TestCoreFormatters:
    """tui.core.formatters 纯函数."""

    def test_none_returns_question_mark(self):
        from tui.core.formatters import format_token_count

        assert format_token_count(None) == "?"
        assert format_token_count(0) == "?"

    def test_negative_returns_as_str(self):
        """负数实现是 str() 直传（不主动转 ?）— 这是当前行为."""
        from tui.core.formatters import format_token_count

        assert format_token_count(-1) == "-1"

    def test_small_number_returns_as_str(self):
        from tui.core.formatters import format_token_count

        assert format_token_count(500) == "500"
        assert format_token_count(999) == "999"

    def test_thousands_format_k(self):
        from tui.core.formatters import format_token_count

        # 接近整数
        assert format_token_count(1000) == "1K"
        assert format_token_count(2000) == "2K"
        # 1 位小数（1500/1000=1.5, round=2, abs(1.5-2)=0.5 > 0.05, → "1.5K"）
        assert format_token_count(1500) == "1.5K"
        # 12345/1000=12.345, round=12, abs(0.345)>0.05, → "12.3K"
        assert format_token_count(12345) == "12.3K"

    def test_millions_format_m(self):
        from tui.core.formatters import format_token_count

        assert format_token_count(1_000_000) == "1M"
        assert format_token_count(128_000_000) == "128M"
        assert format_token_count(1_200_000) == "1.2M"

    def test_alias_format_context_works(self):
        """format_context 是 format_token_count 的别名."""
        from tui.core.formatters import format_context, format_token_count

        assert format_context is format_token_count
        assert format_context(1500) == "1.5K"
