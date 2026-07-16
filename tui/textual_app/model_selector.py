#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ModelSelectorMixin — 模型下拉选择

🚪 Access - 💬 TUI - Textual App - Model Selector

v8.x 从 ``tui/textual_app/app.py`` L860–967 抽出：
- ``_get_configured_models`` 读取已配置模型
- ``_init_model_select`` 初始化下拉
- ``_on_model_selected`` 选中事件处理
- ``_show_custom_model_input`` / ``_handle_custom_model_input``

依赖主类的 ``self.notify`` / ``self._logger`` / ``self._builtin_models``。
"""

from __future__ import annotations

import logging

from .imports import Select, on  # type: ignore[attr-defined]
from .screens import CustomModelInputScreen

logger = logging.getLogger(__name__)


class ModelSelectorMixin:
    """模型下拉选择 Mixin."""

    _logger = logging.getLogger(__name__)
    _builtin_models: list = []

    # ------------------------------------------------------------------
    # 读取已配置模型
    # ------------------------------------------------------------------

    def _get_configured_models(self) -> list[tuple[str, str]]:
        """从用户配置中获取已配置的模型列表."""
        models: list[tuple[str, str]] = []

        # 1. 从 common.config 读取（跨端共享配置层）
        try:
            from common.config import load_config

            config = load_config()
            llm = config.get("llm", {})
            provider = llm.get("provider", "")
            model = llm.get("model", "")
            if provider and provider != "none" and model:
                models.append((f"{provider}/{model}", f"{provider}/{model}"))
        except (ImportError, Exception):
            pass

        # 2. 从 common.config.llm_providers 读取
        if not models:
            try:
                from common.config import get_settings

                providers = get_settings().llm_providers
                for p_name, p_cfg in providers.items():
                    if isinstance(p_cfg, dict) and p_cfg.get("enabled"):
                        model = p_cfg.get("model")
                        if model:
                            models.append((f"{p_name}/{model}", f"{p_name}/{model}"))
            except Exception:
                pass

        # 3. 如果还是没有配置，使用"未配置"提示
        if not models:
            models.append(("not_configured", "⚠️ 未配置，请先在设置中配置模型"))

        models.append(("custom", "其他..."))
        return models

    # ------------------------------------------------------------------
    # 初始化下拉
    # ------------------------------------------------------------------

    def _init_model_select(self) -> None:
        """初始化模型选择下拉菜单."""
        try:
            select_widget = self.query_one("#status-model", Select)

            if not self._builtin_models:
                self._logger.warning("No models configured, cannot init select")
                return

            # 找到第一个非 not_configured 的模型（使用 label，因为 allow_blank=False 时 label 就是 value）
            current_label = None
            for value, label in self._builtin_models:
                if value != "not_configured":
                    current_label = (
                        label  # 使用 label，因为 allow_blank=False 时 label 即 value
                    )
                    break

            # 如果没有配置任何有效模型，使用 not_configured
            if not current_label:
                current_label = self._builtin_models[0][1]  # 第一个的 label

            select_widget.value = current_label
            self._logger.debug(f"Model select initialized with: {current_label}")
        except Exception as e:
            self._logger.error(f"Failed to init model select: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # 选择变化
    # ------------------------------------------------------------------

    @on(Select.Changed)
    def _on_model_selected(self, event) -> None:
        """处理模型选择变化（仅预览，不真实切换）."""
        if event.control.id == "status-model":
            selected = event.value
            if selected == "custom":
                self._show_custom_model_input()
            elif selected == "not_configured":
                self.notify("⚠️ 请先在设置中配置 LLM 模型")
            elif selected:
                self._logger.info(f"Model preview: {selected}")
                self.notify(f"预览模型: {selected}")

    # ------------------------------------------------------------------
    # 自定义模型输入
    # ------------------------------------------------------------------

    def _show_custom_model_input(self) -> None:
        """显示自定义模型输入对话框."""
        self.push_screen(
            CustomModelInputScreen(on_submit=self._handle_custom_model_input),
        )

    def _handle_custom_model_input(self, value: str) -> None:
        """处理自定义模型输入（仅预览，不真实切换）."""
        if value and value.strip():
            # 仅显示预览，不真实切换模型
            try:
                select_widget = self.query_one("#status-model", Select)
                custom_model = value.strip()
                # 检查自定义模型是否已在列表中，不在则添加
                model_values = [opt[0] for opt in self._builtin_models]
                if custom_model not in model_values:
                    # 在 "其他..." 选项前插入自定义模型
                    custom_index = (
                        model_values.index("custom")
                        if "custom" in model_values
                        else len(self._builtin_models)
                    )
                    self._builtin_models.insert(
                        custom_index, (custom_model, custom_model)
                    )
                    select_widget.set_options(self._builtin_models)
                select_widget.value = custom_model
            except Exception:
                pass
            self._logger.info(f"Custom model preview: {value.strip()}")
            self.notify(f"预览自定义模型: {value.strip()}")


__all__ = ["ModelSelectorMixin"]