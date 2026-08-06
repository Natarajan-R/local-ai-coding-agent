"""Tests the agent writes during a run must actually be run by the evaluator.

Detection used to consult a snapshot of test files taken before the run started
(`initial_test_files`). On a greenfield task that snapshot is empty, so tests the
agent wrote were invisible, `_detect_command` returned None, and evaluation fell
through to a compile check — which passes. The run was reported green having
verified nothing.

Observed for real on 2026-07-22: "create a simple calculator" in an empty directory
produced a correct `calculator.py` and a `test_calculator.py` covering all four
functions, and evaluation still reported "No tests found; sources compile cleanly"
while `pytest` in that same directory gave `4 passed`.
"""
from agent.evaluation.evaluator import Evaluator


def test_agent_written_tests_are_detected_on_a_greenfield_run(local_sandbox, policy, workspace):
    """The core regression: an empty baseline must not blind the evaluator."""
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])  # workspace was empty at start

    # The agent then writes its implementation and its tests.
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )

    assert ev._has_python_tests(workspace) is True, "agent-written tests must be visible"
    assert ev._detect_command(workspace).startswith("PYTHONPATH=. python -m pytest -q"), (
        "must run pytest, not fall through to the compile-check that always passes"
    )


def test_greenfield_pass_is_marked_as_self_authored(local_sandbox, policy, workspace):
    """A green suite the agent wrote itself is weaker evidence, and must say so."""
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert result.passed is True
    assert result.ran_tests is True, "the agent's own tests must have actually run"
    assert "written during this run" in result.summary, (
        f"a self-authored pass must be flagged; got {result.summary!r}"
    )


def test_pre_existing_suite_is_not_flagged_as_self_authored(local_sandbox, policy, workspace):
    """The note must not cry wolf when a real, pre-existing suite passes."""
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    ev = Evaluator(local_sandbox, policy, initial_test_files=["test_calculator.py"])

    result = ev.evaluate(workspace)

    assert result.passed is True
    assert "written during this run" not in result.summary


def test_a_failing_agent_written_test_is_reported_as_failure(local_sandbox, policy, workspace):
    """The point of running them: a broken implementation must now be caught.

    Under the old behaviour this run went green via the compile-check fallback.
    """
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a - b\n")  # wrong
    (workspace / "test_calculator.py").write_text(
        "from calculator import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert result.passed is False, "a wrong implementation must not evaluate as passing"
    assert result.ran_tests is True


def test_workspace_with_no_tests_still_falls_back_to_compile_check(local_sandbox, policy, workspace):
    """The genuine no-tests case is unchanged: nothing to run, so compile instead."""
    (workspace / "calculator.py").write_text("def add(a, b):\n    return a + b\n")
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])

    assert ev._has_python_tests(workspace) is False
    assert ev._detect_command(workspace) is None
