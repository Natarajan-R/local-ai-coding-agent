"""P4 regression: a failed planner/editor subtask must not become a false success.

Root cause (verified in code): _execute_with_planner_editor() logged the bool
returned by _execute_subtask() and then called _transition_to_done() regardless.
The evaluator could still pass (e.g. an already-green unrelated suite), the FSM
moved EVALUATING --passed--> DONE, and cli/main.py printed "Success" purely on
final_state == "done".

Fix: failed subtasks are recorded in frame.metadata["subtask_failures"], and
EvaluatorValidator (Rule 3) flips a passing evaluation to failed when that list
is non-empty — so the FSM transitions to REFLEXING instead of DONE, and the CLI
cannot report success. Normal successful execution is untouched.
"""
from unittest.mock import MagicMock

import pytest

from agent.agents.coder import CoderAgent  # noqa: F401
from agent.agents.reviewer import EvaluatorValidator
from agent.evaluation.evaluator import EvalResult
from agent.fsm import AgentState
from agent.orchestrator import Orchestrator
from agent.state import AgentFrame


# ---------------------------------------------------------------------------
# 1. Failure propagation: _execute_with_planner_editor records failed subtasks
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_editor_records_failed_subtask(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False,
                        sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.EXECUTING
    orch.frame.metadata["checklist"] = [
        {"path": "foo.py", "change_description": "create hello", "is_new": True},
    ]

    async def fake_subtask(**kwargs):
        return False  # simulate exhausted step budget / broken syntax

    orch.coder_agent._execute_subtask = fake_subtask
    await orch.coder_agent.execute()

    failures = orch.frame.metadata.get("subtask_failures")
    assert failures, "failed subtask must be propagated into frame.metadata"
    assert failures[0]["path"] == "foo.py"
    assert failures[0]["index"] == 0
    # FSM/evaluator architecture preserved: execution_done still moves to EVALUATING
    assert orch.fsm.state == AgentState.EVALUATING


@pytest.mark.asyncio
async def test_planner_editor_all_success_leaves_no_failures(workspace):
    """Normal successful execution must stay exactly as before."""
    orch = Orchestrator(workspace=workspace, interactive=False,
                        sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.EXECUTING
    orch.frame.metadata["checklist"] = [
        {"path": "foo.py", "change_description": "create hello", "is_new": True},
        {"path": "bar.py", "change_description": "create world", "is_new": True},
    ]

    async def fake_subtask(**kwargs):
        return True

    orch.coder_agent._execute_subtask = fake_subtask
    await orch.coder_agent.execute()

    assert not orch.frame.metadata.get("subtask_failures")
    assert orch.fsm.state == AgentState.EVALUATING


# ---------------------------------------------------------------------------
# 2. Prevention of false completion: validator overrides a green evaluation
# ---------------------------------------------------------------------------

def _fake_orch(frame):
    orch = MagicMock()
    orch.frame = frame
    orch._missing_requested_files.return_value = []
    orch._no_progress_abort = False
    orch._mutations = 3
    return orch


def test_validator_flips_pass_when_subtask_failed():
    frame = AgentFrame(task_description="t")
    frame.metadata["subtask_failures"] = [
        {"index": 0, "path": "app.py", "change_description": "fix bug"},
    ]
    validator = EvaluatorValidator(_fake_orch(frame))

    result = validator.validate(EvalResult(passed=True, summary="All tests passed"))

    assert result.passed is False, "green eval must not mask a failed required subtask"
    assert "app.py" in result.summary
    assert "subtask" in result.summary.lower()


def test_validator_keeps_pass_without_failures():
    frame = AgentFrame(task_description="t")
    validator = EvaluatorValidator(_fake_orch(frame))

    result = validator.validate(EvalResult(passed=True, summary="All tests passed"))

    assert result.passed is True
    assert result.summary == "All tests passed"


def test_validator_does_not_touch_already_failed_result():
    frame = AgentFrame(task_description="t")
    frame.metadata["subtask_failures"] = [{"index": 0, "path": "app.py"}]
    validator = EvaluatorValidator(_fake_orch(frame))

    result = validator.validate(EvalResult(passed=False, summary="2 tests failed"))

    assert result.passed is False
    assert result.summary == "2 tests failed"  # original failure kept intact


# ---------------------------------------------------------------------------
# 3. End-to-end guard: failed subtask + green eval -> no DONE, no Success print
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_failed_subtask_green_eval_does_not_reach_done(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False,
                        sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.EXECUTING
    orch.frame.metadata["checklist"] = [
        {"path": "foo.py", "change_description": "create hello", "is_new": True},
    ]

    async def fake_subtask(**kwargs):
        return False

    orch.coder_agent._execute_subtask = fake_subtask
    await orch.coder_agent.execute()
    assert orch.fsm.state == AgentState.EVALUATING

    # Evaluator itself says green (e.g. unrelated leftover tests already pass).
    green = EvalResult(passed=True, summary="All tests passed", ran_tests=True)
    validated = orch.reviewer_agent._validator.validate(green)

    # This is exactly what execute_evaluation() branches on.
    if validated.passed:
        orch.fsm.transition("passed")
    else:
        orch.frame.last_error_summary = validated.summary
        orch.fsm.transition("failed")

    assert orch.fsm.state != AgentState.DONE, \
        "task must not reach DONE while a required subtask failed"
    # cli/main.py reports Success only for final_state == "done":
    assert (orch.fsm.state.value == "done") is False
