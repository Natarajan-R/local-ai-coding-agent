import pytest
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
    assert ev._detect_command(workspace).startswith("PYTHONPATH=. python -m pytest -q")

    # REVERSED deliberately. This used to assert that a run starting with no tests
    # must ignore tests the model creates, so it could not grade its own homework.
    # The effect was the opposite of the intent: on a greenfield task detection
    # returned None and evaluation fell back to a compile check that passes, so the
    # run went green with nothing verified at all. Running a self-authored test is
    # strictly more informative; self-authorship is surfaced in the summary instead.
    ev_empty = Evaluator(local_sandbox, policy, initial_test_files=[])
    assert ev_empty._has_python_tests(workspace) is True
    assert ev_empty._detect_command(workspace).startswith("PYTHONPATH=. python -m pytest -q")

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
    await orch.coder_agent.execute()
    
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
    await orch.coder_agent.execute()
    
    # Verify the last message is a tool result containing the block error message
    last_msg = orch.frame.messages[-1]
    assert last_msg["role"] == "tool"
    assert "not available in a single-file workspace" in last_msg["content"]




def test_parse_pytest_tally_extracts_counts_and_failing_ids():
    """The eval-delta parser must surface passed/failed counts and failing test ids."""
    from agent.evaluation.evaluator import _parse_pytest_tally

    out = ("FAILED tests/test_a.py::test_one\nFAILED tests/test_b.py::test_two\n"
           "6 failed, 15 passed in 0.13s")
    passed, failed, skipped, failing = _parse_pytest_tally(out)
    assert (passed, failed, skipped) == (15, 6, 0)
    assert failing == ["tests/test_a.py::test_one", "tests/test_b.py::test_two"]

    # Collection/execution errors count as failures (nothing was verified).
    assert _parse_pytest_tally("2 errors in 0.20s")[1] == 2
    # All green.
    assert _parse_pytest_tally("..... 5 passed in 0.04s") == (5, 0, 0, [])
    # Skipped tests are captured (green-by-skipping must be visible).
    assert _parse_pytest_tally("9 passed, 3 skipped in 0.05s") == (9, 0, 3, [])
    # Non-pytest / empty output degrades to zeros, never raises.
    assert _parse_pytest_tally("") == (0, 0, 0, [])


def test_evaluate_populates_structured_tally(local_sandbox, policy, workspace):
    """evaluate() must fill EvalResult.tests_passed/failed/failing_tests from pytest output."""
    (workspace / "solution.py").write_text("def add(a, b):\n    return a - b\n")  # deliberate bug
    (workspace / "test_solution.py").write_text(
        "from solution import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n"
    )
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])
    result = ev.evaluate(workspace)
    assert result.passed is False
    assert result.tests_failed >= 1
    assert any("test_add" in t for t in result.failing_tests)


def test_parse_pytest_tally_ignores_spurious_failed_in_traceback():
    """The count must come from the summary line, not a stray '0 failed' in a traceback."""
    from agent.evaluation.evaluator import _parse_pytest_tally
    out = (
        "tests/test_r.py::test_render FAILED\n"
        "E   AssertionError: expected banner '0 failed items' but got '3 items'\n"
        "=========== short test summary info ===========\n"
        "FAILED tests/test_r.py::test_render\n"
        "FAILED tests/test_p.py::test_parse\n"
        "20 failed, 5 passed in 1.23s\n"
    )
    passed, failed, skipped, failing = _parse_pytest_tally(out)
    assert passed == 5
    assert failed == 20            # from summary line, NOT the spurious "0 failed"
    assert len(failing) == 2


def test_evaluate_surfaces_skipped_tests(local_sandbox, policy, workspace):
    """A green run that SKIPS required tests must surface it, not look like a clean pass."""
    (workspace / "solution.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_solution.py").write_text(
        "import pytest\n"
        "from solution import add\n\n\n"
        "def test_add():\n    assert add(2, 3) == 5\n\n\n"
        "@pytest.mark.skip(reason='Extension system not yet implemented')\n"
        "def test_feature():\n    assert False\n"
    )
    ev = Evaluator(local_sandbox, policy, initial_test_files=[])
    result = ev.evaluate(workspace)
    assert result.passed is False         # skip-to-green is unverified, not done
    assert result.tests_skipped == 1
    assert "SKIPPED" in result.summary    # surfaced loudly, not hidden as a clean green
