"""Escalation gate: ask a human for a hint when the retry budget is exhausted."""
from agent.evaluation.evaluator import EvalResult
from agent.fsm import AgentState
from agent.model.client import ChatResponse
from agent.orchestrator import Orchestrator

from test_end_to_end import _install_fake, _tool_call


class _FailingModel:
    """Never actually fixes anything; every finish leaves the tests failing."""

    host = "fake://failing"

    def __init__(self):
        self.closed = False

    async def is_available(self):
        return True

    async def close(self):
        self.closed = True

    async def chat(self, messages, tools=None):
        if tools is None:
            return ChatResponse(content="plan: try to fix it")
        return ChatResponse(content=_tool_call("finish", summary="attempted"))


def _seed_failing_tests(workspace):
    (workspace / "mod.py").write_text("def f():\n    return 1\n")
    (workspace / "test_mod.py").write_text("from mod import f\n\n\ndef test_f():\n    assert f() == 2\n")


async def test_escalation_asked_when_budget_exhausted(workspace):
    _seed_failing_tests(workspace)
    calls = {"n": 0}

    async def hint_cb(context):
        calls["n"] += 1
        return None  # decline -> give up

    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local", max_retries=1,
        escalation_callback=hint_cb,
    )
    _install_fake(orch, _FailingModel())

    await orch.run_task("make the test pass", stream=False)

    assert calls["n"] == 1  # escalation was requested exactly once
    assert orch.fsm.state == AgentState.ERROR


async def test_hint_grants_another_round_and_can_succeed(workspace):
    _seed_failing_tests(workspace)
    fixed = "def f():\n    return 2\n"

    class HintAwareModel:
        host = "fake://hint"

        def __init__(self):
            self.closed = False
            self.hinted = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            if tools is None:
                return ChatResponse(content="plan")
            # After a human hint appears in the conversation, actually fix it.
            if any("human operator" in str(m.get("content", "")).lower() for m in messages):
                self.hinted = True
                return ChatResponse(content=_tool_call("write_file", path="mod.py", content=fixed))
            return ChatResponse(content=_tool_call("finish", summary="noop"))

    async def hint_cb(context):
        return "f() should return 2"

    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local", max_retries=1,
        escalation_callback=hint_cb,
    )
    _install_fake(orch, HintAwareModel())

    await orch.run_task("make the test pass", stream=False)

    assert orch.frame.metadata.get("escalated") is True
    assert orch.fsm.state == AgentState.DONE
    assert (workspace / "mod.py").read_text() == fixed


def test_eval_result_details_available():
    # sanity: EvalResult carries details used in the escalation context
    r = EvalResult(passed=False, summary="Tests failed", details="traceback...", ran_tests=True)
    assert "traceback" in r.details
