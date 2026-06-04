#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACP Transport Layer.

Provides stdio and HTTP transport for ACP communication.
"""

# 🧠 Decision - 💾 Memory - ACP Transport

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from common.logging_manager import get_decision_logger

logger = get_decision_logger(__name__)


class ACPTransport(ABC):
    """Abstract base class for ACP transports."""

    @abstractmethod
    async def start(self) -> None:
        """Start the transport."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport."""
        pass

    @abstractmethod
    async def send(self, message: Dict[str, Any]) -> None:
        """Send a message."""
        pass

    @abstractmethod
    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a message. Returns None if no message available."""
        pass


class StdioTransport(ACPTransport):
    """
    ACP transport using stdio.

    Reads JSON-RPC requests from stdin and writes responses to stdout.
    Each line is a complete JSON message.
    """

    def __init__(self):
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._running = False

    async def start(self) -> None:
        """Start stdio transport."""
        loop = asyncio.get_event_loop()
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        self._writer = asyncio.StreamWriter(asyncio.get_event_loop(), None, None, None)
        self._running = True
        logger.info("Stdio transport started")

    async def stop(self) -> None:
        """Stop stdio transport."""
        self._running = False
        if self._writer:
            self._writer.close()
        logger.info("Stdio transport stopped")

    async def send(self, message: Dict[str, Any]) -> None:
        """Send a JSON-RPC message."""
        if not self._writer:
            return

        line = json.dumps(message) + "\n"
        self._writer.write(line.encode("utf-8"))
        await self._writer.drain()

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive a JSON-RPC message."""
        if not self._reader:
            return None

        try:
            line = await asyncio.wait_for(self._reader.readline(), timeout=1.0)
            if not line:
                return None
            return json.loads(line.decode("utf-8"))
        except asyncio.TimeoutError:
            return None
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON received: {e}")
            return None


class HttpTransport(ACPTransport):
    """
    ACP transport using HTTP.

    Provides HTTP endpoints for ACP communication.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8002):
        self._host = host
        self._port = port
        self._app: Optional[Any] = None
        self._runner: Optional[Any] = None
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._response_map: Dict[str, asyncio.Future] = {}

    async def start(self) -> None:
        """Start HTTP transport."""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp is required for HTTP transport")
            return

        self._app = web.Application()
        self._app.router.add_post("/acp", self._handle_request)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._running = True
        logger.info(f"HTTP transport started on {self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop HTTP transport."""
        self._running = False
        if self._runner:
            await self._runner.cleanup()
        logger.info("HTTP transport stopped")

    async def send(self, message: Dict[str, Any]) -> None:
        """Send is not used for HTTP (it's request-response)."""
        pass

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive is not used for HTTP (requests come via handlers)."""
        return None

    async def _handle_request(self, request) -> web.Response:
        """Handle incoming ACP request."""
        try:
            body = await request.json()
            response = await self._process_request(body)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return web.json_response(
                {"error": {"code": -32603, "message": str(e)}},
                status=500,
            )

    async def _handle_health(self, request) -> web.Response:
        """Handle health check."""
        return web.json_response({"status": "ok"})

    async def _process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")

        try:
            result = await self._dispatch_method(method, params)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result,
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            }

    async def _dispatch_method(
        self, method: str, params: Dict[str, Any]
    ) -> Any:
        """Dispatch method to handler."""
        # This will be overridden by ACPServer
        return {}


class WebSocketTransport(ACPTransport):
    """
    ACP transport using WebSocket.

    Provides bidirectional streaming communication.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8003):
        self._host = host
        self._port = port
        self._app: Optional[Any] = None
        self._running = False

    async def start(self) -> None:
        """Start WebSocket transport."""
        try:
            from aiohttp import web
        except ImportError:
            logger.error("aiohttp is required for WebSocket transport")
            return

        self._app = web.Application()
        self._app.router.add_get("/ws", self._handle_websocket)
        self._app.router.add_get("/health", self._handle_health)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        self._running = True
        logger.info(f"WebSocket transport started on {self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop WebSocket transport."""
        self._running = False
        if self._runner:
            await self._runner.cleanup()

    async def send(self, message: Dict[str, Any]) -> None:
        """Send is not used for WebSocket."""
        pass

    async def receive(self) -> Optional[Dict[str, Any]]:
        """Receive is not used for WebSocket."""
        return None

    async def _handle_websocket(self, request) -> web.WebSocketResponse:
        """Handle WebSocket connection."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    response = await self._process_message(data)
                    if response:
                        await ws.send_json(response)
                except json.JSONDecodeError:
                    await ws.send_json({"error": "Invalid JSON"})
            elif msg.type == web.WSMsgType.ERROR:
                logger.error(f"WebSocket error: {ws.exception()}")

        return ws

    async def _handle_health(self, request) -> web.Response:
        """Handle health check."""
        return web.json_response({"status": "ok"})

    async def _process_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming message."""
        return None
