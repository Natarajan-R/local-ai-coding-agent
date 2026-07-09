"""Persistent memory: a fact saved in one run is recalled in the next."""
from agent.memory import MemoryStore
from agent.model.client import ChatResponse
from agent.orchestrator import Orchestrator

from test_end_to_end import _install_fake, _tool_call


class _RememberingModel:
    """Run 1: saves a convention, then finishes. Captures planning context each run."""

    host = "fake://mem"

    def __init__(self, saw):
        self.saw = saw
        self.closed = False
        self.step = 0

    async def is_available(self):
        return True

    async def close(self):
        self.closed = True

    async def chat(self, messages, tools=None):
        if tools is None:  # planning: record whether memory was in context
            self.saw.append("\n".join(str(m.get("content", "")) for m in messages))
            return ChatResponse(content="plan")
        self.step += 1
        if self.step == 1:
            return ChatResponse(content=_tool_call(
                "remember", text="This project pins dependencies in constraints.txt", kind="convention"))
        return ChatResponse(content=_tool_call("finish", summary="done"))


async def test_memory_persists_across_runs(workspace):
    # -- Run 1: the agent remembers a convention --------------------------------
    saw1: list = []
    orch1 = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    _install_fake(orch1, _RememberingModel(saw1))
    await orch1.run_task("do something", stream=False)

    store = MemoryStore(workspace)
    assert store.count() == 1
    assert "constraints.txt" in store.load()[0].text

    # -- Run 2 (fresh Orchestrator): the fact is recalled into the context ------
    saw2: list = []

    class _Plain:
        host = "fake://plain"

        def __init__(self):
            self.closed = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            if tools is None:
                saw2.append("\n".join(str(m.get("content", "")) for m in messages))
                return ChatResponse(content="plan")
            return ChatResponse(content=_tool_call("finish", summary="done"))

    orch2 = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    _install_fake(orch2, _Plain())
    await orch2.run_task("another task", stream=False)

    # The remembered convention appears in run 2's planning context.
    assert any("constraints.txt" in ctx for ctx in saw2)


async def test_no_memory_flag_disables_recall(workspace):
    MemoryStore(workspace).add("secret convention xyz", kind="convention")
    saw: list = []

    class _M:
        host = "fake://m"

        def __init__(self):
            self.closed = False

        async def is_available(self):
            return True

        async def close(self):
            self.closed = True

        async def chat(self, messages, tools=None):
            if tools is None:
                saw.append("\n".join(str(m.get("content", "")) for m in messages))
                return ChatResponse(content="plan")
            return ChatResponse(content=_tool_call("finish", summary="done"))

    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", use_memory=False)
    _install_fake(orch, _M())
    await orch.run_task("task", stream=False)
    assert not any("secret convention xyz" in ctx for ctx in saw)
