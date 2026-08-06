"""Green must mean "this run verified something", not merely "pytest exited 0".

Two ways that failed, both observed on real runs:

1. Tests existed but could not be collected. pytest exits 5, which was read as
   "this project has no tests", so evaluation fell through to a compile check and
   PASSED. Demo 05's false green was originally attributed here; measuring real
   pytest shows it was not (import errors exit 2, async-without-plugin exits 1 --
   both already fail). Its actual cause was the frozen test-file snapshot, fixed
   separately. These lock in the residual exit-5 gap regardless.

2. The suite was already green before the agent touched anything. stop-when-green
   then fired on the first edit and ended the run: "create a simple calculator"
   stopped at step 1 of its own 6-step plan because an unrelated leftover
   test_greet.py was passing, leaving the calculator with no tests at all.
"""
from unittest.mock import MagicMock

import pytest

from agent.evaluation.evaluator import PYTEST_NO_TESTS, EvalResult, Evaluator
from agent.orchestrator import Orchestrator


# -- 1. uncollectable tests must fail, not pass -------------------------------

def _sandbox_returning(exit_code, output=""):
    """A sandbox whose every exec returns the given exit code."""
    sb = MagicMock()
    sb.exec = MagicMock(return_value=MagicMock(
        exit_code=exit_code, ok=(exit_code == 0), output=output, timed_out=False
    ))
    return sb


def test_tests_that_exist_but_cannot_be_collected_fail(policy, workspace):
    """Test files present, pytest collects none -> NOT verified."""
    (workspace / "app.py").write_text("x = 1\n")
    (workspace / "test_app.py").write_text("import missing_plugin\n")  # would not import

    # Realistic pytest collection-error output (markers taken from a real run).
    sandbox = _sandbox_returning(PYTEST_NO_TESTS, (
        "==================================== ERRORS ====================================\n"
        "_______________________ ERROR collecting test_app.py ________________________\n"
        "ImportError while importing test module '/ws/test_app.py'.\n"
        "!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!\n"
    ))
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert result.passed is False, "a suite that could not run must not evaluate as passing"
    assert result.ran_tests is False
    assert "none could be collected" in result.summary
    assert "NOT verified" in result.summary


def test_green_by_skipping_unimplemented_tests_is_not_a_pass(policy, workspace):
    """pytest exits 0 but only because required tests were skipped as 'not implemented'."""
    (workspace / "app.py").write_text("x = 1\n")
    (workspace / "test_app.py").write_text("def test_a(): assert True\n")

    sandbox = _sandbox_returning(0, (
        "SKIPPED [1] test_app.py:10: Extension system not yet implemented\n"
        "1 passed, 1 skipped in 0.10s\n"
    ))
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert result.passed is False, "a green reached by skipping required work is a false green"
    assert "skipped" in result.summary.lower()
    assert "not yet implemented" in result.summary.lower()


def test_green_with_legitimate_skip_still_passes(policy, workspace):
    """A skip for a platform/optional-dep reason must NOT block a genuine green."""
    (workspace / "app.py").write_text("x = 1\n")
    (workspace / "test_app.py").write_text("def test_a(): assert True\n")

    sandbox = _sandbox_returning(0, (
        "SKIPPED [1] test_app.py:10: requires Windows\n"
        "3 passed, 1 skipped in 0.10s\n"
    ))
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert result.passed is True
    assert result.tests_skipped == 1   # still surfaced, just not treated as failure


def test_a_workspace_with_no_tests_still_falls_back_to_the_compile_check(policy, workspace):
    """The genuine no-tests case is unchanged -- nothing to run, so compile instead."""
    (workspace / "app.py").write_text("x = 1\n")  # no test files at all

    sandbox = _sandbox_returning(0)
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    # Falls through to _syntax_check, which reports on compilation rather than tests.
    assert result.ran_tests is False
    assert "no tests found" in result.summary.lower()


def test_collected_nothing_without_an_error_is_not_a_failure(policy, workspace):
    """pytest also exits 5 when collection SUCCEEDS but finds no test functions.

    A file of module-level asserts is the real-world case: those statements ran on
    import and passed, so treating it as "nothing was verified" would be wrong. Only
    a collection *error* means the code went unchecked.
    """
    (workspace / "mod.py").write_text("def f():\n    return 1\n")
    (workspace / "test_mod.py").write_text("import mod\n\nassert mod.f() == 1\n")

    # exit 5, but the output carries no collection-error marker.
    sandbox = _sandbox_returning(PYTEST_NO_TESTS, "no tests ran in 0.01s")
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    result = ev.evaluate(workspace)

    assert "none could be collected" not in result.summary, (
        "collecting nothing is only a failure when collection ERRORED"
    )


def test_the_failure_names_the_likely_cause(policy, workspace):
    """A bare 'failed' would send the agent editing code that is probably fine."""
    (workspace / "test_app.py").write_text("import nope\n")
    sandbox = _sandbox_returning(
        PYTEST_NO_TESTS, "ERROR collecting test_app.py\nImportError while importing test module")
    ev = Evaluator(sandbox, policy, initial_test_files=[])

    summary = ev.evaluate(workspace).summary.lower()

    assert "import" in summary or "plugin" in summary or "conftest" in summary


# -- 2. an already-green suite must not end the run ---------------------------

def test_baseline_green_disables_stop_when_green(workspace, monkeypatch):
    """A suite green before the run proves nothing when it is green after."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.evaluator.evaluate = MagicMock(
        return_value=EvalResult(passed=True, summary="Tests passed", ran_tests=True)
    )

    orch._capture_green_baseline()

    assert orch._baseline_green is True, "an already-passing suite must be recorded"


def test_baseline_not_green_keeps_stop_when_green_active(workspace):
    """The intended use -- 'make the failing tests pass' -- must still short-circuit."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.evaluator.evaluate = MagicMock(
        return_value=EvalResult(passed=False, summary="Tests failed", ran_tests=True)
    )

    orch._capture_green_baseline()

    assert orch._baseline_green is False


def test_greenfield_workspace_keeps_stop_when_green_active(workspace):
    """An empty workspace has nothing green, so the shortcut stays available."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.evaluator.evaluate = MagicMock(
        return_value=EvalResult(passed=True, summary="No tests found", ran_tests=False)
    )

    orch._capture_green_baseline()

    # passed=True but ran_tests=False -- the compile-check fallback, not a real suite.
    assert orch._baseline_green is False


def test_baseline_failure_never_blocks_the_run(workspace):
    """If the baseline cannot be taken, degrade rather than refuse to start."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.evaluator.evaluate = MagicMock(side_effect=RuntimeError("sandbox exploded"))

    orch._capture_green_baseline()

    assert orch._baseline_green is False


@pytest.mark.asyncio
async def test_stop_when_green_is_skipped_when_baseline_was_green(workspace):
    """The guard itself must consult the baseline, not just record it."""
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch._baseline_green = True
    orch.evaluator.evaluate = MagicMock(
        return_value=EvalResult(passed=True, summary="Tests passed", ran_tests=True)
    )

    # The condition guarding the shortcut, as evaluated in _execution_step.
    should_short_circuit = orch.stop_when_green and not orch._baseline_green

    assert should_short_circuit is False, "an already-green suite must not end the run early"
