#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SlashCompletionMixin — 斜杠命令补全浮层

🚪 Access - 💬 TUI - Textual App - Slash Completion

v8.x 从 ``tui/textual_app/app.py`` L1024–1090 抽出：
- ``_dismiss_slash_palette`` 关闭浮层
- ``_bind_slash_completion`` 绑定浮层回调（show/update/confirm/dismiss）
- ``_on_input_area_click`` 点击输入区域时关闭浮层

依赖主类的 ``self.query_one`` / ``self._logger`` / ``self._widget_cache``。
"""

from __future__ import annotations

from tui.widgets.slash_completion import SlashCompletionList

from .text_area import SubmitTextArea
from common.logging_manager import get_access_logger


class SlashCompletionMixin:
    """斜杠命令补全浮层 Mixin."""

    _logger = get_access_logger("slash_completion_bind")

    # ------------------------------------------------------------------
    # 浮层关闭
    # ------------------------------------------------------------------

    def _dismiss_slash_palette(self) -> None:
        """关闭斜杠补全浮层."""
        try:
            completion = self.query_one("#slash-completion", SlashCompletionList)
            text_area = self.query_one("#user-input", SubmitTextArea)
            completion.set_class(False, "visible")
            completion.clear()
            text_area._slash_snapshot = None
        except Exception:
            pass

    # ------------------------------------------------------------------
    # 浮层回调绑定
    # ------------------------------------------------------------------

    def _bind_slash_completion(self) -> None:
        """绑定斜杠命令补全浮层的回调."""
        try:
            text_area = self.query_one("#user-input", SubmitTextArea)
            completion = self.query_one("#slash-completion", SlashCompletionList)
        except Exception as e:
            self._logger.warning(f"Failed to bind slash completion: {e}")
            return

        def show_palette():
            completion.dismiss()  # 先清空再显示
            completion.set_class(True, "visible")

        def update_filter(query: str):
            completion.filter_commands(query)

        def confirm_and_insert() -> str | None:
            cmd = completion.insert_selected()
            if cmd:
                snapshot = text_area._slash_snapshot
                if snapshot:
                    snapshot_text, _ = snapshot
                    # 用快照长度定位 / 位置，截断 / 之后的内容并替换为完整命令
                    slash_text_len = len(snapshot_text)
                    text_area.text = text_area.text[:slash_text_len] + cmd
                    text_area.cursor_location = slash_text_len + len(cmd)
                completion.dismiss()
                text_area._slash_snapshot = None
            return cmd

        def dismiss_palette():
            completion.dismiss()
            text_area._slash_snapshot = None

        text_area.slash_show = show_palette
        text_area.slash_update = update_filter
        text_area.slash_complete = confirm_and_insert
        text_area.slash_dismiss = dismiss_palette

        completion.on_dismiss = dismiss_palette

    # ------------------------------------------------------------------
    # 点击行为
    # ------------------------------------------------------------------

    def _on_input_area_click(self, event) -> None:
        """点击输入区域时，若点击的不是补全列表则关闭浮层."""
        try:
            completion = self.query_one("#slash-completion", SlashCompletionList)
            if not completion.has_class("visible"):
                return
            # query_one 会抛出如果点击目标在 completion 内
            self.query_one("#slash-completion", SlashCompletionList)
        except Exception:
            # 点击不在 completion 内，关闭浮层
            self._dismiss_slash_palette()


__all__ = ["SlashCompletionMixin"]