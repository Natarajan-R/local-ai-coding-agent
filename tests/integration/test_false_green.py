"""A stalled run must not be certified as a success.

Found 2026-07-16 by running Tier 3 against a 120B cloud model. One run in four
never called a single edit tool: it searched, read, ran pytest a few times, hit
the no-progress detector, fell through to evaluation — and the suite was green,
because on a refactor the suite is green *before* the first edit. The FSM
reported `done` on a workspace it had not touched.

The 7B did the same thing at 32k context. Both ends of the model scale, same
pathology: the bug is in the harness, not the model. The no-progress abort and a
genuine completion took the same `execution_done` edge, so nothing downstream
could tell them apart.
"""
from agent.fsm import AgentState
from agent.orchestrator import Orchestrator

from test_end_to_end import FakeModel, _install_fake, _tool_call


def _seed_green_workspace(workspace):
    """A workspace whose tests already pass — the refactor starting condition."""
    (workspace / "schemas.py").write_text("USER_ID = 'user_id'\n")
    (workspace / "test_schemas.py").write_text(
        "from schemas import USER_ID\n\n\ndef test_present():\n    assert USER_ID\n"
    )


async def test_stall_without_edits_is_not_success(workspace):
    _seed_green_workspace(workspace)
    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0
    )
    # The model spins on one read-only action until the no-progress detector bails.
    fake = FakeModel(
        plan="1. Rename user_id to uuid everywhere",
        exec_responses=[_tool_call("read_file", path="schemas.py")] * 8,
    )
    _install_fake(orch, fake)

    await orch.run_task("Rename the field user_id to uuid across the repo", stream=False)

    assert orch._mutations == 0
    assert orch._no_progress_abort is True
    # The suite is green. That is not evidence of anything: nothing was edited.
    assert orch.fsm.state != AgentState.DONE, (
        "a run that stalled without editing any file was certified as done"
    )


async def test_stall_after_real_edits_still_passes(workspace):
    """The gate must not punish an agent that did the work and then wandered.

    Edits land, the suite passes, and only then does the model start repeating
    itself. That green is earned, so `done` is correct.
    """
    _seed_green_workspace(workspace)
    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0
    )
    fake = FakeModel(
        plan="1. Rename user_id to uuid",
        exec_responses=[
            _tool_call("write_file", path="schemas.py", content="UUID = 'uuid'\n"),
            _tool_call("write_file", path="test_schemas.py",
                       content="from schemas import UUID\n\n\ndef test_present():\n    assert UUID\n"),
        ] + [_tool_call("read_file", path="schemas.py")] * 8,
    )
    _install_fake(orch, fake)

    await orch.run_task("Rename the field user_id to uuid across the repo", stream=False)

    assert orch._mutations == 2
    assert orch._no_progress_abort is True
    assert orch.fsm.state == AgentState.DONE
