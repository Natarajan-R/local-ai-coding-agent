"""Model interaction service — context-aware chat with streaming support."""
from __future__ import annotations

import sys
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import ContextManager
    from .event_bus import EventBus
    from .telemetry import RunStats


class ModelService:
    """Encapsulates model interaction: context fitting, streaming, stats recording.

    Extracted from Orchestrator._model_turn so the orchestrator stays focused on
    coordination while the model call mechanics live in one place.

    Uses a *get_chat* / *get_chat_stream* callable so the orchestrator can swap
    the underlying chat function (e.g. for testing) without needing to rebuild
    the ModelService.
    """

    def __init__(
        self,
        context: "ContextManager",
        get_chat: Any,
        get_chat_stream: Any,
        stats: "RunStats",
        event_bus: "EventBus",
    ) -> None:
        self._context = context
        self._get_chat = get_chat
        self._get_chat_stream = get_chat_stream
        self._stats = stats
        self._event_bus = event_bus

    async def turn(
        self,
        messages,
        tools=None,
        label: str = "",
        stream: bool = True,
    ) -> Any:
        """Call the model with context management and optional streaming."""
        fitted = self._context.fit(messages)
        if fitted.trimmed:
            self._event_bus.emit(
                "context_trimmed",
                dropped=fitted.dropped,
                est_tokens=fitted.est_tokens,
            )

        send_messages = fitted.messages

        if not stream:
            response = await self._get_chat()(send_messages, tools)
            self._stats.record(response.raw)
            self._event_bus.emit("assistant_message", label=label, content=response.content)
            return response

        if label:
            from .display import OrchestratorDisplay
            OrchestratorDisplay.print_label(label)

        wrote = {"any": False}

        def writer(token: str) -> None:
            wrote["any"] = True
            sys.stdout.write(token)
            sys.stdout.flush()
            self._event_bus.emit("token", text=token, label=label)

        response = await self._get_chat_stream()(send_messages, tools, on_token=writer)
        if wrote["any"]:
            sys.stdout.write("\n")
            sys.stdout.flush()

        self._stats.record(response.raw)
        return response
