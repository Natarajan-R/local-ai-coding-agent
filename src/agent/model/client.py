"""Async client for a local Ollama server (/api/chat)."""
from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

import httpx

from ..errors import ModelError

logger = logging.getLogger(__name__)


class ChatResponse:
    """Normalized view of an Ollama chat response."""

    def __init__(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None,
                 raw: Optional[Dict[str, Any]] = None) -> None:
        self.content = content or ""
        self.tool_calls = tool_calls or []
        self.raw = raw or {}


class OllamaClient:
    """Talk to a local Ollama instance.

    Only depends on the HTTP API, so no model weights are pulled in-process.
    """

    def __init__(
        self,
        model_name: str = "qwen2.5:7b",
        host: str = "http://localhost:11434",
        timeout: float = 180.0,
        options: Optional[Dict[str, Any]] = None,
        client: Optional[httpx.AsyncClient] = None,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.model_name = model_name
        self.host = host.rstrip("/")
        self.options = options or {"temperature": 0.1, "num_ctx": 16384}
        if client is not None:
            self._client = client
        else:
            self._client = httpx.AsyncClient(timeout=timeout, transport=transport)

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    async def is_available(self) -> bool:
        try:
            resp = await self._client.get(f"{self.host}/api/tags", timeout=5.0)
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatResponse:
        """Send a (non-streaming) chat request and return the assistant turn."""
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": self.options,
        }
        if tools:
            payload["tools"] = tools

        logger.debug("Ollama chat request: %s", json.dumps(payload))
        try:
            resp = await self._client.post(f"{self.host}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            logger.debug("Ollama chat response: %s", json.dumps(data))
        except httpx.HTTPError as exc:
            raise ModelError(f"Ollama chat request failed: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ModelError(f"Invalid JSON from Ollama: {exc}") from exc

        message = data.get("message", {}) or {}
        return ChatResponse(
            content=message.get("content", ""),
            tool_calls=message.get("tool_calls", []),
            raw=data,
        )

    async def chat_stream(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> ChatResponse:
        """Stream a chat response, invoking ``on_token`` for each content token.

        The full content and any native ``tool_calls`` are accumulated and
        returned as a :class:`ChatResponse`, so callers get live output *and* a
        complete message to parse tool calls from.
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": self.options,
        }
        if tools:
            payload["tools"] = tools

        logger.debug("Ollama stream chat request: %s", json.dumps(payload))
        content_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        final_raw: Dict[str, Any] = {}
        try:
            async with self._client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    message = chunk.get("message", {}) or {}
                    token = message.get("content", "")
                    if token:
                        content_parts.append(token)
                        if on_token is not None:
                            on_token(token)
                    if message.get("tool_calls"):
                        tool_calls.extend(message["tool_calls"])
                    if chunk.get("done"):
                        final_raw = chunk
                        break
        except httpx.HTTPError as exc:
            raise ModelError(f"Ollama stream request failed: {exc}") from exc

        res = ChatResponse("".join(content_parts), tool_calls, final_raw)
        logger.debug("Ollama stream chat response complete. content=%r tool_calls=%r raw=%s",
                     res.content, res.tool_calls, json.dumps(res.raw))
        return res

    async def generate_stream(self, messages: List[Dict[str, Any]]) -> AsyncIterator[str]:
        """Yield content tokens as they arrive from a streaming chat request."""
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": self.options,
        }
        logger.debug("Ollama generate stream request: %s", json.dumps(payload))
        try:
            async with self._client.stream("POST", f"{self.host}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        logger.debug("Ollama generate stream done: %s", json.dumps(chunk))
                        break
        except httpx.HTTPError as exc:
            raise ModelError(f"Ollama stream request failed: {exc}") from exc
