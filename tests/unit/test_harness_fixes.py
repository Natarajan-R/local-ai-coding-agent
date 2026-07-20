import pytest
from pathlib import Path
from agent.orchestrator import Orchestrator
from agent.evaluation.evaluator import Evaluator
from unittest.mock import MagicMock

def test_find_target_file_solution_py(workspace):
    # If solution.py exists, it should be selected
    (workspace / "solution.py").write_text("def f(): pass")
    (workspace / "other.py").write_text("def g(): pass")
    
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    assert orch._find_target_file() == "solution.py"

def test_find_target_file_single_candidate(workspace):
    # Exactly one candidate file exists
    (workspace / "main.go").write_text("package main")
    # Test/spec files and standard ignores should be ignored
    (workspace / "main_test.go").write_text("package main")
    (workspace / "test_main.py").write_text("def test(): pass")
    
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    assert orch._find_target_file() == "main.go"

def test_find_target_file_multiple_candidates(workspace):
    # Multiple candidate source files exist
    (workspace / "foo.py").write_text("def foo(): pass")
    (workspace / "bar.py").write_text("def bar(): pass")
    
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    assert orch._find_target_file() is None

def test_extract_implicit_code_fenced(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    
    text = "Here is the code:\n```python\ndef f():\n    return 42\n```\nLet me know if it works."
    assert orch._extract_implicit_code(text, is_py=True) == "def f():\n    return 42"
    
    # Generic code block
    text2 = "```\nhello_world()\n```"
    assert orch._extract_implicit_code(text2, is_py=False) == "hello_world()"

def test_extract_implicit_code_bare_python(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    
    # Compiles cleanly
    text = "def sum_to_n(n):\n    return n * (n + 1) // 2"
    assert orch._extract_implicit_code(text, is_py=True) == text
    
    # Leading and trailing prose
    text2 = "Here is my answer.\n\ndef sum_to_n(n):\n    return n * (n + 1) // 2\n\nHope this helps!"
    expected = "def sum_to_n(n):\n    return n * (n + 1) // 2"
    assert orch._extract_implicit_code(text2, is_py=True) == expected

def test_extract_implicit_code_invalid_bare(workspace):
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    
    # Generic prose that doesn't look like code
    text = "Sorry, I cannot solve this task. Please provide more details."
    assert orch._extract_implicit_code(text, is_py=True) is None
    assert orch._extract_implicit_code(text, is_py=False) is None

def test_evaluator_initial_test_files(local_sandbox, policy, workspace):
    # Pre-existing test file
    (workspace / "test_calc.py").write_text("def test_calc(): pass")
    
    # Evaluator should track and run it
    ev = Evaluator(local_sandbox, policy, initial_test_files=["test_calc.py"])
    assert ev._has_python_tests(workspace) is True
    assert ev._detect_command(workspace) == "python -m pytest -q"
    
    # If no initial test files, should ignore model-created tests
    ev_empty = Evaluator(local_sandbox, policy, initial_test_files=[])
    assert ev_empty._has_python_tests(workspace) is False
    assert ev_empty._detect_command(workspace) is None

def test_evaluator_tamper_proofing(local_sandbox, policy, workspace):
    # Pre-existing test file
    test_file = workspace / "test_calc.py"
    test_file.write_text("def test_calc():\n    assert True\n")
    
    # Mock self.sandbox.exec to track calls
    local_sandbox.exec = MagicMock(return_value=MagicMock(exit_code=0, ok=True, output=""))
    
    ev = Evaluator(local_sandbox, policy, initial_test_files=["test_calc.py"])
    ev.evaluate(workspace)
    
    # Verify that git checkout was called on test_calc.py before running tests
    local_sandbox.exec.assert_any_call("git checkout -- test_calc.py")

@pytest.mark.asyncio
async def test_stop_when_green_guard(workspace):
    # Setup Orchestrator
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.lsp = None
    
    # Mock self.evaluator.evaluate to return passed and ran_tests
    from agent.evaluation.evaluator import EvalResult
    orch.evaluator.evaluate = MagicMock(return_value=EvalResult(passed=True, ran_tests=True, summary="Tests passed"))
    
    # Mock self.tools.execute to return a ToolResult that is not final
    from agent.tools.registry import ToolResult
    async def mock_execute(*args, **kwargs):
        return ToolResult(ok=True, content="Wrote file")
    orch.tools.execute = mock_execute
    
    # Setup a mock response from the model
    class MockChatResponse:
        def __init__(self):
            self.content = ""
            self.tool_calls = [{"function": {"name": "write_file", "arguments": {"path": "solution.py", "content": "x = 1"}}}]
            self.raw = {}
            
    async def mock_chat(*args, **kwargs):
        return MockChatResponse()
            
    orch._chat = mock_chat
    orch._chat_stream = mock_chat
    orch.frame.messages = [{"role": "system", "content": "prime"}]
    
    from agent.fsm import AgentState
    orch.fsm.state = AgentState.EXECUTING
    orch.max_steps = 5
    await orch._execution_step()
    
    # Verify that evaluate was called
    orch.evaluator.evaluate.assert_called_once()
    
    # Verify that execution finished summary is stop-when-green
    assert orch.frame.metadata.get("finish_summary") == "Stop-when-green: tests passed successfully."

@pytest.mark.asyncio
async def test_scoping_semantic_tools_in_single_file_workspace(workspace):
    # Setup single-file workspace candidate
    (workspace / "solution.py").write_text("def main(): pass")
    
    orch = Orchestrator(workspace=workspace, interactive=False, sandbox_backend="local")
    orch.lsp = None
    
    assert orch._is_single_file_workspace() is True
    
    # Mock evaluate to not interfere
    from agent.evaluation.evaluator import EvalResult
    orch.evaluator.evaluate = MagicMock(return_value=EvalResult(passed=False, ran_tests=False, summary=""))
    
    class MockChatResponse:
        def __init__(self):
            self.content = ""
            self.tool_calls = [{"function": {"name": "rename_symbol", "arguments": {"old": "foo", "new": "bar"}}}]
            self.raw = {}
            
    async def mock_chat(*args, **kwargs):
        return MockChatResponse()
        
    orch._chat = mock_chat
    orch._chat_stream = mock_chat
    orch.frame.messages = [{"role": "system", "content": "prime"}]
    
    from agent.fsm import AgentState
    orch.fsm.state = AgentState.EXECUTING
    orch.max_steps = 1
    await orch._execution_step()
    
    # Verify the last message is a tool result containing the block error message
    last_msg = orch.frame.messages[-1]
    assert last_msg["role"] == "tool"
    assert "not available in a single-file workspace" in last_msg["content"]


