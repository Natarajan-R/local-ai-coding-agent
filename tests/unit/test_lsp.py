import asyncio
import shutil
import sys
from pathlib import Path

import pytest

from agent.perception.lsp import LSPClient

# The LSP tests need a real python-lsp-server (pylsp) binary. Skip gracefully
# when it isn't installed instead of failing.
_pylsp_available = (
    shutil.which("pylsp") is not None
    or (Path(sys.executable).parent / "pylsp").exists()
)
pytestmark = pytest.mark.skipif(not _pylsp_available, reason="pylsp not installed")


@pytest.mark.asyncio
async def test_lsp_client_lifecycle_and_queries(tmp_path):
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

    # Start server
    await client.start()

    try:
        # Open document
        await client.open_document(py_file, py_content)

        # Give the server a brief moment to parse the file
        await asyncio.sleep(1.5)

        # Query definition of 'bar' on line 4 (0-indexed line 3, character 4)
        defs = await client.get_definition(py_file, 3, 4)
        assert len(defs) > 0

        # The location uri should match foo.py and point to definition on line 1 (0-indexed line 0)
        loc = defs[0]
        assert "foo.py" in loc["uri"]
        assert loc["range"]["start"]["line"] == 0

        # Query references of 'bar' on line 1 (0-indexed line 0, character 4)
        refs = await client.get_references(py_file, 0, 4)
        assert len(refs) >= 2  # Definition itself + usage in line 4

        # Verify get_all_diagnostics compiles
        diags_text = client.get_all_diagnostics()
        assert isinstance(diags_text, str)

    finally:
        await client.stop()
