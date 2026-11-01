"""P3 regression tests: repeated full-file overwrite (thrash) guard.

Bug (observed in a real Gemma run): the agent rewrote storage.py over and
over; nothing blocked repeated write_file calls to the same path, so the
mutation budget was burned on redundant full-file rewrites.

Fix under test (src/agent/tools/registry.py):
  - ToolRegistry._write_counts — task-scoped counter keyed by normalized
    workspace-relative path; incremented only for EXECUTED successful writes.
  - _check_write_overwrite_guard runs BEFORE dispatch inside execute(): once a
    path has WRITE_OVERWRITE_LIMIT (3) executed writes, the next call is
    rejected with a structured error and the writer never runs.
  - begin_task() clears the counters; Orchestrator.run_task() calls it exactly
    once per task (not per retry/subtask), so retries/reflexion keep the block.
"""

import asyncio
import json

from agent.tools.registry import ToolRegistry


def _run(reg, path, content="X = 1\n"):
    return asyncio.run(reg.execute("write_file", {"path": path, "content": content}))


# ---------------------------------------------------------------------------
# Threshold: 3 executed writes allowed, the 4th blocked before dispatch
# ---------------------------------------------------------------------------

def test_first_three_writes_allowed_fourth_blocked(local_sandbox, policy, workspace):
    reg = ToolRegistry(local_sandbox, policy, workspace)
    target = workspace / "storage.py"

    for i in range(1, 4):
        res = _run(reg, "storage.py", f"V = {i}\n")
        assert res.ok is True, f"write #{i} must succeed: {res.content}"
    assert target.read_text() == "V = 3\n"

    res = _run(reg, "storage.py", "V = 4\n")
    assert res.ok is False, "the 4th overwrite of the same path must be blocked"
    payload = json.loads(res.content)
    assert payload["error"] == "repeated_overwrite_blocked"
    assert payload["tool"] == "write_file"
    assert payload["path"] == "storage.py"
    assert payload["prior_writes"] == 3
    assert payload["limit"] == 3
    # Must NOT suggest another full-file overwrite as the remedy.
    hint = payload["hint"].lower()
    assert "do not retry write_file" in hint
    assert "search_replace" in hint or "edit_lines" in hint

    # Blocked write must not reach the writer: file keeps the 3rd version.
    assert target.read_text() == "V = 3\n"


def test_blocked_call_does_not_invoke_writer(local_sandbox, policy, workspace, monkeypatch):
    """Prove pre-dispatch placement: patch the actual commit function and
    assert it is not called for the blocked 4th write."""
    reg = ToolRegistry(local_sandbox, policy, workspace)
    calls = []
    real_commit = ToolRegistry._atomic_commit_and_refresh

    async def counting_commit(self, target, content):
        calls.append(str(target))
        return await real_commit(self, target, content)

    monkeypatch.setattr(ToolRegistry, "_atomic_commit_and_refresh", counting_commit)

    for _ in range(3):
        assert _run(reg, "a.py").ok is True
    assert len(calls) == 3

    res = _run(reg, "a.py")
    assert res.ok is False
    assert len(calls) == 3, "writer must NOT run for the blocked overwrite"


# ---------------------------------------------------------------------------
# Path normalization: './x', 'sub/../x' collapse to the same key
# ---------------------------------------------------------------------------

def test_equivalent_paths_share_one_counter(local_sandbox, policy, workspace):
    reg = ToolRegistry(local_sandbox, policy, workspace)
    assert _run(reg, "pkg/mod.py").ok is True
    assert _run(reg, "./pkg/mod.py").ok is True          # './' variant
    assert _run(reg, "pkg/sub/../mod.py").ok is True     # '..' variant
    res = _run(reg, "pkg/./mod.py")                      # 4th equivalent path
    assert res.ok is False, "normalization must prevent bypassing the limit"
    assert json.loads(res.content)["path"] == "pkg/mod.py"


# ---------------------------------------------------------------------------
# Different paths are independent
# ---------------------------------------------------------------------------

def test_other_paths_remain_writable(local_sandbox, policy, workspace):
    reg = ToolRegistry(local_sandbox, policy, workspace)
    for _ in range(4):
        _run(reg, "hot.py")
    assert _run(reg, "cold.py").ok is True, "per-path counters must be independent"


# ---------------------------------------------------------------------------
# Lifecycle: survives retries/reflexion, resets only for a new task
# ---------------------------------------------------------------------------

def test_retry_subtask_rerun_cannot_bypass_limit(local_sandbox, policy, workspace):
    """Real subtask-rerun scenario: within one task the coder may re-run a
    failed subtask (retry/reflexion), and nothing on that path calls
    begin_task(); the counters must keep the block."""
    reg = ToolRegistry(local_sandbox, policy, workspace)  # one registry per task
    for _ in range(3):
        assert _run(reg, "storage.py").ok is True

    # --- attempt 2 of the same subtask (reflexion/retry) ---
    assert _run(reg, "storage.py").ok is False


def test_orchestrator_does_not_reset_counters_on_retry():
    """begin_task() is called ONLY at run_task() entry.  Retry/reflexion are
    FSM-loop iterations inside run_task; no reset-capable call exists there."""
    import inspect

    from agent.orchestrator import Orchestrator

    src = inspect.getsource(Orchestrator.run_task)
    assert src.count("begin_task") == 1
    assert src.index("begin_task") < src.index("while not self.fsm.is_terminal()")
    # No other orchestrator method resets the P3 counters mid-task.
    whole = inspect.getsource(Orchestrator)
    assert whole.count("begin_task") == 1


def test_new_task_resets_counters(local_sandbox, policy, workspace):
    reg = ToolRegistry(local_sandbox, policy, workspace)
    for _ in range(3):
        _run(reg, "storage.py")
    assert _run(reg, "storage.py").ok is False

    reg.begin_task()  # what Orchestrator.run_task() does at the start of a task
    assert _run(reg, "storage.py").ok is True, "new task starts with clean state"


def test_orchestrator_calls_begin_task_once_per_task():
    """Verify the wiring in Orchestrator.run_task: begin_task() is invoked at
    task start (and therefore NOT on retry/reflexion, which never re-enter
    run_task)."""
    import inspect

    from agent.orchestrator import Orchestrator

    src = inspect.getsource(Orchestrator.run_task)
    assert "self.tools.begin_task()" in src
    # It must appear before the FSM loop that drives retries.
    assert src.index("begin_task") < src.index("while not self.fsm.is_terminal()")


# ---------------------------------------------------------------------------
# Only executed writes consume the budget
# ---------------------------------------------------------------------------

def test_failed_writes_do_not_consume_budget(local_sandbox, policy, workspace):
    reg = ToolRegistry(local_sandbox, policy, workspace)
    # Empty-content overwrite of an existing file is refused by the writer...
    assert _run(reg, "keep.py", "A = 1\n").ok is True
    refused = _run(reg, "keep.py", "")
    assert refused.ok is False and "Refused" in refused.content
    # ...so it must not count toward the limit: two more real writes + one
    # blocked-attempt already made -> we still get our full 3 executed writes.
    assert _run(reg, "keep.py", "B = 2\n").ok is True
    assert _run(reg, "keep.py", "C = 3\n").ok is True
    assert _run(reg, "keep.py", "D = 4\n").ok is False  # now blocked (3 executed)
    assert (workspace / "keep.py").read_text() == "C = 3\n"


# ---------------------------------------------------------------------------
# P2 and P4 behavior remain intact
# ---------------------------------------------------------------------------

def test_p2_missing_path_still_structured_error(local_sandbox, policy, workspace):
    """P2 required-args validation runs BEFORE the P3 guard: no path -> the
    missing_required_arguments error, not the thrash error."""
    reg = ToolRegistry(local_sandbox, policy, workspace)
    res = asyncio.run(reg.execute("write_file", {"content": "hello"}))
    assert res.ok is False
    payload = json.loads(res.content)
    assert payload["error"] == "missing_required_arguments"
    assert payload["missing"] == ["path"]


def test_normal_write_and_edit_tools_unaffected(local_sandbox, policy, workspace):
    """Ordinary single write works; edit_lines/search_replace counters
    (_edit_misses) untouched by the P3 guard."""
    reg = ToolRegistry(local_sandbox, policy, workspace)
    res = _run(reg, "fresh.py", "print('hi')\n")
    assert res.ok is True
    assert (workspace / "fresh.py").read_text() == "print('hi')\n"
    # A read tool must not be affected at all.
    r = asyncio.run(reg.execute("read_file", {"path": "fresh.py"}))
    assert r.ok is True and "print('hi')" in r.content
    # edit-miss bookkeeping is separate from write counts
    assert reg._edit_misses == {}
