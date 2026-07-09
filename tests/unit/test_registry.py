import pytest

from agent.tools.registry import ToolRegistry


@pytest.fixture
def registry(local_sandbox, policy, workspace):
    return ToolRegistry(local_sandbox, policy, workspace)


async def test_write_then_read(registry, workspace):
    res = await registry.execute("write_file", {"path": "a.py", "content": "print(1)"})
    assert res.ok
    assert (workspace / "a.py").read_text() == "print(1)"

    res = await registry.execute("read_file", {"path": "a.py"})
    assert res.ok
    assert "print(1)" in res.content


async def test_read_missing(registry):
    res = await registry.execute("read_file", {"path": "nope.py"})
    assert not res.ok


async def test_read_file_line_range(registry, workspace):
    (workspace / "big.py").write_text("\n".join(f"line{i}" for i in range(1, 21)) + "\n")
    res = await registry.execute("read_file", {"path": "big.py", "start_line": 3, "end_line": 5})
    assert res.ok
    assert "line3" in res.content and "line5" in res.content
    assert "line6" not in res.content
    assert "line2" not in res.content


async def test_read_file_range_out_of_bounds_clamps(registry, workspace):
    (workspace / "small.py").write_text("a\nb\n")
    res = await registry.execute("read_file", {"path": "small.py", "start_line": 1, "end_line": 999})
    assert res.ok
    assert "a" in res.content and "b" in res.content


async def test_search_replace(registry, workspace):
    (workspace / "b.py").write_text("x = 1\n")
    res = await registry.execute("search_replace", {"path": "b.py", "search": "x = 1", "replace": "x = 2"})
    assert res.ok
    assert (workspace / "b.py").read_text() == "x = 2\n"


async def test_path_escape_blocked(registry):
    res = await registry.execute("write_file", {"path": "../evil.py", "content": "bad"})
    assert not res.ok
    assert "outside" in res.content.lower()


async def test_list_files(registry, workspace):
    (workspace / "one.py").write_text("1")
    (workspace / "two.py").write_text("2")
    res = await registry.execute("list_files", {})
    assert "one.py" in res.content and "two.py" in res.content


async def test_run_command(registry):
    res = await registry.execute("run_command", {"command": "echo hi"})
    assert res.ok
    assert "hi" in res.content


async def test_run_command_blocked(registry):
    res = await registry.execute("run_command", {"command": "rm -rf /"})
    assert not res.ok


async def test_write_invalid_python_warns_but_writes(registry, workspace):
    res = await registry.execute("write_file", {"path": "bad.py", "content": "def f(:\n"})
    assert res.ok  # the write still happens
    assert (workspace / "bad.py").exists()
    assert "syntax error" in res.content.lower()


async def test_write_valid_python_has_no_warning(registry):
    res = await registry.execute("write_file", {"path": "good.py", "content": "x = 1\n"})
    assert res.ok
    assert "syntax error" not in res.content.lower()


async def test_search_text_tool(registry, workspace):
    (workspace / "a.py").write_text("needle = 1\n")
    (workspace / "b.py").write_text("other = 2\n")
    res = await registry.execute("search_text", {"query": "needle"})
    assert res.ok
    assert "a.py:1" in res.content
    assert "b.py" not in res.content


async def test_search_text_no_matches(registry, workspace):
    (workspace / "a.py").write_text("x = 1\n")
    res = await registry.execute("search_text", {"query": "zzznotfound"})
    assert res.ok and "No matches" in res.content


async def test_outline_tool(registry, workspace):
    (workspace / "m.py").write_text("class A:\n    def go(self):\n        return 1\n")
    res = await registry.execute("outline", {"path": "m.py"})
    assert res.ok
    assert "class A" in res.content and "def go" in res.content
    assert "return 1" not in res.content  # bodies dropped


async def test_list_files_directory_scope(registry, workspace):
    (workspace / "src").mkdir()
    (workspace / "src" / "x.py").write_text("x = 1")
    (workspace / "top.py").write_text("y = 2")
    res = await registry.execute("list_files", {"directory": "src"})
    assert res.ok
    assert "src/x.py" in res.content and "top.py" not in res.content


async def test_exploration_tools_registered(registry):
    names = {s["function"]["name"] for s in registry.get_descriptions()}
    assert {"search_text", "outline", "find_symbol", "find_importers"} <= names


async def test_find_symbol_tool(registry, workspace):
    (workspace / "models.py").write_text("class Account:\n    def close(self):\n        return 1\n")
    res = await registry.execute("find_symbol", {"name": "Account"})
    assert res.ok
    assert "models.py:1" in res.content and "class Account" in res.content


async def test_find_importers_tool(registry, workspace):
    (workspace / "lib.py").write_text("def util():\n    return 1\n")
    (workspace / "main.py").write_text("from lib import util\n")
    res = await registry.execute("find_importers", {"name": "util"})
    assert res.ok
    assert "main.py" in res.content


async def test_remember_tool(local_sandbox, policy, workspace):
    from agent.memory import MemoryStore
    from agent.tools.registry import ToolRegistry

    store = MemoryStore(workspace)
    reg = ToolRegistry(local_sandbox, policy, workspace, memory=store)
    names = {s["function"]["name"] for s in reg.get_descriptions()}
    assert "remember" in names

    res = await reg.execute("remember", {"text": "Use pathlib, not os.path", "kind": "convention"})
    assert res.ok
    assert store.count() == 1
    # duplicate is a no-op
    res = await reg.execute("remember", {"text": "Use pathlib, not os.path"})
    assert store.count() == 1


def test_remember_tool_absent_without_memory(registry):
    names = {s["function"]["name"] for s in registry.get_descriptions()}
    assert "remember" not in names  # the default fixture registry has no memory


async def test_finish_is_final(registry):
    res = await registry.execute("finish", {"summary": "done"})
    assert res.ok and res.is_final


async def test_unknown_tool(registry):
    res = await registry.execute("frobnicate", {})
    assert not res.ok


def test_descriptions_are_valid_schemas(registry):
    schemas = registry.get_descriptions()
    names = {s["function"]["name"] for s in schemas}
    assert {"read_file", "write_file", "search_replace", "run_command", "finish"} <= names


class _FakeLSP:
    """Stand-in for LSPClient so registry LSP wiring can be tested without pylsp."""

    async def get_definition(self, path, line, character):
        return [{"uri": path.as_uri(),
                 "range": {"start": {"line": 0, "character": 4}, "end": {"line": 0, "character": 7}}}]

    async def get_references(self, path, line, character):
        return [{"uri": path.as_uri(), "range": {"start": {"line": 3, "character": 4}}}]

    def get_all_diagnostics(self):
        return "No diagnostics reported."

    async def open_document(self, path, content):
        pass

    async def change_document(self, path, content):
        pass


def test_lsp_tools_registered_only_when_lsp_present(local_sandbox, policy, workspace):
    without = ToolRegistry(local_sandbox, policy, workspace)
    names = {s["function"]["name"] for s in without.get_descriptions()}
    assert "find_definition" not in names

    with_lsp = ToolRegistry(local_sandbox, policy, workspace, lsp=_FakeLSP())
    names = {s["function"]["name"] for s in with_lsp.get_descriptions()}
    assert {"find_definition", "find_references", "get_diagnostics"} <= names


async def test_lsp_tools_dispatch(local_sandbox, policy, workspace):
    (workspace / "foo.py").write_text("def bar():\n    return 1\nx = bar()\n")
    reg = ToolRegistry(local_sandbox, policy, workspace, lsp=_FakeLSP())

    res = await reg.execute("find_definition", {"path": "foo.py", "line": 2, "character": 4})
    assert res.ok and "foo.py" in res.content

    res = await reg.execute("find_references", {"path": "foo.py", "line": 0, "character": 4})
    assert res.ok and "foo.py" in res.content

    res = await reg.execute("get_diagnostics", {})
    assert res.ok
