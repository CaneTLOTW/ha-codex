"""Small authenticated Home Assistant WebSocket client for Lovelace resources."""

from __future__ import annotations

import asyncio
import json
import os
from urllib.parse import urlsplit, urlunsplit

import websockets


class HomeAssistantAPIError(RuntimeError):
    """A sanitized transport or Home Assistant WebSocket error."""


def websocket_url(base_url: str) -> str:
    parts = urlsplit(base_url)
    scheme = {"http": "ws", "https": "wss", "ws": "ws", "wss": "wss"}.get(parts.scheme)
    if not scheme or not parts.netloc:
        raise HomeAssistantAPIError("HA_URL must be an absolute HTTP(S) URL")
    path = parts.path.rstrip("/") + "/api/websocket"
    return urlunsplit((scheme, parts.netloc, path, "", ""))


class HomeAssistantWebSocket:
    """One-request authenticated WebSocket client; token never enters logs or errors."""

    def __init__(self, base_url: str | None = None, token: str | None = None):
        self.base_url = base_url or os.environ.get("HA_URL", "http://supervisor/core")
        self.token = token if token is not None else os.environ.get("HA_TOKEN", "")
        if not self.token:
            raise HomeAssistantAPIError("HA_TOKEN is unavailable to the privileged resource helper")
        self.url = websocket_url(self.base_url)

    async def request(self, command: dict) -> object:
        try:
            async with websockets.connect(self.url, open_timeout=10, close_timeout=2, max_size=2**20) as ws:
                greeting = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if greeting.get("type") != "auth_required":
                    raise HomeAssistantAPIError("Unexpected HA WebSocket authentication handshake")
                await ws.send(json.dumps({"type": "auth", "access_token": self.token}))
                auth = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if auth.get("type") != "auth_ok":
                    raise HomeAssistantAPIError("Home Assistant rejected WebSocket authentication")
                message_id = 1
                await ws.send(json.dumps({"id": message_id, **command}))
                while True:
                    response = json.loads(await asyncio.wait_for(ws.recv(), timeout=20))
                    if response.get("id") != message_id:
                        continue
                    if not response.get("success"):
                        error = response.get("error", {})
                        message = str(error.get("message", "Home Assistant API request failed"))
                        message = message.replace(self.token, "[redacted]")
                        raise HomeAssistantAPIError(message[:300])
                    return response.get("result")
        except HomeAssistantAPIError:
            raise
        except Exception as err:
            message = str(err).replace(self.token, "[redacted]")
            raise HomeAssistantAPIError(f"Home Assistant WebSocket request failed: {message[:200]}") from None


class ResourceAPI:
    """The only HA collection operations exposed to this MCP server."""

    def __init__(self, client: HomeAssistantWebSocket):
        self.client = client

    async def list(self) -> list[dict]:
        result = await self.client.request({"type": "lovelace/resources"})
        if not isinstance(result, list) or any(not isinstance(item, dict) for item in result):
            raise HomeAssistantAPIError("Unexpected Lovelace resource list response")
        return result

    async def create(self, url: str, resource_type: str) -> dict:
        result = await self.client.request({
            "type": "lovelace/resources/create",
            "url": url,
            "res_type": resource_type,
        })
        if not isinstance(result, dict) or not result.get("id"):
            raise HomeAssistantAPIError("Unexpected resource create response")
        return result

    async def update(self, resource_id: str, url: str, resource_type: str) -> dict:
        result = await self.client.request({
            "type": "lovelace/resources/update",
            "resource_id": resource_id,
            "url": url,
            "res_type": resource_type,
        })
        if not isinstance(result, dict):
            raise HomeAssistantAPIError("Unexpected resource update response")
        return result

    async def delete(self, resource_id: str) -> None:
        await self.client.request({
            "type": "lovelace/resources/delete",
            "resource_id": resource_id,
        })
