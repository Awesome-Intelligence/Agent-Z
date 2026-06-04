#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for ACP module.
"""

# 🏃 Execution - 🛠️ ToolExec - ACP Tests

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.acp.session import SessionManager, SessionState, SessionStatus
from agent.acp.adapter import ACPServer, ACPError


class TestSessionManager:
    """Tests for SessionManager."""

    def test_create_session(self, tmp_path):
        """Test session creation."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        session = manager.create_session(
            cwd="/test",
            model="test-model",
            title="Test Session",
        )

        assert session.session_id.startswith("sess_")
        assert session.cwd == "/test"
        assert session.model == "test-model"
        assert session.title == "Test Session"
        assert session.status == SessionStatus.ACTIVE

    def test_get_session(self, tmp_path):
        """Test getting a session."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        session = manager.create_session()
        session_id = session.session_id

        retrieved = manager.get_session(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id

    def test_get_nonexistent_session(self, tmp_path):
        """Test getting nonexistent session returns None."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        retrieved = manager.get_session("nonexistent")
        assert retrieved is None

    def test_add_message(self, tmp_path):
        """Test adding message to session."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        session = manager.create_session()

        manager.add_message(session.session_id, "user", "Hello")
        manager.add_message(session.session_id, "assistant", "Hi there")

        retrieved = manager.get_session(session.session_id)
        assert len(retrieved.history) == 2
        assert retrieved.history[0]["role"] == "user"
        assert retrieved.history[0]["content"] == "Hello"

    def test_delete_session(self, tmp_path):
        """Test deleting a session."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        session = manager.create_session()
        session_id = session.session_id

        deleted = manager.delete_session(session_id)
        assert deleted is True
        assert manager.get_session(session_id) is None

    def test_list_sessions(self, tmp_path):
        """Test listing sessions."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        manager.create_session(title="Session 1")
        manager.create_session(title="Session 2")
        manager.create_session(title="Session 3")

        sessions = manager.list_sessions(limit=10)
        assert len(sessions) == 3

    def test_update_session(self, tmp_path):
        """Test updating session."""
        manager = SessionManager(storage_path=tmp_path / "sessions.json")
        session = manager.create_session()

        manager.update_session(
            session.session_id,
            status=SessionStatus.COMPLETED,
            title="Updated Title",
        )

        retrieved = manager.get_session(session.session_id)
        assert retrieved.status == SessionStatus.COMPLETED
        assert retrieved.title == "Updated Title"


class TestSessionState:
    """Tests for SessionState."""

    def test_to_dict(self):
        """Test serialization to dict."""
        state = SessionState(
            session_id="test-123",
            title="Test Session",
            cwd="/home/user",
        )
        data = state.to_dict()

        assert data["session_id"] == "test-123"
        assert data["title"] == "Test Session"
        assert data["cwd"] == "/home/user"
        assert data["status"] == "pending"

    def test_from_dict(self):
        """Test deserialization from dict."""
        data = {
            "session_id": "test-456",
            "title": "Loaded Session",
            "cwd": "/tmp",
            "status": "active",
        }
        state = SessionState.from_dict(data)

        assert state.session_id == "test-456"
        assert state.title == "Loaded Session"
        assert state.status == SessionStatus.ACTIVE


class TestACPServer:
    """Tests for ACPServer."""

    @pytest.fixture
    def server(self):
        """Create server instance."""
        return ACPServer(agent=None)

    @pytest.mark.asyncio
    async def test_initialize(self, server):
        """Test initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {},
        }

        response = await server.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "1"
        assert "result" in response
        assert response["result"]["protocolVersion"] == "1.0"

    @pytest.mark.asyncio
    async def test_ping(self, server):
        """Test ping request."""
        request = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "ping",
            "params": {},
        }

        response = await server.handle_request(request)

        assert response["result"]["pong"] is True

    @pytest.mark.asyncio
    async def test_session_new(self, server):
        """Test session/new request."""
        request = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "session/new",
            "params": {
                "cwd": "/test",
                "title": "Test Session",
            },
        }

        response = await server.handle_request(request)

        assert "sessionId" in response["result"]
        assert response["result"]["title"] == "Test Session"

    @pytest.mark.asyncio
    async def test_session_list(self, server):
        """Test session/list request."""
        # Create some sessions first
        await server.handle_request({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "session/new",
            "params": {},
        })

        request = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "session/list",
            "params": {},
        }

        response = await server.handle_request(request)

        assert len(response["result"]["sessions"]) >= 1

    @pytest.mark.asyncio
    async def test_method_not_found(self, server):
        """Test unknown method returns error."""
        request = {
            "jsonrpc": "2.0",
            "id": "5",
            "method": "unknown/method",
            "params": {},
        }

        response = await server.handle_request(request)

        assert "error" in response
        assert response["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_fs_read_text_file(self, server, tmp_path):
        """Test fs/read_text_file request."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        request = {
            "jsonrpc": "2.0",
            "id": "6",
            "method": "fs/read_text_file",
            "params": {"path": str(test_file)},
        }

        response = await server.handle_request(request)

        assert response["result"]["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_fs_write_text_file(self, server, tmp_path):
        """Test fs/write_text_file request."""
        test_file = tmp_path / "output.txt"

        request = {
            "jsonrpc": "2.0",
            "id": "7",
            "method": "fs/write_text_file",
            "params": {
                "path": str(test_file),
                "content": "Test content",
            },
        }

        response = await server.handle_request(request)

        assert response["result"]["written"] is True
        assert test_file.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_session_prompt(self, server):
        """Test session/prompt request."""
        # Create a session first
        new_response = await server.handle_request({
            "jsonrpc": "2.0",
            "id": "1",
            "method": "session/new",
            "params": {},
        })
        session_id = new_response["result"]["sessionId"]

        # Send prompt
        request = {
            "jsonrpc": "2.0",
            "id": "8",
            "method": "session/prompt",
            "params": {
                "sessionId": session_id,
                "message": "Hello, agent!",
            },
        }

        response = await server.handle_request(request)

        assert "message" in response["result"]
        assert response["result"]["message"]["role"] == "assistant"

        # Check history was updated
        history = server._session_manager.get_session_history(session_id)
        assert len(history) == 2  # user message + assistant response


class TestACPError:
    """Tests for ACPError."""

    def test_error_creation(self):
        """Test error creation."""
        error = ACPError(-32601, "Method not found", {"method": "test"})

        assert error.code == -32601
        assert error.message == "Method not found"
        assert error.data == {"method": "test"}
