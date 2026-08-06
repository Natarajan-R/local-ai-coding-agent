import asyncio

from agent.tools.registry import ToolRegistry


def test_write_file_refuses_to_blank_an_existing_file(local_sandbox, policy, workspace):
    """Empty content must never silently destroy a file.

    Found 2026-07-21 while using the agent on its own codebase: a run told not to
    modify shell_driver.py left it at 0 bytes. _write_file had no guard, so a
    tool call whose content arrived empty -- truncated, or malformed and parsed
    to "" -- overwrote 711 bytes of source and reported ToolResult(ok=True,
    "Wrote 0 bytes"). A destructive action that reports success is worse than
    one that fails.
    """
    src = workspace / "keep.py"
    src.write_text("VALUE = 1\n")
    reg = ToolRegistry(local_sandbox, policy, workspace)

    res = asyncio.run(reg._write_file("keep.py", ""))

    assert res.ok is False
    assert "Refused" in res.content
    assert src.read_text() == "VALUE = 1\n", "the file must be untouched"


def test_write_file_refuses_whitespace_only_over_existing_content(local_sandbox, policy, workspace):
    src = workspace / "keep.py"
    src.write_text("VALUE = 1\n")
    res = asyncio.run(ToolRegistry(local_sandbox, policy, workspace)._write_file("keep.py", "   \n\n  "))
    assert res.ok is False
    assert src.read_text() == "VALUE = 1\n"


def test_write_file_still_allows_a_genuinely_empty_new_file(local_sandbox, policy, workspace):
    """__init__.py is legitimately empty -- the guard must not block creation."""
    res = asyncio.run(ToolRegistry(local_sandbox, policy, workspace)._write_file("pkg/__init__.py", ""))
    assert res.ok is True
    assert (workspace / "pkg" / "__init__.py").exists()


def test_write_file_still_overwrites_with_real_content(local_sandbox, policy, workspace):
    src = workspace / "keep.py"
    src.write_text("OLD = 1\n")
    res = asyncio.run(ToolRegistry(local_sandbox, policy, workspace)._write_file("keep.py", "NEW = 2\n"))
    assert res.ok is True
    assert src.read_text() == "NEW = 2\n"
