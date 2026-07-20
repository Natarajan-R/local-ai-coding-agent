import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from agent.orchestrator import Orchestrator
from agent.fsm import AgentState
from agent import prompts
from agent.model.client import ChatResponse


def test_planner_messages():
    msgs = prompts.planner_messages("task desc", "skeleton", "memory", ["rule1"])
    assert any("PLANNER_SYSTEM_PROMPT" in str(m.get("content")) or "software architect" in str(m.get("content")) for m in msgs)
    assert any("task desc" in str(m.get("content")) for m in msgs)
    assert any("memory" in str(m.get("content")) for m in msgs)


def test_editor_messages():
    msgs = prompts.editor_messages(
        task="original task",
        path="file.py",
        change_description="make change",
        content="original content",
        reflexion_lesson="avoid bug",
        compiler_error="syntax error at line 3"
    )
    assert any("make change" in str(m.get("content")) for m in msgs)
    assert any("original content" in str(m.get("content")) for m in msgs)
    assert any("avoid bug" in str(m.get("content")) for m in msgs)
    assert any("syntax error at line 3" in str(m.get("content")) for m in msgs)


@pytest.mark.asyncio
async def test_planning_step_planner_editor(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.PLANNING
    
    mock_checklist = [
        {"path": "foo.py", "change_description": "implement foo", "is_new": True}
    ]
    
    mock_response = ChatResponse(
        content=f"```json\n{json.dumps(mock_checklist)}\n```",
        raw={}
    )
    orch._chat = AsyncMock(return_value=mock_response)
    orch._chat_stream = AsyncMock(return_value=mock_response)

    await orch._planning_step()
    
    assert orch.frame.metadata["checklist"] == mock_checklist
    assert orch.frame.plan == json.dumps(mock_checklist, indent=2)
    assert orch.fsm.state == AgentState.EXECUTING # transitioned via plan_ready
    assert orch.fsm.can("execution_done")


@pytest.mark.asyncio
async def test_planning_step_invalid_json_fallback(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.PLANNING
    
    mock_response = ChatResponse(
        content="This is not JSON text at all.",
        raw={}
    )
    orch._chat = AsyncMock(return_value=mock_response)
    orch._chat_stream = AsyncMock(return_value=mock_response)

    await orch._planning_step()
    
    checklist = orch.frame.metadata["checklist"]
    assert len(checklist) == 1
    assert checklist[0]["path"] == "solution.py"
    assert checklist[0]["is_new"] is True


@pytest.mark.asyncio
async def test_execution_step_planner_editor(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.EXECUTING
    
    checklist = [
        {"path": "foo.py", "change_description": "create hello function", "is_new": True}
    ]
    orch.frame.metadata["checklist"] = checklist

    edited_content = "def hello():\n    return 'world'\n"
    mock_response = ChatResponse(
        content=f"```python\n{edited_content}```",
        raw={}
    )
    orch._chat = AsyncMock(return_value=mock_response)
    orch._chat_stream = AsyncMock(return_value=mock_response)

    await orch._execution_step()
    
    assert orch.fsm.state == AgentState.EVALUATING # transitioned via execution_done
    assert (workspace / "foo.py").exists()
    assert (workspace / "foo.py").read_text().strip() == edited_content.strip()


@pytest.mark.asyncio
async def test_execution_step_syntax_error_retry(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.EXECUTING
    
    checklist = [
        {"path": "foo.py", "change_description": "fix syntax", "is_new": True}
    ]
    orch.frame.metadata["checklist"] = checklist

    # First response has a syntax error (missing colon after def)
    bad_content = "def hello()\n    return 'world'\n"
    # Second response has correct syntax
    good_content = "def hello():\n    return 'world'\n"

    mock_responses = [
        ChatResponse(content=f"```python\n{bad_content}```", raw={}),
        ChatResponse(content=f"```python\n{good_content}```", raw={})
    ]
    
    response_idx = 0
    async def mock_chat(messages, tools=None, on_token=None):
        nonlocal response_idx
        resp = mock_responses[min(response_idx, len(mock_responses)-1)]
        response_idx += 1
        return resp

    orch._chat = mock_chat
    orch._chat_stream = mock_chat

    await orch._execution_step()
    
    assert (workspace / "foo.py").exists()
    assert (workspace / "foo.py").read_text().strip() == good_content.strip()
    assert response_idx == 2  # Proves the compiler gate retried the model


def test_subtask_prompts():
    sys_prompt = prompts.subtask_system_prompt("foo.py", "change something")
    assert "expert coder" in sys_prompt
    assert "Available tools" in sys_prompt
    
    usr_prompt = prompts.subtask_user_prompt(
        task="orig task",
        path="foo.py",
        change_description="change something",
        content="foo content",
        repo_map="my dummy repo map",
        reflexion_lesson="failed lesson"
    )
    assert "orig task" in usr_prompt
    assert "change something" in usr_prompt
    assert "my dummy repo map" in usr_prompt
    assert "failed lesson" in usr_prompt


def test_planner_refiner_messages():
    msgs = prompts.planner_refiner_messages("task desc", [{"path": "foo.py"}], "failed tests", "reflexion lesson")
    assert len(msgs) == 2
    assert "PLANNER_REFINER_SYSTEM_PROMPT" in str(msgs[0].get("content")) or "software architect" in str(msgs[0].get("content"))
    assert "task desc" in str(msgs[1].get("content"))
    assert "foo.py" in str(msgs[1].get("content"))
    assert "failed tests" in str(msgs[1].get("content"))
    assert "reflexion lesson" in str(msgs[1].get("content"))


@pytest.mark.asyncio
async def test_reflexion_step_checklist_refinement(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.REFLEXING
    orch.frame.metadata["checklist"] = [{"path": "foo.py", "change_description": "fix syntax"}]
    
    mock_eval = MagicMock()
    mock_eval.details = "some pytest failure log"
    mock_eval.__str__ = lambda s: "some pytest failure log"
    orch.frame.metadata["last_eval"] = mock_eval
    
    refined_checklist = [{"path": "foo.py", "change_description": "fix syntax carefully"}]
    mock_response = ChatResponse(
        content=f"```json\n{json.dumps(refined_checklist)}\n```",
        raw={}
    )
    orch._chat = AsyncMock(return_value=mock_response)
    orch._chat_stream = AsyncMock(return_value=mock_response)
    
    # Run the reflexion step, should refine the checklist and transition to EXECUTING
    await orch._reflexion_step()
    
    assert orch.frame.metadata["checklist"] == refined_checklist
    assert orch.fsm.state == AgentState.EXECUTING


def test_find_impacted_tests_basic(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    
    mock_index = MagicMock()
    mock_index.importers.side_effect = lambda name: [
        ("test_solution.py", 1, "solution")
    ] if name == "solution" else []
    
    orch.tools._symbol_index = MagicMock(return_value=mock_index)
    
    impacted = orch.find_impacted_tests(["solution.py"])
    assert impacted == ["test_solution.py"]


@pytest.mark.asyncio
async def test_reflexion_step_passes_impacted_tests(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.REFLEXING
    orch.frame.metadata["checklist"] = [{"path": "solution.py", "change_description": "fix syntax"}]
    
    mock_eval = MagicMock()
    mock_eval.details = "some pytest failure log"
    mock_eval.__str__ = lambda s: "some pytest failure log"
    orch.frame.metadata["last_eval"] = mock_eval
    
    mock_index = MagicMock()
    mock_index.importers.return_value = [("test_solution.py", 1, "solution")]
    orch.tools._symbol_index = MagicMock(return_value=mock_index)
    
    refined_checklist = [{"path": "solution.py", "change_description": "fix syntax carefully"}]
    mock_response = ChatResponse(
        content=f"```json\n{json.dumps(refined_checklist)}\n```",
        raw={}
    )
    orch._chat = AsyncMock(return_value=mock_response)
    orch._chat_stream = AsyncMock(return_value=mock_response)
    
    original_refiner_msgs = prompts.planner_refiner_messages
    refiner_args = {}
    
    def mock_refiner_messages(*args, **kwargs):
        refiner_args.update(kwargs)
        if len(args) > 4:
            refiner_args["impacted_tests"] = args[4]
        return original_refiner_msgs(*args, **kwargs)
        
    prompts.planner_refiner_messages = mock_refiner_messages
    
    try:
        await orch._reflexion_step()
    finally:
        prompts.planner_refiner_messages = original_refiner_msgs
        
    assert "test_solution.py" in refiner_args.get("impacted_tests", [])


def test_dynamic_prompt_masking():
    prompt = prompts.system_prompt(exclude_names={"rename_symbol", "add_parameter"})
    assert "- rename_symbol" not in prompt
    assert "- add_parameter" not in prompt
    assert "- read_file" in prompt
    
    subtask_prompt = prompts.subtask_system_prompt("foo.py", "desc", exclude_names={"search_replace"})
    assert "- search_replace" not in subtask_prompt
    assert "- write_file" in subtask_prompt


@pytest.mark.asyncio
async def test_orchestrator_passes_exclude_names(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local", planner_editor=True)
    
    orch._is_single_file_workspace = MagicMock(return_value=True)
    orch.fsm.state = AgentState.PLANNING
    
    original_system_prompt = prompts.system_prompt
    spied_exclude_names = None
    
    def spy_system_prompt(exclude_names=None):
        nonlocal spied_exclude_names
        spied_exclude_names = exclude_names
        return original_system_prompt(exclude_names)
        
    prompts.system_prompt = spy_system_prompt
    
    try:
        mock_response = ChatResponse(content='[{"path": "foo.py", "change_description": "fix", "is_new": true}]', raw={})
        orch._chat = AsyncMock(return_value=mock_response)
        orch._chat_stream = AsyncMock(return_value=mock_response)
        
        await orch._planning_step()
    finally:
        prompts.system_prompt = original_system_prompt
        
    assert spied_exclude_names == {"rename_symbol", "add_parameter", "add_docstring"}


def test_apply_ast_splice_function():
    from agent.tools.patcher import apply_search_replace
    
    content = """def my_func(x):
    # Some comment
    return x + 1
"""
    search = "def my_func(x):\n    # completely different comment\n    return x + 1"
    replace = "def my_func(x):\n    return x + 42"
    
    patched = apply_search_replace(content, search, replace)
    assert "return x + 42" in patched
    assert "# Some comment" not in patched


def test_apply_ast_splice_method():
    from agent.tools.patcher import apply_search_replace
    
    content = """class MyClass:
    def method(self):
        # old method
        pass
"""
    search = "def method(self):\n        # mismatched comment\n        pass"
    replace = "def method(self):\n    return 'new'"
    
    patched = apply_search_replace(content, search, replace)
    expected = """class MyClass:
    def method(self):
        return 'new'
"""
    assert patched.strip() == expected.strip()


def test_apply_ast_splice_syntax_error():
    from agent.tools.patcher import apply_ast_splice
    
    content = "def hello():\n    return 'hi'"
    replace = "def hello(\n    return 'hi'"
    
    res = apply_ast_splice(content, replace)
    assert res is None


def test_swe_bench_example_load():
    from pathlib import Path
    import json
    
    project_root = Path(__file__).resolve().parents[2]
    example_path = project_root / "benchmarks" / "swe_bench_example.json"
    
    assert example_path.exists()
    with open(example_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    assert "instance_id" in data
    assert "repo" in data
    assert "base_commit" in data
    assert "problem_statement" in data


@pytest.mark.asyncio
async def test_reflexion_forces_is_new_false_for_existing_file(workspace):
    """enhancements-03 #2: on a retry, the checklist refiner can hallucinate
    is_new:true for a file that already exists — which strips the model of its
    line-editing tools mid-run. The reflexion step must hard-override is_new to
    False when the file is present on disk. (Already implemented; this locks it in.)
    """
    (workspace / "foo.py").write_text("def foo():\n    pass\n")  # the file EXISTS

    orch = Orchestrator(workspace=workspace, interactive=False,
                        sandbox_backend="local", planner_editor=True)
    orch.fsm.state = AgentState.REFLEXING
    orch.frame.retry_count = 0
    orch.frame.max_retries = 2
    orch.frame.metadata["last_eval"] = "Tests failed: AssertionError"
    orch.frame.metadata["checklist"] = [
        {"path": "foo.py", "change_description": "fix", "is_new": False}
    ]
    orch.reflexion.reflect = AsyncMock(return_value="the bug is an off-by-one")
    orch.find_impacted_tests = MagicMock(return_value=[])
    # the refiner HALLUCINATES is_new:true for the existing foo.py
    orch._model_turn = AsyncMock(return_value=ChatResponse(
        content='[{"path": "foo.py", "change_description": "fix", "is_new": true}]', raw={}))

    await orch._reflexion_step()

    checklist = orch.frame.metadata["checklist"]
    assert checklist[0]["path"] == "foo.py"
    assert checklist[0]["is_new"] is False, "is_new must be forced False for an existing file"


def test_subtask_user_prompt_includes_test_spec():
    # The editor must see the test as the exact spec (exact strings/values the
    # test asserts on), which is the dominant remaining failure mode when absent.
    out = prompts.subtask_user_prompt(
        task="implement", path="dot_dsl.py", change_description="build Graph",
        content="# stub",
        test_content="def test_attr():\n    with pytest.raises(ValueError, match='Attribute is malformed'):\n        Graph([[ATTR, 1]])",
    )
    assert "exact specification" in out
    assert "Attribute is malformed" in out
    # and it is omitted cleanly when no test is available
    assert "exact specification" not in prompts.subtask_user_prompt(
        task="t", path="a.py", change_description="c", content="s")


def test_relevant_test_content_finds_matching_test_and_skips_tests(tmp_path):
    orch = Orchestrator(workspace=tmp_path, interactive=False,
                        sandbox_backend="local", planner_editor=True)
    (tmp_path / "dot_dsl.py").write_text("# stub\n", encoding="utf-8")
    (tmp_path / "dot_dsl_test.py").write_text(
        "def test_x():\n    assert msg == 'Node is malformed'\n", encoding="utf-8")

    got = orch._relevant_test_content("dot_dsl.py")
    assert "Node is malformed" in got                 # editor now sees the spec
    # asking for a test file itself returns nothing (we never feed a test as target)
    assert orch._relevant_test_content("dot_dsl_test.py") == ""
