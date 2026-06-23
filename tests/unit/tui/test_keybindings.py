#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Key Bindings Unit Tests

测试 tui/core/keybindings.py 模块的快捷键绑定功能。
"""

import pytest
from unittest.mock import MagicMock, patch


class TestKeyBinding:
    """测试 KeyBinding 数据类"""

    def test_key_binding_creation(self):
        """测试快捷键绑定创建"""
        from tui.core.keybindings import KeyBinding, KeyBindingCategory
        
        action_mock = MagicMock()
        binding = KeyBinding(
            key="ctrl+k",
            description="打开命令面板",
            action=action_mock,
            category=KeyBindingCategory.COMMAND,
        )
        
        assert binding.key == "ctrl+k"
        assert binding.description == "打开命令面板"
        assert binding.action is action_mock
        assert binding.category == "command"
        assert binding.hidden is False

    def test_key_normalization(self):
        """测试快捷键字符串规范化"""
        from tui.core.keybindings import KeyBinding
        
        action_mock = MagicMock()
        
        # 测试大小写规范化
        binding1 = KeyBinding(key="Ctrl+K", description="Test", action=action_mock)
        assert binding1.key == "ctrl+k"
        
        # 测试空格规范化
        binding2 = KeyBinding(key="  ctrl+k  ", description="Test", action=action_mock)
        assert binding2.key == "ctrl+k"

    def test_key_binding_default_values(self):
        """测试快捷键绑定默认值"""
        from tui.core.keybindings import KeyBinding, KeyBindingCategory
        
        action_mock = MagicMock()
        binding = KeyBinding(
            key="escape",
            description="Test",
            action=action_mock,
        )
        
        assert binding.category == KeyBindingCategory.COMMAND
        assert binding.hidden is False


class TestKeyBindingManager:
    """测试 KeyBindingManager 快捷键管理器"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        from tui.core.keybindings import KeyBindingManager
        
        manager = KeyBindingManager()
        
        assert manager.bindings == []
        assert manager.custom_overrides == {}

    def test_register_single_binding(self):
        """测试注册单个快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        binding = KeyBinding(
            key="ctrl+k",
            description="打开命令面板",
            action=action_mock,
        )
        
        manager.register(binding)
        
        assert len(manager.bindings) == 1
        assert manager.bindings[0].key == "ctrl+k"

    def test_register_batch(self):
        """测试批量注册快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        bindings = [
            KeyBinding(key="ctrl+k", description="命令面板", action=action_mock),
            KeyBinding(key="f1", description="帮助", action=action_mock),
        ]
        
        manager.register_batch(bindings)
        
        assert len(manager.bindings) == 2

    def test_register_override_existing(self):
        """测试覆盖已存在的快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock1 = MagicMock()
        action_mock2 = MagicMock()
        
        binding1 = KeyBinding(key="ctrl+k", description="旧描述", action=action_mock1)
        binding2 = KeyBinding(key="ctrl+k", description="新描述", action=action_mock2)
        
        manager.register(binding1)
        manager.register(binding2)
        
        assert len(manager.bindings) == 1
        assert manager.bindings[0].description == "新描述"

    def test_unregister_existing(self):
        """测试取消注册存在的快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        binding = KeyBinding(key="ctrl+k", description="Test", action=action_mock)
        
        manager.register(binding)
        result = manager.unregister("ctrl+k")
        
        assert result is True
        assert len(manager.bindings) == 0

    def test_unregister_non_existing(self):
        """测试取消注册不存在的快捷键"""
        from tui.core.keybindings import KeyBindingManager
        
        manager = KeyBindingManager()
        result = manager.unregister("nonexistent")
        
        assert result is False

    def test_get_by_key(self):
        """测试根据键获取快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        binding = KeyBinding(key="ctrl+k", description="Test", action=action_mock)
        
        manager.register(binding)
        result = manager.get_by_key("ctrl+k")
        
        assert result is not None
        assert result.key == "ctrl+k"

    def test_get_by_key_case_insensitive(self):
        """测试根据键获取快捷键（大小写不敏感）"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        binding = KeyBinding(key="ctrl+k", description="Test", action=action_mock)
        
        manager.register(binding)
        result = manager.get_by_key("CTRL+K")
        
        assert result is not None
        assert result.key == "ctrl+k"

    def test_get_by_key_nonexistent(self):
        """测试获取不存在的快捷键"""
        from tui.core.keybindings import KeyBindingManager
        
        manager = KeyBindingManager()
        result = manager.get_by_key("nonexistent")
        
        assert result is None

    def test_get_by_category(self):
        """测试根据类别获取快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding, KeyBindingCategory
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令", action=action_mock, category=KeyBindingCategory.COMMAND))
        manager.register(KeyBinding(key="f1", description="帮助", action=action_mock, category=KeyBindingCategory.HELP))
        manager.register(KeyBinding(key="up", description="上", action=action_mock, category=KeyBindingCategory.NAVIGATION))
        
        command_bindings = manager.get_by_category(KeyBindingCategory.COMMAND)
        
        assert len(command_bindings) == 1
        assert command_bindings[0].key == "ctrl+k"

    def test_search_by_key(self):
        """测试通过键搜索快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令面板", action=action_mock))
        manager.register(KeyBinding(key="ctrl+l", description="清屏", action=action_mock))
        
        results = manager.search("ctrl")
        
        assert len(results) == 2

    def test_search_by_description(self):
        """测试通过描述搜索快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="打开命令面板", action=action_mock))
        manager.register(KeyBinding(key="f1", description="显示帮助", action=action_mock))
        
        results = manager.search("面板")
        
        assert len(results) == 1
        assert results[0].key == "ctrl+k"

    def test_search_exclude_hidden(self):
        """测试搜索排除隐藏快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令", action=action_mock, hidden=True))
        manager.register(KeyBinding(key="ctrl+l", description="清屏", action=action_mock, hidden=False))
        
        results = manager.search("命令", include_hidden=False)
        
        assert len(results) == 0

    def test_search_include_hidden(self):
        """测试搜索包含隐藏快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令", action=action_mock, hidden=True))
        manager.register(KeyBinding(key="ctrl+l", description="清屏", action=action_mock, hidden=False))
        
        results = manager.search("命令", include_hidden=True)
        
        assert len(results) == 1
        assert results[0].key == "ctrl+k"

    def test_get_all_categories(self):
        """测试获取所有类别"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding, KeyBindingCategory
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令", action=action_mock, category=KeyBindingCategory.COMMAND))
        manager.register(KeyBinding(key="up", description="上", action=action_mock, category=KeyBindingCategory.NAVIGATION))
        
        categories = manager.get_all_categories()
        
        assert "command" in categories
        assert "navigation" in categories

    def test_get_grouped_bindings(self):
        """测试获取分组快捷键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding, KeyBindingCategory
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="命令", action=action_mock, category=KeyBindingCategory.COMMAND))
        manager.register(KeyBinding(key="up", description="上", action=action_mock, category=KeyBindingCategory.NAVIGATION))
        
        grouped = manager.get_grouped_bindings()
        
        assert KeyBindingCategory.COMMAND in grouped
        assert KeyBindingCategory.NAVIGATION in grouped
        assert len(grouped[KeyBindingCategory.COMMAND]) == 1

    def test_override(self):
        """测试快捷键覆盖"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        original = KeyBinding(key="ctrl+k", description="原始", action=action_mock)
        override = KeyBinding(key="ctrl+k", description="覆盖", action=action_mock)
        
        manager.register(original)
        manager.override("ctrl+k", override)
        
        result = manager.get_by_key("ctrl+k")
        
        assert result.description == "覆盖"

    def test_clear_overrides(self):
        """测试清除覆盖"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        action_mock = MagicMock()
        
        manager.register(KeyBinding(key="ctrl+k", description="原始", action=action_mock))
        manager.override("ctrl+k", KeyBinding(key="ctrl+k", description="覆盖", action=action_mock))
        manager.clear_overrides()
        
        assert len(manager.custom_overrides) == 0


class TestCreateDefaultKeybindings:
    """测试创建默认快捷键"""

    def test_create_all_callbacks(self):
        """测试创建带所有回调的默认快捷键"""
        from tui.core.keybindings import create_default_keybindings
        
        callbacks = {
            "on_new_tab": MagicMock(),
            "on_close_tab": MagicMock(),
            "on_next_tab": MagicMock(),
            "on_prev_tab": MagicMock(),
            "on_open_command_palette": MagicMock(),
            "on_scroll_up": MagicMock(),
            "on_scroll_down": MagicMock(),
            "on_open_help": MagicMock(),
            "on_open_session_selector": MagicMock(),
            "on_clear_screen": MagicMock(),
            "on_copy": MagicMock(),
            "on_paste": MagicMock(),
            "on_escape": MagicMock(),
            "on_quit": MagicMock(),
        }
        
        bindings = create_default_keybindings(**callbacks)
        
        # 验证快捷键数量（不包括quit的q和help的ctrl+/）
        assert len(bindings) >= 14

    def test_create_ctrl_k_binding(self):
        """测试Ctrl+K快捷键"""
        from tui.core.keybindings import create_default_keybindings
        
        action_mock = MagicMock()
        bindings = create_default_keybindings(on_open_command_palette=action_mock)
        
        ctrl_k = next((b for b in bindings if b.key == "ctrl+k"), None)
        
        assert ctrl_k is not None
        assert ctrl_k.description == "打开命令面板"

    def test_create_navigation_bindings(self):
        """测试导航快捷键（方向键和j/k）"""
        from tui.core.keybindings import create_default_keybindings
        
        scroll_up = MagicMock()
        scroll_down = MagicMock()
        bindings = create_default_keybindings(on_scroll_up=scroll_up, on_scroll_down=scroll_down)
        
        up_keys = [b for b in bindings if b.key in ("up", "k")]
        down_keys = [b for b in bindings if b.key in ("down", "j")]
        
        assert len(up_keys) == 2  # up 和 k
        assert len(down_keys) == 2  # down 和 j

    def test_create_f1_help_binding(self):
        """测试F1帮助快捷键"""
        from tui.core.keybindings import create_default_keybindings
        
        action_mock = MagicMock()
        bindings = create_default_keybindings(on_open_help=action_mock)
        
        f1 = next((b for b in bindings if b.key == "f1"), None)
        ctrl_slash = next((b for b in bindings if b.key == "ctrl+/"), None)
        
        assert f1 is not None
        assert ctrl_slash is not None
        assert f1.description == "打开帮助"

    def test_create_tab_switching_bindings(self):
        """测试标签切换快捷键"""
        from tui.core.keybindings import create_default_keybindings
        
        next_tab = MagicMock()
        prev_tab = MagicMock()
        bindings = create_default_keybindings(on_next_tab=next_tab, on_prev_tab=prev_tab)
        
        ctrl_tab = next((b for b in bindings if b.key == "ctrl+tab"), None)
        ctrl_shift_tab = next((b for b in bindings if b.key == "ctrl+shift+tab"), None)
        
        assert ctrl_tab is not None
        assert ctrl_shift_tab is not None

    def test_create_no_callbacks(self):
        """测试不提供任何回调"""
        from tui.core.keybindings import create_default_keybindings
        
        bindings = create_default_keybindings()
        
        assert len(bindings) == 0


class TestKeyBindingCategory:
    """测试快捷键类别枚举"""

    def test_category_values(self):
        """测试类别值"""
        from tui.core.keybindings import KeyBindingCategory
        
        assert KeyBindingCategory.NAVIGATION == "navigation"
        assert KeyBindingCategory.TAB == "tab"
        assert KeyBindingCategory.COMMAND == "command"
        assert KeyBindingCategory.HELP == "help"
        assert KeyBindingCategory.SESSION == "session"


class TestKeyBindingFormat:
    """测试快捷键格式化"""

    def test_format_key_ctrl(self):
        """测试格式化Ctrl修饰键"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        binding = KeyBinding(key="ctrl+k", description="Test", action=MagicMock())
        
        formatted = manager._format_key(binding.key)
        
        assert "Ctrl+" in formatted

    def test_format_key_with_modifiers(self):
        """测试格式化带多个修饰键的组合"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        binding = KeyBinding(key="ctrl+shift+tab", description="Test", action=MagicMock())
        
        formatted = manager._format_key(binding.key)
        
        assert "Ctrl+" in formatted
        assert "Shift+" in formatted

    def test_format_for_display(self):
        """测试格式化显示"""
        from tui.core.keybindings import KeyBindingManager, KeyBinding
        
        manager = KeyBindingManager()
        binding = KeyBinding(key="ctrl+k", description="打开命令面板", action=MagicMock())
        
        with patch("tui.core.keybindings.get_i18n") as mock_i18n:
            mock_i18n_instance = MagicMock()
            mock_i18n_instance.t.return_value = "打开命令面板"
            mock_i18n.return_value = mock_i18n_instance
            
            display = manager.format_for_display(binding, i18n_enabled=False)
            
            assert "Ctrl+" in display
            assert "打开命令面板" in display


class TestKeyBindingIntegration:
    """集成测试：快捷键绑定与动作映射"""

    def test_action_triggered(self):
        """测试快捷键触发动作"""
        from tui.core.keybindings import KeyBinding
        
        action_mock = MagicMock()
        binding = KeyBinding(
            key="ctrl+k",
            description="测试动作",
            action=action_mock,
        )
        
        # 模拟触发动作
        binding.action()
        
        action_mock.assert_called_once()

    def test_action_with_parameters(self):
        """测试带参数的动作"""
        from tui.core.keybindings import KeyBinding
        
        def parameterized_action(param1, param2):
            return param1 + param2
        
        action_mock = MagicMock(side_effect=parameterized_action)
        binding = KeyBinding(
            key="test",
            description="测试",
            action=action_mock,
        )
        
        result = binding.action(1, 2)
        
        assert result == 3
        action_mock.assert_called_once_with(1, 2)
