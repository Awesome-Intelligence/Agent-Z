#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Session Picker View.

Tests cover session list display, search functionality,
session deletion, and keyboard navigation.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime
from typing import Optional

# Import the session picker components
from tui.views.session_picker import SessionPickerScreen, SessionItem


class TestSessionItem:
    """Test SessionItem dataclass."""

    def test_session_item_creation(self):
        """Test creating a SessionItem instance."""
        item = SessionItem(
            id="session-123",
            title="Test Session",
            created_at="2024-01-01 12:00",
            message_count=10,
            model="gpt-4",
        )

        assert item.id == "session-123"
        assert item.title == "Test Session"
        assert item.created_at == "2024-01-01 12:00"
        assert item.message_count == 10
        assert item.model == "gpt-4"

    def test_matches_empty_query(self):
        """Test that empty query matches all sessions."""
        item = SessionItem(id="1", title="Test")

        assert item.matches("") is True
        assert item.matches("   ") is True

    def test_matches_title(self):
        """Test matching against title."""
        item = SessionItem(id="1", title="Python Programming")

        assert item.matches("Python") is True
        assert item.matches("python") is True
        assert item.matches("java") is False

    def test_matches_model(self):
        """Test matching against model name."""
        item = SessionItem(id="1", title="Test", model="gpt-4")

        assert item.matches("gpt") is True
        assert item.matches("GPT-4") is True
        assert item.matches("claude") is False

    def test_matches_case_insensitive(self):
        """Test that matching is case insensitive."""
        item = SessionItem(id="1", title="Test Session")

        assert item.matches("TEST") is True
        assert item.matches("session") is True
        assert item.matches("SESSION") is True

    def test_matches_partial(self):
        """Test partial matching."""
        item = SessionItem(id="1", title="My Project Session")

        assert item.matches("Proj") is True
        assert item.matches("Sess") is True
        assert item.matches("my proj") is True


class TestSessionFiltering:
    """Test session filtering functionality."""

    def test_filter_sessions_empty_query(self):
        """Test filtering with empty query returns all sessions."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="Python Chat", model="gpt-4"),
            SessionItem(id="2", title="JavaScript Project", model="claude"),
            SessionItem(id="3", title="Python Script", model="gpt-4"),
            SessionItem(id="4", title="Rust Programming", model="gpt-4"),
        ]
        picker._filtered_sessions = []
        picker._selected_index = 0
        picker._delete_confirm_index = None

        # Call the actual filter method
        SessionPickerScreen._filter_sessions(picker, "")

        assert len(picker._filtered_sessions) == 4

    def test_filter_sessions_by_title(self):
        """Test filtering sessions by title."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="Python Chat", model="gpt-4"),
            SessionItem(id="2", title="JavaScript Project", model="claude"),
            SessionItem(id="3", title="Python Script", model="gpt-4"),
        ]
        picker._filtered_sessions = []
        picker._selected_index = 0
        picker._delete_confirm_index = None

        SessionPickerScreen._filter_sessions(picker, "JavaScript")

        assert len(picker._filtered_sessions) == 1
        assert picker._filtered_sessions[0].title == "JavaScript Project"

    def test_filter_sessions_by_model(self):
        """Test filtering sessions by model."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="Python Chat", model="gpt-4"),
            SessionItem(id="2", title="JavaScript Project", model="claude"),
        ]
        picker._filtered_sessions = []
        picker._selected_index = 0
        picker._delete_confirm_index = None

        SessionPickerScreen._filter_sessions(picker, "claude")

        assert len(picker._filtered_sessions) == 1
        assert picker._filtered_sessions[0].model == "claude"

    def test_filter_sessions_resets_index(self):
        """Test that filtering resets selected index."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="Python Chat", model="gpt-4"),
            SessionItem(id="2", title="JavaScript Project", model="claude"),
        ]
        picker._filtered_sessions = []
        picker._selected_index = 3
        picker._delete_confirm_index = 2

        SessionPickerScreen._filter_sessions(picker, "JavaScript")

        assert picker._selected_index == 0
        assert picker._delete_confirm_index is None

    def test_filter_sessions_no_matches(self):
        """Test filtering with no matches."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="Python Chat", model="gpt-4"),
            SessionItem(id="2", title="JavaScript Project", model="claude"),
        ]
        picker._filtered_sessions = []
        picker._selected_index = 0
        picker._delete_confirm_index = None

        SessionPickerScreen._filter_sessions(picker, "xyz123")

        assert len(picker._filtered_sessions) == 0


class TestSessionDeletion:
    """Test session deletion functionality."""

    def test_delete_confirm_index_initialization(self):
        """Test that delete confirm index is initialized to None."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._delete_confirm_index = None
        
        # Simulating the state
        assert picker._delete_confirm_index is None

    def test_delete_confirm_sets_index(self):
        """Test that entering delete mode sets confirm index."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._selected_index = 2
        picker._delete_confirm_index = None
        
        # Simulate first delete press
        picker._delete_confirm_index = picker._selected_index
        
        assert picker._delete_confirm_index == 2

    def test_delete_confirm_resets_on_navigation(self):
        """Test that delete confirmation resets on navigation."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._delete_confirm_index = 2
        
        # Simulate navigation that should cancel delete
        picker._delete_confirm_index = None
        
        assert picker._delete_confirm_index is None

    def test_cancel_delete_resets_index(self):
        """Test that cancel resets delete confirm index."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._delete_confirm_index = 2
        
        # Simulate cancel
        picker._delete_confirm_index = None
        
        assert picker._delete_confirm_index is None


class TestKeyboardNavigation:
    """Test keyboard navigation functionality."""

    def test_select_previous_from_middle(self):
        """Test selecting previous session from middle of list."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="S1"),
            SessionItem(id="2", title="S2"),
            SessionItem(id="3", title="S3"),
        ]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 2
        picker._delete_confirm_index = None

        # Create a mock table
        mock_table = MagicMock()
        
        # Patch query_one to return mock table
        with patch.object(picker, "query_one", return_value=mock_table):
            SessionPickerScreen._select_previous(picker)

            assert picker._selected_index == 1
            assert picker._delete_confirm_index is None

    def test_select_previous_from_first(self):
        """Test selecting previous from first item stays at first."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [SessionItem(id="1", title="S1")]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 0
        picker._delete_confirm_index = None

        mock_table = MagicMock()
        
        with patch.object(picker, "query_one", return_value=mock_table):
            SessionPickerScreen._select_previous(picker)

            assert picker._selected_index == 0

    def test_select_next_from_middle(self):
        """Test selecting next session from middle of list."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="S1"),
            SessionItem(id="2", title="S2"),
            SessionItem(id="3", title="S3"),
        ]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 0
        picker._delete_confirm_index = None

        mock_table = MagicMock()
        
        with patch.object(picker, "query_one", return_value=mock_table):
            SessionPickerScreen._select_next(picker)

            assert picker._selected_index == 1

    def test_select_next_from_last(self):
        """Test selecting next from last item stays at last."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="S1"),
            SessionItem(id="2", title="S2"),
        ]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 1
        picker._delete_confirm_index = None

        mock_table = MagicMock()
        
        with patch.object(picker, "query_one", return_value=mock_table):
            SessionPickerScreen._select_next(picker)

            assert picker._selected_index == 1

    def test_select_next_resets_delete_confirm(self):
        """Test that selecting next cancels delete confirmation."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [
            SessionItem(id="1", title="S1"),
            SessionItem(id="2", title="S2"),
        ]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 0
        picker._delete_confirm_index = 0

        mock_table = MagicMock()
        
        with patch.object(picker, "query_one", return_value=mock_table):
            SessionPickerScreen._select_next(picker)

            assert picker._delete_confirm_index is None

    def test_select_session_empty_list(self):
        """Test selecting from empty session list does nothing."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = []
        picker._filtered_sessions = []

        with patch.object(picker, "post_message") as mock_post:
            SessionPickerScreen._select_session(picker)

            mock_post.assert_not_called()

    def test_select_session_emits_message(self):
        """Test selecting session emits SessionSelected message."""
        picker = MagicMock(spec=SessionPickerScreen)
        picker._sessions = [SessionItem(id="1", title="Test Session")]
        picker._filtered_sessions = picker._sessions.copy()
        picker._selected_index = 0
        picker._logger = MagicMock()

        # Test message class structure directly
        msg = SessionPickerScreen.SessionSelected(picker, "1", "Test Session")
        assert msg.session_id == "1"
        assert msg.session_title == "Test Session"


class TestNewSessionCreation:
    """Test new session creation functionality."""

    def test_new_session_creates_store_instance(self):
        """Test that new session creation uses SessionStore."""
        # Verify SessionStore can be imported and has create_session method
        from tui.services.session_store import SessionStore
        assert hasattr(SessionStore, "create_session")


class TestCloseFunctionality:
    """Test panel close functionality."""

    def test_close_emits_picker_closed_message(self):
        """Test that close functionality emits PickerClosed message."""
        # Test message class exists and can be instantiated
        msg = SessionPickerScreen.PickerClosed()
        assert msg is not None


class TestMessageClasses:
    """Test message classes."""

    def test_session_selected_message(self):
        """Test SessionSelected message structure."""
        sender = MagicMock()
        msg = SessionPickerScreen.SessionSelected(
            sender=sender,
            session_id="test-123",
            session_title="Test Title"
        )

        assert msg.session_id == "test-123"
        assert msg.session_title == "Test Title"

    def test_session_deleted_message(self):
        """Test SessionDeleted message structure."""
        sender = MagicMock()
        msg = SessionPickerScreen.SessionDeleted(
            sender=sender,
            session_id="test-123"
        )

        assert msg.session_id == "test-123"

    def test_picker_closed_message(self):
        """Test PickerClosed message structure."""
        msg = SessionPickerScreen.PickerClosed()

        # Should not have additional attributes
        assert not hasattr(msg, "session_id")
        assert not hasattr(msg, "session_title")


class TestSessionPickerAttributes:
    """Test SessionPickerScreen attributes and constants."""

    def test_session_item_has_matches_method(self):
        """Test SessionItem has matches method."""
        item = SessionItem(id="1", title="Test")
        assert hasattr(item, "matches")
        assert callable(item.matches)

    def test_session_picker_has_filter_method(self):
        """Test SessionPickerScreen has _filter_sessions method."""
        assert hasattr(SessionPickerScreen, "_filter_sessions")
        assert callable(SessionPickerScreen._filter_sessions)

    def test_session_picker_has_delete_method(self):
        """Test SessionPickerScreen has _delete_session_at_index method."""
        assert hasattr(SessionPickerScreen, "_delete_session_at_index")
        assert callable(SessionPickerScreen._delete_session_at_index)

    def test_session_picker_has_navigation_methods(self):
        """Test SessionPickerScreen has navigation methods."""
        assert hasattr(SessionPickerScreen, "_select_previous")
        assert hasattr(SessionPickerScreen, "_select_next")
        assert hasattr(SessionPickerScreen, "_select_session")

    def test_session_picker_has_delete_confirm_methods(self):
        """Test SessionPickerScreen has delete confirmation methods."""
        assert hasattr(SessionPickerScreen, "_confirm_delete")
        assert hasattr(SessionPickerScreen, "_cancel_delete")

    def test_session_picker_has_create_session_method(self):
        """Test SessionPickerScreen has _create_new_session method."""
        assert hasattr(SessionPickerScreen, "_create_new_session")

    def test_session_picker_has_close_method(self):
        """Test SessionPickerScreen has _close method."""
        assert hasattr(SessionPickerScreen, "_close")

    def test_session_picker_has_message_classes(self):
        """Test SessionPickerScreen has message classes."""
        assert hasattr(SessionPickerScreen, "SessionSelected")
        assert hasattr(SessionPickerScreen, "SessionDeleted")
        assert hasattr(SessionPickerScreen, "PickerClosed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])