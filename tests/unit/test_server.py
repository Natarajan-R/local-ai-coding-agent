import asyncio

import pytest

from agent.server.broadcaster import ApprovalBroker, Broadcaster, HintBroker

pytestmark = pytest.mark.filterwarnings("ignore")


# -- broadcaster ------------------------------------------------------------
async def test_broadcaster_fans_out_to_all_subscribers():
    b = Broadcaster()
    q1 = b.subscribe()
    q2 = b.subscribe()
    b.publish({"event": "hello"})
    assert (await q1.get())["event"] == "hello"
    assert (await q2.get())["event"] == "hello"
    assert b.client_count == 2
    b.unsubscribe(q1)
    assert b.client_count == 1


async def test_approval_broker_resolves():
    b = Broadcaster()
    broker = ApprovalBroker(b, timeout=5)
    q = b.subscribe()

    async def approve_soon():
        req = await q.get()
        assert req["event"] == "approval_required"
        broker.resolve(req["id"], True)

    asyncio.create_task(approve_soon())
    assert await broker.request("run_command", "pytest") is True


async def test_approval_broker_times_out_to_false():
    broker = ApprovalBroker(Broadcaster(), timeout=0.05)
    assert await broker.request("run_command", "rm x") is False


async def test_hint_broker_resolves_and_times_out():
    b = Broadcaster()
    broker = HintBroker(b, timeout=5)
    q = b.subscribe()

    async def answer():
        req = await q.get()
        assert req["event"] == "escalation_required"
        broker.resolve(req["id"], "try returning 2")

    asyncio.create_task(answer())
    assert await broker.request("stuck on test") == "try returning 2"

    # Blank hint -> None (give up); timeout -> None.
    slow = HintBroker(Broadcaster(), timeout=0.05)
    assert await slow.request("no one answers") is None


# -- server plumbing (aiohttp) ----------------------------------------------
class _FakeOrchestrator:
    """Emits a minimal event stream without touching Ollama."""

    def __init__(self, *args, event_sink=None, **kwargs):
        self._sink = event_sink

    async def run_task(self, task, stream=True):
        self._sink({"event": "run_started", "task": task})
        self._sink({"event": "state_changed", "state": "planning"})
        self._sink({"event": "run_finished", "final_state": "done", "summary": "ok", "stats": {}})


async def test_health_and_ws_run_flow(monkeypatch, tmp_path):
    pytest.importorskip("aiohttp")
    from aiohttp.test_utils import TestClient, TestServer

    from agent.server import app as appmod

    monkeypatch.setattr(appmod, "Orchestrator", _FakeOrchestrator)
    server = appmod.AgentServer(appmod.ServerConfig(workspace=tmp_path, model="fake"))
    client = TestClient(TestServer(server.build_app()))
    await client.start_server()
    try:
        health = await (await client.get("/api/health")).json()
        assert health["status"] == "ok"

        index = await client.get("/")
        assert index.status == 200
        assert "AI Coding Agent" in await index.text()

        # Auth is on by default: a socket without the token is rejected.
        rejected = await client.get("/ws")  # no Upgrade + no token -> 403
        assert rejected.status == 403

        ws = await client.ws_connect(f"/ws?token={server.token}")
        hello = await ws.receive_json()
        assert hello["event"] == "connected"
        assert hello["config"]["model"] == "fake"

        await ws.send_json({"type": "run", "task": "do it", "options": {"interactive": False}})
        events = []
        for _ in range(10):
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5)
            events.append(msg["event"])
            if msg["event"] == "run_finished":
                break
        assert "run_started" in events
        assert "run_finished" in events
        await ws.close()
    finally:
        await client.close()


async def test_ws_allowed_without_token_when_auth_disabled(tmp_path):
    pytest.importorskip("aiohttp")
    from aiohttp.test_utils import TestClient, TestServer

    from agent.server import app as appmod

    server = appmod.AgentServer(appmod.ServerConfig(workspace=tmp_path, require_auth=False))
    assert server.token is None
    client = TestClient(TestServer(server.build_app()))
    await client.start_server()
    try:
        ws = await client.ws_connect("/ws")  # no token needed
        hello = await ws.receive_json()
        assert hello["event"] == "connected"
        await ws.close()
    finally:
        await client.close()


def test_find_free_port_skips_used_port():
    import socket

    from agent.server.app import find_free_port

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        used = s.getsockname()[1]
        # The used port is taken, so the finder must return a different one.
        got = find_free_port("127.0.0.1", used)
        assert got != used
