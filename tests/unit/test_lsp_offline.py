"""LSP behaviour when no server is running — must never hang (regression)."""
import asyncio

from agent.perception.lsp import LSPClient


def test_is_available_returns_bool(tmp_path):
    assert isinstance(LSPClient.is_available(tmp_path), bool)


def test_is_available_false_for_bogus_binary(tmp_path):
    assert LSPClient.is_available(tmp_path, cmd=["definitely-not-a-real-binary-xyz"]) is False


async def test_unstarted_client_queries_return_quickly(tmp_path):
    # A client that was never started (e.g. pylsp missing) must return promptly,
    # not block forever on the readiness event.
    client = LSPClient(tmp_path)
    assert client.running is False
    defs = await asyncio.wait_for(client.get_definition(tmp_path / "x.py", 0, 0), timeout=5)
    refs = await asyncio.wait_for(client.get_references(tmp_path / "x.py", 0, 0), timeout=5)
    assert defs == []
    assert refs == []
    # Document sync is a no-op (returns) rather than hanging.
    await asyncio.wait_for(client.open_document(tmp_path / "x.py", "x = 1"), timeout=5)


def test_orchestrator_disables_lsp_when_unavailable(tmp_path, monkeypatch):
    # When no server is available, the orchestrator must not register LSP tools.
    import agent.orchestrator as orch_mod

    monkeypatch.setattr(orch_mod.LSPManager, "is_available", classmethod(lambda cls, *a, **k: False))
    orch = orch_mod.Orchestrator(workspace=tmp_path, sandbox_backend="local", interactive=False)
    assert orch.lsp is None
    names = {s["function"]["name"] for s in orch.tools.get_descriptions()}
    assert "find_definition" not in names
    asyncio.run(orch.model.close())


def test_lsp_manager_routes_by_extension(tmp_path):
    from agent.perception.lsp import LSPManager

    mgr = LSPManager(tmp_path)
    # Each extension maps to the right server command + languageId.
    assert mgr._spec_for("a.py") == (("pylsp",), "python")
    assert mgr._spec_for("main.go") == (("gopls",), "go")
    ts_cmd, ts_lang = mgr._spec_for("app.ts")
    assert ts_cmd == ("typescript-language-server", "--stdio") and ts_lang == "typescript"
    js_cmd, js_lang = mgr._spec_for("app.jsx")
    assert js_cmd == ts_cmd and js_lang == "javascript"   # same server, different id
    assert mgr._spec_for("lib.rs") == (("rust-analyzer",), "rust")
    assert mgr._spec_for("readme.md") is None              # no server for this type


async def test_lsp_manager_noop_for_unknown_and_unavailable(tmp_path):
    from agent.perception.lsp import LSPManager

    # A server map pointing at a bogus binary -> not available, ops are safe no-ops.
    ext_map = {".xx": (("definitely-not-a-real-lsp-xyz",), "xx")}
    assert LSPManager.is_available(tmp_path, ext_map) is False
    mgr = LSPManager(tmp_path, ext_map)
    await mgr.open_document(tmp_path / "f.xx", "data")      # no crash
    assert await mgr.get_definition(tmp_path / "f.xx", 0, 0) == []
    assert await mgr.get_definition(tmp_path / "f.unknown", 0, 0) == []
    assert mgr.get_all_diagnostics() == "No diagnostics reported."


def test_await_diagnostics_waits_for_the_server_then_returns(tmp_path):
    """get_diagnostics must not answer 'clean' before the server has analysed.

    Regression: diagnostics arrive ~1s after didOpen, so reading the cache straight
    after a write reported "No diagnostics reported." for code with an obvious error —
    a false all-clear the model then acted on.
    """
    client = LSPClient(tmp_path)
    uri = (tmp_path / "x.py").resolve().as_uri()

    client._expect_diagnostics(uri)
    # Nothing published yet: must report that it gave up rather than claim success.
    assert asyncio.run(client.await_diagnostics(timeout=0.2)) is False

    client.diagnostics[uri] = []          # server answers (clean file -> empty list)
    assert asyncio.run(client.await_diagnostics(timeout=0.2)) is True


def test_expect_diagnostics_drops_the_stale_result(tmp_path):
    """A re-edit must invalidate the previous diagnostics, not return them again.

    Without the pop, await_diagnostics sees the *old* entry, returns instantly, and the
    model is told about the bug it just fixed.
    """
    client = LSPClient(tmp_path)
    uri = (tmp_path / "x.py").resolve().as_uri()
    client.diagnostics[uri] = [{"message": "undefined name 'itms'"}]

    client._expect_diagnostics(uri)       # file was just edited

    assert uri not in client.diagnostics
    assert asyncio.run(client.await_diagnostics(timeout=0.2)) is False
