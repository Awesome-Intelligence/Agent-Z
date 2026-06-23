#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for TUI tab management.

Tests cover:
- Creating new tabs
- Closing tabs
- Switching tabs
- Ctrl+T shortcut
- Ctrl+W shortcut
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
import sys


class TestTabBasics:
    """Test basic tab functionality."""

    def test_tab_counter_initialization(self):
        """Test tab counter starts at zero."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        assert app._tab_counter == 0

    def test_tab_states_initialization(self):
        """Test tab states dictionary is empty initially."""
        from tui.textual_app.app import TEXTUAL_AVAILABLE
        
        if not TEXTUAL_AVAILABLE:
            pytest.skip("Textual not available")
        
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        assert len(app._tab_states) == 0
        assert app._active_tab_id is None


class TestAddTab:
    """Test adding new tabs."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    @patch('tui.textual_app.app.ChatView')
    @patch('tui.textual_app.app.Tabs')
    @patch('tui.textual_app.app.Tab')
    @patch('tui.textual_app.app.VerticalScroll')
    def test_add_tab_returns_tab_id(self, mock_scroll, mock_tab, mock_tabs, mock_chat_view):
        """Test add_tab returns a valid tab ID."""
        from tui.textual_app.app import HandsomeAgentApp
        
        # Setup mocks
        mock_tabs_instance = MagicMock()
        mock_tabs.return_value = mock_tabs_instance
        
        mock_scroll_instance = MagicMock()
        mock_scroll.return_value = mock_scroll_instance
        
        mock_chat_view_instance = MagicMock()
        mock_chat_view_instance.parent = None
        mock_chat_view.return_value = mock_chat_view_instance
        
        app = HandsomeAgentApp()
        
        # Mock query_one to return our mock components
        with patch.object(app, 'query_one') as mock_query:
            mock_query.side_effect = lambda selector, cls: (
                mock_tabs_instance if cls == mock_tabs else mock_scroll_instance
            )
            
            # Use add_tab with mocked components
            app._tab_counter = 0
            tab_id = app.add_tab()
            
            assert tab_id is not None
            assert "chat-tab-" in tab_id
            assert tab_id == "chat-tab-1"

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    @patch('tui.textual_app.app.ChatView')
    @patch('tui.textual_app.app.Tabs')
    @patch('tui.textual_app.app.Tab')
    @patch('tui.textual_app.app.VerticalScroll')
    def test_add_tab_increments_counter(self, mock_scroll, mock_tab, mock_tabs, mock_chat_view):
        """Test adding a tab increments the counter."""
        from tui.textual_app.app import HandsomeAgentApp
        
        mock_tabs_instance = MagicMock()
        mock_tabs.return_value = mock_tabs_instance
        
        mock_scroll_instance = MagicMock()
        mock_scroll.return_value = mock_scroll_instance
        
        mock_chat_view_instance = MagicMock()
        mock_chat_view_instance.parent = None
        mock_chat_view.return_value = mock_chat_view_instance
        
        app = HandsomeAgentApp()
        initial_count = app._tab_counter
        
        with patch.object(app, 'query_one') as mock_query:
            mock_query.side_effect = lambda selector, cls: (
                mock_tabs_instance if cls == mock_tabs else mock_scroll_instance
            )
            
            app.add_tab()
            
            assert app._tab_counter == initial_count + 1

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    @patch('tui.textual_app.app.ChatView')
    @patch('tui.textual_app.app.Tabs')
    @patch('tui.textual_app.app.Tab')
    @patch('tui.textual_app.app.VerticalScroll')
    def test_add_tab_stores_state(self, mock_scroll, mock_tab, mock_tabs, mock_chat_view):
        """Test adding a tab stores its state."""
        from tui.textual_app.app import HandsomeAgentApp
        
        mock_tabs_instance = MagicMock()
        mock_tabs.return_value = mock_tabs_instance
        
        mock_scroll_instance = MagicMock()
        mock_scroll.return_value = mock_scroll_instance
        
        mock_chat_view_instance = MagicMock()
        mock_chat_view_instance.parent = None
        mock_chat_view.return_value = mock_chat_view_instance
        
        app = HandsomeAgentApp()
        
        with patch.object(app, 'query_one') as mock_query:
            mock_query.side_effect = lambda selector, cls: (
                mock_tabs_instance if cls == mock_tabs else mock_scroll_instance
            )
            
            tab_id = app.add_tab()
            
            assert tab_id in app._tab_states
            assert "title" in app._tab_states[tab_id]
            assert "chat_view" in app._tab_states[tab_id]


class TestCloseTab:
    """Test closing tabs."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_close_tab_returns_false_for_last_tab(self):
        """Test cannot close the last tab."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        app._tab_counter = 1
        app._active_tab_id = "chat-tab-1"
        
        # Mock query_one to return single tab
        mock_tab = MagicMock()
        mock_tab.id = "chat-tab-1"
        
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = [mock_tab]
        
        with patch.object(app, 'query_one', return_value=mock_tabs):
            result = app.close_tab("chat-tab-1")
            
            # Should return False because cannot close last tab
            assert result is False

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_close_tab_not_found(self):
        """Test closing a non-existent tab."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        app._tab_counter = 0
        
        result = app.close_tab("non-existent-tab")
        
        assert result is False

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_close_tab_removes_from_states(self):
        """Test closing a tab removes it from states."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Add some tabs to states
        app._tab_counter = 2
        app._tab_states = {
            "chat-tab-1": {"title": "Chat 1", "chat_view": MagicMock()},
            "chat-tab-2": {"title": "Chat 2", "chat_view": MagicMock()},
        }
        app._active_tab_id = "chat-tab-1"
        
        # Mock query_one
        mock_tab1 = MagicMock()
        mock_tab1.id = "chat-tab-1"
        mock_tab2 = MagicMock()
        mock_tab2.id = "chat-tab-2"
        
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = [mock_tab1, mock_tab2]
        mock_tabs.active = "chat-tab-1"
        
        mock_scroll = MagicMock()
        
        def query_side_effect(selector, cls=None):
            if "Tabs" in str(cls):
                return mock_tabs
            return mock_scroll
        
        with patch.object(app, 'query_one', side_effect=query_side_effect):
            result = app.close_tab("chat-tab-1")
            
            # Tab should be removed from states
            assert "chat-tab-1" not in app._tab_states


class TestSwitchTab:
    """Test tab switching."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_next_tab_no_tabs(self):
        """Test next tab action with no tabs."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Mock query_one to return empty tabs
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = []
        
        with patch.object(app, 'query_one', return_value=mock_tabs):
            # Should not raise
            app.action_next_tab()

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_prev_tab_no_tabs(self):
        """Test previous tab action with no tabs."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = []
        
        with patch.object(app, 'query_one', return_value=mock_tabs):
            app.action_prev_tab()

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_next_tab_cycles(self):
        """Test next tab cycles through all tabs."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Create mock tabs
        mock_tab1 = MagicMock()
        mock_tab1.id = "tab-1"
        mock_tab2 = MagicMock()
        mock_tab2.id = "tab-2"
        
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = [mock_tab1, mock_tab2]
        mock_tabs.active = "tab-1"
        
        with patch.object(app, 'query_one', return_value=mock_tabs):
            app.action_next_tab()
            
            # Should have cycled to tab-2
            assert mock_tabs.active == "tab-2"

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_prev_tab_cycles_backwards(self):
        """Test previous tab cycles backwards."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        mock_tab1 = MagicMock()
        mock_tab1.id = "tab-1"
        mock_tab2 = MagicMock()
        mock_tab2.id = "tab-2"
        
        mock_tabs = MagicMock()
        mock_tabs.query.return_value = [mock_tab1, mock_tab2]
        mock_tabs.active = "tab-2"
        
        with patch.object(app, 'query_one', return_value=mock_tabs):
            app.action_prev_tab()
            
            # Should have cycled back to tab-1
            assert mock_tabs.active == "tab-1"


class TestTabKeyboardShortcuts:
    """Test tab keyboard shortcuts."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_new_tab(self):
        """Test Ctrl+T shortcut (new tab action)."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        with patch.object(app, 'add_tab', return_value="chat-tab-1") as mock_add:
            app.action_new_tab()
            
            mock_add.assert_called_once()

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_close_tab_with_active(self):
        """Test Ctrl+W shortcut (close tab action)."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        app._active_tab_id = "chat-tab-1"
        
        with patch.object(app, 'close_tab', return_value=True) as mock_close:
            app.action_close_tab()
            
            mock_close.assert_called_once_with("chat-tab-1")

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_action_close_tab_without_active(self):
        """Test close tab action with no active tab."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        app._active_tab_id = None
        
        with patch.object(app, 'close_tab') as mock_close:
            app.action_close_tab()
            
            # Should not call close_tab when no active tab
            mock_close.assert_not_called()


class TestTabEvents:
    """Test tab-related events."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_on_tabs_tab_activated(self):
        """Test tab activation event handler."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Mock event
        mock_tab = MagicMock()
        mock_tab.id = "chat-tab-1"
        
        mock_event = MagicMock()
        mock_event.tab = mock_tab
        
        # Mock query_one for _show_tab_content
        mock_scroll = MagicMock()
        
        app._tab_states = {
            "chat-tab-1": {"title": "Chat 1", "chat_view": MagicMock()},
        }
        
        with patch.object(app, 'query_one', return_value=mock_scroll):
            app.on_tabs_tab_activated(mock_event)
            
            # Active tab should be updated
            assert app._active_tab_id == "chat-tab-1"


class TestShowTabContent:
    """Test showing tab content."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_show_tab_content_hides_others(self):
        """Test showing a tab hides other tabs."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        # Create mock chat views
        mock_view1 = MagicMock()
        mock_view2 = MagicMock()
        
        app._tab_states = {
            "chat-tab-1": {"title": "Chat 1", "chat_view": mock_view1},
            "chat-tab-2": {"title": "Chat 2", "chat_view": mock_view2},
        }
        
        mock_scroll = MagicMock()
        
        with patch.object(app, 'query_one', return_value=mock_scroll):
            app._show_tab_content("chat-tab-1")
            
            # First view should be visible
            assert mock_view1.display is True
            # Second view should be hidden
            assert mock_view2.display is False

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_show_tab_content_nonexistent(self):
        """Test showing content for non-existent tab."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        app._tab_states = {}
        
        mock_scroll = MagicMock()
        
        with patch.object(app, 'query_one', return_value=mock_scroll):
            # Should not raise
            app._show_tab_content("non-existent")


class TestTabVisibility:
    """Test tab visibility management."""

    @patch('tui.textual_app.app.TEXTUAL_AVAILABLE', True)
    def test_tab_content_visibility_toggle(self):
        """Test toggling tab content visibility."""
        from tui.textual_app.app import HandsomeAgentApp
        
        app = HandsomeAgentApp()
        
        mock_view = MagicMock()
        app._tab_states = {
            "chat-tab-1": {"title": "Chat 1", "chat_view": mock_view},
        }
        
        # Initially not visible
        mock_view.display = False
        app._show_tab_content("chat-tab-1")
        assert mock_view.display is True
        
        # After hiding
        mock_view.display = True
        app._show_tab_content("chat-tab-1")
        assert mock_view.display is True  # Should remain visible when explicitly shown


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
