import asyncio
import json
import pytest
from agent.fsm import AgentState
from agent.orchestrator import Orchestrator


class ChatResponse:
    def __init__(self, content: str, tool_calls=None, raw=None):
        self.content = content or ""
        self.tool_calls = tool_calls or []
        self.raw = raw or {}


class FakeModel:
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
        if tools is None:
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
    orchestrator._chat = fake.chat


async def test_orchestrator_stop_control(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0)
    orch.lsp = None

    async def chat_mock(messages, tools=None):
        if tools is None:
            return ChatResponse(content="1. Write file")
        orch.stop()
        return ChatResponse(content=_tool_call("write_file", path="a.py", content="x = 1"))

    orch.model = FakeModel("1. Write file", [])
    orch.model.chat = chat_mock
    _install_fake(orch, orch.model)

    await orch.run_task("Write some code", stream=False)

    assert orch._stopped is True
    assert orch.fsm.state != AgentState.DONE


async def test_orchestrator_pause_resume_control(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", max_retries=0)
    orch.lsp = None

    async def chat_mock(messages, tools=None):
        if tools is None:
            return ChatResponse(content="1. Write file")
        
        orch.pause()
        assert orch._paused is True
        
        async def resume_after_delay():
            await asyncio.sleep(0.1)
            orch.resume()

        asyncio.create_task(resume_after_delay())
        
        return ChatResponse(content=_tool_call("finish", summary="done"))

    orch.model = FakeModel("1. Write file", [])
    orch.model.chat = chat_mock
    _install_fake(orch, orch.model)

    await orch.run_task("Write some code", stream=False)

    assert orch._paused is False
    assert orch.fsm.state == AgentState.DONE


def test_missing_requested_files_catches_silently_skipped_files(tmp_path):
    """A green suite is not proof the task was done.

    Found 2026-07-20: asked for 11 files across nested packages, the agent wrote
    8, called finish, and pytest passed -- PEP 420 namespace packages import
    fine without __init__.py, so the three missing ones stayed invisible until
    packaging would break far from the cause.
    """
    from agent.orchestrator import Orchestrator
    from agent.state import AgentFrame

    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "core").mkdir()
    (tmp_path / "pkg" / "core" / "note.py").write_text("x = 1\n")

    o = Orchestrator.__new__(Orchestrator)
    o.workspace = tmp_path
    # A real AgentFrame, not a MagicMock: a mock invents any attribute you ask
    # for, which is exactly how the first version of this shipped reading a
    # frame.task that does not exist.
    o.frame = AgentFrame(task_description=(
        "Build pkg/__init__.py; pkg/core/__init__.py; "
        "pkg/core/note.py; tests/test_note.py"))

    missing = o._missing_requested_files()
    assert "pkg/core/__init__.py" in missing
    assert "tests/test_note.py" in missing
    assert "pkg/__init__.py" not in missing     # exists
    assert "pkg/core/note.py" not in missing    # exists


def test_missing_requested_files_is_quiet_when_no_files_named(tmp_path):
    """Must not invent findings from prose, or every refactor task fails."""
    from agent.orchestrator import Orchestrator
    from agent.state import AgentFrame

    o = Orchestrator.__new__(Orchestrator)
    o.workspace = tmp_path
    o.frame = AgentFrame(task_description="")

    for prose in [
        "Refactor the code to be faster and add better error handling.",
        "Rename user_id to account_id everywhere.",
        "Read the docs at https://example.com/guide.py and improve things.",
    ]:
        o.frame.task_description = prose
        assert o._missing_requested_files() == [], prose
