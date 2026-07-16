#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CustomModelInputScreen — 自定义模型输入弹窗

🚪 Access - 💬 TUI - Textual App - Screens - CustomModelInputScreen

v8.x 从 ``tui/textual_app/app.py`` L2662–2694 抽出。

CSS 来自 ``tui.textual_app.css.screens.CUSTOM_MODEL_SCREEN_CSS``，
避免与 ``app.py`` 主样式表混淆。
"""

from __future__ import annotations

import logging

from ..css.screens import CUSTOM_MODEL_SCREEN_CSS
from ..imports import (
    TEXTUAL_AVAILABLE,
    Button,
    ComposeResult,
    Container,
    Input,
    Static,
    TextualScreen,
)

logger = logging.getLogger(__name__)


# ============================================================================
# CustomModelInputScreen
# ============================================================================


class CustomModelInputScreen(TextualScreen if TEXTUAL_AVAILABLE else object):
    """自定义模型输入对话框.

    v8.x: CSS 已迁移到 ``tui.textual_app.css.screens`` 子模块。
    """

    CSS = CUSTOM_MODEL_SCREEN_CSS

    def __init__(self, on_submit=None, **kwargs):
        super().__init__(**kwargs)
        self._on_submit = on_submit

    def compose(self):
        with Container(id="dialog"):
            yield Static("输入自定义模型名称", id="title")
            with Container(id="input-container"):
                yield Input(placeholder="例如: custom-model-v1", id="model-input")
            with Container(id="buttons"):
                yield Button("确认", id="btn-submit", variant="primary")
                yield Button("取消", id="btn-cancel", variant="default")

    def on_button_pressed(self, event) -> None:
        if event.button.id == "btn-submit":
            input_widget = self.query_one("#model-input", Input)
            value = input_widget.value.strip()
            if value and self._on_submit:
                self.dismiss(value)
        elif event.button.id == "btn-cancel":
            self.dismiss(None)


__all__ = ["CustomModelInputScreen"]