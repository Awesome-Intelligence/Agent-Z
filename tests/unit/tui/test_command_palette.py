#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command Palette Unit Tests

测试 tui/widgets/command_palette.py 模块的命令面板功能。
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


class TestCommand:
    """测试 Command 数据类"""

    def test_command_creation(self):
        """测试命令创建"""
        from tui.widgets.command_palette import Command
        
        action_mock = MagicMock()
        cmd = Command(
            id="test_command",
            name="测试命令",
            description="这是一个测试命令",
            action=action_mock,
            shortcut="Ctrl+T",
            category="test",
        )
        
        assert cmd.id == "test_command"
        assert cmd.name == "测试命令"
        assert cmd.description == "这是一个测试命令"
        assert cmd.action is action_mock
        assert cmd.shortcut == "Ctrl+T"
        assert cmd.category == "test"

    def test_command_default_values(self):
        """测试命令默认值"""
        from tui.widgets.command_palette import Command
        
        action_mock = MagicMock()
        cmd = Command(
            id="minimal",
            name="最小命令",
            description="最小描述",
            action=action_mock,
        )
        
        assert cmd.shortcut == ""
        assert cmd.category == "general"

    def test_matches_empty_query(self):
        """测试空查询匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="测试命令",
            description="测试描述",
            action=MagicMock(),
        )
        
        assert cmd.matches("") is True
        assert cmd.matches("  ") is True

    def test_matches_name_substring(self):
        """测试名称子串匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="新建标签",
            description="创建一个新标签",
            action=MagicMock(),
        )
        
        assert cmd.matches("新建") is True
        assert cmd.matches("标签") is True
        assert cmd.matches("new") is False  # 大小写敏感

    def test_matches_description_substring(self):
        """测试描述子串匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="清屏",
            description="清除屏幕内容",
            action=MagicMock(),
        )
        
        assert cmd.matches("清除") is True
        assert cmd.matches("屏幕") is True

    def test_matches_case_insensitive(self):
        """测试大小写不敏感匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="New Tab",
            description="Create a new tab",
            action=MagicMock(),
        )
        
        assert cmd.matches("new") is True
        assert cmd.matches("NEW") is True
        assert cmd.matches("New") is True

    def test_matches_initial_letters(self):
        """测试首字母匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="New Tab",
            description="Create a new tab",
            action=MagicMock(),
        )
        
        assert cmd.matches("nt") is True  # N(ew) T(ab)
        assert cmd.matches("n") is True

    def test_matches_no_match(self):
        """测试不匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="test",
            name="清屏",
            description="清除屏幕",
            action=MagicMock(),
        )
        
        assert cmd.matches("标签") is False
        assert cmd.matches("xyz") is False


class TestCommandPaletteScreen:
    """测试 CommandPaletteScreen 组件"""

    def test_init_with_commands(self):
        """测试使用自定义命令初始化"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        
        assert len(screen._commands) == 2
        assert screen._selected_index == 0

    def test_init_with_default_commands(self):
        """测试使用默认命令初始化"""
        with patch("tui.widgets.command_palette.get_i18n") as mock_i18n:
            mock_i18n_instance = MagicMock()
            mock_i18n_instance.t.side_effect = lambda key, default=None, **kwargs: default or key
            mock_i18n.return_value = mock_i18n_instance
            
            from tui.widgets.command_palette import CommandPaletteScreen
            
            screen = CommandPaletteScreen()
            
            # 默认应该有命令
            assert len(screen._commands) > 0

    def test_filtered_commands_initial_state(self):
        """测试过滤命令初始状态"""
        with patch("tui.widgets.command_palette.get_i18n") as mock_i18n:
            mock_i18n_instance = MagicMock()
            mock_i18n_instance.t.side_effect = lambda key, default=None, **kwargs: default or key
            mock_i18n.return_value = mock_i18n_instance
            
            from tui.widgets.command_palette import CommandPaletteScreen
            
            screen = CommandPaletteScreen()
            
            # 初始时过滤后的命令应该等于所有命令
            assert len(screen._filtered_commands) == len(screen._commands)

    def test_filtered_commands_with_query(self):
        """测试带查询的过滤"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="new_tab", name="新建标签", description="创建新标签", action=MagicMock()),
            Command(id="close_tab", name="关闭标签", description="关闭标签", action=MagicMock()),
            Command(id="settings", name="设置", description="应用设置", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        
        # 模拟搜索查询
        screen._commands = commands
        screen._filtered_commands = [
            cmd for cmd in commands
            if cmd.matches("标签")
        ]
        
        assert len(screen._filtered_commands) == 2
        assert screen._filtered_commands[0].id == "new_tab"
        assert screen._filtered_commands[1].id == "close_tab"

    def test_selected_index_initial(self):
        """测试初始选中索引"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        
        assert screen._selected_index == 0

    def test_execute_selected_no_commands(self):
        """测试执行时没有命令"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        screen = CommandPaletteScreen(commands=[])
        screen._filtered_commands = []
        
        # 不应抛出异常
        screen._execute_selected()

    def test_execute_selected_with_command(self):
        """测试执行选中的命令"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        action_mock = MagicMock()
        commands = [
            Command(id="test", name="测试", description="测试命令", action=action_mock),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "_close"):
            screen._execute_selected()
        
        action_mock.assert_called_once()

    def test_execute_selected_posts_message(self):
        """测试执行命令后发送消息"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="test", name="测试", description="测试命令", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "post_message") as mock_post, \
             patch.object(screen, "_close"):
            screen._execute_selected()
            
            mock_post.assert_called()
            # 检查消息类型
            call_args = mock_post.call_args
            assert hasattr(call_args[0][0], "command")

    def test_close_posts_message(self):
        """测试关闭面板发送消息"""
        from tui.widgets.command_palette import CommandPaletteScreen
        
        screen = CommandPaletteScreen()
        
        with patch.object(screen, "post_message") as mock_post, \
             patch.object(screen.app, "pop_screen"):
            screen._close()
            
            mock_post.assert_called_once()

    def test_select_previous_at_beginning(self):
        """测试在开头选择上一个"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 0
            mock_query.return_value = mock_list_view
            
            screen._select_previous()
            
            # 在索引0时不应改变
            assert screen._selected_index == 0

    def test_select_previous_normal(self):
        """测试正常选择上一个"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 1
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 1
            mock_query.return_value = mock_list_view
            
            screen._select_previous()
            
            assert screen._selected_index == 0

    def test_select_next_at_end(self):
        """测试在末尾选择下一个"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 1  # 最后一个
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 1
            mock_query.return_value = mock_list_view
            
            screen._select_next()
            
            # 在最后索引时不应改变
            assert screen._selected_index == 1

    def test_select_next_normal(self):
        """测试正常选择下一个"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 0
            mock_query.return_value = mock_list_view
            
            screen._select_next()
            
            assert screen._selected_index == 1


class TestCommandPaletteMessages:
    """测试命令面板消息"""

    def test_command_executed_message(self):
        """测试命令执行消息"""
        from tui.widgets.command_palette import Command, CommandPaletteScreen, CommandExecuted
        from unittest.mock import MagicMock
        
        cmd = Command(id="test", name="Test", description="Test", action=MagicMock())
        screen = CommandPaletteScreen()
        
        msg = CommandPaletteScreen.CommandExecuted(screen, cmd)
        
        assert msg.command is cmd

    def test_palette_closed_message(self):
        """测试面板关闭消息"""
        from tui.widgets.command_palette import CommandPaletteScreen, PaletteClosed
        
        msg = PaletteClosed()
        
        assert msg is not None


class TestCommandMatching:
    """测试命令匹配逻辑"""

    def test_match_with_spaces_in_name(self):
        """测试带空格的命令名匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="toggle_theme",
            name="Toggle Theme",
            description="Switch between themes",
            action=MagicMock(),
        )
        
        assert cmd.matches("Toggle") is True
        assert cmd.matches("Theme") is True
        assert cmd.matches("toggle theme") is True

    def test_match_chinese_commands(self):
        """测试中文命令匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="new_tab",
            name="新建标签",
            description="创建一个新的标签页",
            action=MagicMock(),
        )
        
        assert cmd.matches("新建") is True
        assert cmd.matches("标签") is True
        assert cmd.matches("创建") is True

    def test_match_partial_word(self):
        """测试部分单词匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="config",
            name="Configuration",
            description="Configure settings",
            action=MagicMock(),
        )
        
        assert cmd.matches("conf") is True
        assert cmd.matches("fig") is False

    def test_match_multiple_words(self):
        """测试多词匹配"""
        from tui.widgets.command_palette import Command
        
        cmd = Command(
            id="new_tab",
            name="New Tab",
            description="Create a new tab",
            action=MagicMock(),
        )
        
        # 首字母匹配
        assert cmd.matches("nt") is True
        assert cmd.matches("new tab") is True  # 子串匹配


class TestCommandPaletteFuzzySearch:
    """测试命令面板模糊搜索"""

    def test_fuzzy_search_ranks(self):
        """测试模糊搜索排名"""
        from tui.widgets.command_palette import Command
        
        commands = [
            Command(id="clear", name="Clear Screen", description="Clear the screen", action=MagicMock()),
            Command(id="color", name="Color Theme", description="Change color scheme", action=MagicMock()),
            Command(id="copy", name="Copy Selection", description="Copy selected text", action=MagicMock()),
        ]
        
        # 搜索 "c" - 应该匹配多个
        matches = [cmd for cmd in commands if cmd.matches("c")]
        
        assert len(matches) == 3

    def test_fuzzy_search_prefix(self):
        """测试前缀模糊搜索"""
        from tui.widgets.command_palette import Command
        
        commands = [
            Command(id="new", name="New File", description="Create new file", action=MagicMock()),
            Command(id="new_tab", name="New Tab", description="Create new tab", action=MagicMock()),
            Command(id="open", name="Open File", description="Open existing file", action=MagicMock()),
        ]
        
        # 搜索 "new"
        matches = [cmd for cmd in commands if cmd.matches("new")]
        
        assert len(matches) == 2
        assert all("new" in cmd.name.lower() for cmd in matches)

    def test_fuzzy_search_no_results(self):
        """测试无结果的模糊搜索"""
        from tui.widgets.command_palette import Command
        
        commands = [
            Command(id="new", name="New File", description="Create new file", action=MagicMock()),
            Command(id="open", name="Open File", description="Open existing file", action=MagicMock()),
        ]
        
        matches = [cmd for cmd in commands if cmd.matches("xyz123")]
        
        assert len(matches) == 0


class TestCommandPaletteKeyboard:
    """测试命令面板键盘导航"""

    def test_key_up_navigation(self):
        """测试上方向键导航"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
            Command(id="cmd3", name="命令3", description="描述3", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 2
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 2
            mock_query.return_value = mock_list_view
            
            # 模拟按上方向键
            screen._select_previous()
            
            assert screen._selected_index == 1

    def test_key_down_navigation(self):
        """测试下方向键导航"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
            Command(id="cmd3", name="命令3", description="描述3", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 0
            mock_query.return_value = mock_list_view
            
            # 模拟按下方向键
            screen._select_next()
            
            assert screen._selected_index == 1

    def test_vim_navigation_k(self):
        """测试Vim风格k键导航"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 1
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 1
            mock_query.return_value = mock_list_view
            
            # k 应该向上导航
            screen._select_previous()
            
            assert screen._selected_index == 0

    def test_vim_navigation_j(self):
        """测试Vim风格j键导航"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "query_one") as mock_query:
            mock_list_view = MagicMock()
            mock_list_view.index = 0
            mock_query.return_value = mock_list_view
            
            # j 应该向下导航
            screen._select_next()
            
            assert screen._selected_index == 1

    def test_enter_executes_command(self):
        """测试回车执行命令"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        action_mock = MagicMock()
        commands = [
            Command(id="test", name="测试", description="测试命令", action=action_mock),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._filtered_commands = commands
        screen._selected_index = 0
        
        with patch.object(screen, "_execute_selected") as mock_execute:
            # 模拟回车键
            class MockEvent:
                key = "enter"
                def prevent_default(self): pass
                def stop(self): pass
            
            screen.on_key(MockEvent())
            
            mock_execute.assert_called_once()

    def test_escape_closes_palette(self):
        """测试Escape关闭面板"""
        from tui.widgets.command_palette import CommandPaletteScreen
        
        screen = CommandPaletteScreen()
        
        with patch.object(screen, "_close") as mock_close:
            # 模拟Escape键
            class MockEvent:
                key = "escape"
                def prevent_default(self): pass
                def stop(self): pass
            
            screen.on_key(MockEvent())
            
            mock_close.assert_called_once()


class TestCommandPaletteUpdateList:
    """测试命令列表更新"""

    def test_update_command_list_filters(self):
        """测试更新命令列表过滤"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="new_tab", name="新建标签", description="创建新标签", action=MagicMock()),
            Command(id="close_tab", name="关闭标签", description="关闭标签", action=MagicMock()),
            Command(id="settings", name="设置", description="应用设置", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        
        with patch.object(screen, "query_one") as mock_query:
            # 设置搜索框的返回值
            mock_input = MagicMock()
            mock_input.value = "标签"
            mock_input.id = "search-input"
            
            mock_list_view = MagicMock()
            mock_list_view.clear = MagicMock()
            mock_list_view.append = MagicMock()
            mock_list_view.index = None
            
            def query_side_effect(selector):
                if selector == "#search-input":
                    return mock_input
                elif selector == "#command-list":
                    return mock_list_view
                return MagicMock()
            
            mock_query.side_effect = query_side_effect
            
            screen._update_command_list()
            
            # 验证列表被清空
            mock_list_view.clear.assert_called_once()
            
            # 验证过滤结果（应该只有2个匹配"标签"的命令）
            assert len(screen._filtered_commands) == 2

    def test_update_command_list_resets_selection(self):
        """测试更新命令列表重置选择"""
        from tui.widgets.command_palette import CommandPaletteScreen, Command
        
        commands = [
            Command(id="cmd1", name="命令1", description="描述1", action=MagicMock()),
            Command(id="cmd2", name="命令2", description="描述2", action=MagicMock()),
        ]
        
        screen = CommandPaletteScreen(commands=commands)
        screen._selected_index = 1  # 之前选择的是索引1
        
        with patch.object(screen, "query_one") as mock_query:
            mock_input = MagicMock()
            mock_input.value = ""  # 空搜索
            mock_input.id = "search-input"
            
            mock_list_view = MagicMock()
            mock_list_view.clear = MagicMock()
            mock_list_view.index = None
            
            mock_query.side_effect = lambda s: mock_input if "input" in s else mock_list_view
            
            screen._update_command_list()
            
            # 选择应该重置到0
            assert screen._selected_index == 0
