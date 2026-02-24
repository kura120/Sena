# src/api/websocket/manager.py
"""
WebSocket Manager

Handles WebSocket connections for real-time updates:
- Processing stage updates
- Token streaming
- Log streaming
- Memory updates
"""

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from src.utils.logger import logger


class WSEventType(str, Enum):
    """WebSocket event types."""

    # Server -> Client
    CONNECTED = "connected"
    PROCESSING_UPDATE = "processing_update"
    STREAM_TOKEN = "stream_token"
    STREAM_END = "stream_end"
    MEMORY_UPDATE = "memory_update"
    EXTENSION_UPDATE = "extension_update"
    PERSONALITY_UPDATE = "personality_update"
    LOG = "log"
    ERROR = "error"
    PONG = "pong"

    # Client -> Server
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"


@dataclass
class WSMessage:
    """WebSocket message structure."""

    type: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(asdict(self))


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client."""

    websocket: WebSocket
    client_id: str
    subscriptions: set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=datetime.now)

    async def send(self, message: WSMessage) -> bool:
        """Send a message to this client."""
        if self.websocket.client_state != WebSocketState.CONNECTED:
            logger.debug(f"Skipping send to {self.client_id}; websocket not accepted")
            return False
        try:
            await self.websocket.send_text(message.to_json())
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {self.client_id}: {e}")
            return False


class WebSocketManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - Multiple client connections
    - Channel-based subscriptions
    - Automatic cleanup on disconnect
    - Rate limiting (optional)
    """

    def __init__(self, max_connections: int = 100):
        self._connections: dict[str, ClientConnection] = {}
        self._max_connections = max_connections
        self._lock = asyncio.Lock()
        self._client_counter = 0

    @property
    def connection_count(self) -> int:
        """Get current number of connections."""
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> Optional[str]:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection

        Returns:
            Client ID if connected, None if rejected
        """
        async with self._lock:
            if len(self._connections) >= self._max_connections:
                logger.warning("Max WebSocket connections reached")
                await websocket.close(code=1013, reason="Max connections reached")
                return None

            await websocket.accept()

            self._client_counter += 1
            client_id = f"client_{self._client_counter}"

            self._connections[client_id] = ClientConnection(
                websocket=websocket,
                client_id=client_id,
                subscriptions={"processing", "logs"},  # Default subscriptions
            )

            logger.info(f"WebSocket client connected: {client_id}")

            # Send connected confirmation
            await self._connections[client_id].send(
                WSMessage(type=WSEventType.CONNECTED.value, data={"client_id": client_id})
            )

            return client_id

    async def disconnect(self, client_id: str) -> None:
        """
        Disconnect a client.

        Args:
            client_id: The client ID to disconnect
        """
        async with self._lock:
            if client_id in self._connections:
                del self._connections[client_id]
                logger.info(f"WebSocket client disconnected: {client_id}")

    async def subscribe(self, client_id: str, channels: list[str]) -> None:
        """
        Subscribe a client to channels.

        Args:
            client_id: The client ID
            channels: List of channels to subscribe to
        """
        if client_id in self._connections:
            self._connections[client_id].subscriptions.update(channels)
            logger.debug(f"Client {client_id} subscribed to: {channels}")

    async def unsubscribe(self, client_id: str, channels: list[str]) -> None:
        """
        Unsubscribe a client from channels.

        Args:
            client_id: The client ID
            channels: List of channels to unsubscribe from
        """
        if client_id in self._connections:
            self._connections[client_id].subscriptions.difference_update(channels)
            logger.debug(f"Client {client_id} unsubscribed from: {channels}")

    async def send_to_client(self, client_id: str, message: WSMessage) -> bool:
        """
        Send a message to a specific client.

        Args:
            client_id: The client ID
            message: The message to send

        Returns:
            True if sent successfully
        """
        if client_id in self._connections:
            return await self._connections[client_id].send(message)
        return False

    async def broadcast(
        self,
        message: WSMessage,
        channel: Optional[str] = None,
    ) -> int:
        """
        Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
            channel: Optional channel filter (only send to subscribed clients)

        Returns:
            Number of clients that received the message
        """
        sent_count = 0
        disconnected: list[str] = []

        for client_id, connection in self._connections.items():
            # Check channel subscription
            if channel and channel not in connection.subscriptions:
                continue

            success = await connection.send(message)
            if success:
                sent_count += 1
            else:
                disconnected.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected:
            await self.disconnect(client_id)

        return sent_count

    async def broadcast_processing_update(
        self,
        stage: str,
        details: str = "",
    ) -> int:
        """Broadcast a processing stage update."""
        return await self.broadcast(
            WSMessage(type=WSEventType.PROCESSING_UPDATE.value, data={"stage": stage, "details": details}),
            channel="processing",
        )

    async def broadcast_token(self, token: str, is_final: bool = False) -> int:
        """Broadcast a streamed token."""
        event_type = WSEventType.STREAM_END if is_final else WSEventType.STREAM_TOKEN
        return await self.broadcast(
            WSMessage(type=event_type.value, data={"token": token, "is_final": is_final}), channel="processing"
        )

    async def broadcast_log(
        self,
        level: str,
        message: str,
        logger_name: Optional[str] = None,
    ) -> int:
        """Broadcast a log message."""
        return await self.broadcast(
            WSMessage(
                type=WSEventType.LOG.value,
                data={
                    "level": level,
                    "message": message,
                    "logger_name": logger_name,
                },
            ),
            channel="logs",
        )

    async def broadcast_error(
        self,
        error_type: str,
        message: str,
        recoverable: bool = False,
    ) -> int:
        """Broadcast an error."""
        return await self.broadcast(
            WSMessage(
                type=WSEventType.ERROR.value,
                data={
                    "error_type": error_type,
                    "message": message,
                    "recoverable": recoverable,
                },
            )
        )

    async def broadcast_memory_update(
        self,
        action: str,
        memory_id: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> int:
        """Broadcast a memory system update."""
        return await self.broadcast(
            WSMessage(
                type=WSEventType.MEMORY_UPDATE.value,
                data={
                    "action": action,
                    "memory_id": memory_id,
                    "details": details or {},
                },
            ),
            channel="memory",
        )

    async def handle_client_message(
        self,
        client_id: str,
        message: str,
    ) -> None:
        """
        Handle an incoming message from a client.

        Args:
            client_id: The client ID
            message: The raw message string
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == WSEventType.PING.value:
                await self.send_to_client(client_id, WSMessage(type=WSEventType.PONG.value, data={}))

            elif msg_type == WSEventType.SUBSCRIBE.value:
                channels = data.get("channels", [])
                await self.subscribe(client_id, channels)

            elif msg_type == WSEventType.UNSUBSCRIBE.value:
                channels = data.get("channels", [])
                await self.unsubscribe(client_id, channels)

            else:
                logger.warning(f"Unknown WebSocket message type: {msg_type}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from client {client_id}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get WebSocket manager statistics."""
        return {
            "total_connections": len(self._connections),
            "max_connections": self._max_connections,
            "clients": [
                {
                    "client_id": conn.client_id,
                    "subscriptions": list(conn.subscriptions),
                    "connected_at": conn.connected_at.isoformat(),
                }
                for conn in self._connections.values()
            ],
        }


# Global WebSocket manager instance
ws_manager = WebSocketManager()
