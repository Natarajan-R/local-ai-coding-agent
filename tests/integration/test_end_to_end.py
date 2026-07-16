"""End-to-end orchestrator tests.

The first test drives the *entire* FSM loop with a scripted fake model, so it is
fully deterministic and needs neither Ollama nor Docker. The second test runs
against a real local Ollama server and is skipped when one is not reachable.
"""
import json

import pytest

from agent.fsm import AgentState
from agent.model.client import ChatResponse
from agent.orchestrator import Orchestrator


class FakeModel:
    """A scripted stand-in for OllamaClient."""

    def __init__(self, plan, exec_responses):
        self._plan = plan
        self._exec = list(exec_responses)
        self._exec_idx = 0
        self.closed = False

    async def is_available(self):
        return True

    async def close(self):
        self.closed = True

    async def chat(self, messages, tools=None):
        if tools is None:  # planning phase
            return ChatResponse(content=self._plan)
        resp = self._exec[min(self._exec_idx, len(self._exec) - 1)]
        self._exec_idx += 1
        return ChatResponse(content=resp)

    @property
    def host(self):
        return "fake://model"


def _tool_call(name, **arguments):
    obj = {"name": name, "arguments": arguments}
    return f"```json\n{json.dumps(obj)}\n```"


def _install_fake(orchestrator, fake):
    orchestrator.model = fake
    orchestrator.reflexion.model = fake
    orchestrator._chat = fake.chat  # bypass the circuit breaker for determinism


async def test_full_loop_creates_file(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    fake = FakeModel(
        plan="1. Create hello.py",
        exec_responses=[
            _tool_call("write_file", path="hello.py", content='print("Hello, World!")'),
            _tool_call("finish", summary="created hello.py"),
        ],
    )
    _install_fake(orch, fake)

    frame = await orch.run_task("Create hello.py that prints Hello, World!", stream=False)

    assert orch.fsm.state == AgentState.DONE
    assert (workspace / "hello.py").exists()
    assert 'print("Hello, World!")' in (workspace / "hello.py").read_text()
    assert fake.closed
    assert frame.metadata.get("finish_summary")


async def test_loop_reflects_then_succeeds(workspace):
    # Seed a buggy module + test; first attempt is a no-op finish (tests fail),
    # then after reflexion the model writes the fix and the tests pass.
    (workspace / "stats.py").write_text("def average(v):\n    return sum(v) / len(v)\n")
    (workspace / "test_stats.py").write_text(
        "from stats import average\n\n\ndef test_empty():\n    assert average([]) == 0.0\n"
    )

    fixed = (
        "def average(v):\n"
        "    if not v:\n"
        "        return 0.0\n"
        "    return sum(v) / len(v)\n"
    )
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=1)
    fake = FakeModel(
        plan="1. Fix average for empty list",
        exec_responses=[
            _tool_call("finish", summary="nothing changed"),          # attempt 1 -> tests fail
            _tool_call("write_file", path="stats.py", content=fixed),  # attempt 2 -> fix
            _tool_call("finish", summary="fixed empty list handling"),
        ],
    )
    _install_fake(orch, fake)

    await orch.run_task("Fix average() to handle empty lists", stream=False)

    assert orch.fsm.state == AgentState.DONE
    assert "return 0.0" in (workspace / "stats.py").read_text()


async def test_no_progress_loop_breaks(workspace):
    # The model keeps issuing the same write and never calls finish; the
    # orchestrator must detect the stall and move on rather than loop forever.
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0)
    same_call = _tool_call("write_file", path="loop.py", content="x = 1\n")
    fake = FakeModel(plan="1. loop", exec_responses=[same_call])  # always returns the same call
    _install_fake(orch, fake)

    await orch.run_task("Write loop.py", stream=False)

    # It should terminate (not hang) and have written the file.
    assert orch.fsm.is_terminal()
    assert (workspace / "loop.py").exists()
    # Stall detection breaks at 5 identical calls, well under the 25-step cap.
    assert fake._exec_idx <= 6


async def test_max_steps_bounds_execution(workspace):
    # Model issues a *distinct* action every step (so no-progress detection never
    # fires); only max_steps should bound the execution phase.
    class Counter:
        host = "fake://counter"

        def __init__(self):
            self.n = 0
            self.closed = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            if tools is None:
                return ChatResponse(content="plan")
            self.n += 1
            return ChatResponse(content=_tool_call("write_file", path=f"f{self.n}.py", content="x = 1\n"))

    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local",
        max_retries=0, max_steps=3,
    )
    fake = Counter()
    _install_fake(orch, fake)

    await orch.run_task("distinct actions forever", stream=False)

    assert orch.fsm.is_terminal()
    assert fake.n == 3  # execution stopped exactly at max_steps
    assert orch.stats.model_calls >= 4  # 1 planning + 3 execution turns


async def test_non_consecutive_repeat_loop_breaks(workspace):
    # Model wanders by alternating between two distinct, already-performed
    # read-only actions (read -> list -> read -> list ...). Consecutive-identical
    # detection would miss this; the "any repeated action" guard must catch it.
    (workspace / "x.py").write_text("x = 1\n")

    class Cycler:
        host = "fake://cycler"

        def __init__(self):
            self.n = 0
            self.closed = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            if tools is None:
                return ChatResponse(content="plan")
            self.n += 1
            if self.n % 2 == 1:
                return ChatResponse(content=_tool_call("read_file", path="x.py"))
            return ChatResponse(content=_tool_call("list_files"))

    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local",
        max_retries=0, max_steps=20,
    )
    fake = Cycler()
    _install_fake(orch, fake)

    await orch.run_task("wander forever", stream=False)

    assert orch.fsm.is_terminal()
    assert fake.n < 20  # bailed via no-progress detection, not the step cap


async def test_context_is_trimmed_before_sending(workspace):
    # A model that pads its output so history grows past a small context window.
    # The orchestrator must trim each call to fit the budget before sending.
    from agent import prompts
    from agent.context import ContextManager

    seen_max = {"tokens": 0}
    cm = ContextManager(max_tokens=2500)

    class CapturingModel:
        host = "fake://capture"

        def __init__(self):
            self.n = 0
            self.closed = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            seen_max["tokens"] = max(seen_max["tokens"], cm.total_tokens(messages))
            if tools is None:
                return ChatResponse(content="plan: " + "detail " * 100)
            self.n += 1
            if self.n < 4:
                pad = "# padding line\n" * 300
                return ChatResponse(content=_tool_call("write_file", path=f"f{self.n}.py", content=pad))
            return ChatResponse(content=_tool_call("finish", summary="done"))

    # num_ctx must leave room for the system prompt AND working space. "Fits the
    # budget" and "the rules are never truncated" are both promises, but they
    # conflict once the system prompt alone approaches the budget — and there the
    # rules win by design (see the errata on _hard_truncate: better to overshoot
    # the window than lobotomize the agent). This test is about trimming, so give
    # it a context where the premise actually holds; the sparing behaviour is
    # asserted below and the too-small case has its own coverage in test_context.
    orch = Orchestrator(
        workspace=workspace, interactive=False, sandbox_backend="local",
        num_ctx=4096, max_steps=8, max_retries=0,
    )
    fake = CapturingModel()
    _install_fake(orch, fake)

    await orch.run_task("build several files", stream=False)

    # Every prompt the model received stayed within the token budget.
    assert seen_max["tokens"] <= orch.context.budget
    assert orch.fsm.is_terminal()
    # ...and trimming never came for the agent's own rules.
    assert cm.total_tokens([{"role": "system", "content": prompts.SYSTEM_PROMPT}]) < orch.context.budget


def _ollama_available():
    import httpx

    try:
        return httpx.get("http://localhost:11434/api/tags", timeout=2.0).status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not _ollama_available(), reason="requires a running Ollama server")
async def test_real_model_smoke(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=1)
    await orch.run_task("Create a file hello.py that prints Hello, World!", stream=False)
    # We don't assert on model quality, only that the loop terminates cleanly.
    assert orch.fsm.is_terminal()
