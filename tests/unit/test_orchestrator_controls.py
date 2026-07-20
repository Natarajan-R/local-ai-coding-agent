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
