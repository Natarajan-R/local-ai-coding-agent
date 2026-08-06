"""A wedged language server must trip a breaker and stop costing per-call timeouts.

Each LSP request is individually bounded by ``REQUEST_TIMEOUT``, but nothing used to
remember that the last several calls all timed out -- so a hung server kept charging
that timeout on every query for the rest of the run. These lock in the fail-fast.
"""
import asyncio

import pytest

from agent.perception.lsp import (
    LSP_FAILURE_THRESHOLD,
    LSPClient,
    LSPManager,
)
from agent.utils.circuit_breaker import CircuitOpenError, CircuitState


def _wedged_client(tmp_path, calls):
    """An LSPClient that looks started but whose transport always times out."""
    client = LSPClient(tmp_path)
    client._running = True
    client._ready.set()

    async def always_times_out(method, params, timeout=None):
        calls["n"] += 1
        raise asyncio.TimeoutError("server wedged")

    client._send_request_raw = always_times_out
    return client


async def test_repeated_failures_trip_the_breaker(tmp_path):
    calls = {"n": 0}
    client = _wedged_client(tmp_path, calls)

    for _ in range(LSP_FAILURE_THRESHOLD):
        assert await client.get_definition(tmp_path / "x.py", 0, 0) == []

    assert client.breaker.state == CircuitState.OPEN
    assert calls["n"] == LSP_FAILURE_THRESHOLD


async def test_open_breaker_fails_fast_without_touching_the_server(tmp_path):
    calls = {"n": 0}
    client = _wedged_client(tmp_path, calls)

    for _ in range(LSP_FAILURE_THRESHOLD):
        await client.get_definition(tmp_path / "x.py", 0, 0)
    assert client.breaker.is_open
    hits_when_tripped = calls["n"]

    # Further queries return the same degraded answer without reaching the transport.
    assert await client.get_definition(tmp_path / "x.py", 0, 0) == []
    assert await client.get_references(tmp_path / "x.py", 0, 0) == []
    assert await client.rename(tmp_path / "x.py", 0, 0, "new") is None
    assert calls["n"] == hits_when_tripped, "open breaker still called the server"


async def test_open_breaker_short_circuits_diagnostics_wait(tmp_path):
    """await_diagnostics polls rather than requesting, so it needs its own guard."""
    calls = {"n": 0}
    client = _wedged_client(tmp_path, calls)
    # Pretend a document is awaiting diagnostics that will never arrive.
    client._pending_uris.add("file:///never-answered.py")

    for _ in range(LSP_FAILURE_THRESHOLD):
        await client.get_definition(tmp_path / "x.py", 0, 0)
    assert client.breaker.is_open

    # Without the guard this would burn the full timeout before returning False.
    result = await asyncio.wait_for(client.await_diagnostics(timeout=5.0), timeout=1.0)
    assert result is False


async def test_breaker_recovers_and_serves_again(tmp_path):
    calls = {"n": 0}
    client = _wedged_client(tmp_path, calls)
    client.breaker.recovery_timeout = 0  # recovery is immediately due

    for _ in range(LSP_FAILURE_THRESHOLD):
        await client.get_definition(tmp_path / "x.py", 0, 0)
    assert client.breaker.state == CircuitState.OPEN

    # The server comes back.
    async def works(method, params, timeout=None):
        return [{"uri": "file:///a.py", "range": {}}]

    client._send_request_raw = works
    await asyncio.sleep(0.01)

    assert client._degraded("definition") is False  # recovery window elapsed
    hits = await client.get_definition(tmp_path / "x.py", 0, 0)
    assert hits == [{"uri": "file:///a.py", "range": {}}]
    assert client.breaker.state == CircuitState.CLOSED


async def test_each_server_gets_its_own_breaker(tmp_path):
    """A wedged pylsp must not disable gopls."""
    py = LSPClient(tmp_path, cmd=["pylsp"])
    go = LSPClient(tmp_path, cmd=["gopls"])
    assert py.breaker is not go.breaker
    assert py.breaker.name != go.breaker.name


async def test_manager_stops_respawning_a_server_that_fails_to_start(tmp_path, monkeypatch):
    """A client that fails to start is never pooled -- the breaker must remember."""
    starts = {"n": 0}

    monkeypatch.setattr(
        LSPClient, "is_available", classmethod(lambda cls, *a, **k: True)
    )

    async def failing_start(self):
        starts["n"] += 1
        raise RuntimeError("handshake hung")

    monkeypatch.setattr(LSPClient, "start", failing_start)

    manager = LSPManager(tmp_path)
    for _ in range(LSP_FAILURE_THRESHOLD + 3):
        client, _lang = await manager._client_for(tmp_path / "x.py")
        assert client is None

    # Spawning stops once the start-up breaker trips, instead of retrying forever.
    assert starts["n"] == LSP_FAILURE_THRESHOLD


async def test_circuit_open_error_is_distinguishable(tmp_path):
    """CircuitOpenError must be catchable apart from a genuine transport error."""
    calls = {"n": 0}
    client = _wedged_client(tmp_path, calls)

    for _ in range(LSP_FAILURE_THRESHOLD):
        await client.get_definition(tmp_path / "x.py", 0, 0)

    with pytest.raises(CircuitOpenError):
        await client._send_request("textDocument/definition", {})
