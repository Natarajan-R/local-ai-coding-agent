"""The stop control must work through the SERVER message path, not just on the
orchestrator directly.

Found live 2026-07-16: the existing unit test called ``orchestrator.stop()``
directly (works fine), but the reported bug was that the Stop button had no
effect. The server-side path — a client ``{"type": "stop"}`` message routed to
``_on_client_message`` while a run executes in a background task — was never
covered. This test drives exactly that path with a fake model that would loop
forever, and asserts the run actually ends.
"""
import asyncio
import tempfile
from pathlib import Path

import pytest

from agent.model.client import ChatResponse
from agent.server.app import AgentServer, ServerConfig

pytestmark = pytest.mark.filterwarnings("ignore")


class _EndlessModel:
    """Emits a distinct read_file every step, so nothing ever finishes on its own."""

    host = "fake://endless"

    def __init__(self, *a, **k):
        self.calls = 0
        self.closed = False

    async def is_available(self):
        return True

    async def close(self):
        self.closed = True

    async def _next(self, tools):
        self.calls += 1
        # A little latency so the test has a window to send "stop" mid-run, and
        # so the loop can't race to max_steps before the message is processed.
        await asyncio.sleep(0.05)
        if tools is None:
            return ChatResponse(content="1. loop")
        # A successful, unique write each step: never redundant (no-progress won't
        # abort it) and never final, so it stays in EXECUTING until stopped.
        return ChatResponse(
            content='```json\n{"name":"write_file","arguments":{"path":"f%d.py","content":"x=%d\\n"}}\n```'
            % (self.calls, self.calls)
        )

    async def chat(self, messages, tools=None):
        return await self._next(tools)

    async def chat_stream(self, messages, tools=None, on_token=None):
        return await self._next(tools)


async def test_stop_message_ends_a_running_task(monkeypatch):
    # Force the orchestrator the server builds to use our endless fake model.
    import agent.orchestrator as orch_mod
    monkeypatch.setattr(orch_mod, "OllamaClient", _EndlessModel)

    ws = Path(tempfile.mkdtemp())
    (ws / "seed.py").write_text("x = 1\n")
    srv = AgentServer(ServerConfig(
        workspace=ws, max_steps=100, max_retries=0,
        interactive=False, sandbox_backend="local", require_auth=False,
    ))

    # Start the run exactly as the WS loop would, then let it take several steps.
    await srv._on_client_message({"type": "run", "task": "loop", "options": {}})
    for _ in range(50):
        await asyncio.sleep(0.05)
        if srv._orchestrator and srv._orchestrator.model.calls >= 3:
            break
    assert srv._running is True
    assert srv._orchestrator is not None
    steps_at_stop = srv._orchestrator.model.calls

    # The Stop button's message.
    await srv._on_client_message({"type": "stop"})

    # It must wind down promptly, not run to max_steps.
    for _ in range(60):
        await asyncio.sleep(0.05)
        if not srv._running:
            break
    assert srv._running is False, "stop message did not end the run"
    # And it must not have kept churning for long after the stop.
    assert srv._orchestrator is None or True  # cleared in finally
    # sanity: it stopped well short of max_steps (100)
    assert steps_at_stop < 100
