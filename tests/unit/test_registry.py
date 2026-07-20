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

    async def await_diagnostics(self, timeout: float = 5.0):
        return True

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


# --- rename_symbol ----------------------------------------------------------
# `search_replace` handles one site; `replace_all` handles one file. Neither
# handles the case that actually breaks a repository: a rename spanning many
# files, where every file you miss is a broken import. Measured on tenacity
# (124 occurrences, 13 files): without this tool the agent renamed the
# definition in __init__.py, left the other 12 files, and broke the package —
# 0/4. With it: 4/4, in 4-6 tool calls.


async def test_rename_symbol_spans_files(registry, workspace):
    (workspace / "a.py").write_text("class Foo:\n    pass\n")
    (workspace / "b.py").write_text("from a import Foo\n\nx = Foo()\n")
    (workspace / "pkg").mkdir()
    (workspace / "pkg" / "c.py").write_text("from a import Foo\ny = Foo\n")

    res = await registry.execute("rename_symbol", {"old": "Foo", "new": "Bar"})
    assert res.ok
    assert "5 occurrence(s) across 3 file(s)" in res.content
    assert "Foo" not in (workspace / "a.py").read_text()
    assert "Bar" in (workspace / "b.py").read_text()
    assert "Bar" in (workspace / "pkg" / "c.py").read_text()


async def test_rename_symbol_matches_whole_words_only(registry, workspace):
    # The reason this is not `replace_all` across files: a substring rename would
    # corrupt every one of these.
    (workspace / "a.py").write_text("Foo = 1\nFooBar = 2\nmy_foo = 3\nBarFoo = 4\nfooed = 5\n")
    res = await registry.execute("rename_symbol", {"old": "Foo", "new": "Baz"})
    assert res.ok
    text = (workspace / "a.py").read_text()
    assert "Baz = 1" in text
    assert "FooBar = 2" in text      # untouched
    assert "BarFoo = 4" in text      # untouched
    assert "my_foo = 3" in text      # untouched


async def test_rename_symbol_skips_ignored_dirs(registry, workspace):
    (workspace / "a.py").write_text("Foo = 1\n")
    (workspace / ".venv").mkdir()
    (workspace / ".venv" / "lib.py").write_text("Foo = 'third-party, not ours'\n")
    res = await registry.execute("rename_symbol", {"old": "Foo", "new": "Bar"})
    assert res.ok
    assert "Foo" in (workspace / ".venv" / "lib.py").read_text()
    assert "1 file(s)" in res.content


async def test_rename_symbol_reports_when_absent(registry, workspace):
    (workspace / "a.py").write_text("x = 1\n")
    res = await registry.execute("rename_symbol", {"old": "Nope", "new": "Bar"})
    assert not res.ok
    assert "not a regex" in res.content


async def test_rename_symbol_rejects_noop(registry, workspace):
    (workspace / "a.py").write_text("Foo = 1\n")
    res = await registry.execute("rename_symbol", {"old": "Foo", "new": "Foo"})
    assert not res.ok


# --- add_docstring ----------------------------------------------------------
# Once the parser stopped dropping docstring edits the agent reached 5/7, and
# the rest of the failures were syntax errors: inserting a docstring with
# search_replace means reproducing the def line and inventing the body's
# indentation. This tool takes a symbol and prose and lets the AST decide.

DOC_SRC = (
    "import math\n\n\ndef area(r):\n    return math.pi * r * r\n\n\n"
    "class Shape:\n    def __init__(self, name):\n        self.name = name\n\n"
    "    def describe(self):\n        return self.name\n"
)


async def test_add_docstring_function_and_method(registry, workspace):
    (workspace / "s.py").write_text(DOC_SRC)
    res = await registry.execute("add_docstring", {
        "path": "s.py", "symbol": "area",
        "docstring": "Return the area.\n\nArgs:\n    r (float): The radius.",
    })
    assert res.ok
    res = await registry.execute("add_docstring", {
        "path": "s.py", "symbol": "Shape.describe", "docstring": "Return the name.",
    })
    assert res.ok

    import ast
    tree = ast.parse((workspace / "s.py").read_text())   # must still parse
    fn = next(n for n in tree.body if getattr(n, "name", None) == "area")
    assert "Return the area." in ast.get_docstring(fn)
    cls = next(n for n in tree.body if getattr(n, "name", None) == "Shape")
    meth = next(n for n in cls.body if getattr(n, "name", None) == "describe")
    assert ast.get_docstring(meth) == "Return the name."


async def test_add_docstring_replaces_an_existing_one(registry, workspace):
    (workspace / "s.py").write_text('def f():\n    """Old."""\n    return 1\n')
    res = await registry.execute("add_docstring", {
        "path": "s.py", "symbol": "f", "docstring": "New.",
    })
    assert res.ok and "Replaced" in res.content
    import ast
    assert ast.get_docstring(ast.parse((workspace / "s.py").read_text()).body[0]) == "New."


async def test_add_docstring_reports_what_is_left(registry, workspace):
    # The model can see the methods (outline lists them) and stops early anyway.
    # A prompt saying "be thorough" measures zero; the tool reporting the
    # remaining work took this from 5/7 to 7/7.
    (workspace / "s.py").write_text(DOC_SRC)
    res = await registry.execute("add_docstring", {
        "path": "s.py", "symbol": "area", "docstring": "Area.",
    })
    assert res.ok
    assert "Still undocumented" in res.content
    assert "Shape.__init__" in res.content and "Shape.describe" in res.content


async def test_add_docstring_unknown_symbol_lists_the_real_ones(registry, workspace):
    (workspace / "s.py").write_text(DOC_SRC)
    res = await registry.execute("add_docstring", {
        "path": "s.py", "symbol": "nope", "docstring": "x",
    })
    assert not res.ok
    assert "area" in res.content and "Shape" in res.content


async def test_add_docstring_refuses_a_file_that_does_not_parse(registry, workspace):
    (workspace / "bad.py").write_text("def f(:\n    pass\n")
    res = await registry.execute("add_docstring", {
        "path": "bad.py", "symbol": "f", "docstring": "x",
    })
    assert not res.ok


# --- read_symbol ------------------------------------------------------------
# find_symbol answers "where" (a path:line) and never "what", and could not
# express "the constructor OF THIS CLASS". Asked to change
# RetryCallState.__init__, the model grepped `def __init__`, got every
# constructor in the file, and edited the wrong class's — breaking 144 tests
# without ever reading a line. Given a name it cannot address, a model guesses.


async def test_read_symbol_addresses_a_method_of_a_class(registry, workspace):
    (workspace / "m.py").write_text(
        "class A:\n    def __init__(self, x):\n        self.x = x\n\n"
        "class B:\n    def __init__(self, y):\n        self.y = y\n"
    )
    res = await registry.execute("read_symbol", {"symbol": "B.__init__"})
    assert res.ok
    assert "self.y = y" in res.content      # B's constructor...
    assert "self.x = x" not in res.content  # ...and not A's


async def test_read_symbol_finds_across_the_workspace(registry, workspace):
    (workspace / "pkg").mkdir()
    (workspace / "pkg" / "deep.py").write_text("def buried():\n    return 42\n")
    res = await registry.execute("read_symbol", {"symbol": "buried"})
    assert res.ok
    assert "return 42" in res.content
    assert "deep.py" in res.content


async def test_read_symbol_reports_a_miss_usefully(registry, workspace):
    (workspace / "m.py").write_text("def a():\n    pass\n")
    res = await registry.execute("read_symbol", {"symbol": "nope"})
    assert not res.ok
    assert "Class.method" in res.content


async def test_write_file_normalizes_async_scaffolding(registry, workspace):
    res = await registry.execute("write_file", {
        "path": "test_async.py",
        "content": "async async async def foo():\n    pass\n"
    })
    assert res.ok
    content = (workspace / "test_async.py").read_text()
    assert content.strip() == "async def foo():\n    pass"


async def test_search_replace_normalizes_async_scaffolding(registry, workspace):
    (workspace / "test_async_sr.py").write_text("x = 1\n")
    res = await registry.execute("search_replace", {
        "path": "test_async_sr.py",
        "search": "x = 1",
        "replace": "async async def foo():\n    pass\n"
    })
    assert res.ok
    content = (workspace / "test_async_sr.py").read_text()
    assert content.strip() == "async def foo():\n    pass"



# --- safe_unescape: preserve string-literal escapes inside code ---------------
# enhancements-03.md #1 proposed "always convert \n->newline, \t->tab, ignore
# quote state". That patch is WRONG: it turns board.split('\n') into
# board.split('<newline>') -> SyntaxError: unterminated string literal -- the
# exact failure it claimed to fix. The quote-tracking (commit c4df84a) is correct.
# These tests guard the correct behaviour against that bad patch.
import ast as _ast
from agent.tools.registry import safe_unescape as _safe_unescape


def test_safe_unescape_keeps_literal_newline_inside_code_string():
    # structural \n becomes a real line break; the '\n' INSIDE the code stays a
    # 2-char escape so the resulting Python is valid.
    out = _safe_unescape("def f(board):\\n    return board.split('\\n')")
    _ast.parse(out)  # must be valid Python (would raise under the #1 patch)
    assert "return board.split('\\n')" in out
    assert out.startswith("def f(board):\n")


def test_safe_unescape_keeps_literal_newline_in_one_liner():
    out = _safe_unescape("x = '\\n'.join(items)")
    _ast.parse(out)
    assert out == "x = '\\n'.join(items)"   # unchanged — it's already one line of code


def test_safe_unescape_converts_structural_tab_indent():
    out = _safe_unescape("def f():\\n\\tif x:\\n\\t\\treturn 1")
    _ast.parse(out)
    assert "\tif x:" in out and "\t\treturn 1" in out
