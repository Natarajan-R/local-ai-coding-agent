from agent.evaluation.evaluator import Evaluator


def test_detects_project_type_from_markers(local_sandbox, policy, workspace):
    ev = Evaluator(local_sandbox, policy)
    (workspace / "go.mod").write_text("module x\n")
    assert ev._detect_command(workspace) == "go test ./..."
    (workspace / "package.json").write_text("{}")
    # package.json is checked before go.mod
    assert ev._detect_command(workspace) == "npm test --silent"


def test_explicit_test_command_overrides_detection(local_sandbox, policy, workspace):
    (workspace / "go.mod").write_text("module x\n")
    ev = Evaluator(local_sandbox, policy, test_command="make check")
    assert ev._detect_command(workspace) == "make check"


def test_test_command_is_run(local_sandbox, policy, workspace):
    # A trivially-passing custom command should make evaluation pass.
    ev = Evaluator(local_sandbox, policy, test_command="true")
    result = ev.evaluate(workspace)
    assert result.passed and result.ran_tests


def test_evaluator_passes_when_tests_pass(local_sandbox, policy, workspace):
    (workspace / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (workspace / "test_calc.py").write_text(
        "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    )
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
    assert result.ran_tests


def test_evaluator_fails_when_tests_fail(local_sandbox, policy, workspace):
    (workspace / "test_bad.py").write_text("def test_bad():\n    assert 1 == 2\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert not result.passed
    assert result.ran_tests


def test_evaluator_syntax_check_without_tests(local_sandbox, policy, workspace):
    (workspace / "ok.py").write_text("x = 1\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
    assert not result.ran_tests


def test_evaluator_handles_test_file_with_no_tests(local_sandbox, policy, workspace):
    # A test file that only has module-level asserts collects zero tests
    # (pytest exit code 5); this must not be reported as a failure.
    (workspace / "mod.py").write_text("def f():\n    return 1\n")
    (workspace / "test_mod.py").write_text("import mod\n\nassert mod.f() == 1\n")
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed


def test_evaluator_syntax_check_fails_when_no_edits(local_sandbox, policy, workspace):
    import subprocess
    subprocess.run(["git", "init"], cwd=str(workspace), check=True)
    subprocess.run(["git", "config", "user.email", "agent@test.com"], cwd=str(workspace), check=True)
    subprocess.run(["git", "config", "user.name", "Agent Test"], cwd=str(workspace), check=True)
    
    (workspace / "ok.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "ok.py"], cwd=str(workspace), check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(workspace), check=True)
    
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert not result.passed
    assert "no edits/mutations made" in result.summary


def test_evaluator_syntax_check_passes_with_edits(local_sandbox, policy, workspace):
    import subprocess
    subprocess.run(["git", "init"], cwd=str(workspace), check=True)
    subprocess.run(["git", "config", "user.email", "agent@test.com"], cwd=str(workspace), check=True)
    subprocess.run(["git", "config", "user.name", "Agent Test"], cwd=str(workspace), check=True)
    
    (workspace / "ok.py").write_text("x = 1\n")
    subprocess.run(["git", "add", "ok.py"], cwd=str(workspace), check=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=str(workspace), check=True)
    
    # Make a change
    (workspace / "ok.py").write_text("x = 2\n")
    
    ev = Evaluator(local_sandbox, policy)
    result = ev.evaluate(workspace)
    assert result.passed
    assert "sources compile cleanly" in result.summary



# --- enhancements-03 #3: condense failed-test output so the traceback survives --
from agent.evaluation.evaluator import _condense_test_output

# A realistic pytest run: lots of passing noise, then the FAILURES section with the
# actual `E  assert ...` detail, then the short summary. The condenser must KEEP the
# assertion detail (which the crude "only FAILED/AssertionError/Error: lines" filter
# in the proposal would DROP) and drop the passing noise.
_PYTEST_OUTPUT = """\
============================= test session starts ==============================
collected 40 items

test_x.py ......................................F.                        [100%]

=================================== FAILURES ===================================
_________________________________ test_thirty _________________________________

    def test_thirty():
>       assert candidate(1) == 2
E       assert 1 == 2
E        +  where 1 = candidate(1)

test_x.py:57: AssertionError
=========================== short test summary info ============================
FAILED test_x.py::test_thirty - assert 1 == 2
========================= 1 failed, 39 passed in 0.42s =========================
"""


def test_condense_keeps_assertion_detail_and_drops_passing_noise():
    out = _condense_test_output(_PYTEST_OUTPUT)
    # the diagnostic that tells the model WHAT failed must survive:
    assert "assert 1 == 2" in out
    assert "where 1 = candidate(1)" in out
    assert "FAILED test_x.py::test_thirty" in out
    # the passing-noise header must be gone:
    assert "test session starts" not in out
    assert "collected 40 items" not in out


def test_condense_keeps_tail_when_capping():
    # a huge run: the summary lives at the END, so capping must keep the tail.
    big = "=================================== FAILURES ===================================\n"
    big += "\n".join(f"noise line {i}" for i in range(5000))
    big += "\nE       assert 1 == 2\nFAILED test_x.py::test_last - assert 1 == 2\n"
    out = _condense_test_output(big, limit=500)
    assert "assert 1 == 2" in out          # tail preserved
    assert "FAILED test_x.py::test_last" in out
    assert len(out) < 700                    # actually capped


def test_condense_falls_back_for_non_pytest_output():
    out = _condense_test_output("Traceback (most recent call last):\n  File x\nValueError: boom")
    assert "ValueError: boom" in out
