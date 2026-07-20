import pytest
from agent.tools.patcher import apply_line_edit
from agent.errors import ToolError
from agent.tools.registry import ToolRegistry


def test_apply_line_edit_direct_match():
    content = (
        "line 1\n"
        "line 2\n"
        "line 3\n"
        "line 4\n"
        "line 5\n"
    )
    # direct match on line 3 (1-indexed)
    res = apply_line_edit(content, start_line=3, end_line=3, search="line 3", replace="line 3 modified")
    expected = (
        "line 1\n"
        "line 2\n"
        "line 3 modified\n"
        "line 4\n"
        "line 5\n"
    )
    assert res == expected


def test_apply_line_edit_drift_positive():
    # Inserted 2 lines at the beginning, shifting target line 3 -> line 5
    content = (
        "inserted line A\n"
        "inserted line B\n"
        "line 1\n"
        "line 2\n"
        "line 3\n"
        "line 4\n"
        "line 5\n"
    )
    # Target lines 3-3, search "line 3" (should find it at index 4 (line 5) due to drift)
    res = apply_line_edit(content, start_line=3, end_line=3, search="line 3", replace="line 3 modified")
    expected = (
        "inserted line A\n"
        "inserted line B\n"
        "line 1\n"
        "line 2\n"
        "line 3 modified\n"
        "line 4\n"
        "line 5\n"
    )
    assert res == expected


def test_apply_line_edit_drift_negative():
    # Deleted 2 lines from the beginning, shifting target line 5 -> line 3
    content = (
        "line 3\n"
        "line 4\n"
        "line 5\n"
    )
    # Target lines 5-5, search "line 5"
    res = apply_line_edit(content, start_line=5, end_line=5, search="line 5", replace="line 5 modified")
    expected = (
        "line 3\n"
        "line 4\n"
        "line 5 modified\n"
    )
    assert res == expected


def test_apply_line_edit_not_found():
    content = (
        "line 1\n"
        "line 2\n"
        "line 3\n"
    )
    with pytest.raises(ToolError) as exc:
        apply_line_edit(content, start_line=2, end_line=2, search="non-existent", replace="modified")
    assert "not found anywhere" in str(exc.value)


def test_apply_line_edit_ambiguous_in_window():
    content = (
        "other\n"
        "target\n"
        "line 3\n"
        "target\n"
        "line 5\n"
    )
    # direct match at line 1 fails.
    # search is ambiguous because "target" appears twice (lines 2 and 4).
    # Both are within window=50 of start_line=1.
    with pytest.raises(ToolError) as exc:
        apply_line_edit(content, start_line=1, end_line=1, search="target", replace="modified", window=50)
    assert "is ambiguous near line 1" in str(exc.value)


def test_apply_line_edit_resolved_ambiguity_by_window():
    content = (
        "target\n" + "\n" * 100 + "target\n"
    )
    # Two targets, but one is at line 1, and the other is at line 102.
    # With window=50, and start_line=102, only the second one is in window!
    res = apply_line_edit(content, start_line=102, end_line=102, search="target", replace="modified", window=50)
    assert res.endswith("modified\n")
    assert res.startswith("target\n")


def test_apply_line_edit_dedented_search_does_not_overindent():
    """Regression: a dedented search block must not over-indent the replacement.

    The matcher normalizes indentation, so a search block matches even when the
    model writes it at the wrong indent. The indentation aligner used to add
    (replace_indent - search_indent) on top of the file's real indent — so an
    unindented search plus a normally-indented replace shifted the block +16
    (16 -> 32 spaces) and produced `IndentationError: unexpected indent`. This
    broke dot-dsl and tree-building (0/5) on tasks the bare model solves cleanly.
    The replacement must anchor to the file's actual indent (16), not double it.
    """
    import ast
    content = (
        "class Graph:\n"
        "    def __init__(self, data=None):\n"
        "        if data is not None:\n"
        "            for item in data:\n"
        "                if item[0] == ATTR and len(item) != 3:\n"
        "                    raise ValueError('bad')\n"
    )
    # search block is DEDENTED relative to the file (still matches after normalize)
    search = "if item[0] == ATTR and len(item) != 3:\n    raise ValueError('bad')"
    # replace written at natural depth (16 / 20 spaces)
    replace = (
        "                if item[0] == NODE:\n"
        "                    self.nodes.append(item)"
    )
    updated = apply_line_edit(content, start_line=5, end_line=6, search=search, replace=replace)
    # must anchor to the file's real 16-space indent, not 32
    assert "                if item[0] == NODE:\n" in updated
    assert "                                if item[0] == NODE:" not in updated
    # and the result must still parse (the original failure was IndentationError)
    ast.parse(updated)


@pytest.fixture
def registry(local_sandbox, policy, workspace):
    return ToolRegistry(local_sandbox, policy, workspace)


@pytest.mark.asyncio
async def test_registry_edit_lines(registry, workspace):
    code = (
        "def hello():\n"
        "    print('hello')\n"
    )
    (workspace / "a.py").write_text(code, encoding="utf-8")

    res = await registry.execute("edit_lines", {
        "path": "a.py",
        "start_line": 2,
        "end_line": 2,
        "search": "    print('hello')",
        "replace": "    print('hello world')",
    })
    assert res.ok, res.content
    assert "Applied line edit to a.py" in res.content

    updated = (workspace / "a.py").read_text(encoding="utf-8")
    assert "print('hello world')" in updated
