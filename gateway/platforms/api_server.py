#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Server platform adapter for Gateway.

This adapter integrates the OpenAI-compatible API server into the Handsome Agent
Gateway, allowing it to be used alongside other platform adapters.
"""

# 🏃 Execution - 🛠️ ToolExec - API Server Gateway Adapter

import logging
from typing import Any, Dict, Optional

from common.logging_manager import get_execution_logger

logger = get_execution_logger(__name__)


class APIPlatformAdapter:
    """Platform adapter for the OpenAI-compatible API server."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the API platform adapter."""
        self._config = config or {}
        self._server = None
        self._running = False

    @property
    def platform_name(self) -> str:
        """Return the platform name."""
        return "api_server"

    @property
    def is_running(self) -> bool:
        """Check if the adapter is running."""
        return self._running

    async def connect(self) -> None:
        """Connect/start the API server."""
        try:
            from api.api_server import create_api_server

            self._server = create_api_server(self._config)
            await self._server.start()
            self._running = True
            logger.info("API server platform adapter started")
        except Exception as e:
            logger.error("Failed to start API server: %s", e)
            raise

    async def disconnect(self) -> None:
        """Disconnect/stop the API server."""
        if self._server:
            await self._server.stop()
            self._running = False
            logger.info("API server platform adapter stopped")

    async def send_message(self, chat_id: str, text: str, **kwargs) -> None:
        """Send a message (not used for API server)."""
        pass

    async def on_message(self, message: Dict[str, Any]) -> None:
        """Handle received message (not used for API server)."""
        pass

    def init_agent(self, agent, llm_provider=None) -> None:
        """Initialize the agent for the API server."""
        if self._server:
            self._server.init_agent(agent, llm_provider)


def create_api_platform_adapter(config: Optional[Dict[str, Any]] = None) -> APIPlatformAdapter:
    """Create an API platform adapter instance."""
    return APIPlatformAdapter(config)
