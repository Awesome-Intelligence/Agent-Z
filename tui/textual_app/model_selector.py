#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ModelSelectorMixin — 模型下拉选择

🚪 Access - 💬 TUI - Textual App - Model Selector

v8.x 从 ``tui/textual_app/app.py`` L860–967 抽出：
- ``_get_configured_models`` 读取已配置模型
- ``_init_model_select`` 初始化下拉
- ``_on_model_selected`` 选中事件处理
- ``_apply_model_switch`` 真实切换并持久化

依赖主类的 ``self.notify`` / ``self._logger`` / ``self._builtin_models``。
"""

from __future__ import annotations

import logging

from common.logging_manager import get_access_logger
from .imports import Select, on  # type: ignore[attr-defined]

logger = get_access_logger("model_selector")


class ModelSelectorMixin:
    """模型下拉选择 Mixin."""

    _logger = get_access_logger("model_selector")
    _builtin_models: list = []

    # ------------------------------------------------------------------
    # 读取已配置模型
    # ------------------------------------------------------------------

    def _get_configured_models(self) -> list[tuple[str, str]]:
        """从用户配置中获取已配置的模型列表.

        Returns:
            list[tuple[label, value]] —— 遵循 Textual Select API 签名
            Iterable[tuple[RenderableType, SelectType]]：
            - label（第 1 个元素）：界面显示名，只显示模型名（精简）
            - value（第 2 个元素）：内部真实值，完整 "provider/model" 格式
        """
        models: list[tuple[str, str]] = []
        seen: set[str] = set()

        def _display_name(provider: str, model: str) -> str:
            """生成显示名称：有 model 显示 model，否则显示 provider."""
            return model if model else provider

        def _add(label: str, value: str) -> None:
            if value and value not in seen:
                seen.add(value)
                models.append((label, value))

        try:
            from common.config import load_config

            config = load_config()

            # 1. 从 config.providers 读取所有已配置的 provider
            providers = config.get("providers", {}) or {}
            for p_name, p_cfg in providers.items():
                if not isinstance(p_cfg, dict):
                    continue
                model = p_cfg.get("model") or ""
                if p_name and p_name != "none":
                    value = f"{p_name}/{model}" if model else p_name
                    _add(_display_name(p_name, model), value)

            # 2. 从 config.llm 读取当前激活的 provider/model（确保它在列表最前）
            llm = config.get("llm", {}) or {}
            active_provider = llm.get("provider", "") or ""
            active_model = llm.get("model", "") or ""
            if active_provider and active_provider != "none":
                active_value = (
                    f"{active_provider}/{active_model}"
                    if active_model
                    else active_provider
                )
                active_label = _display_name(active_provider, active_model)
                # 如果激活模型已在列表中，把它移到最前
                if active_value in seen:
                    models = [(l, v) for l, v in models if v != active_value]
                    models.insert(0, (active_label, active_value))
                else:
                    models.insert(0, (active_label, active_value))
                    seen.add(active_value)

            # 3. 从 fallback_providers 读取备选模型
            fallbacks = config.get("fallback_providers", []) or []
            for fb in fallbacks:
                if isinstance(fb, dict):
                    fb_provider = fb.get("provider", "") or ""
                    fb_model = fb.get("model", "") or ""
                    if fb_provider and fb_provider != "none":
                        fb_value = (
                            f"{fb_provider}/{fb_model}" if fb_model else fb_provider
                        )
                        _add(_display_name(fb_provider, fb_model), fb_value)
        except (ImportError, Exception) as e:
            self._logger.warning(f"Failed to load configured models: {e}")

        # 4. 如果还是没有配置，使用"未配置"提示
        if not models:
            models.append(("⚠️ 未配置，请先在设置中配置模型", "not_configured"))

        return models

    def _refresh_model_selector(self) -> None:
        """重新读取配置并刷新模型选择下拉菜单（设置保存后调用）."""
        try:
            new_models = self._get_configured_models()
            self._builtin_models = new_models

            # 更新 Select widget 选项
            select_widget = self._widget_cache.get("status_model")
            if select_widget is None:
                try:
                    from .imports import Select

                    select_widget = self.query_one("#status-model", Select)
                except Exception:
                    select_widget = None

            if select_widget is not None:
                old_value = getattr(select_widget, "value", None)
                select_widget.set_options(new_models)

                # 尝试保持原选中值，否则选第一个有效项（基于 value=元组[1] 匹配）
                new_values = [value for _, value in new_models]
                if old_value and old_value in new_values:
                    select_widget.value = old_value
                elif new_models:
                    # 跳过 "⚠️ 未配置..." 占位符（优先用真实模型）
                    first_valid = None
                    for label, value in new_models:
                        if label and not label.startswith("⚠️"):
                            first_valid = value
                            break
                    select_widget.value = first_valid if first_valid else new_models[0][1]

                self._logger.info(
                    f"Model selector refreshed, {len(new_models)} models available"
                )
        except Exception as e:
            self._logger.error(f"Failed to refresh model selector: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # 模型切换核心：真实生效 agent + 持久化配置
    # ------------------------------------------------------------------

    def _apply_model_switch(self, model_value: str) -> bool:
        """把选中的 value 真实切换为 agent 的运行时模型并保存到配置.

        Args:
            model_value: Select 组件返回的内部 value（元组第二个元素），
                         格式通常为 "provider/model" 或纯 "provider"。
                         支持 "provider:model" 或直接一个 token。

        Returns:
            True 表示成功切换；False 表示失败（用户已通过 notify 收到提示）。
        """
        if not model_value:
            return False

        # 1. 解析 provider / model
        raw = model_value.strip()
        provider: str = ""
        model: str = ""
        if "/" in raw:
            provider, _, model = raw.partition("/")
        elif ":" in raw:
            provider, _, model = raw.partition(":")
        else:
            provider = raw

        provider = provider.strip()
        model = model.strip()
        if not provider or provider.lower() in {"none", ""}:
            self.notify("⚠️ 模型格式无效，应为 provider/model 或 provider")
            return False

        # 2. 从配置中查找该 provider 的凭证（api_key/base_url）
        api_key: str | None = None
        base_url: str | None = None
        try:
            from common.config import load_config

            cfg = load_config()
            providers_cfg = cfg.get("providers", {}) or {}
            p_cfg = providers_cfg.get(provider, {}) or {}
            if isinstance(p_cfg, dict):
                api_key = p_cfg.get("api_key") or None
                base_url = p_cfg.get("base_url") or None
        except Exception:
            pass

        # 3. 调用 agent.set_model() 运行时切换
        try:
            if hasattr(self, "_agent") and self._agent is not None:
                self._agent.set_model(
                    provider=provider,
                    model=model or None,
                    api_key=api_key,
                    base_url=base_url,
                )
                self._logger.info(
                    f"Agent model switched to {provider}/{model or 'default'}"
                )
            else:
                self._logger.warning(
                    "Agent not initialized, runtime switch skipped (config persisted only)"
                )
        except Exception as e:
            self._logger.error(f"Failed to switch agent model: {e}", exc_info=True)
            self.notify(f"❌ 模型切换失败: {e}", title="模型切换")
            return False

        # 4. 持久化到 common.config（让 Settings 页面下次打开同步看到选中值）
        try:
            from common.config import set_config_value

            set_config_value("llm.provider", provider)
            set_config_value("llm.model", model)
            self._logger.debug("llm.provider/model persisted via set_config_value")
        except Exception as e:
            self._logger.warning(f"Failed to persist model to config: {e}")

        self.notify(
            f"✅ 已切换模型: {provider}{'/' + model if model else ''}",
            title="模型切换",
        )
        return True

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

            # 找到第一个非 not_configured 的模型（使用 value=元组[1]，Select.value 存储的是 SelectType）
            current_value = None
            for label, value in self._builtin_models:
                if value != "not_configured":
                    current_value = value
                    break

            # 如果没有配置任何有效模型，使用 not_configured
            if not current_value:
                current_value = self._builtin_models[0][1]  # 第一个的 value

            select_widget.value = current_value
            self._logger.debug(f"Model select initialized with: {current_value}")
        except Exception as e:
            self._logger.error(f"Failed to init model select: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # 选择变化：真实切换
    # ------------------------------------------------------------------

    @on(Select.Changed)
    def _on_model_selected(self, event) -> None:
        """处理模型选择变化：真实切换 agent 模型并持久化配置."""
        if event.control.id == "status-model":
            selected = event.value
            if selected == "not_configured":
                self.notify("⚠️ 请先在设置中配置 LLM 模型")
            elif selected:
                self._apply_model_switch(selected)


__all__ = ["ModelSelectorMixin"]
