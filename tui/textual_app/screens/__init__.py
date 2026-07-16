#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Textual App Modal/Dialog Screens

🚪 Access - 💬 TUI - Textual App - Screens

v8.x 子包：原内嵌在 ``app.py`` 末尾的 ``CustomModelInputScreen`` 类
迁移至 ``screens/custom_model.py``。

外部导入仍可走 ``from tui.textual_app import CustomModelInputScreen``，
由 ``tui/textual_app/__init__.py`` 提供 re-export。
"""

from .custom_model import CustomModelInputScreen

__all__ = ["CustomModelInputScreen"]