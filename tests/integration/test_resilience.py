"""Integration tests for retry/circuit-breaker resilience and the audit trail."""
import json

from agent.errors import TransientError
from agent.fsm import AgentState
from agent.model.client import ChatResponse
from agent.orchestrator import Orchestrator
from agent.utils.retry import async_retry

from test_end_to_end import FakeModel, _install_fake, _tool_call


class FlakyModel:
    """Fails its first ``fail_times`` chat calls, then behaves normally."""

    host = "fake://flaky"

    def __init__(self, fail_times, plan, exec_responses):
        self.fail_times = fail_times
        self.calls = 0
        self.closed = False
        self._plan = plan
        self._exec = list(exec_responses)
        self._i = 0

    async def is_available(self):
        return True

    async def close(self):
        self.closed = True

    async def chat(self, messages, tools=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            from agent.errors import ModelError
            raise ModelError("transient boom")
        if tools is None:
            return ChatResponse(content=self._plan)
        resp = self._exec[min(self._i, len(self._exec) - 1)]
        self._i += 1
        return ChatResponse(content=resp)


def _install_resilient_fake(orch, fake, attempts=3):
    """Wire the fake through the real retry + circuit-breaker stack (fast delays)."""
    orch.model = fake
    retry = async_retry(max_attempts=attempts, base_delay=0.01, exceptions=(TransientError,))
    orch._chat = orch.model_circuit(retry(fake.chat))
    orch.reflexion._chat = orch._chat


async def test_retry_recovers_from_transient_model_errors(workspace):
    fake = FlakyModel(
        fail_times=2,  # first two model calls fail, third succeeds
        plan="1. write the file",
        exec_responses=[
            _tool_call("write_file", path="r.py", content="x = 1\n"),
            _tool_call("finish", summary="done"),
        ],
    )
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0)
    _install_resilient_fake(orch, fake, attempts=3)

    await orch.run_task("write r.py", stream=False)

    assert orch.fsm.state == AgentState.DONE
    assert (workspace / "r.py").exists()
    assert fake.calls >= 3  # proves the transient failures were retried


async def test_retry_exhaustion_ends_in_error(workspace):
    fake = FlakyModel(fail_times=99, plan="", exec_responses=[])
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0)
    _install_resilient_fake(orch, fake, attempts=2)

    await orch.run_task("this will fail", stream=False)

    assert orch.fsm.is_terminal()
    assert orch.fsm.state == AgentState.ERROR


async def test_audit_trail_records_full_lifecycle(workspace):
    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local",
        log_dir=workspace.parent / "audit_logs",
    )
    fake = FakeModel(
        plan="1. create hello.py",
        exec_responses=[
            _tool_call("write_file", path="hello.py", content='print("hi")'),
            _tool_call("finish", summary="created hello.py"),
        ],
    )
    _install_fake(orch, fake)

    await orch.run_task("Create hello.py", stream=False)

    entries = [json.loads(line) for line in orch.policy.audit.path.read_text().splitlines()]
    actions = {e["action"] for e in entries}
    assert {"task_start", "plan_created", "tool_call", "evaluation", "task_end"} <= actions

    # Lifecycle entries are all tagged with this run's correlation id.
    lifecycle = [e for e in entries if e["action"] in {"task_start", "plan_created", "task_end"}]
    assert lifecycle
    assert all(e.get("run_id") == orch.run_id for e in lifecycle)

    # task_end carries the final state and token accounting.
    end = next(e for e in entries if e["action"] == "task_end" and e["run_id"] == orch.run_id)
    assert end["final_state"] == "done"
    assert "total_tokens" in end
