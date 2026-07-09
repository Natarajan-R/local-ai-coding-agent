"""Event fan-out and human-approval brokering for the web server.

Both are transport-agnostic and dependency-free (stdlib asyncio only), so they
are unit-testable without aiohttp.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any, Awaitable, Callable, Dict, Optional, Set


class Broadcaster:
    """Fan structured events out to every subscribed client queue.

    ``publish`` is synchronous and non-blocking so the orchestrator (running in
    the same event loop) can emit events from anywhere, including sync callbacks.
    """

    def __init__(self) -> None:
        self._queues: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._queues.discard(queue)

    def publish(self, event: Dict[str, Any]) -> None:
        for queue in list(self._queues):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # pragma: no cover - unbounded queues
                pass

    @property
    def client_count(self) -> int:
        return len(self._queues)


class ApprovalBroker:
    """Bridge the async approval request to a human decision over the socket.

    The orchestrator awaits :meth:`request`; the web layer calls :meth:`resolve`
    when the browser answers. Times out (deny) if no decision arrives.
    """

    def __init__(self, broadcaster: Broadcaster, timeout: float = 300.0) -> None:
        self._broadcaster = broadcaster
        self._timeout = timeout
        self._pending: Dict[str, asyncio.Future] = {}

    async def request(self, action: str, detail: str) -> bool:
        req_id = uuid.uuid4().hex[:8]
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        self._broadcaster.publish(
            {"event": "approval_required", "id": req_id, "action": action, "detail": detail}
        )
        try:
            return bool(await asyncio.wait_for(future, timeout=self._timeout))
        except asyncio.TimeoutError:
            self._broadcaster.publish({"event": "approval_timeout", "id": req_id})
            return False
        finally:
            self._pending.pop(req_id, None)

    def resolve(self, req_id: str, approved: bool) -> bool:
        future = self._pending.get(req_id)
        if future is not None and not future.done():
            future.set_result(bool(approved))
            return True
        return False

    def as_callback(self) -> Callable[[str, str], Awaitable[bool]]:
        return self.request


class HintBroker:
    """Ask the browser for a free-text hint when the agent escalates."""

    def __init__(self, broadcaster: Broadcaster, timeout: float = 600.0) -> None:
        self._broadcaster = broadcaster
        self._timeout = timeout
        self._pending: Dict[str, asyncio.Future] = {}

    async def request(self, context: str) -> Optional[str]:
        req_id = uuid.uuid4().hex[:8]
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[req_id] = future
        self._broadcaster.publish(
            {"event": "escalation_required", "id": req_id, "context": context}
        )
        try:
            value = await asyncio.wait_for(future, timeout=self._timeout)
            return (value or "").strip() or None
        except asyncio.TimeoutError:
            self._broadcaster.publish({"event": "escalation_timeout", "id": req_id})
            return None
        finally:
            self._pending.pop(req_id, None)

    def resolve(self, req_id: str, hint: Optional[str]) -> bool:
        future = self._pending.get(req_id)
        if future is not None and not future.done():
            future.set_result(hint or "")
            return True
        return False
