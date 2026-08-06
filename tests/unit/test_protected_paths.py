"""A file the task says not to touch must be unwritable, not merely discouraged.

Path confinement keeps edits inside the workspace, but "do not modify X" had no
enforcement behind it -- it was an instruction in a prompt, honoured at the model's
discretion. On 2026-07-23 the agent modified tracked files it had been told to leave
alone in 2 of 6 runs of the same task. These lock in the mechanism that makes such
an instruction real.
"""
import pytest

from agent.errors import ToolError
from agent.guardrails.policy import SecurityPolicy
from agent.tools.registry import ToolRegistry


def _registry(sandbox, workspace, protected):
    """A registry whose policy protects ``protected`` (workspace-relative globs)."""
    policy = SecurityPolicy(workspace, interactive=False, protected_paths=protected)
    return ToolRegistry(sandbox, policy, workspace)


# -- the policy layer ---------------------------------------------------------

def test_nothing_is_protected_by_default(workspace):
    """The guard must be opt-in: an unconfigured policy protects nothing."""
    policy = SecurityPolicy(workspace, interactive=False)
    assert policy.is_protected("anything.py") is False
    assert policy.validate_write("anything.py") is True


@pytest.mark.parametrize("pattern,path,expected", [
    ("secrets.py",       "secrets.py",                 True),
    ("secrets.py",       "other.py",                   False),
    ("migrations/**",    "migrations/0001_init.py",    True),
    ("migrations/**",    "migrations",                 True),   # the dir itself
    ("migrations/**",    "app/models.py",              False),
    ("migrations",       "migrations/0002_add.py",     True),   # bare dir covers below
    ("*.lock",           "poetry.lock",                True),
    ("*.lock",           "deep/nested/yarn.lock",      True),   # any depth
    ("*.lock",           "poetry.toml",                False),
])
def test_pattern_matching(workspace, pattern, path, expected):
    policy = SecurityPolicy(workspace, interactive=False, protected_paths=[pattern])
    assert policy.is_protected(path) is expected


def test_refusal_is_audited(workspace):
    """A refused write must leave a trace -- silent enforcement is unauditable."""
    policy = SecurityPolicy(workspace, interactive=False, protected_paths=["locked.py"])
    records = []
    policy.audit.record = lambda action, **f: records.append((action, f))

    assert policy.validate_write("locked.py") is False

    assert any(a == "write_denied" for a, _ in records), f"no audit record: {records}"


# -- the tool layer -----------------------------------------------------------

async def test_write_file_is_refused(local_sandbox, policy, workspace):
    (workspace / "locked.py").write_text("original = 1\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("write_file", {"path": "locked.py", "content": "clobbered"})

    assert result.ok is False
    assert "protected" in result.content.lower()
    assert (workspace / "locked.py").read_text() == "original = 1\n", "file was modified"


async def test_search_replace_is_refused(local_sandbox, policy, workspace):
    (workspace / "locked.py").write_text("value = 1\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute(
        "search_replace", {"path": "locked.py", "search": "value = 1", "replace": "value = 2"}
    )

    assert result.ok is False
    assert (workspace / "locked.py").read_text() == "value = 1\n"


async def test_edit_lines_is_refused(local_sandbox, policy, workspace):
    (workspace / "locked.py").write_text("a = 1\nb = 2\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute(
        "edit_lines",
        {"path": "locked.py", "start_line": 1, "end_line": 1, "search": "a = 1", "replace": "a = 9"},
    )

    assert result.ok is False
    assert (workspace / "locked.py").read_text() == "a = 1\nb = 2\n"


async def test_reading_a_protected_file_is_still_allowed(local_sandbox, policy, workspace):
    """Only mutation is refused.

    The agent frequently needs to *understand* a file it must not change -- a
    migration, a lockfile, a generated schema. Blocking reads too would push it into
    guessing at content it could simply have looked at.
    """
    (workspace / "locked.py").write_text("SCHEMA_VERSION = 7\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("read_file", {"path": "locked.py"})

    assert result.ok is True
    assert "SCHEMA_VERSION = 7" in result.content


async def test_unprotected_files_are_unaffected(local_sandbox, policy, workspace):
    """The guard must not become a blanket write ban."""
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("write_file", {"path": "free.py", "content": "x = 1\n"})

    assert result.ok is True
    assert (workspace / "free.py").read_text() == "x = 1\n"


async def test_refusal_tells_the_agent_not_to_retry(local_sandbox, policy, workspace):
    """The message must read as a boundary, not a transient error.

    A bare failure invites the model to retry the same write until it burns its step
    budget -- the exact thrash seen with search_replace elsewhere.
    """
    (workspace / "locked.py").write_text("x = 1\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("write_file", {"path": "locked.py", "content": "y = 2\n"})

    assert result.ok is False
    assert "do not retry" in result.content.lower()


async def test_directory_glob_protects_everything_beneath(local_sandbox, policy, workspace):
    (workspace / "migrations").mkdir()
    (workspace / "migrations" / "0001_init.py").write_text("# generated\n")
    reg = _registry(local_sandbox, workspace, ["migrations/**"])

    result = await reg.execute(
        "write_file", {"path": "migrations/0001_init.py", "content": "# clobbered\n"}
    )

    assert result.ok is False
    assert (workspace / "migrations" / "0001_init.py").read_text() == "# generated\n"


async def test_rename_symbol_skips_protected_files_and_says_so(local_sandbox, policy, workspace):
    """A workspace-wide rename must not quietly include an off-limits file.

    This is the dangerous case: one call rewrites every file the symbol appears in,
    so a single up-front check would let the rest through. Skipping silently would be
    worse still -- the caller would believe the rename was complete while a protected
    file still references the old name.
    """
    (workspace / "app.py").write_text("old_name = 1\nprint(old_name)\n")
    (workspace / "locked.py").write_text("import app\nx = app.old_name\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("rename_symbol", {"old": "old_name", "new": "new_name"})

    assert result.ok is True
    assert "new_name" in (workspace / "app.py").read_text(), "unprotected file should be renamed"
    assert (workspace / "locked.py").read_text() == "import app\nx = app.old_name\n"
    assert "locked.py" in result.content, "the skipped file must be reported"


async def test_rename_reports_honestly_when_every_match_is_protected(
    local_sandbox, policy, workspace
):
    """Reporting 'not found' here would send the agent hunting for a typo."""
    (workspace / "locked.py").write_text("only_here = 1\n")
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    result = await reg.execute("rename_symbol", {"old": "only_here", "new": "renamed"})

    assert result.ok is False
    assert "protected" in result.content.lower()
    assert "not found" not in result.content.lower()
    assert (workspace / "locked.py").read_text() == "only_here = 1\n"


def test_tool_layer_raises_for_a_protected_write(local_sandbox, policy, workspace):
    """_safe_write_path is the choke point; _safe_path (reads) stays permissive."""
    reg = _registry(local_sandbox, workspace, ["locked.py"])

    with pytest.raises(ToolError, match="protected"):
        reg._safe_write_path("locked.py")

    assert reg._safe_path("locked.py")  # reads resolve fine
