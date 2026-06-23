#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for the Session Store Service.

Tests cover session CRUD operations, message storage,
and database persistence functionality.
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from tui.services.session_store import SessionStore, Session, Message


class TestSessionModel:
    """Test Session dataclass."""

    def test_session_creation(self):
        """Test creating a Session instance."""
        session = Session(
            id="test-123",
            title="Test Session",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            model="gpt-4",
            provider="OpenAI",
            context_tokens=1000,
            message_count=5,
        )

        assert session.id == "test-123"
        assert session.title == "Test Session"
        assert session.model == "gpt-4"
        assert session.provider == "OpenAI"
        assert session.context_tokens == 1000
        assert session.message_count == 5

    def test_session_to_dict(self):
        """Test converting Session to dictionary."""
        now = datetime.now()
        session = Session(
            id="test-123",
            title="Test Session",
            created_at=now,
            updated_at=now,
        )

        result = session.to_dict()

        assert result["id"] == "test-123"
        assert result["title"] == "Test Session"
        assert result["created_at"] == now.isoformat()
        assert result["updated_at"] == now.isoformat()


class TestMessageModel:
    """Test Message dataclass."""

    def test_message_creation(self):
        """Test creating a Message instance."""
        message = Message(
            id="msg-123",
            session_id="test-123",
            role="user",
            content="Hello, world!",
            created_at=datetime.now(),
            tokens=10,
        )

        assert message.id == "msg-123"
        assert message.session_id == "test-123"
        assert message.role == "user"
        assert message.content == "Hello, world!"
        assert message.tokens == 10

    def test_message_with_metadata(self):
        """Test creating a Message with metadata."""
        metadata = {"key": "value"}
        message = Message(
            id="msg-123",
            session_id="test-123",
            role="assistant",
            content="Response",
            metadata=metadata,
        )

        assert message.metadata == metadata

    def test_message_to_dict(self):
        """Test converting Message to dictionary."""
        now = datetime.now()
        message = Message(
            id="msg-123",
            session_id="test-123",
            role="user",
            content="Test",
            created_at=now,
        )

        result = message.to_dict()

        assert result["id"] == "msg-123"
        assert result["session_id"] == "test-123"
        assert result["role"] == "user"
        assert result["content"] == "Test"
        assert result["created_at"] == now.isoformat()


class TestSessionStoreCreation:
    """Test SessionStore creation and initialization."""

    def test_create_session_store_with_temp_db(self, sealed_workspace):
        """Test creating a SessionStore with temporary database."""
        SessionStore.reset_instance()
        
        db_path = sealed_workspace["workspace"] / "test_sessions.db"
        store = SessionStore(db_path=db_path)
        
        assert store._db_path == db_path
        assert db_path.parent.exists()
        
        SessionStore.reset_instance()

    def test_singleton_pattern(self, sealed_workspace):
        """Test that SessionStore follows singleton pattern."""
        SessionStore.reset_instance()
        
        db_path = sealed_workspace["workspace"] / "test_singleton.db"
        store1 = SessionStore(db_path=db_path)
        store2 = SessionStore(db_path=db_path)
        
        assert store1 is store2
        
        SessionStore.reset_instance()

    def test_database_schema_initialization(self, sealed_workspace):
        """Test database schema is properly initialized."""
        SessionStore.reset_instance()
        
        db_path = sealed_workspace["workspace"] / "test_schema.db"
        store = SessionStore(db_path=db_path)
        
        # Verify tables exist
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('sessions', 'messages', 'input_history')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        assert "sessions" in tables
        assert "messages" in tables
        
        conn.close()
        SessionStore.reset_instance()


class TestSessionCRUD:
    """Test session CRUD operations."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_crud.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_create_session(self):
        """Test creating a new session."""
        session_id = self.store.create_session(
            model="gpt-4",
            provider="OpenAI"
        )

        assert session_id is not None
        assert len(session_id) > 0

    def test_create_session_with_custom_id(self):
        """Test creating a session with custom ID."""
        custom_id = "my-custom-session-id"
        session_id = self.store.create_session(session_id=custom_id)

        assert session_id == custom_id

    def test_create_session_with_title(self):
        """Test creating a session with custom title."""
        session_id = self.store.create_session(title="My Custom Title")

        session = self.store.get_session(session_id)
        assert session is not None
        assert session.title == "My Custom Title"

    def test_get_session(self):
        """Test retrieving a session."""
        session_id = self.store.create_session()

        session = self.store.get_session(session_id)

        assert session is not None
        assert session.id == session_id

    def test_get_nonexistent_session(self):
        """Test retrieving a non-existent session returns None."""
        session = self.store.get_session("nonexistent-id")

        assert session is None

    def test_list_sessions(self):
        """Test listing all sessions."""
        # Create multiple sessions
        self.store.create_session()
        self.store.create_session()
        self.store.create_session()

        sessions = self.store.list_sessions()

        assert len(sessions) == 3
        assert all(isinstance(s, Session) for s in sessions)

    def test_list_sessions_with_limit(self):
        """Test listing sessions with limit."""
        for i in range(5):
            self.store.create_session()

        sessions = self.store.list_sessions(limit=2)

        assert len(sessions) == 2

    def test_list_sessions_with_search(self):
        """Test listing sessions with search query."""
        self.store.create_session(title="Python Project")
        self.store.create_session(title="JavaScript Project")
        self.store.create_session(title="Python Scripts")

        sessions = self.store.list_sessions(search_query="Python")

        assert len(sessions) == 2
        assert all("Python" in s.title for s in sessions)

    def test_update_session_title(self):
        """Test updating session title."""
        session_id = self.store.create_session()

        result = self.store.update_session(session_id, title="New Title")

        assert result is True
        session = self.store.get_session(session_id)
        assert session.title == "New Title"

    def test_update_session_context_tokens(self):
        """Test updating session context tokens."""
        session_id = self.store.create_session()

        result = self.store.update_session(session_id, context_tokens=5000)

        assert result is True
        session = self.store.get_session(session_id)
        assert session.context_tokens == 5000

    def test_update_session_message_count(self):
        """Test updating session message count."""
        session_id = self.store.create_session()

        result = self.store.update_session(session_id, message_count=10)

        assert result is True
        session = self.store.get_session(session_id)
        assert session.message_count == 10

    def test_update_nonexistent_session(self):
        """Test updating a non-existent session returns False."""
        result = self.store.update_session("nonexistent-id", title="Test")

        assert result is False

    def test_delete_session(self):
        """Test deleting a session."""
        session_id = self.store.create_session()

        result = self.store.delete_session(session_id)

        assert result is True
        assert self.store.get_session(session_id) is None

    def test_delete_nonexistent_session(self):
        """Test deleting a non-existent session returns False."""
        result = self.store.delete_session("nonexistent-id")

        assert result is False


class TestMessageCRUD:
    """Test message CRUD operations."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_msg.db"
        self.store = SessionStore(db_path=self.db_path)
        self.session_id = self.store.create_session()
        yield
        SessionStore.reset_instance()

    def test_save_message(self):
        """Test saving a message."""
        message_id = self.store.save_message(
            session_id=self.session_id,
            role="user",
            content="Hello, world!",
            tokens=5,
        )

        assert message_id is not None
        assert len(message_id) > 0

    def test_save_message_with_custom_id(self):
        """Test saving a message with custom ID."""
        message_id = self.store.save_message(
            session_id=self.session_id,
            role="user",
            content="Test",
            message_id="my-msg-id",
        )

        assert message_id == "my-msg-id"

    def test_save_message_with_metadata(self):
        """Test saving a message with metadata."""
        metadata = {"source": "test"}
        message_id = self.store.save_message(
            session_id=self.session_id,
            role="assistant",
            content="Response",
            metadata=metadata,
        )

        messages = self.store.get_messages(self.session_id)
        assert len(messages) == 1
        assert messages[0].metadata == metadata

    def test_get_messages(self):
        """Test retrieving messages for a session."""
        self.store.save_message(self.session_id, "user", "Hello")
        self.store.save_message(self.session_id, "assistant", "Hi there!")
        self.store.save_message(self.session_id, "user", "How are you?")

        messages = self.store.get_messages(self.session_id)

        assert len(messages) == 3
        assert messages[0].role == "user"
        assert messages[1].role == "assistant"
        assert messages[2].role == "user"

    def test_get_messages_with_limit(self):
        """Test retrieving messages with limit."""
        for i in range(5):
            self.store.save_message(self.session_id, "user", f"Message {i}")

        messages = self.store.get_messages(self.session_id, limit=2)

        assert len(messages) == 2

    def test_get_message_count(self):
        """Test getting message count for a session."""
        self.store.save_message(self.session_id, "user", "First")
        self.store.save_message(self.session_id, "assistant", "Second")

        count = self.store.get_message_count(self.session_id)

        assert count == 2

    def test_message_increments_session_count(self):
        """Test that saving messages increments session message_count."""
        self.store.save_message(self.session_id, "user", "Hello")
        self.store.save_message(self.session_id, "assistant", "Hi")

        session = self.store.get_session(self.session_id)
        assert session.message_count == 2


class TestPendingMessages:
    """Test pending message batch writing."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_pending.db"
        self.store = SessionStore(db_path=self.db_path)
        self.session_id = self.store.create_session()
        yield
        SessionStore.reset_instance()

    def test_save_message_without_flush(self):
        """Test saving message without immediate flush."""
        self.store.save_message(
            self.session_id,
            "user",
            "Test",
            flush=False,
        )

        # Message should not be in database yet
        count = self.store.get_message_count(self.session_id)
        assert count == 0

    def test_flush_pending_messages(self):
        """Test flushing pending messages to database."""
        self.store.save_message(self.session_id, "user", "Test 1", flush=False)
        self.store.save_message(self.session_id, "user", "Test 2", flush=False)

        flushed = self.store.flush_pending_messages()

        assert flushed == 2
        assert self.store.get_message_count(self.session_id) == 2

    def test_flush_empty_pending(self):
        """Test flushing when no pending messages."""
        flushed = self.store.flush_pending_messages()

        assert flushed == 0


class TestInputHistory:
    """Test input history operations."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_history.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_save_input_history(self):
        """Test saving input history."""
        self.store.save_input_history("ls -la")

        history = self.store.load_input_history()

        assert "ls -la" in history

    def test_input_history_deduplication(self):
        """Test that duplicate inputs update use count."""
        self.store.save_input_history("ls -la")
        self.store.save_input_history("ls -la")

        history = self.store.load_input_history()

        assert history.count("ls -la") == 1

    def test_load_input_history_with_limit(self):
        """Test loading input history with limit."""
        for i in range(5):
            self.store.save_input_history(f"command_{i}")

        history = self.store.load_input_history(limit=3)

        assert len(history) == 3

    def test_delete_input_history(self):
        """Test deleting input history."""
        self.store.save_input_history("secret_command")

        result = self.store.delete_input_history("secret_command")

        assert result is True
        assert "secret_command" not in self.store.load_input_history()

    def test_clear_input_history(self):
        """Test clearing all input history."""
        self.store.save_input_history("cmd1")
        self.store.save_input_history("cmd2")

        deleted = self.store.clear_input_history()

        assert deleted == 2
        assert len(self.store.load_input_history()) == 0


class TestSearchAndUtility:
    """Test search and utility methods."""

    @pytest.fixture(autouse=True)
    def setup(self, sealed_workspace):
        """Set up test fixtures."""
        SessionStore.reset_instance()
        self.db_path = sealed_workspace["workspace"] / "test_search.db"
        self.store = SessionStore(db_path=self.db_path)
        yield
        SessionStore.reset_instance()

    def test_get_or_create_existing_session(self):
        """Test getting an existing session."""
        session_id = self.store.create_session()

        returned_id, is_new = self.store.get_or_create_session(
            session_id=session_id
        )

        assert returned_id == session_id
        assert is_new is False

    def test_get_or_create_new_session(self):
        """Test creating a new session when one doesn't exist."""
        returned_id, is_new = self.store.get_or_create_session(
            model="gpt-4",
            provider="OpenAI"
        )

        assert returned_id is not None
        assert is_new is True

    def test_search_sessions(self):
        """Test searching sessions."""
        self.store.create_session(title="Python Chat")
        self.store.create_session(title="JavaScript Project")
        self.store.create_session(title="Python Script")

        results = self.store.search_sessions("Python")

        assert len(results) == 2

    def test_search_sessions_with_limit(self):
        """Test searching sessions with limit."""
        for i in range(10):
            self.store.create_session(title=f"Project {i}")

        results = self.store.search_sessions("Project", limit=3)

        assert len(results) == 3

    def test_close(self):
        """Test closing the store."""
        # Should not raise
        self.store.close()

    def test_reset_instance(self):
        """Test resetting the singleton instance."""
        SessionStore.reset_instance()

        # Create new instance should work
        new_db = self.db_path.parent / "new_test.db"
        store = SessionStore(db_path=new_db)

        assert store is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])