import asyncio
import shutil
import sys
from pathlib import Path

import pytest

from agent.perception.lsp import LSPClient
from agent.tools.registry import ToolRegistry

_pylsp_available = (
    shutil.which("pylsp") is not None
    or (Path(sys.executable).parent / "pylsp").exists()
)
pytestmark = pytest.mark.skipif(not _pylsp_available, reason="pylsp not installed")


@pytest.mark.asyncio
async def test_lsp_client_rename(tmp_path):
    # Set up a small test workspace
    workspace = tmp_path
    py_file = workspace / "foo.py"
    py_content = (
        "def bar():\n"
        "    return 42\n"
        "\n"
        "x = bar()\n"
    )
    py_file.write_text(py_content, encoding="utf-8")

    # Initialize LSPClient
    client = LSPClient(workspace)
    await client.start()

    try:
        await client.open_document(py_file, py_content)
        await asyncio.sleep(1.5)

        # Query rename of 'bar' at line 0, column 4 (inside the def statement)
        edit = await client.rename(py_file, 0, 4, "new_bar")
        assert edit is not None
        assert "changes" in edit or "documentChanges" in edit

        # Verify that changes or documentChanges contain the edit
        changes = edit.get("changes", {})
        doc_changes = edit.get("documentChanges", [])
        assert len(changes) > 0 or len(doc_changes) > 0
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_registry_rename_symbol_lsp(local_sandbox, policy, workspace):
    registry = ToolRegistry(local_sandbox, policy, workspace)

    foo_code = (
        "def compute_value():\n"
        "    return 100\n"
    )
    (workspace / "foo.py").write_text(foo_code, encoding="utf-8")

    main_code = (
        "from foo import compute_value\n"
        "\n"
        "res = compute_value()\n"
    )
    (workspace / "main.py").write_text(main_code, encoding="utf-8")

    # Initialize indexer & symbols
    registry._symbol_index().refresh()

    if registry.lsp:
        await registry.lsp.open_document(workspace / "foo.py", foo_code)
        await registry.lsp.open_document(workspace / "main.py", main_code)
        await asyncio.sleep(1.5)

        # Try rename
        res = await registry.execute("rename_symbol", {
            "old": "compute_value",
            "new": "get_computed_value",
        })

        assert res.ok, f"Rename failed: {res.content}"
        assert "Semantically renamed" in res.content

        # Verify both files updated
        updated_foo = (workspace / "foo.py").read_text(encoding="utf-8")
        updated_main = (workspace / "main.py").read_text(encoding="utf-8")
        assert "def get_computed_value():" in updated_foo
        assert "from foo import get_computed_value" in updated_main
        assert "res = get_computed_value()" in updated_main

        # Cleanup
        await registry.lsp.stop()
