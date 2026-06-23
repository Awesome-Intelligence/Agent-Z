#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Session Restore functionality.

Tests cover normal session restoration, corrupted data handling,
and historical message loading.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from tui.services.session_store import SessionStore, Session, Message


class TestNormalSessionRestore:
    """Test normal session restoration scenarios."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_restore.db"
        self.store = SessionStore(db_path=self.db_path)
        self.session_id = self.store.create_session(
            model="gpt-4",
            provider="OpenAI",
            title="Test Session"
        )
        yield
        SessionStore.reset_instance()

    def test_restore_empty_session(self):
        """Test restoring a session with no messages."""
        session = self.store.get_session(self.session_id)
        messages = self.store.get_messages(self.session_id)

        assert session is not None
        assert session.id == self.session_id
        assert len(messages) == 0

    def test_restore_session_with_messages(self, sample_message_history):
        """Test restoring a session with message history."""
        for msg in sample_message_history:
            self.store.save_message(
                session_id=self.session_id,
                role=msg["role"],
                content=msg["content"],
            )

        messages = self.store.get_messages(self.session_id)

        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[0].content == "Hello, how are you?"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"

    def test_restore_preserves_message_order(self, sample_message_history):
        """Test that message order is preserved during restore."""
        for msg in sample_message_history:
            self.store.save_message(
                session_id=self.session_id,
                role=msg["role"],
                content=msg["content"],
            )

        messages = self.store.get_messages(self.session_id)

        for i, original in enumerate(sample_message_history):
            assert messages[i].role == original["role"]
            assert messages[i].content == original["content"]

    def test_restore_session_metadata(self):
        """Test restoring session with metadata."""
        self.store.update_session(
            self.session_id,
            context_tokens=5000,
            message_count=10,
        )

        session = self.store.get_session(self.session_id)

        assert session.context_tokens == 5000
        assert session.message_count == 10

    def test_restore_session_timestamps(self):
        """Test that session timestamps are preserved."""
        session = self.store.get_session(self.session_id)

        assert session.created_at is not None
        assert session.updated_at is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)


class TestCorruptedDataRecovery:
    """Test handling of corrupted session data."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_corrupt.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_restore_session_with_missing_fields(self):
        """Test restoring session with missing optional fields."""
        session_id = self.store.create_session()

        # Manually insert a minimal message
        conn = self.store._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("msg-minimal", session_id, "user", "Minimal message", datetime.now()),
        )
        conn.commit()

        messages = self.store.get_messages(session_id)

        assert len(messages) == 1
        assert messages[0].tokens is None
        assert messages[0].thinking_content is None
        assert messages[0].metadata is None

    def test_restore_session_with_empty_content(self):
        """Test restoring messages with empty content."""
        session_id = self.store.create_session()

        self.store.save_message(
            session_id=session_id,
            role="assistant",
            content="",
        )

        messages = self.store.get_messages(session_id)

        assert len(messages) == 1
        assert messages[0].content == ""

    def test_restore_session_with_unicode_content(self):
        """Test restoring messages with unicode content."""
        session_id = self.store.create_session()

        unicode_content = "你好世界！🎉 مرحبا العالم 🌍"
        self.store.save_message(
            session_id=session_id,
            role="user",
            content=unicode_content,
        )

        messages = self.store.get_messages(session_id)

        assert len(messages) == 1
        assert messages[0].content == unicode_content

    def test_restore_with_deleted_session_id(self):
        """Test behavior when restoring from a deleted session."""
        session_id = self.store.create_session()
        self.store.save_message(session_id, "user", "Test message")

        # Delete the session
        self.store.delete_session(session_id)

        # Session should not exist
        session = self.store.get_session(session_id)
        messages = self.store.get_messages(session_id)

        assert session is None
        assert len(messages) == 0

    def test_restore_partial_message_data(self):
        """Test restoring messages with partial data."""
        session_id = self.store.create_session()

        # Insert message with only required fields
        conn = self.store._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("partial-msg", session_id, "system", "You are helpful.", datetime.now()),
        )
        conn.commit()

        messages = self.store.get_messages(session_id)

        assert len(messages) == 1
        assert messages[0].role == "system"
        assert messages[0].content == "You are helpful."


class TestHistoricalMessageLoading:
    """Test loading historical message data."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_history_load.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_load_message_history_in_order(self):
        """Test that message history loads in chronological order."""
        session_id = self.store.create_session()

        # Add messages in specific order
        messages_content = ["First", "Second", "Third", "Fourth", "Fifth"]
        for content in messages_content:
            self.store.save_message(session_id, "user", content)

        loaded_messages = self.store.get_messages(session_id)

        assert len(loaded_messages) == 5
        for i, content in enumerate(messages_content):
            assert loaded_messages[i].content == content

    def test_load_message_history_with_offset(self):
        """Test loading message history with offset."""
        session_id = self.store.create_session()

        for i in range(10):
            self.store.save_message(session_id, "user", f"Message {i}")

        # Load from offset 3
        messages = self.store.get_messages(session_id, offset=3)

        assert len(messages) == 7
        assert messages[0].content == "Message 3"

    def test_load_message_history_with_limit(self):
        """Test loading message history with limit."""
        session_id = self.store.create_session()

        for i in range(10):
            self.store.save_message(session_id, "user", f"Message {i}")

        # Load only first 5
        messages = self.store.get_messages(session_id, limit=5)

        assert len(messages) == 5
        assert messages[0].content == "Message 0"
        assert messages[4].content == "Message 4"

    def test_load_message_history_with_offset_and_limit(self):
        """Test loading message history with both offset and limit."""
        session_id = self.store.create_session()

        for i in range(20):
            self.store.save_message(session_id, "user", f"Message {i}")

        # Load middle portion
        messages = self.store.get_messages(session_id, limit=5, offset=10)

        assert len(messages) == 5
        assert messages[0].content == "Message 10"
        assert messages[4].content == "Message 14"

    def test_load_message_history_empty_session(self):
        """Test loading history from empty session."""
        session_id = self.store.create_session()

        messages = self.store.get_messages(session_id)

        assert len(messages) == 0

    def test_load_message_history_with_tool_calls(self):
        """Test loading messages with tool call metadata."""
        session_id = self.store.create_session()

        # Add user message
        self.store.save_message(session_id, "user", "Search for Python")

        # Add assistant message with tool calls
        metadata = {
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "search",
                        "arguments": {"query": "Python"}
                    }
                }
            ]
        }
        self.store.save_message(
            session_id=session_id,
            role="assistant",
            content="",
            metadata=metadata,
        )

        messages = self.store.get_messages(session_id)

        assert len(messages) == 2
        assert messages[1].metadata is not None
        assert "tool_calls" in messages[1].metadata

    def test_load_message_history_with_thinking_content(self):
        """Test loading messages with thinking content."""
        session_id = self.store.create_session()

        thinking = "Let me think about this..."
        self.store.save_message(
            session_id=session_id,
            role="assistant",
            content="Final response",
            thinking_content=thinking,
        )

        messages = self.store.get_messages(session_id)

        assert len(messages) == 1
        assert messages[0].thinking_content == thinking

    def test_load_message_count_accuracy(self):
        """Test message count accuracy."""
        session_id = self.store.create_session()

        initial_count = self.store.get_message_count(session_id)
        assert initial_count == 0

        # Add messages
        for i in range(5):
            self.store.save_message(session_id, "user", f"Message {i}")

        count = self.store.get_message_count(session_id)
        assert count == 5

    def test_load_message_history_with_tokens(self):
        """Test loading messages with token counts."""
        session_id = self.store.create_session()

        self.store.save_message(
            session_id=session_id,
            role="user",
            content="Hello world",
            tokens=10,
        )
        self.store.save_message(
            session_id=session_id,
            role="assistant",
            content="Hi there!",
            tokens=20,
        )

        messages = self.store.get_messages(session_id)

        assert messages[0].tokens == 10
        assert messages[1].tokens == 20


class TestSessionRestoreEdgeCases:
    """Test edge cases in session restoration."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_edge.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_restore_session_after_store_reinit(self):
        """Test restoring session after store reinitialization."""
        session_id = self.store.create_session()
        self.store.save_message(session_id, "user", "Test")

        # Reinitialize store
        SessionStore.reset_instance()
        new_store = SessionStore(db_path=self.db_path)

        # Should be able to restore
        session = new_store.get_session(session_id)
        messages = new_store.get_messages(session_id)

        assert session is not None
        assert len(messages) == 1

    def test_restore_from_concurrent_writes(self):
        """Test restoration consistency under concurrent-like scenarios."""
        session_id = self.store.create_session()

        # Simulate multiple writes
        for i in range(10):
            self.store.save_message(session_id, "user", f"Concurrent {i}")

        # Verify final count matches
        session = self.store.get_session(session_id)
        messages = self.store.get_messages(session_id)

        assert session.message_count == 10
        assert len(messages) == 10

    def test_restore_session_with_special_characters_in_title(self):
        """Test restoring session with special characters in title."""
        special_titles = [
            "Test & Development",
            "Project 'Quotes'",
            'Double "Quotes"',
            "Path\\Backslash",
            "Emoji 🎉",
            "Unicode 你好",
        ]

        for title in special_titles:
            session_id = self.store.create_session(title=title)
            session = self.store.get_session(session_id)

            assert session.title == title

    def test_restore_session_pagination(self):
        """Test session restoration with pagination."""
        session_id = self.store.create_session()

        # Create 25 messages
        for i in range(25):
            self.store.save_message(session_id, "user", f"Page {i}")

        # Load in pages
        page1 = self.store.get_messages(session_id, limit=10, offset=0)
        page2 = self.store.get_messages(session_id, limit=10, offset=10)
        page3 = self.store.get_messages(session_id, limit=10, offset=20)

        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5

        # Verify no overlap
        page1_ids = {m.id for m in page1}
        page2_ids = {m.id for m in page2}
        page3_ids = {m.id for m in page3}

        assert len(page1_ids & page2_ids) == 0
        assert len(page2_ids & page3_ids) == 0
        assert len(page1_ids & page3_ids) == 0

    def test_restore_session_with_all_roles(self):
        """Test restoring session with all message roles."""
        session_id = self.store.create_session()

        self.store.save_message(session_id, "system", "You are a helpful assistant.")
        self.store.save_message(session_id, "user", "Hello")
        self.store.save_message(session_id, "assistant", "Hi there!")
        self.store.save_message(session_id, "tool", "Tool result")

        messages = self.store.get_messages(session_id)

        assert len(messages) == 4
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[2].role == "assistant"
        assert messages[3].role == "tool"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])